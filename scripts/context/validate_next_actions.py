#!/usr/bin/env python3
"""Validate the executable task DAG used by Clever-Agent agents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = Path(".agentic/context/NEXT_ACTIONS.json")
ALLOWED_STATUSES = {"READY", "BLOCKED", "IN_PROGRESS", "COMPLETE"}


def validate_payload(payload: dict[str, Any], *, expected_frontier: str | None = None) -> list[str]:
    errors: list[str] = []
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return ["NEXT_ACTIONS.tasks must be a non-empty list"]

    by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(tasks):
        if not isinstance(row, dict):
            errors.append(f"task at index {index} is not an object")
            continue
        task_id = row.get("id")
        if not isinstance(task_id, str) or not task_id:
            errors.append(f"task at index {index} has invalid id")
            continue
        if task_id in by_id:
            errors.append(f"duplicate task id: {task_id}")
        by_id[task_id] = row
        status = row.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{task_id}: invalid status {status!r}")
        dependencies = row.get("depends_on")
        if not isinstance(dependencies, list) or any(not isinstance(dep, str) or not dep for dep in dependencies):
            errors.append(f"{task_id}: depends_on must be a list of non-empty task ids")

    for task_id, row in by_id.items():
        dependencies = row.get("depends_on", [])
        for dependency in dependencies:
            if dependency == task_id:
                errors.append(f"{task_id}: self dependency")
            elif dependency not in by_id:
                errors.append(f"{task_id}: unknown dependency {dependency}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, stack: list[str]) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            try:
                start = stack.index(task_id)
                cycle = stack[start:] + [task_id]
            except ValueError:
                cycle = stack + [task_id]
            errors.append("dependency cycle: " + " -> ".join(cycle))
            return
        visiting.add(task_id)
        stack.append(task_id)
        for dependency in by_id.get(task_id, {}).get("depends_on", []):
            if dependency in by_id:
                visit(dependency, stack)
        stack.pop()
        visiting.discard(task_id)
        visited.add(task_id)

    for task_id in sorted(by_id):
        visit(task_id, [])

    for task_id, row in by_id.items():
        status = row.get("status")
        unresolved = [
            dep for dep in row.get("depends_on", [])
            if dep in by_id and by_id[dep].get("status") != "COMPLETE"
        ]
        if status == "READY" and unresolved:
            errors.append(f"{task_id}: READY with unresolved dependencies {unresolved}")
        if status == "BLOCKED" and not unresolved:
            errors.append(f"{task_id}: BLOCKED but all dependencies are COMPLETE")

    first = payload.get("first_executable_task")
    if first not in by_id:
        errors.append(f"first_executable_task missing from task graph: {first!r}")
    elif by_id[first].get("status") not in {"READY", "IN_PROGRESS"}:
        errors.append(f"first_executable_task {first} is not executable")

    frontier = payload.get("frontier_wave")
    if expected_frontier is not None and frontier != expected_frontier:
        errors.append(f"frontier_wave drift: plan={frontier!r}, execution={expected_frontier!r}")

    return errors


def main() -> int:
    payload = json.loads((ROOT / PLAN_PATH).read_text(encoding="utf-8"))
    execution = json.loads((ROOT / "EXECUTION_STATE.json").read_text(encoding="utf-8"))
    errors = validate_payload(payload, expected_frontier=execution.get("next_wave"))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        "OK: executable task DAG is valid "
        f"frontier={payload['frontier_wave']} first={payload['first_executable_task']} tasks={len(payload['tasks'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
