from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PIN = "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"


class AdapterContractTests(unittest.TestCase):
    def test_manifest_adds_adapter_as_minor_v1_extension(self) -> None:
        manifest = json.loads((ROOT / "contracts/contract_manifest.json").read_text())
        self.assertEqual({"major": 1, "minor": 1}, manifest["wire_version"])
        contracts = {row["id"]: row for row in manifest["contracts"]}
        self.assertIn("adapter_transport", contracts)
        self.assertEqual("clever.v1.AdapterFrame", contracts["adapter_transport"]["message"])

    def test_adapter_fixture_is_pinned_and_deadline_bounded(self) -> None:
        fixture = json.loads((ROOT / "contracts/fixtures/adapter.json").read_text())
        self.assertEqual(PIN, fixture["hello"]["upstreamCommit"])
        self.assertEqual(1, fixture["contractVersion"]["major"])
        self.assertEqual(1, fixture["contractVersion"]["minor"])
        self.assertEqual("4194304", fixture["hello"]["maxFrameBytes"])
        self.assertNotEqual(fixture["sentAt"], fixture["deadlineAt"])

    def test_transport_proto_has_control_messages_but_no_policy_grants(self) -> None:
        text = (ROOT / "contracts/proto/clever/v1/adapter.proto").read_text()
        for token in ("AdapterHello", "RegistrySnapshot", "AdapterCancel", "AdapterShutdown", "AdapterBusy", "AdapterError"):
            self.assertIn(token, text)
        lowered = text.lower()
        self.assertNotIn("policy_grant", lowered)
        self.assertNotIn("risk_class", lowered)
        self.assertNotIn("verified_parity", lowered)


if __name__ == "__main__":
    unittest.main()
