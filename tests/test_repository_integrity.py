from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode("utf-8")
    return [ROOT / item for item in output.split("\0") if item]


class RepositoryIntegrityTests(unittest.TestCase):
    def test_all_tracked_json_documents_parse(self) -> None:
        failures: list[str] = []
        for path in tracked_files():
            if path.suffix == ".json":
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                    failures.append(f"{path.relative_to(ROOT)}: {error}")
        self.assertEqual([], failures)

    def test_all_tracked_json_lines_parse_to_objects(self) -> None:
        failures: list[str] = []
        for path in tracked_files():
            if path.suffix not in {".jsonl", ".ndjson"}:
                continue
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        failures.append(
                            f"{path.relative_to(ROOT)}:{line_number}: not an object"
                        )
                except json.JSONDecodeError as error:
                    failures.append(
                        f"{path.relative_to(ROOT)}:{line_number}: {error}"
                    )
        self.assertEqual([], failures)

    def test_no_unresolved_merge_markers_in_tracked_text(self) -> None:
        proc = subprocess.run(
            ["git", "grep", "-n", "-E", "^(<<<<<<< |=======|>>>>>>> )"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
