from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.contracts.validate_manifest import validate

ROOT = Path(__file__).resolve().parents[1]


class CP02ContractTests(unittest.TestCase):
    def test_manifest_and_security_invariants(self) -> None:
        self.assertEqual(validate(), [])

    def test_contract_ids_and_fixtures_are_unique(self) -> None:
        manifest = json.loads((ROOT / "contracts/contract_manifest.json").read_text(encoding="utf-8"))
        ids = [row["id"] for row in manifest["contracts"]]
        fixtures = [row["fixture"] for row in manifest["contracts"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(fixtures), len(set(fixtures)))
        self.assertGreaterEqual(len(ids), 10)

    def test_extension_metadata_is_not_permission_channel(self) -> None:
        schema = json.loads((ROOT / "contracts/jsonschema/capability.schema.json").read_text(encoding="utf-8"))
        extension = schema["properties"]["extensionMetadata"]
        self.assertEqual(extension["additionalProperties"], {"type": "string"})
        self.assertIn("permissions", schema["properties"])

    def test_all_fixtures_use_major_v1(self) -> None:
        for path in (ROOT / "contracts/fixtures").glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["contractVersion"]["major"], 1, path.name)


if __name__ == "__main__":
    unittest.main()
