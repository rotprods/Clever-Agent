#!/usr/bin/env python3
"""Validate the subordinate W02 planning DAG, not runtime or capability parity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PLAN_DIR = Path("iterations/03/waves/CP03-W02")
PIN = "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"
DIMENSIONS = (
    "MISSION_GOAL", "PROVENANCE_EVIDENCE", "SOURCE_TOPOLOGY", "CAPABILITY_SEMANTICS",
    "DEPENDENCY_GRAPH", "RUNTIME_OWNERSHIP", "INTERFACE_CONTRACTS", "STATE_DATA",
    "MEMORY_KNOWLEDGE", "INTENT_CONTROL", "LIFECYCLE_CONCURRENCY",
    "SIDE_EFFECT_IDEMPOTENCY", "SECURITY_PERMISSION", "FAILURE_RECOVERY",
    "OBSERVABILITY_ECONOMICS", "TEST_EVAL_PARITY", "PLATFORM_DEVICE",
    "EMBODIMENT_UX", "SUPPLY_CHAIN_DEPLOYMENT", "TEMPORAL_DRIFT",
)


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def validate(plan: dict[str, Any], findings: dict[str, Any], cos: dict[str, Any]) -> dict[str, Any]:
    for key, expected in {
        "schema_version": 1, "project_id": "CLEVER-JARVIS-001",
        "parent_task": "CP03-002", "wave": "CP03-W02", "iteration": "I03",
        "global_denominator": 7565, "openjarvis_obligations": 646,
        "upstream_commit": PIN,
        "schedule_basis": "GATE_RELATIVE_NOT_CALENDAR_COMMITMENT",
    }.items():
        require(plan.get(key) == expected, f"invalid canonical field: {key}")
    source = plan.get("source_sha", "")
    require(isinstance(source, str) and len(source) == 40 and all(c in "0123456789abcdef" for c in source), "invalid source SHA")
    k = plan.get("w02_obligation_count")
    require(k is None or (type(k) is int and 0 < k <= 646), "invalid W02 obligation count")
    tasks = plan.get("tasks")
    require(isinstance(tasks, list) and bool(tasks), "empty task graph")
    by_id: dict[str, dict[str, Any]] = {}
    for task in tasks:
        require(isinstance(task, dict), "invalid task record")
        task_id = task.get("id")
        require(isinstance(task_id, str) and task_id.startswith("W02-"), "invalid task ID")
        require(task_id not in by_id, "duplicate task ID")
        by_id[task_id] = task
        for key in ("title", "owner_role", "reviewer_role", "rollback"):
            require(isinstance(task.get(key), str) and bool(task[key].strip()), f"missing {key}: {task_id}")
        for key in ("deliverables", "acceptance_tests"):
            value = task.get(key)
            require(isinstance(value, list) and bool(value) and all(isinstance(x, str) and x.strip() for x in value), f"missing {key}: {task_id}")
        require(task.get("status") in {"READY", "BLOCKED", "IN_PROGRESS", "COMPLETE"}, "invalid task status")
        require(task.get("gate") in {f"G{i}" for i in range(8)}, "invalid gate")
        deps = task.get("depends_on")
        require(isinstance(deps, list) and all(isinstance(d, str) for d in deps), "invalid dependency list")
        require(len(set(deps)) == len(deps), "duplicate dependency")
        proof = task.get("proof")
        require(isinstance(proof, list), "invalid proof list")
        require(task["status"] != "COMPLETE" or bool(proof), "COMPLETE without proof")
        path = task.get("evidence_path", "")
        require(isinstance(path, str), "invalid evidence path")
        parts = PurePosixPath(path).parts
        require(path.startswith("evidence/cp03/cp03-w02/") and ".." not in parts and "\\" not in path, "unsafe evidence path")
    for task_id, task in by_id.items():
        for dep in task["depends_on"]:
            require(dep in by_id, f"missing dependency: {dep}")
            require(dep != task_id, "self dependency")
        if task["status"] in {"READY", "IN_PROGRESS", "COMPLETE"}:
            require(all(by_id[d]["status"] == "COMPLETE" for d in task["depends_on"]), f"false-ready task: {task_id}")
    seen: set[str] = set()
    visiting: set[str] = set()
    order: list[str] = []

    def visit(task_id: str) -> None:
        require(task_id not in visiting, "dependency cycle")
        if task_id in seen:
            return
        visiting.add(task_id)
        for dep in sorted(by_id[task_id]["depends_on"]):
            visit(dep)
        visiting.remove(task_id)
        seen.add(task_id)
        order.append(task_id)

    for task_id in sorted(by_id):
        visit(task_id)
    first = plan.get("first_executable_task")
    require(first in by_id and by_id[first]["status"] in {"READY", "IN_PROGRESS"}, "invalid first executable task")
    require({t["gate"] for t in tasks} == {f"G{i}" for i in range(8)}, "missing gate")
    require(findings.get("source_sha") == source, "findings source drift")
    finding_rows = findings.get("findings", [])
    require(bool(finding_rows), "missing findings")
    require(len({f.get("id") for f in finding_rows}) == len(finding_rows), "duplicate finding ID")
    for f in finding_rows:
        require(bool(f.get("resolved_by")) and all(x in by_id for x in f["resolved_by"]), "unmapped finding")
    dims = cos.get("dimensions", [])
    expected_dims = {f"D{i:02d}_{name}" for i, name in enumerate(DIMENSIONS)}
    require(len(dims) == 20 and {d.get("id") for d in dims} == expected_dims, "COS20D drift")
    for d in dims:
        require(bool(d.get("tasks")) and all(t in by_id for t in d["tasks"]), "unmapped COS dimension")
    return {"status": "PASS", "scope": "PLAN_INTEGRITY_ONLY", "task_count": len(tasks),
            "gate_count": 8, "finding_count": len(finding_rows), "dimension_count": 20,
            "first_executable_task": first, "topological_order": order,
            "runtime_tests_executed_by_this_validator": 0, "parity_promotions": 0}


def load(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    folder = root / PLAN_DIR
    return tuple(json.loads((folder / name).read_text(encoding="utf-8")) for name in (
        "TASK_GRAPH.json", "REVIEW_FINDINGS.json", "COS20D_REVIEW.json"))  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        report = validate(*load(args.root))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "scope": "PLAN_INTEGRITY_ONLY", "error": str(exc)}))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
