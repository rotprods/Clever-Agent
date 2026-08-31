#!/usr/bin/env python3
"""Validate Clever-Agent's canonical project-control, context and planning state."""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_FILES = [
    "AGENTS.md", "GOAL.md", "STATE.md", "HANDOFF.md", "CHANGELOG.md", "CHECKPOINTS.md", "PROTOCOLS.md",
    "GOAL_STATE.json", "EXECUTION_STATE.json", "CHECKPOINT_REGISTRY.json", "UPSTREAM_LEDGER.yaml", ".agentic/CONFIG.yaml",
    ".agentic/context/COS20D.json", ".agentic/context/CURRENT_CONTEXT.json", ".agentic/context/CURRENT_CONTEXT.md",
    ".agentic/context/NEXT_ACTIONS.json", "docs/REGRESSION_2026-08-31.md", "docs/ACTA_DE_CONSCIENCIA.md",
    "docs/COS_GRAPH_ENGINE_V2.md", "docs/GRAPH_ENGINEERING_PROTOCOL.md", "IMPLEMENTATION_PLAN.md", "TASKS.md",
    "commands/EMPEZARPROYECTO.md", "iterations/01/ITERATION.md", "iterations/01/METAPROMPT.md", "iterations/01/STATE.json",
]

NDJSON_FILES = [
    "ledgers/RUN_LOG.ndjson", "ledgers/WAVE_LEDGER.ndjson", "ledgers/CLAIM_LEDGER.ndjson", "ledgers/DECISION_LEDGER.ndjson",
    "ledgers/RISK_LEDGER.ndjson", "ledgers/EVIDENCE_LEDGER.ndjson", "ledgers/CAPABILITY_LEDGER.jsonl", "ledgers/UPSTREAM_DRIFT.ndjson",
]


def load_json(relative_path: str):
    with (ROOT / relative_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_json_lines(relative_path: str, errors: list[str]) -> None:
    path = ROOT / relative_path
    if not path.exists():
        errors.append(f"missing ledger: {relative_path}")
        return
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            json.loads(raw_line)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSONL {relative_path}:{line_number}: {exc}")


def main() -> int:
    errors: list[str] = []
    for relative_path in REQUIRED_FILES:
        if not (ROOT / relative_path).is_file():
            errors.append(f"missing required file: {relative_path}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    goal_state = load_json("GOAL_STATE.json")
    execution_state = load_json("EXECUTION_STATE.json")
    checkpoint_registry = load_json("CHECKPOINT_REGISTRY.json")
    iteration_state = load_json("iterations/01/STATE.json")

    goal_ids = {goal_state.get("goal_id"), execution_state.get("goal_id"), checkpoint_registry.get("goal_id"), iteration_state.get("goal_id")}
    if len(goal_ids) != 1 or None in goal_ids:
        errors.append(f"goal_id drift across state files: {sorted(str(value) for value in goal_ids)}")

    active_checkpoint = goal_state.get("active_checkpoint")
    if execution_state.get("current_checkpoint") != active_checkpoint:
        errors.append("GOAL_STATE.active_checkpoint != EXECUTION_STATE.current_checkpoint")
    if iteration_state.get("checkpoint_id") != active_checkpoint:
        errors.append("iteration checkpoint_id != GOAL_STATE.active_checkpoint")

    checkpoint_map = {item.get("id"): item for item in checkpoint_registry.get("checkpoints", []) if isinstance(item, dict) and item.get("id")}
    if active_checkpoint not in checkpoint_map:
        errors.append(f"active checkpoint {active_checkpoint!r} missing from registry")
    elif checkpoint_map[active_checkpoint].get("status") not in {"IN_PROGRESS", "READY_FOR_REVIEW"}:
        errors.append(f"active checkpoint {active_checkpoint} has non-active registry status {checkpoint_map[active_checkpoint].get('status')!r}")

    active_iteration = goal_state.get("active_iteration")
    if execution_state.get("active_iteration") != active_iteration:
        errors.append("active_iteration drift between GOAL_STATE and EXECUTION_STATE")
    if iteration_state.get("iteration_id") != active_iteration:
        errors.append("iteration STATE iteration_id != active_iteration")
    if execution_state.get("active_subcheckpoint") != iteration_state.get("active_subcheckpoint"):
        errors.append("active_subcheckpoint drift between EXECUTION_STATE and iteration STATE")
    if execution_state.get("next_wave") != iteration_state.get("next_wave"):
        errors.append("next_wave drift between EXECUTION_STATE and iteration STATE")

    next_wave = str(execution_state.get("next_wave"))
    frontier_text = str(goal_state.get("frontier", ""))
    if next_wave not in frontier_text:
        errors.append(f"GOAL_STATE.frontier does not mention canonical next_wave {next_wave}")

    state_md = (ROOT / "STATE.md").read_text(encoding="utf-8")
    for required_token in (str(active_checkpoint), str(active_iteration), next_wave):
        if required_token not in state_md:
            errors.append(f"STATE.md does not contain canonical token {required_token!r}")

    config = (ROOT / ".agentic/CONFIG.yaml").read_text(encoding="utf-8")
    for token in (
        f"active_checkpoint: {active_checkpoint}", f"active_iteration: {active_iteration}",
        f"next_wave: {next_wave}", "next_actions: .agentic/context/NEXT_ACTIONS.json",
        "plan_validator: python scripts/context/validate_next_actions.py",
    ):
        if token not in config:
            errors.append(f".agentic/CONFIG.yaml drift/missing token: {token}")

    for relative_path in NDJSON_FILES:
        validate_json_lines(relative_path, errors)

    if not errors:
        from scripts.context.validate_context_pack import validate_context_pack
        from scripts.context.validate_next_actions import validate_payload
        errors.extend(validate_context_pack(ROOT))
        plan = load_json(".agentic/context/NEXT_ACTIONS.json")
        errors.extend(validate_payload(plan, expected_frontier=next_wave))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "OK: agentic state/context/plan are consistent "
        f"goal={goal_state['goal_id']} checkpoint={active_checkpoint} iteration={active_iteration} next_wave={next_wave}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
