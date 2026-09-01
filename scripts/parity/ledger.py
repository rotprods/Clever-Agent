from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_LEDGER = Path("ledgers/CAPABILITY_LEDGER.jsonl")
PARITY_LEDGER = Path("ledgers/PARITY_LEDGER.ndjson")

NON_TERMINAL = ("UNVERIFIED", "MAPPED", "IMPLEMENTED", "TESTED", "VERIFIED")
TERMINAL_EXCEPTIONS = {"BLOCKED", "OUT_OF_SCOPE_WITH_WAIVER", "UPSTREAM_DEAD"}
ALL_STATES = set(NON_TERMINAL) | TERMINAL_EXCEPTIONS
RANK = {state: index for index, state in enumerate(NON_TERMINAL)}
REQUIRED_VERIFIED_FIELDS = {
    "adapter_mapping",
    "canonical_contract",
    "parity_test_id",
    "test_result",
    "evidence_id",
    "availability_semantics",
    "degradation_semantics",
    "platform",
    "observed_at",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def capabilities(root: Path = ROOT) -> list[dict[str, Any]]:
    return read_jsonl(root / CAPABILITY_LEDGER)


def capability_index(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    rows = capabilities(root)
    indexed = {str(row["capability_id"]): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("duplicate capability_id in denominator ledger")
    return indexed


def compile_obligations(source_repo: str, root: Path = ROOT) -> list[dict[str, Any]]:
    rows = [
        row
        for row in capabilities(root)
        if row.get("source_repo") == source_repo
        and row.get("promotion_status") == "BEHAVIOR_MAPPED"
        and row.get("status") == "IN_SCOPE"
    ]
    rows.sort(key=lambda row: str(row["capability_id"]))
    return rows


def _transition_allowed(previous: str, current: str) -> bool:
    if current in TERMINAL_EXCEPTIONS:
        return True
    if previous in TERMINAL_EXCEPTIONS:
        return current == previous
    if previous not in RANK or current not in RANK:
        return False
    return RANK[current] >= RANK[previous]


def validate_records(records: Iterable[dict[str, Any]], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    indexed = capability_index(root)
    effective: dict[str, str] = {cap_id: str(row.get("parity_status", "UNVERIFIED")) for cap_id, row in indexed.items()}
    for number, record in enumerate(records, start=1):
        cap_id = str(record.get("capability_id", ""))
        state = str(record.get("state", ""))
        if cap_id not in indexed:
            errors.append(f"record {number}: unknown capability_id {cap_id!r}")
            continue
        if state not in ALL_STATES:
            errors.append(f"record {number}: invalid state {state!r}")
            continue
        expected_commit = indexed[cap_id].get("source_commit")
        if record.get("upstream_commit") != expected_commit:
            errors.append(f"record {number}: upstream_commit drift for {cap_id}")
        previous = effective[cap_id]
        if not _transition_allowed(previous, state):
            errors.append(f"record {number}: invalid parity transition {cap_id}: {previous} -> {state}")
        if state == "VERIFIED":
            missing = sorted(field for field in REQUIRED_VERIFIED_FIELDS if not record.get(field))
            if missing:
                errors.append(f"record {number}: VERIFIED {cap_id} missing {missing}")
        if state == "OUT_OF_SCOPE_WITH_WAIVER" and not record.get("waiver_id"):
            errors.append(f"record {number}: waiver state requires waiver_id")
        if state in {"BLOCKED", "UPSTREAM_DEAD"} and not record.get("reason"):
            errors.append(f"record {number}: {state} requires reason")
        effective[cap_id] = state
    return errors


def effective_states(root: Path = ROOT) -> dict[str, str]:
    indexed = capability_index(root)
    effective = {cap_id: str(row.get("parity_status", "UNVERIFIED")) for cap_id, row in indexed.items()}
    records = read_jsonl(root / PARITY_LEDGER)
    errors = validate_records(records, root)
    if errors:
        raise ValueError("; ".join(errors))
    for record in records:
        effective[str(record["capability_id"])] = str(record["state"])
    return effective


def summary(root: Path = ROOT, source_repo: str | None = None) -> dict[str, Any]:
    indexed = capability_index(root)
    states = effective_states(root)
    selected = [cap_id for cap_id, row in indexed.items() if source_repo is None or row.get("source_repo") == source_repo]
    counts = Counter(states[cap_id] for cap_id in selected)
    return {
        "schema_version": 1,
        "source_repo": source_repo,
        "total": len(selected),
        "counts": dict(sorted(counts.items())),
        "verified": counts.get("VERIFIED", 0),
    }


def write_obligations(path: Path, source_repo: str, root: Path = ROOT) -> int:
    rows = compile_obligations(source_repo, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = {
                "schema_version": 1,
                "capability_id": row["capability_id"],
                "source_repo": row["source_repo"],
                "source_commit": row["source_commit"],
                "family": row["family"],
                "surface_kind": row["surface_kind"],
                "name": row["name"],
                "runtime_owner": row["runtime_owner"],
                "source_path": row["source_path"],
                "source_line": row["source_line"],
                "interface": row.get("interface", {}),
                "contract_fingerprint": row["contract_fingerprint"],
                "initial_parity_state": "UNVERIFIED",
            }
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate/derive append-only Clever parity state")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--source-repo")
    parser.add_argument("--write-obligations")
    args = parser.parse_args()
    records = read_jsonl(ROOT / PARITY_LEDGER)
    errors = validate_records(records, ROOT)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    if args.write_obligations:
        count = write_obligations(ROOT / args.write_obligations, args.source_repo or "openjarvis", ROOT)
        print(f"Wrote {count} obligations")
    result = summary(ROOT, args.source_repo)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
