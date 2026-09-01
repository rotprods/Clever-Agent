from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.parity.ledger import compile_obligations, write_obligations

ROOT = Path(__file__).resolve().parents[2]
PIN = "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"
EXPECTED = 646


def compile_summary(root: Path = ROOT) -> dict[str, object]:
    rows = compile_obligations("openjarvis", root)
    if len(rows) != EXPECTED:
        raise RuntimeError(f"OpenJarvis obligation drift: expected {EXPECTED}, got {len(rows)}")
    commits = {row.get("source_commit") for row in rows}
    if commits != {PIN}:
        raise RuntimeError(f"OpenJarvis pin drift in obligation set: {sorted(str(v) for v in commits)}")
    families: dict[str, int] = {}
    for row in rows:
        family = str(row["family"])
        families[family] = families.get(family, 0) + 1
    return {
        "schema_version": 1,
        "source_repo": "openjarvis",
        "source_commit": PIN,
        "obligation_count": len(rows),
        "candidate_definition_count": 2188,
        "initial_verified": 0,
        "by_family": dict(sorted(families.items())),
        "denominator_mutation_authorized": False,
    }


def materialize(root: Path = ROOT) -> dict[str, object]:
    summary = compile_summary(root)
    output = root / "inventory/cp03/openjarvis_obligations.jsonl"
    count = write_obligations(output, "openjarvis", root)
    if count != EXPECTED:
        raise RuntimeError("materialized obligation count drift")
    report = root / "reports/cp03/OPENJARVIS_OBLIGATIONS.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialize", action="store_true")
    args = parser.parse_args()
    result = materialize(ROOT) if args.materialize else compile_summary(ROOT)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
