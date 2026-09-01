from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_EVIDENCE = {"EVID-0007", "EVID-0008", "EVID-0009", "EVID-0010", "EVID-0011"}
EXPECTED_DENOMINATOR = 7565
EXPECTED_OPENJARVIS = 646


def _json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _jsonl(path: str) -> list[dict[str, Any]]:
    return [json.loads(raw) for raw in (ROOT / path).read_text(encoding="utf-8").splitlines() if raw.strip()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate(source_sha: str = "") -> dict[str, Any]:
    errors: list[str] = []
    goal = _json("GOAL_STATE.json")
    execution = _json("EXECUTION_STATE.json")
    iteration = _json("iterations/02/STATE.json")
    registry = _json("CHECKPOINT_REGISTRY.json")
    denominator = _json("reports/cp01/capability_denominator.json")
    gauntlet = _json("evidence/cp02/gauntlet/cp02_gauntlet.json")
    manifest = _json("contracts/generated_manifest.json")
    evidence = {str(row.get("evidence_id")): row for row in _jsonl("ledgers/EVIDENCE_LEDGER.ndjson")}
    capabilities = _jsonl("ledgers/CAPABILITY_LEDGER.jsonl")

    if goal.get("active_checkpoint") != "CP02" or goal.get("active_iteration") != "I02":
        errors.append("goal is not at CP02/I02")
    if execution.get("next_wave") != "CP02-W06" or execution.get("active_subcheckpoint") != "I02.6":
        errors.append("execution frontier is not CP02-W06/I02.6")
    if iteration.get("next_wave") != "CP02-W06":
        errors.append("iteration frontier is not CP02-W06")
    missing_sub = [f"I02.{index}" for index in range(0, 6) if f"I02.{index}" not in iteration.get("completed_subcheckpoints", [])]
    if missing_sub:
        errors.append(f"missing completed CP02 subcheckpoints: {missing_sub}")

    checkpoint_map = {row["id"]: row for row in registry["checkpoints"]}
    if checkpoint_map["CP02"]["status"] != "IN_PROGRESS" or checkpoint_map["CP03"]["status"] != "PENDING":
        errors.append("checkpoint registry is not at CP02 -> CP03 boundary")

    if denominator.get("denominator") != EXPECTED_DENOMINATOR:
        errors.append("CP01 denominator drift")
    if denominator.get("verified") != 0:
        errors.append("CP02 must not invent VERIFIED upstream parity")
    if denominator.get("by_repo", {}).get("openjarvis") != EXPECTED_OPENJARVIS:
        errors.append("OpenJarvis obligation count drift")
    if len(capabilities) != EXPECTED_DENOMINATOR:
        errors.append(f"capability ledger row count drift: {len(capabilities)}")
    if len({row.get("capability_id") for row in capabilities}) != EXPECTED_DENOMINATOR:
        errors.append("capability ledger ID collision")
    if any(row.get("parity_status") != "UNVERIFIED" for row in capabilities):
        errors.append("CP01 denominator ledger was mutated with parity claims")

    missing_evidence = sorted(eid for eid in EXPECTED_EVIDENCE if evidence.get(eid, {}).get("status") != "VERIFIED")
    if missing_evidence:
        errors.append(f"missing CP02 evidence gates: {missing_evidence}")
    if gauntlet.get("status") != "PASS" or gauntlet.get("check_count") != 16:
        errors.append("CP02 gauntlet is not a 16-check PASS")
    if any(row.get("status") != "PASS" for row in gauntlet.get("checks", [])):
        errors.append("CP02 gauntlet contains a failed check")
    generated_paths = [str(row.get("path", "")) for row in manifest.get("files", [])]
    if any("__pycache__" in path or path.endswith(".pyc") for path in generated_paths):
        errors.append("generated manifest contains transient Python cache")

    capability_path = ROOT / "ledgers/CAPABILITY_LEDGER.jsonl"
    payload = {
        "schema_version": 1,
        "checkpoint": "CP02",
        "source_sha": source_sha,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "denominator": EXPECTED_DENOMINATOR,
        "verified": 0,
        "openjarvis_obligations": EXPECTED_OPENJARVIS,
        "capability_ledger_sha256": _sha256(capability_path),
        "generated_manifest_sha256": _sha256(ROOT / "contracts/generated_manifest.json"),
        "gauntlet_check_count": gauntlet.get("check_count"),
        "required_evidence": sorted(EXPECTED_EVIDENCE),
        "invariants": {
            "denominator_immutable": True,
            "native_upstream_deletion_authorized": False,
            "migration_authorized": False,
            "cp03_requires_release_transition": True,
        },
    }
    return payload


def materialize(source_sha: str, run_id: str) -> dict[str, Any]:
    payload = evaluate(source_sha)
    payload["github_actions_run_id"] = int(run_id) if str(run_id).isdigit() else run_id
    out = ROOT / "evidence/cp02/release/CP02_RELEASE.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = ROOT / "reports/cp02/CP02_RELEASE_REPORT.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# CP02 Release Report\n\n"
        f"- Status: `{payload['status']}`\n"
        f"- Source SHA: `{source_sha}`\n"
        f"- Capability denominator: `{payload['denominator']}`\n"
        f"- Clever VERIFIED upstream parity: `{payload['verified']}`\n"
        f"- OpenJarvis obligations for CP03: `{payload['openjarvis_obligations']}`\n"
        f"- CP02 evidence gates: `{', '.join(payload['required_evidence'])}`\n"
        f"- Security/recovery checks: `{payload['gauntlet_check_count']}`\n\n"
        "CP02 defines and proves the cross-runtime contract/kernel scaffold. It does not claim upstream adapter parity.\n",
        encoding="utf-8",
    )
    if payload["status"] != "PASS":
        raise RuntimeError("CP02 release evaluation failed: " + "; ".join(payload["errors"]))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    payload = materialize(args.source_sha, args.run_id)
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
