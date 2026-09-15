#!/usr/bin/env python3
"""Fail closed when a workflow executes an action through a mutable ref."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
USE_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def audit(root: Path = ROOT) -> dict[str, object]:
    workflows = sorted((root / ".github" / "workflows").glob("*.y*ml"))
    references: list[dict[str, object]] = []
    violations: list[dict[str, object]] = []
    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = USE_RE.match(line)
            if match is None:
                continue
            action = match.group(1)
            if action.startswith("./"):
                continue
            row = {
                "workflow": str(workflow.relative_to(root)),
                "line": line_number,
                "action": action,
            }
            references.append(row)
            ref = action.rsplit("@", 1)[1] if "@" in action else ""
            if SHA_RE.fullmatch(ref) is None:
                violations.append(row)
    return {
        "schema_version": 1,
        "status": "PASS" if not violations else "FAIL",
        "workflow_count": len(workflows),
        "external_action_references": len(references),
        "mutable_references": len(violations),
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    report = audit(args.root.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
