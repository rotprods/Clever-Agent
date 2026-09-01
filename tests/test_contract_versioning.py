from __future__ import annotations

import unittest

from scripts.contracts.versioning import UnsupportedContractVersion, require_supported_major, require_supported_mapping


class ContractVersioningTests(unittest.TestCase):
    def test_accepts_major_v1(self) -> None:
        require_supported_major(1)
        require_supported_mapping({"contractVersion":{"major":1,"minor":99}})

    def test_rejects_unknown_major(self) -> None:
        for major in (0, 2, 999):
            with self.assertRaises(UnsupportedContractVersion):
                require_supported_major(major)

    def test_rejects_missing_or_malformed_version(self) -> None:
        for payload in ({}, {"contractVersion":None}, {"contractVersion":{}}, {"contractVersion":{"major":"1"}}):
            with self.assertRaises(UnsupportedContractVersion):
                require_supported_mapping(payload)


if __name__ == "__main__":
    unittest.main()
