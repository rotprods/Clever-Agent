from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]


class CP02JsonSchemaGauntlet(unittest.TestCase):
    def test_unknown_major_is_rejected_by_json_schema(self) -> None:
        schemas = [json.loads(path.read_text()) for path in sorted((ROOT / "contracts/jsonschema").glob("*.schema.json"))]
        registry = Registry().with_resources((schema["$id"], Resource.from_contents(schema)) for schema in schemas)
        schema = json.loads((ROOT / "contracts/jsonschema/event.schema.json").read_text())
        fixture = json.loads((ROOT / "contracts/fixtures/event.json").read_text())
        poisoned = copy.deepcopy(fixture)
        poisoned["contractVersion"]["major"] = 2
        validator = Draft202012Validator(schema, registry=registry)
        self.assertTrue(list(validator.iter_errors(poisoned)))

    def test_unknown_security_fields_are_rejected(self) -> None:
        schemas = [json.loads(path.read_text()) for path in sorted((ROOT / "contracts/jsonschema").glob("*.schema.json"))]
        registry = Registry().with_resources((schema["$id"], Resource.from_contents(schema)) for schema in schemas)
        schema = json.loads((ROOT / "contracts/jsonschema/capability.schema.json").read_text())
        fixture = json.loads((ROOT / "contracts/fixtures/capability.json").read_text())
        poisoned = copy.deepcopy(fixture)
        poisoned["permissionOverride"] = "root"
        validator = Draft202012Validator(schema, registry=registry)
        self.assertTrue(list(validator.iter_errors(poisoned)))


if __name__ == "__main__":
    unittest.main()
