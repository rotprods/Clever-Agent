from __future__ import annotations

import unittest

from scripts.context.validate_next_actions import validate_payload


def task(task_id: str, status: str, deps: list[str]) -> dict[str, object]:
    return {
        "id": task_id,
        "priority": "P0",
        "wave": "W",
        "status": status,
        "depends_on": deps,
        "owner_role": "builder",
        "objective": "fixture",
        "outputs": ["out"],
        "gates": ["pass"],
    }


class NextActionsTests(unittest.TestCase):
    def test_valid_dag(self) -> None:
        payload = {
            "frontier_wave": "W",
            "first_executable_task": "A",
            "tasks": [task("A", "READY", []), task("B", "BLOCKED", ["A"])],
        }
        self.assertEqual(validate_payload(payload, expected_frontier="W"), [])

    def test_missing_dependency_is_rejected(self) -> None:
        payload = {
            "frontier_wave": "W",
            "first_executable_task": "A",
            "tasks": [task("A", "READY", []), task("B", "BLOCKED", ["MISSING"])],
        }
        errors = validate_payload(payload, expected_frontier="W")
        self.assertTrue(any("unknown dependency" in error for error in errors))

    def test_cycle_is_rejected(self) -> None:
        payload = {
            "frontier_wave": "W",
            "first_executable_task": "A",
            "tasks": [task("A", "IN_PROGRESS", ["B"]), task("B", "BLOCKED", ["A"])],
        }
        errors = validate_payload(payload, expected_frontier="W")
        self.assertTrue(any("dependency cycle" in error for error in errors))

    def test_frontier_drift_is_rejected(self) -> None:
        payload = {
            "frontier_wave": "OLD",
            "first_executable_task": "A",
            "tasks": [task("A", "READY", [])],
        }
        errors = validate_payload(payload, expected_frontier="NEW")
        self.assertTrue(any("frontier_wave drift" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
