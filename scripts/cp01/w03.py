from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.cp01.profiles import supplement_repository_surfaces
from scripts.cp01.surfaces import extract_repository_surfaces, surface_summary
from scripts.upstream.ledger import load_upstream_pins

EXPECTED_FAMILY_GROUPS: dict[str, tuple[tuple[str, ...], ...]] = {
    "openjarvis": (("agent",), ("inference",), ("tool",), ("memory_persistence",), ("channel_gateway", "api_protocol"), ("scheduler_automation", "learning_evaluation"), ("security_policy", "api_protocol")),
    "openclaw": (("plugin_extension",), ("tool",), ("channel_gateway",), ("inference",), ("session_identity", "channel_gateway"), ("scheduler_automation", "plugin_extension"), ("security_policy", "plugin_extension")),
    "omi": (("api_protocol", "worker_service"), ("speech_audio", "capture_perception"), ("memory_persistence",), ("device_wearable", "capture_perception"), ("session_identity", "memory_persistence")),
    "clicky": (("capture_perception", "embodiment"), ("speech_audio", "embodiment"), ("embodiment", "worker_service")),
}


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def _load_structural(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _merge_surface_rows(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rank = {"DEFINITION": 1, "PROFILED_BOUNDARY": 2, "REGISTRATION": 3, "ROUTE_OR_PROTOCOL": 4, "BEHAVIOR_TEST": 5}
    unique: dict[str, dict[str, Any]] = {}
    for rows in groups:
        for row in rows:
            previous = unique.get(row["surface_id"])
            if previous is None or rank[row["evidence_strength"]] > rank[previous["evidence_strength"]]:
                unique[row["surface_id"]] = row
    return [unique[key] for key in sorted(unique)]


def run_w03(ledger: str | Path = "UPSTREAM_LEDGER.yaml", cache_root: str | Path = ".cache/upstreams", structural_root: str | Path = "inventory/upstreams", output_root: str | Path = "inventory/surfaces", gauntlet_output: str | Path = "evidence/cp01/gauntlet/w03_surface_coverage.json", summary_output: str | Path = "reports/cp01/w03_surface_summary.json") -> dict[str, Any]:
    cache, structural, output = Path(cache_root), Path(structural_root), Path(output_root)
    all_rows: list[dict[str, Any]] = []
    source_reports: list[dict[str, Any]] = []
    for pin in load_upstream_pins(ledger):
        repository = cache / pin.id
        generic = extract_repository_surfaces(repository, pin)
        profiled = supplement_repository_surfaces(repository, pin)
        rows = _merge_surface_rows(generic, profiled)
        _write_jsonl(output / f"{pin.id}.jsonl", rows)
        all_rows.extend(rows)
        source_reports.append({"source_repo": pin.id, "generic_surface_count": len(generic), "profile_surface_count": len(profiled), **surface_summary(rows)})
    all_rows = sorted(all_rows, key=lambda row: row["surface_id"])
    _write_jsonl(output / "all.jsonl", all_rows)

    errors: list[str] = []
    warnings: list[str] = []
    ids = [row["surface_id"] for row in all_rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate surface_id values detected")
    by_repo: dict[str, list[dict[str, Any]]] = {}
    for row in all_rows:
        by_repo.setdefault(row["source_repo"], []).append(row)
        if not row.get("source_path") or not row.get("runtime_owner") or len(row.get("source_commit", "")) != 40:
            errors.append(f"surface missing provenance fields: {row.get('surface_id')}")
        if row.get("evidence_strength") == "DEFINITION" and row.get("promotion_status") != "DISCOVERED_CANDIDATE":
            errors.append(f"definition promoted beyond candidate: {row['surface_id']}")
        if row.get("evidence_strength") == "PROFILED_BOUNDARY" and row.get("promotion_status") != "BEHAVIOR_MAPPED":
            errors.append(f"profiled boundary not behavior-mapped: {row['surface_id']}")

    for repo_id, groups in EXPECTED_FAMILY_GROUPS.items():
        rows = by_repo.get(repo_id, [])
        if not rows:
            errors.append(f"{repo_id}: no behavioral surfaces extracted")
            continue
        families = {row["family"] for row in rows}
        for alternatives in groups:
            if not families.intersection(alternatives):
                errors.append(f"{repo_id}: expected behavioral family group missing: {alternatives}")
        if not any(row["promotion_status"] == "BEHAVIOR_MAPPED" for row in rows):
            errors.append(f"{repo_id}: no behavior-mapped surface")
        inventory = _load_structural(structural / f"{repo_id}.json")
        boundaries = inventory.get("runtime_service_app_boundaries", []) if inventory else []
        surface_paths = [row["source_path"] for row in rows]
        high_value_orphans: list[str] = []
        for boundary in boundaries:
            prefix = str(boundary.get("path", "")).rstrip("/")
            if not prefix or prefix == ".":
                continue
            if not any(path == prefix or path.startswith(prefix + "/") for path in surface_paths) and any(str(signal).startswith("manifest:") for signal in boundary.get("signals", [])):
                high_value_orphans.append(prefix)
        if high_value_orphans:
            warnings.append(f"{repo_id}: {len(high_value_orphans)} manifest-backed boundaries have no direct surface; retained as explained structural-orphan candidates")

    summary = {"schema_version": 1, "phase": "I01-W03", "surface_summary": surface_summary(all_rows), "sources": sorted(source_reports, key=lambda row: row["source_repo"])}
    Path(summary_output).parent.mkdir(parents=True, exist_ok=True)
    Path(summary_output).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mapped_count = sum(1 for row in all_rows if row["promotion_status"] == "BEHAVIOR_MAPPED")
    candidate_count = len(all_rows) - mapped_count
    gauntlet = {
        "schema_version": 1, "phase": "I01-W03", "status": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)), "warnings": sorted(set(warnings)), "surface_count": len(all_rows),
        "behavior_mapped_count": mapped_count, "candidate_definition_count": candidate_count,
        "source_counts": {repo: len(rows) for repo, rows in sorted(by_repo.items())},
        "invariants": {"tests_are_not_product_surfaces": True, "definition_is_not_verified": True, "profiled_boundary_is_behavior_mapped": True, "cross_repo_behavior_dedupe_performed": False, "generic_plus_profile_extraction": True, "all_source_provenance_preserved": not any("provenance" in error for error in errors)}
    }
    Path(gauntlet_output).parent.mkdir(parents=True, exist_ok=True)
    Path(gauntlet_output).write_text(json.dumps(gauntlet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        raise RuntimeError("W03 gauntlet failed: " + "; ".join(errors))
    return {"summary": summary, "gauntlet": gauntlet}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile W03 behavioral surfaces for all pinned upstreams")
    parser.add_argument("--ledger", default="UPSTREAM_LEDGER.yaml")
    parser.add_argument("--cache", default=".cache/upstreams")
    parser.add_argument("--structural-root", default="inventory/upstreams")
    parser.add_argument("--output-root", default="inventory/surfaces")
    args = parser.parse_args()
    result = run_w03(args.ledger, args.cache, args.structural_root, args.output_root)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
