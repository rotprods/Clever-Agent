from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import scripts.agentic.advance as advance


class ClaimReleaseTests(unittest.TestCase):
    def test_active_claim_is_released_and_no_longer_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ledgers/CLAIM_LEDGER.ndjson"
            ledger.parent.mkdir(parents=True)
            ledger.write_text(json.dumps({
                "claim_id": "CLAIM-CP03-W00-001",
                "wave_id": "CP03-W00",
                "status": "ACTIVE",
            }) + "\n", encoding="utf-8")
            with patch.object(advance, "ROOT", root):
                released = advance.release_claims_for_wave("CP03-W00", "EVID-0013", "2026-09-01")
                self.assertEqual(["CLAIM-CP03-W00-001"], released)
                self.assertEqual([], advance.active_claim_ids_for_wave("CP03-W00"))
            rows = [json.loads(line) for line in ledger.read_text().splitlines()]
            self.assertEqual("RELEASED", rows[-1]["status"])
            self.assertEqual("EVID-0013", rows[-1]["release_evidence_id"])

    def test_missing_active_claim_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ledgers").mkdir(parents=True)
            with patch.object(advance, "ROOT", root):
                with self.assertRaisesRegex(RuntimeError, "no ACTIVE claim"):
                    advance.release_claims_for_wave("CP03-W00", "EVID-0013", "2026-09-01")


if __name__ == "__main__":
    unittest.main()
