from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    schemas = []
    for path in sorted((ROOT / "contracts/jsonschema").glob("*.schema.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        schemas.append(payload)
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    manifest = json.loads((ROOT / "contracts/contract_manifest.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    for row in manifest["contracts"]:
        schema = json.loads((ROOT / row["json_schema"]).read_text(encoding="utf-8"))
        fixture = json.loads((ROOT / row["fixture"]).read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())
        problems = sorted(validator.iter_errors(fixture), key=lambda exc: list(exc.path))
        for problem in problems:
            errors.append(f"{row['id']}: {list(problem.path)}: {problem.message}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {len(manifest['contracts'])} canonical JSON fixtures validate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
