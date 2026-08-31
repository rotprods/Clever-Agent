from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rows.append(json.loads(raw))
    return rows


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _normalized_interface(surface: dict[str, Any]) -> dict[str, Any]:
    interface = surface.get("interface") or {}
    return {str(key): interface[key] for key in sorted(interface)}


def capability_from_surface(surface: dict[str, Any]) -> dict[str, Any]:
    surface_id = str(surface["surface_id"])
    identity = [surface["source_repo"], surface["source_commit"], surface_id]
    contract = {
        "family": surface["family"],
        "surface_kind": surface["surface_kind"],
        "interface": _normalized_interface(surface),
        "runtime_owner": surface["runtime_owner"],
    }
    # Candidate key intentionally excludes source repo/owner. It is only a signal
    # for later equivalence review; W04 never collapses rows on this key.
    equivalence_candidate = {
        "family": surface["family"],
        "surface_kind": surface["surface_kind"],
        "interface": _normalized_interface(surface),
        "normalized_name": str(surface["name"]).strip().lower(),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "capability_id": f"cap_{_stable_hash(identity)[:24]}",
        "source_surface_id": surface_id,
        "source_repo": surface["source_repo"],
        "source_commit": surface["source_commit"],
        "family": surface["family"],
        "surface_kind": surface["surface_kind"],
        "name": surface["name"],
        "runtime_owner": surface["runtime_owner"],
        "interface": _normalized_interface(surface),
        "source_path": surface["source_path"],
        "source_line": surface["line"],
        "evidence_strength": surface["evidence_strength"],
        "promotion_status": surface["promotion_status"],
        "parity_status": "UNVERIFIED",
        "equivalence_status": "UNPROVEN",
        "contract_fingerprint": _stable_hash(contract),
        "equivalence_candidate_key": _stable_hash(equivalence_candidate),
        "status": "IN_SCOPE",
    }


def compile_capabilities(surfaces: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [capability_from_surface(surface) for surface in surfaces]
    rows.sort(key=lambda row: row["capability_id"])
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")


def denominator_report(capabilities: list[dict[str, Any]]) -> dict[str, Any]:
    by_repo = Counter(row["source_repo"] for row in capabilities)
    by_family = Counter(row["family"] for row in capabilities)
    by_promotion = Counter(row["promotion_status"] for row in capabilities)
    by_strength = Counter(row["evidence_strength"] for row in capabilities)
    candidate_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in capabilities:
        candidate_groups[row["equivalence_candidate_key"]].append(
            {"capability_id": row["capability_id"], "source_repo": row["source_repo"], "name": row["name"]}
        )
    cross_repo_candidates: list[dict[str, Any]] = []
    for key, members in candidate_groups.items():
        repos = {member["source_repo"] for member in members}
        if len(repos) > 1:
            cross_repo_candidates.append({"equivalence_candidate_key": key, "repositories": sorted(repos), "members": sorted(members, key=lambda item: item["capability_id"])})
    return {
        "schema_version": 1,
        "phase": "I01-W04",
        "denominator": len(capabilities),
        "verified": 0,
        "parity_ratio": 0.0 if capabilities else None,
        "denominator_status": "GENERATED_UNVERIFIED",
        "by_repo": dict(sorted(by_repo.items())),
        "by_family": dict(sorted(by_family.items())),
        "by_promotion_status": dict(sorted(by_promotion.items())),
        "by_evidence_strength": dict(sorted(by_strength.items())),
        "cross_repo_equivalence_candidates": sorted(cross_repo_candidates, key=lambda item: item["equivalence_candidate_key"]),
        "rules": {
            "one_surface_maps_to_one_capability": True,
            "cross_repo_auto_dedupe": False,
            "name_only_equivalence_forbidden": True,
            "candidate_equivalence_does_not_change_denominator": True,
            "all_capabilities_unverified_at_cp01": True
        }
    }


def gauntlet(surfaces: list[dict[str, Any]], capabilities: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    source_surface_ids = [row["surface_id"] for row in surfaces]
    mapped_surface_ids = [row["source_surface_id"] for row in capabilities]
    capability_ids = [row["capability_id"] for row in capabilities]
    if len(capability_ids) != len(set(capability_ids)):
        errors.append("capability_id collision")
    if len(mapped_surface_ids) != len(set(mapped_surface_ids)):
        errors.append("a surface maps to multiple capabilities")
    if set(source_surface_ids) != set(mapped_surface_ids):
        missing = sorted(set(source_surface_ids) - set(mapped_surface_ids))
        extra = sorted(set(mapped_surface_ids) - set(source_surface_ids))
        errors.append(f"surface mapping mismatch missing={len(missing)} extra={len(extra)}")
    if len(surfaces) != len(capabilities):
        errors.append(f"denominator changed by normalization surfaces={len(surfaces)} capabilities={len(capabilities)}")
    for row in capabilities:
        if row["parity_status"] != "UNVERIFIED":
            errors.append(f"CP01 capability marked verified: {row['capability_id']}")
        if row["equivalence_status"] != "UNPROVEN":
            errors.append(f"equivalence asserted without proof: {row['capability_id']}")
    return {
        "schema_version": 1,
        "phase": "I01-W04",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "surface_count": len(surfaces),
        "capability_count": len(capabilities),
        "invariants": {
            "no_capability_loss": len(surfaces) == len(capabilities),
            "no_cross_repo_auto_dedupe": True,
            "no_manual_parity_percentage": True,
            "all_capabilities_source_backed": set(source_surface_ids) == set(mapped_surface_ids),
        },
    }


def run_w04(
    surfaces_path: str | Path = "inventory/surfaces/all.jsonl",
    ledger_path: str | Path = "ledgers/CAPABILITY_LEDGER.jsonl",
    denominator_path: str | Path = "reports/cp01/capability_denominator.json",
    gauntlet_path: str | Path = "evidence/cp01/gauntlet/w04_denominator.json",
) -> dict[str, Any]:
    surfaces = read_jsonl(surfaces_path)
    if not surfaces:
        raise RuntimeError("W04 refuses an empty W03 surface ledger")
    capabilities = compile_capabilities(surfaces)
    report = denominator_report(capabilities)
    check = gauntlet(surfaces, capabilities)
    if check["status"] != "PASS":
        raise RuntimeError("W04 gauntlet failed: " + "; ".join(check["errors"]))
    _write_jsonl(Path(ledger_path), capabilities)
    denominator = Path(denominator_path)
    denominator.parent.mkdir(parents=True, exist_ok=True)
    denominator.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    gauntlet_output = Path(gauntlet_path)
    gauntlet_output.parent.mkdir(parents=True, exist_ok=True)
    gauntlet_output.write_text(json.dumps(check, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"capabilities": capabilities, "report": report, "gauntlet": check}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile the conservative CP01 capability denominator")
    parser.add_argument("--surfaces", default="inventory/surfaces/all.jsonl")
    parser.add_argument("--ledger", default="ledgers/CAPABILITY_LEDGER.jsonl")
    args = parser.parse_args()
    result = run_w04(args.surfaces, args.ledger)
    print(json.dumps(result["report"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
