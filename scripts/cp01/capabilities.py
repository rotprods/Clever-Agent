from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [json.loads(raw) for raw in Path(path).read_text(encoding="utf-8").splitlines() if raw.strip()]


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _normalized_interface(surface: dict[str, Any]) -> dict[str, Any]:
    interface = surface.get("interface") or {}
    return {str(key): interface[key] for key in sorted(interface)}


def _eligible(surface: dict[str, Any]) -> bool:
    return surface.get("promotion_status") == "BEHAVIOR_MAPPED" and surface.get("evidence_strength") in {"PROFILED_BOUNDARY", "REGISTRATION", "ROUTE_OR_PROTOCOL", "BEHAVIOR_TEST"}


def capability_from_surface(surface: dict[str, Any]) -> dict[str, Any]:
    if not _eligible(surface):
        raise ValueError(f"candidate-only surface is not denominator eligible: {surface.get('surface_id')}")
    surface_id = str(surface["surface_id"])
    identity = [surface["source_repo"], surface["source_commit"], surface_id]
    contract = {"family": surface["family"], "surface_kind": surface["surface_kind"], "interface": _normalized_interface(surface), "runtime_owner": surface["runtime_owner"]}
    equivalence_candidate = {"family": surface["family"], "surface_kind": surface["surface_kind"], "interface": _normalized_interface(surface), "normalized_name": str(surface["name"]).strip().lower()}
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
        "promotion_status": "BEHAVIOR_MAPPED",
        "eligibility_basis": surface["evidence_strength"],
        "parity_status": "UNVERIFIED",
        "equivalence_status": "UNPROVEN",
        "contract_fingerprint": _stable_hash(contract),
        "equivalence_candidate_key": _stable_hash(equivalence_candidate),
        "status": "IN_SCOPE",
    }


def compile_capabilities(surfaces: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [capability_from_surface(surface) for surface in surfaces if _eligible(surface)]
    rows.sort(key=lambda row: row["capability_id"])
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")


def denominator_report(capabilities: list[dict[str, Any]], source_surface_count: int = 0, deferred_candidate_count: int = 0) -> dict[str, Any]:
    by_repo = Counter(row["source_repo"] for row in capabilities)
    by_family = Counter(row["family"] for row in capabilities)
    by_promotion = Counter(row["promotion_status"] for row in capabilities)
    by_strength = Counter(row["evidence_strength"] for row in capabilities)
    candidate_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in capabilities:
        candidate_groups[row["equivalence_candidate_key"]].append({"capability_id": row["capability_id"], "source_repo": row["source_repo"], "name": row["name"]})
    cross_repo_candidates: list[dict[str, Any]] = []
    for key, members in candidate_groups.items():
        repos = {member["source_repo"] for member in members}
        if len(repos) > 1:
            cross_repo_candidates.append({"equivalence_candidate_key": key, "repositories": sorted(repos), "members": sorted(members, key=lambda item: item["capability_id"])})
    return {
        "schema_version": 1,
        "phase": "I01-W04",
        "source_surface_count": source_surface_count or len(capabilities) + deferred_candidate_count,
        "denominator_eligible_surface_count": len(capabilities),
        "deferred_candidate_surface_count": deferred_candidate_count,
        "denominator": len(capabilities),
        "verified": 0,
        "parity_ratio": 0.0 if capabilities else None,
        "denominator_status": "GENERATED_UNVERIFIED",
        "by_repo": dict(sorted(by_repo.items())),
        "by_family": dict(sorted(by_family.items())),
        "by_promotion_status": dict(sorted(by_promotion.items())),
        "by_evidence_strength": dict(sorted(by_strength.items())),
        "cross_repo_equivalence_candidates": sorted(cross_repo_candidates, key=lambda item: item["equivalence_candidate_key"]),
        "rules": {"candidate_definition_is_not_capability": True, "cross_repo_auto_dedupe": False, "name_only_equivalence_forbidden": True, "candidate_equivalence_does_not_change_denominator": True, "all_capabilities_unverified_at_cp01": True}
    }


def gauntlet(surfaces: list[dict[str, Any]], capabilities: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    all_ids = {row["surface_id"] for row in surfaces}
    eligible_ids = {row["surface_id"] for row in surfaces if _eligible(row)}
    deferred_ids = all_ids - eligible_ids
    mapped_ids = [row["source_surface_id"] for row in capabilities]
    capability_ids = [row["capability_id"] for row in capabilities]
    if len(capability_ids) != len(set(capability_ids)):
        errors.append("capability_id collision")
    if len(mapped_ids) != len(set(mapped_ids)):
        errors.append("a denominator-eligible surface maps to multiple capabilities")
    if set(mapped_ids) != eligible_ids:
        errors.append(f"eligible surface mapping mismatch missing={len(eligible_ids - set(mapped_ids))} extra={len(set(mapped_ids) - eligible_ids)}")
    if len(capabilities) != len(eligible_ids):
        errors.append("denominator changed eligible surface count")
    if eligible_ids & deferred_ids or eligible_ids | deferred_ids != all_ids:
        errors.append("surface eligibility partition invalid")
    for row in capabilities:
        if row["parity_status"] != "UNVERIFIED" or row["equivalence_status"] != "UNPROVEN":
            errors.append(f"premature verification/equivalence: {row['capability_id']}")
        if row["promotion_status"] != "BEHAVIOR_MAPPED":
            errors.append(f"candidate surface leaked into denominator: {row['capability_id']}")
    return {
        "schema_version": 1,
        "phase": "I01-W04",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "source_surface_count": len(surfaces),
        "eligible_surface_count": len(eligible_ids),
        "deferred_candidate_surface_count": len(deferred_ids),
        "capability_count": len(capabilities),
        "invariants": {"all_surfaces_accounted_for": len(all_ids) == len(eligible_ids) + len(deferred_ids), "no_eligible_capability_loss": len(eligible_ids) == len(capabilities), "candidate_definition_is_not_capability": True, "no_cross_repo_auto_dedupe": True, "no_manual_parity_percentage": True}
    }


def run_w04(surfaces_path: str | Path = "inventory/surfaces/all.jsonl", ledger_path: str | Path = "ledgers/CAPABILITY_LEDGER.jsonl", denominator_path: str | Path = "reports/cp01/capability_denominator.json", gauntlet_path: str | Path = "evidence/cp01/gauntlet/w04_denominator.json") -> dict[str, Any]:
    surfaces = read_jsonl(surfaces_path)
    if not surfaces:
        raise RuntimeError("W04 refuses an empty W03 surface ledger")
    capabilities = compile_capabilities(surfaces)
    deferred = sum(1 for row in surfaces if not _eligible(row))
    report = denominator_report(capabilities, len(surfaces), deferred)
    check = gauntlet(surfaces, capabilities)
    if check["status"] != "PASS":
        raise RuntimeError("W04 gauntlet failed: " + "; ".join(check["errors"]))
    _write_jsonl(Path(ledger_path), capabilities)
    Path(denominator_path).parent.mkdir(parents=True, exist_ok=True)
    Path(denominator_path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path(gauntlet_path).parent.mkdir(parents=True, exist_ok=True)
    Path(gauntlet_path).write_text(json.dumps(check, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
