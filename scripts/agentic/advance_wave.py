from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = ROOT / path
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: str, row: dict[str, Any], *, id_key: str | None = None) -> None:
    target = ROOT / path
    if id_key and target.exists():
        for raw in target.read_text(encoding="utf-8").splitlines():
            if raw.strip() and json.loads(raw).get(id_key) == row.get(id_key):
                return
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def update_config(next_wave: str) -> None:
    path = ROOT / ".agentic/CONFIG.yaml"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^  next_wave: .*?$", f"  next_wave: {next_wave}", text, count=1)
    # The config contains another next_wave under current_iteration; update all remaining I02 frontier entries.
    text = re.sub(r"(?m)^  next_wave: CP02-W[0-9]+$", f"  next_wave: {next_wave}", text)
    path.write_text(text, encoding="utf-8")


def render_state(execution: dict[str, Any], denominator: int) -> str:
    return f"""# STATE — Clever-Agent live pointer\n\n> Machine mirrors and evidence outrank this human-readable pointer if drift is detected.\n\n## Current\n\n- Goal: `CLEVER-JARVIS-001`\n- Global status: `IN_PROGRESS`\n- Active checkpoint: `CP02 — Canonical contracts and Rust kernel scaffold`\n- Active iteration: `I02 — Canonical Contracts + Rust Kernel Scaffold`\n- Active subcheckpoint: `{execution['active_subcheckpoint']}`\n- Next executable wave: `{execution['next_wave']} — {execution['next_wave_name']}`\n- Capability denominator: `{denominator}`\n- Clever VERIFIED parity: `0 / {denominator}`\n\n## Canonical frontier\n\nExecute `/empezarproyecto`, claim `{execution['next_wave']}`, and follow `iterations/02/METAPROMPT.md`. Contracts remain authoritative over kernel implementation.\n"""


def render_handoff(execution: dict[str, Any], complete_task: str, next_task: str, evidence_id: str) -> str:
    return f"""# HANDOFF — Clever-Agent\n\n## Current\n\n- Goal: `CLEVER-JARVIS-001`\n- Checkpoint: `CP02`\n- Iteration: `I02`\n- Completed task: `{complete_task}`\n- Evidence: `{evidence_id}`\n- Next task: `{next_task}`\n- Next wave: `{execution['next_wave']}`\n\n## Recovery\n\n1. `/empezarproyecto`.\n2. Validate state/context/task DAG.\n3. Read `iterations/02/METAPROMPT.md`.\n4. Claim `{execution['next_wave']}`.\n5. Execute `{next_task}` and persist evidence before advancing again.\n\nCP01 denominator remains an integration obligation, not VERIFIED adapter parity. No native upstream implementation may be removed during CP02.\n"""


def render_tasks(plan: dict[str, Any]) -> str:
    lines = ["# TASKS — CLEVER-JARVIS-001 executable backlog", "", "Machine authority: `.agentic/context/NEXT_ACTIONS.json`.", "", "## CP02", ""]
    for row in plan["tasks"]:
        if not str(row.get("id", "")).startswith("CP02-"):
            continue
        marker = "x" if row["status"] == "COMPLETE" else " "
        lines.append(f"- [{marker}] **{row['id']} / {row['wave']} — {row['objective']}** Status: `{row['status']}`.")
    lines.extend(["", "No native upstream implementation is removed in CP02.", ""])
    return "\n".join(lines)


def advance(*, complete_task: str, complete_wave: str, complete_subcheckpoint: str, next_task: str, next_wave: str, next_wave_name: str, next_subcheckpoint: str, evidence_id: str, evidence_claim: str, run_id: str, head_sha: str, date: str) -> None:
    plan = load_json(".agentic/context/NEXT_ACTIONS.json")
    rows = {row["id"]: row for row in plan["tasks"]}
    if complete_task not in rows or next_task not in rows:
        raise RuntimeError("unknown task transition")
    current = rows[complete_task]
    if current["status"] not in {"READY", "IN_PROGRESS"}:
        raise RuntimeError(f"{complete_task} must be READY/IN_PROGRESS, got {current['status']}")
    incomplete_dependencies = [dep for dep in current.get("depends_on", []) if rows[dep]["status"] != "COMPLETE"]
    if incomplete_dependencies:
        raise RuntimeError(f"cannot complete {complete_task}; incomplete dependencies: {incomplete_dependencies}")
    next_row = rows[next_task]
    if complete_task not in next_row.get("depends_on", []):
        raise RuntimeError(f"{next_task} must depend on {complete_task}")
    current["status"] = "COMPLETE"
    next_row["status"] = "READY"
    plan["frontier_wave"] = next_wave
    plan["first_executable_task"] = next_task
    write_json(".agentic/context/NEXT_ACTIONS.json", plan)

    execution = load_json("EXECUTION_STATE.json")
    completed_waves = list(execution.get("completed_waves", []))
    if complete_wave not in completed_waves:
        completed_waves.append(complete_wave)
    execution.update({"active_subcheckpoint": next_subcheckpoint, "next_wave": next_wave, "next_wave_name": next_wave_name, "completed_waves": completed_waves})
    write_json("EXECUTION_STATE.json", execution)

    iteration = load_json("iterations/02/STATE.json")
    completed_sub = list(iteration.get("completed_subcheckpoints", []))
    if complete_subcheckpoint not in completed_sub:
        completed_sub.append(complete_subcheckpoint)
    iteration.update({"completed_subcheckpoints": completed_sub, "active_subcheckpoint": next_subcheckpoint, "next_wave": next_wave, "next_wave_name": next_wave_name, "last_updated_date": date})
    write_json("iterations/02/STATE.json", iteration)

    goal = load_json("GOAL_STATE.json")
    goal["frontier"] = f"Execute /empezarproyecto at {next_wave} and execute {next_task} before advancing the CP02 kernel frontier."
    goal["last_updated_date"] = date
    write_json("GOAL_STATE.json", goal)
    update_config(next_wave)

    denominator = int(goal.get("parity", {}).get("total") or 0)
    (ROOT / "STATE.md").write_text(render_state(execution, denominator), encoding="utf-8")
    (ROOT / "HANDOFF.md").write_text(render_handoff(execution, complete_task, next_task, evidence_id), encoding="utf-8")
    (ROOT / "TASKS.md").write_text(render_tasks(plan), encoding="utf-8")

    append_jsonl("ledgers/EVIDENCE_LEDGER.ndjson", {"schema_version":1,"date":date,"evidence_id":evidence_id,"status":"VERIFIED","type":"cp02_wave_gate","claim":evidence_claim,"github_actions_run_id":int(run_id) if str(run_id).isdigit() else run_id,"validated_head":head_sha,"wave_id":complete_wave}, id_key="evidence_id")
    append_jsonl("ledgers/WAVE_LEDGER.ndjson", {"schema_version":1,"date":date,"wave_id":complete_wave,"event":"VERIFICATION","status":"COMPLETE","evidence_id":evidence_id,"next_wave":next_wave})
    append_jsonl("ledgers/WAVE_LEDGER.ndjson", {"schema_version":1,"date":date,"wave_id":next_wave,"iteration":"I02","checkpoint":"CP02","objective":next_row["objective"],"status":"PROPOSED"})
    append_jsonl("ledgers/RUN_LOG.ndjson", {"schema_version":1,"date":date,"event":"CP02_WAVE_ADVANCED","goal_id":"CLEVER-JARVIS-001","checkpoint":"CP02","iteration":"I02","wave_id":complete_wave,"status":"ADVANCED","evidence_id":evidence_id,"next_wave":next_wave,"head":head_sha})

    from scripts.context.build_context_pack import CONTEXT_JSON, CONTEXT_MD, build_context_pack, render_markdown
    pack = build_context_pack(ROOT)
    (ROOT / CONTEXT_JSON).write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / CONTEXT_MD).write_text(render_markdown(pack), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Advance one CP02 task/wave only after an evidence-producing gate passes")
    parser.add_argument("--complete-task", required=True)
    parser.add_argument("--complete-wave", required=True)
    parser.add_argument("--complete-subcheckpoint", required=True)
    parser.add_argument("--next-task", required=True)
    parser.add_argument("--next-wave", required=True)
    parser.add_argument("--next-wave-name", required=True)
    parser.add_argument("--next-subcheckpoint", required=True)
    parser.add_argument("--evidence-id", required=True)
    parser.add_argument("--evidence-claim", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--date", default="2026-09-01")
    args = parser.parse_args()
    advance(**vars(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
