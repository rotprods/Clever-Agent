from __future__ import annotations

import unittest

from scripts.cp03.obligations import EXPECTED, PIN, compile_summary


class OpenJarvisObligationsTests(unittest.TestCase):
    def test_obligations_are_exact_and_pinned(self) -> None:
        result = compile_summary()
        self.assertEqual(EXPECTED, result["obligation_count"])
        self.assertEqual(PIN, result["source_commit"])
        self.assertEqual(0, result["initial_verified"])
        self.assertFalse(result["denominator_mutation_authorized"])

    def test_candidates_stay_outside_denominator(self) -> None:
        result = compile_summary()
        self.assertEqual(2188, result["candidate_definition_count"])
        self.assertEqual(646, result["obligation_count"])


if __name__ == "__main__":
    unittest.main()
