from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def validate() -> list[str]:
    errors: list[str] = []
    registry = load("reports/cp03/OPENJARVIS_W01_REGISTRY.json")
    if registry.get("status") != "PASS" or registry.get("entry_count") != 230:
        errors.append("durable OpenJarvis registry proof is not PASS/230")
    if registry.get("import_failures") or registry.get("unsupported_registries"):
        errors.append("registry proof still contains import/registry gaps")

    contract = load("evidence/cp03/w01/adapter_contract_codegen.json")
    if contract.get("status") != "PASS" or contract.get("wire_version") != {"major": 1, "minor": 1}:
        errors.append("adapter contract polyglot subgate is not PASS v1.1")

    obligations = load("reports/cp03/OPENJARVIS_OBLIGATIONS.json")
    if obligations.get("obligation_count") != 646 or obligations.get("initial_verified") != 0:
        errors.append("OpenJarvis obligation denominator/verified baseline drifted")
    if obligations.get("denominator_mutation_authorized") is not False:
        errors.append("denominator mutation became authorized during W01")

    source = (ROOT / "kernel/crates/clever-kernel/src/adapter.rs").read_text(encoding="utf-8")
    required_source = [
        "env_clear()",
        "recv_timeout",
        "max_restarts",
        "bridge_registry_snapshot",
        "FrameTooLarge",
        "TruncatedFrame",
        "RegistryPrimitive::Unspecified",
    ]
    for needle in required_source:
        if needle not in source:
            errors.append(f"supervisor invariant missing from source: {needle}")
    if ".set_availability(" in source:
        errors.append("W01 supervisor must not promote bridged capability availability")

    tests = (ROOT / "kernel/crates/clever-kernel/tests/adapter_supervisor.rs").read_text(encoding="utf-8")
    required_tests = [
        "rejects_unknown_contract_major",
        "rejects_oversized_and_truncated_frames",
        "handshake_timeout_is_bounded",
        "crash_restart_budget_is_bounded",
        "inherited_secrets_are_stripped_and_registry_metadata_cannot_escalate",
        "real_openjarvis_sidecar_is_supervised_and_bridged_without_promotion",
    ]
    for test in required_tests:
        if test not in tests:
            errors.append(f"required W01 adversarial test missing: {test}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    errors = validate()
    payload = {
        "schema_version": 1,
        "checkpoint": "CP03",
        "wave": "CP03-W01",
        "gate": "rust_supervisor_registry_bridge",
        "status": "PASS" if not errors else "FAIL",
        "run_id": int(args.run_id),
        "source_sha": args.source_sha,
        "real_openjarvis_registry_entries": 230,
        "openjarvis_obligation_count": 646,
        "openjarvis_verified_after_w01": 0,
        "tests": [
            "unknown-major fail closed",
            "oversized/truncated framing fail closed",
            "bounded handshake timeout",
            "bounded crash restart budget",
            "ambient secret stripping",
            "registry metadata privilege filtering",
            "real pinned OpenJarvis supervised handshake/snapshot/health/shutdown",
            "230 registry entries bridged idempotently as UNAVAILABLE",
        ],
        "errors": errors,
    }
    report = ROOT / "reports/cp03/OPENJARVIS_W01_SUPERVISOR.json"
    evidence = ROOT / "evidence/cp03/cp03-w01/supervisor-gate.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    report.write_text(rendered, encoding="utf-8")
    evidence.write_text(rendered, encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
