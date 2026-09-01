from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.parity.ledger import compile_obligations, summary, validate_records


class ParityLedgerTests(unittest.TestCase):
    def test_openjarvis_obligation_count_is_frozen(self) -> None:
        rows = compile_obligations("openjarvis")
        self.assertEqual(646, len(rows))
        self.assertTrue(all(row["parity_status"] == "UNVERIFIED" for row in rows))
        self.assertTrue(all(row["source_repo"] == "openjarvis" for row in rows))

    def test_global_denominator_is_frozen(self) -> None:
        result = summary()
        self.assertEqual(7565, result["total"])
        self.assertEqual(0, result["verified"])

    def test_verified_requires_full_evidence(self) -> None:
        cap = compile_obligations("openjarvis")[0]
        errors = validate_records([
            {
                "schema_version": 1,
                "capability_id": cap["capability_id"],
                "state": "VERIFIED",
                "upstream_commit": cap["source_commit"],
            }
        ])
        self.assertTrue(any("missing" in error for error in errors))

    def test_unknown_capability_fails_closed(self) -> None:
        errors = validate_records([
            {"schema_version": 1, "capability_id": "cap_ffffffffffffffffffffffff", "state": "MAPPED", "upstream_commit": "0" * 40}
        ])
        self.assertTrue(any("unknown capability_id" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
