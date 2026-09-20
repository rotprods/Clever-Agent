from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TASK_GRAPH = ROOT / "iterations/03/waves/CP03-W02/TASK_GRAPH.json"
CLAIMS = ROOT / "ledgers/CLAIM_LEDGER.ndjson"
RUN_LOG = ROOT / "ledgers/RUN_LOG.ndjson"
SESSION_DIR = ROOT / "sessions/20260920-w02-inference-contracts"
CLAIM_ID = "CLAIM-CP03-W02-INFERENCE-CONTRACTS-001"
WAVE_ID = "CP03-W02-INFERENCE-CONTRACTS-20260920"
TASK_ID = "W02-06"
OWNER = "chatgpt-gpt-5.6-sol"
SCOPE = [
    "contracts/proto/clever/v1/inference.proto",
    "contracts/proto/clever/v1/adapter.proto",
    "contracts/contract_manifest.json",
    "contracts/jsonschema/inference.schema.json",
    "contracts/fixtures/inference.json",
    "contracts/fixtures/wire/inference-*",
    "contracts/sdk/python/gen/clever/v1/inference_pb2.py",
    "contracts/sdk/python/gen/clever/v1/adapter_pb2.py",
    "contracts/sdk/typescript/src/gen/clever/v1/inference_pb.ts",
    "contracts/sdk/typescript/src/gen/clever/v1/adapter_pb.ts",
    "contracts/sdk/rust/src/gen/clever.v1.rs",
    "contracts/sdk/swift/Sources/CleverContracts/Gen/clever/v1/inference.pb.swift",
    "contracts/sdk/swift/Sources/CleverContracts/Gen/clever/v1/adapter.pb.swift",
    "contracts/generated_manifest.json",
    "scripts/contracts/build_inference_wire_fixture.py",
    "contracts/sdk/rust/tests/inference_roundtrip.rs",
    "contracts/sdk/typescript/test/inference-roundtrip.test.mjs",
    "contracts/sdk/swift/Tests/CleverContractsTests/InferenceRoundTripTests.swift",
    "tests/test_cp03_w02_inference_contracts.py",
    "docs/adr/ADR-CP03-002-inference-contracts.md",
    ".github/workflows/cp03-w02-inference-contracts.yml",
    "scripts/cp03/finalize_w02_inference_contracts.py",
    "tests/test_cp03_w02_inference_finalizer.py",
    ".github/workflows/cp03-w02-inference-finalize.yml",
    "iterations/03/waves/CP03-W02/TASK_GRAPH.json",
    "ledgers/CLAIM_LEDGER.ndjson",
    "ledgers/EVIDENCE_LEDGER.ndjson",
    "ledgers/RUN_LOG.ndjson",
    "ledgers/WAVE_LEDGER.ndjson",
    "HANDOFF.md",
    ".agentic/context/CURRENT_CONTEXT.json",
    ".agentic/context/CURRENT_CONTEXT.md",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_ndjson(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def normalize_scope(value: str) -> str:
    return value[:-3] if value.endswith("/**") else value.rstrip("*")


def overlaps(left: str, right: str) -> bool:
    a = normalize_scope(left)
    b = normalize_scope(right)
    return a == b or a.startswith(b.rstrip("/") + "/") or b.startswith(a.rstrip("/") + "/")


def active_claims(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        claim_id = row.get("claim_id")
        if claim_id:
            latest[claim_id] = row
    return {
        claim_id: row
        for claim_id, row in latest.items()
        if row.get("status") == "ACTIVE" and row.get("event") != "RELEASE"
    }


def main() -> int:
    graph = load_json(TASK_GRAPH)
    if graph.get("first_executable_task") != TASK_ID:
        raise SystemExit(f"frontier drift: expected {TASK_ID}, got {graph.get('first_executable_task')}")
    tasks = {row["id"]: row for row in graph["tasks"]}
    task = tasks[TASK_ID]
    if task.get("status") != "READY":
        raise SystemExit(f"{TASK_ID} is not READY: {task.get('status')}")
    incomplete = [dep for dep in task.get("depends_on", []) if tasks[dep].get("status") != "COMPLETE"]
    if incomplete:
        raise SystemExit(f"{TASK_ID} dependencies incomplete: {incomplete}")

    rows = load_ndjson(CLAIMS)
    active = active_claims(rows)
    existing = active.get(CLAIM_ID)
    if existing is None:
        for other_id, other in active.items():
            for ours in SCOPE:
                for theirs in other.get("scope", []):
                    if overlaps(ours, theirs):
                        raise SystemExit(f"claim collision with {other_id}: {ours} <> {theirs}")
        claim = {
            "schema_version": 1,
            "date": "2026-09-20",
            "claim_id": CLAIM_ID,
            "wave_id": WAVE_ID,
            "parent_wave": "CP03-W02",
            "canonical_task": TASK_ID,
            "owner": OWNER,
            "scope": SCOPE,
            "coordination": "W02-06 only: additive typed inference request/chunk/terminal/error/cancel contracts, four-language generated bindings and compatibility/round-trip evidence. Does not implement egress policy W02-07, model/engine bridge W02-08, real-model lane W02-09, execute inference, mutate denominator/parity, or promote capabilities.",
            "status": "ACTIVE",
        }
        append_ndjson(CLAIMS, claim)
    else:
        if existing.get("scope") != SCOPE:
            raise SystemExit("existing W02-06 claim scope drift")

    run_rows = load_ndjson(RUN_LOG)
    if not any(row.get("event") == "WORK_STARTED" and row.get("wave_id") == WAVE_ID for row in run_rows):
        append_ndjson(
            RUN_LOG,
            {
                "schema_version": 1,
                "date": "2026-09-20",
                "event": "WORK_STARTED",
                "goal_id": "CLEVER-JARVIS-001",
                "checkpoint": "CP03",
                "iteration": "I03",
                "wave_id": WAVE_ID,
                "task_id": TASK_ID,
                "status": "CLAIMED",
            },
        )

    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    (SESSION_DIR / "CLAIM.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "date": "2026-09-20",
                "claim_id": CLAIM_ID,
                "wave_id": WAVE_ID,
                "canonical_task": TASK_ID,
                "owner": OWNER,
                "scope": SCOPE,
                "status": "ACTIVE",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    from scripts.context.build_context_pack import CONTEXT_JSON, CONTEXT_MD, build_context_pack, render_markdown

    pack = build_context_pack(ROOT)
    (ROOT / CONTEXT_JSON).write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / CONTEXT_MD).write_text(render_markdown(pack), encoding="utf-8")
    print(f"OK: acquired {CLAIM_ID} for {TASK_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
