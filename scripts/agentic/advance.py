from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

from scripts.context.iteration import iteration_state_path

ROOT = Path(__file__).resolve().parents[2]


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: str, row: dict[str, Any], id_key: str | None = None) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if id_key and target.exists():
        for raw in target.read_text(encoding="utf-8").splitlines():
            if raw.strip() and json.loads(raw).get(id_key) == row.get(id_key):
                return
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def _update_config(checkpoint: str, iteration: str, next_wave: str) -> None:
    path = ROOT / ".agentic/CONFIG.yaml"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^  active_iteration: I[0-9]+$", f"  active_iteration: {iteration}", text, count=1)
    text = re.sub(r"(?m)^  active_checkpoint: CP[0-9]+$", f"  active_checkpoint: {checkpoint}", text, count=1)
    text = re.sub(r"(?ms)^current_iteration:\n(?:  .*\n?)*", f"current_iteration:\n  id: {iteration}\n  metaprompt: iterations/{int(iteration[1:]):02d}/METAPROMPT.md\n  plan: iterations/{int(iteration[1:]):02d}/ITERATION.md\n  state: iterations/{int(iteration[1:]):02d}/STATE.json\n  next_wave: {next_wave}\n", text)
    path.write_text(text, encoding="utf-8")


def _render_tasks(plan: dict[str, Any], checkpoint: str) -> str:
    lines = ["# TASKS — CLEVER-JARVIS-001 executable backlog", "", "Machine authority: `.agentic/context/NEXT_ACTIONS.json`.", "", f"## {checkpoint}", ""]
    for row in plan["tasks"]:
        marker = "x" if row["status"] == "COMPLETE" else " "
        lines.append(f"- [{marker}] **{row['id']} / {row['wave']} — {row['objective']}** Status: `{row['status']}`.")
    lines.append("")
    return "\n".join(lines)


def advance(*, checkpoint: str, iteration: str, complete_task: str, complete_wave: str, complete_subcheckpoint: str, next_task: str, next_wave: str, next_wave_name: str, next_subcheckpoint: str, evidence_id: str, evidence_claim: str, run_id: str, head_sha: str, date: str) -> None:
    plan = load_json(".agentic/context/NEXT_ACTIONS.json")
    if plan.get("checkpoint") != checkpoint or plan.get("iteration") != iteration:
        raise RuntimeError("task graph checkpoint/iteration drift")
    rows = {row["id"]: row for row in plan["tasks"]}
    current, nxt = rows[complete_task], rows[next_task]
    if current["status"] not in {"READY", "IN_PROGRESS"}:
        raise RuntimeError(f"{complete_task} is not executable")
    missing = [dep for dep in current.get("depends_on", []) if rows[dep]["status"] != "COMPLETE"]
    if missing:
        raise RuntimeError(f"incomplete dependencies: {missing}")
    if complete_task not in nxt.get("depends_on", []):
        raise RuntimeError("next task does not depend on completed task")
    current["status"] = "COMPLETE"
    nxt["status"] = "READY"
    plan["first_executable_task"] = next_task
    plan["frontier_wave"] = next_wave
    write_json(".agentic/context/NEXT_ACTIONS.json", plan)

    execution = load_json("EXECUTION_STATE.json")
    completed = list(execution.get("completed_waves", []))
    if complete_wave not in completed:
        completed.append(complete_wave)
    execution.update({"active_subcheckpoint": next_subcheckpoint, "next_wave": next_wave, "next_wave_name": next_wave_name, "completed_waves": completed})
    write_json("EXECUTION_STATE.json", execution)

    iteration_path = iteration_state_path(iteration)
    state = load_json(iteration_path)
    completed_sub = list(state.get("completed_subcheckpoints", []))
    if complete_subcheckpoint not in completed_sub:
        completed_sub.append(complete_subcheckpoint)
    state.update({"completed_subcheckpoints": completed_sub, "active_subcheckpoint": next_subcheckpoint, "next_wave": next_wave, "next_wave_name": next_wave_name, "last_updated_date": date})
    write_json(iteration_path, state)

    goal = load_json("GOAL_STATE.json")
    goal["frontier"] = f"Execute /empezarproyecto at {next_wave} and execute {next_task}."
    goal["last_updated_date"] = date
    write_json("GOAL_STATE.json", goal)
    _update_config(checkpoint, iteration, next_wave)

    denominator = int(goal.get("parity", {}).get("total") or 0)
    state_md = f"# STATE — Clever-Agent live pointer\n\n## Current\n\n- Goal: `CLEVER-JARVIS-001`\n- Global status: `IN_PROGRESS`\n- Active checkpoint: `{checkpoint}`\n- Active iteration: `{iteration}`\n- Active subcheckpoint: `{next_subcheckpoint}`\n- Next executable wave: `{next_wave} — {next_wave_name}`\n- Capability denominator: `{denominator}`\n\n## Canonical frontier\n\nExecute `/empezarproyecto`, claim `{next_wave}`, and follow the active iteration METAPROMPT.\n"
    (ROOT / "STATE.md").write_text(state_md, encoding="utf-8")
    (ROOT / "HANDOFF.md").write_text(f"# HANDOFF — Clever-Agent\n\n- Checkpoint: `{checkpoint}`\n- Iteration: `{iteration}`\n- Completed: `{complete_task}` / `{complete_wave}`\n- Evidence: `{evidence_id}`\n- Next: `{next_task}` / `{next_wave}`\n\nRun `/empezarproyecto`, validate state/context, then continue the active METAPROMPT.\n", encoding="utf-8")
    (ROOT / "TASKS.md").write_text(_render_tasks(plan, checkpoint), encoding="utf-8")

    append_jsonl("ledgers/EVIDENCE_LEDGER.ndjson", {"schema_version":1,"date":date,"evidence_id":evidence_id,"status":"VERIFIED","type":"wave_gate","claim":evidence_claim,"github_actions_run_id":int(run_id) if str(run_id).isdigit() else run_id,"validated_head":head_sha,"wave_id":complete_wave}, "evidence_id")
    append_jsonl("ledgers/WAVE_LEDGER.ndjson", {"schema_version":1,"date":date,"wave_id":complete_wave,"event":"VERIFICATION","status":"COMPLETE","evidence_id":evidence_id,"next_wave":next_wave})
    append_jsonl("ledgers/WAVE_LEDGER.ndjson", {"schema_version":1,"date":date,"wave_id":next_wave,"iteration":iteration,"checkpoint":checkpoint,"objective":nxt["objective"],"status":"PROPOSED"})
    append_jsonl("ledgers/RUN_LOG.ndjson", {"schema_version":1,"date":date,"event":"WAVE_ADVANCED","goal_id":"CLEVER-JARVIS-001","checkpoint":checkpoint,"iteration":iteration,"wave_id":complete_wave,"status":"ADVANCED","evidence_id":evidence_id,"next_wave":next_wave,"head":head_sha})

    from scripts.context.build_context_pack import CONTEXT_JSON, CONTEXT_MD, build_context_pack, render_markdown
    pack = build_context_pack(ROOT)
    (ROOT / CONTEXT_JSON).write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / CONTEXT_MD).write_text(render_markdown(pack), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("checkpoint", "iteration", "complete-task", "complete-wave", "complete-subcheckpoint", "next-task", "next-wave", "next-wave-name", "next-subcheckpoint", "evidence-id", "evidence-claim", "run-id", "head-sha"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--date", default="2026-09-01")
    args = parser.parse_args()
    advance(**vars(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
