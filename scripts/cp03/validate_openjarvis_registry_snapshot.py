from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_COMMIT = "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"
RESERVED = ("permission", "scope", "risk", "policy", "authorization", "authz")
REQUIRED_REGISTRIES = {"AgentRegistry", "EngineRegistry", "ToolRegistry"}


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("upstream_commit") != EXPECTED_COMMIT:
        errors.append("snapshot is not bound to the pinned OpenJarvis commit")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("registry snapshot contains no native entries")
        return errors
    if payload.get("entry_count") != len(entries):
        errors.append("entry_count does not match entries length")
    counts = payload.get("registry_counts", {})
    if not REQUIRED_REGISTRIES.issubset(counts):
        errors.append("required core registries were not reflected")
    if not all(int(counts.get(name, 0)) > 0 for name in REQUIRED_REGISTRIES):
        errors.append("agent/engine/tool registries must each expose at least one entry")

    observed: list[tuple[str, str, str]] = []
    for row in entries:
        primitive = str(row.get("primitive", ""))
        key = str(row.get("key", ""))
        implementation = str(row.get("implementation", ""))
        if not primitive or primitive.endswith("UNSPECIFIED") or not key or not implementation:
            errors.append(f"invalid registry entry: {row!r}")
            continue
        identity = (primitive, key, implementation)
        if identity in observed:
            errors.append(f"duplicate registry entry: {identity!r}")
        observed.append(identity)
        metadata = row.get("metadata", {})
        for metadata_key in metadata:
            normalized = str(metadata_key).casefold()
            if any(token in normalized for token in RESERVED):
                errors.append(f"security-reserved metadata leaked: {metadata_key}")
    if observed != sorted(observed):
        errors.append("registry entries are not deterministically ordered")

    source = (ROOT / "adapters/openjarvis/sidecar.py").read_text(encoding="utf-8")
    # Provider keys are discovered from upstream registries, not copied into Clever source.
    for _, key, _ in observed:
        if len(key) >= 4 and re.search(rf"[\"']{re.escape(key)}[\"']", source):
            errors.append(f"discovered provider/component key is hard-coded in sidecar: {key}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot")
    parser.add_argument("--report", default="reports/cp03/OPENJARVIS_W01_REGISTRY.json")
    args = parser.parse_args()
    payload = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    errors = validate(payload)
    report = {
        "schema_version": 1,
        "checkpoint": "CP03",
        "wave": "CP03-W01",
        "gate": "openjarvis_registry_discovery",
        "status": "PASS" if not errors else "FAIL",
        "upstream_commit": payload.get("upstream_commit"),
        "registry_class_count": payload.get("registry_class_count"),
        "entry_count": payload.get("entry_count"),
        "registry_counts": payload.get("registry_counts", {}),
        "import_failures": payload.get("import_failures", []),
        "unsupported_registries": payload.get("unsupported_registries", []),
        "errors": errors,
        "invariants": {
            "provider_keys_discovered_not_hardcoded": not any("hard-coded" in error for error in errors),
            "reserved_metadata_filtered": not any("reserved metadata" in error for error in errors),
            "exact_upstream_pin": payload.get("upstream_commit") == EXPECTED_COMMIT,
        },
    }
    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
