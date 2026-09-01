from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PROTO_ROOT = ROOT / "contracts/proto"
MANIFEST = ROOT / "contracts/contract_manifest.json"


def validate() -> list[str]:
    errors: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids: set[str] = set()
    for row in manifest.get("contracts", []):
        contract_id = row.get("id")
        if not contract_id or contract_id in ids:
            errors.append(f"invalid/duplicate contract id: {contract_id!r}")
            continue
        ids.add(contract_id)
        proto = PROTO_ROOT / row["proto"]
        schema = ROOT / row["json_schema"]
        fixture = ROOT / row["fixture"]
        for label, path in (("proto", proto), ("schema", schema), ("fixture", fixture)):
            if not path.is_file():
                errors.append(f"{contract_id}: missing {label}: {path.relative_to(ROOT)}")
        if proto.is_file():
            text = proto.read_text(encoding="utf-8")
            if 'syntax = "proto3";' not in text or "package clever.v1;" not in text:
                errors.append(f"{contract_id}: proto lacks canonical syntax/package")
            message_name = str(row["message"]).rsplit(".", 1)[-1]
            if re.search(rf"\bmessage\s+{re.escape(message_name)}\b", text) is None:
                errors.append(f"{contract_id}: manifest message missing from proto: {message_name}")
        if schema.is_file():
            payload = json.loads(schema.read_text(encoding="utf-8"))
            if payload.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                errors.append(f"{contract_id}: unexpected JSON Schema dialect")
            required = set(payload.get("required", []))
            if "contractVersion" not in required:
                errors.append(f"{contract_id}: contractVersion must be required")
    common = json.loads((ROOT / "contracts/jsonschema/common.schema.json").read_text(encoding="utf-8"))
    major_schema = common.get("$defs", {}).get("contractVersion", {}).get("properties", {}).get("major", {})
    if major_schema.get("const") != 1:
        errors.append("contract major version schema must fail closed to v1 exactly")
    action = json.loads((ROOT / "contracts/jsonschema/action-intent.schema.json").read_text(encoding="utf-8"))
    if not {"idempotencyKey", "policyDecisionId", "sideEffectClass"}.issubset(action.get("required", [])):
        errors.append("ActionIntent must require idempotency/policy/side-effect semantics")
    memory = json.loads((ROOT / "contracts/jsonschema/memory.schema.json").read_text(encoding="utf-8"))
    if not {"accessScope", "retention", "nativeOwnerRuntime"}.issubset(memory.get("required", [])):
        errors.append("MemoryRecord must require scope/retention/native ownership")
    perception = json.loads((ROOT / "contracts/jsonschema/perception.schema.json").read_text(encoding="utf-8"))
    if not {"consentActive", "permissionGrantId"}.issubset(perception.get("required", [])):
        errors.append("PerceptionObservation must carry consent/permission state")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: CP02 contract manifest and security invariants are structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
