from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

from scripts.cp03.obligations import materialize as materialize_obligations

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-09-01"


def load_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write_json(path: str, payload: dict[str, Any]) -> None:
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


def cp03_plan() -> dict[str, Any]:
    objectives = [
        ("CP03-000", "CP03-W00", "Run hermetic pinned OpenJarvis baseline and classify gated tests."),
        ("CP03-001", "CP03-W01", "Implement supervised adapter transport, lifecycle and typed registry bridge."),
        ("CP03-002", "CP03-W02", "Map models, engines and inference behavior through canonical contracts."),
        ("CP03-003", "CP03-W03", "Map agents, tools and MCP while enforcing Clever action authority."),
        ("CP03-004", "CP03-W04", "Map memory/retrieval with principal-scoped ownership and provenance."),
        ("CP03-005", "CP03-W05", "Map traces, telemetry, evals and proposal-only learning signals."),
        ("CP03-006", "CP03-W06", "Map scheduler/proactive/persistent operative semantics with replay safety."),
        ("CP03-007", "CP03-W07", "Reconcile OpenJarvis defense-in-depth security under Clever T0 policy."),
        ("CP03-008", "CP03-W08", "Compile and burn down parity for all 646 OpenJarvis obligations."),
        ("CP03-009", "CP03-W09", "Run adversarial recovery and performance gauntlet."),
        ("CP03-010", "CP03-W10", "Reconcile CP03 release evidence and hand off to CP04."),
    ]
    tasks: list[dict[str, Any]] = []
    previous: str | None = None
    for index, (task_id, wave, objective) in enumerate(objectives):
        tasks.append({
            "id": task_id,
            "wave": wave,
            "objective": objective,
            "owner_role": "release_reconciler" if index in {0, 8, 9, 10} else "builder",
            "priority": "P0",
            "depends_on": [previous] if previous else [],
            "gates": ["evidence-backed wave gate", "Agentic Contract", "parity denominator unchanged"],
            "outputs": [f"evidence/cp03/{wave.lower()}/"],
            "status": "READY" if index == 0 else "BLOCKED",
        })
        previous = task_id
    return {
        "schema_version": 1,
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "iteration": "I03",
        "frontier_wave": "CP03-W00",
        "first_executable_task": "CP03-000",
        "status_model": ["READY", "BLOCKED", "IN_PROGRESS", "COMPLETE"],
        "tasks": tasks,
    }


def render_tasks(plan: dict[str, Any]) -> str:
    lines = ["# TASKS — CLEVER-JARVIS-001 executable backlog", "", "Machine authority: `.agentic/context/NEXT_ACTIONS.json`.", "", "## CP03 — OpenJarvis cognitive adapter", ""]
    for row in plan["tasks"]:
        marker = "x" if row["status"] == "COMPLETE" else " "
        lines.append(f"- [{marker}] **{row['id']} / {row['wave']} — {row['objective']}** Status: `{row['status']}`.")
    lines.extend(["", "Frozen OpenJarvis obligation set: **646**. Global denominator: **7565**. Native state deletion/migration is forbidden in CP03.", ""])
    return "\n".join(lines)


def update_config() -> None:
    path = ROOT / ".agentic/CONFIG.yaml"
    text = path.read_text(encoding="utf-8")
    text = text.replace("active_iteration: I02", "active_iteration: I03", 1)
    text = text.replace("active_checkpoint: CP02", "active_checkpoint: CP03", 1)
    if "    - ledgers/PARITY_LEDGER.ndjson" not in text:
        text = text.replace("    - ledgers/CAPABILITY_LEDGER.jsonl\n", "    - ledgers/CAPABILITY_LEDGER.jsonl\n    - ledgers/PARITY_LEDGER.ndjson\n", 1)
    text = re.sub(
        r"(?ms)^current_iteration:\n.*\Z",
        "current_iteration:\n  id: I03\n  metaprompt: iterations/03/METAPROMPT.md\n  plan: iterations/03/ITERATION.md\n  state: iterations/03/STATE.json\n  next_wave: CP03-W00\n",
        text,
    )
    path.write_text(text, encoding="utf-8")


def finalize(source_sha: str, run_id: str) -> None:
    release = load_json("evidence/cp02/release/CP02_RELEASE.json")
    if release.get("status") != "PASS" or release.get("denominator") != 7565 or release.get("openjarvis_obligations") != 646:
        raise RuntimeError("CP02 release evidence is not eligible for transition")

    obligations = materialize_obligations(ROOT)
    if obligations["obligation_count"] != 646:
        raise RuntimeError("OpenJarvis obligation compiler drift")

    registry = load_json("CHECKPOINT_REGISTRY.json")
    for row in registry["checkpoints"]:
        if row["id"] == "CP02":
            row["status"] = "COMPLETE"
        elif row["id"] == "CP03":
            row["status"] = "IN_PROGRESS"
    write_json("CHECKPOINT_REGISTRY.json", registry)

    i02 = load_json("iterations/02/STATE.json")
    complete_sub = list(i02.get("completed_subcheckpoints", []))
    if "I02.6" not in complete_sub:
        complete_sub.append("I02.6")
    i02.update({"completed_subcheckpoints": complete_sub, "status": "COMPLETE", "active_subcheckpoint": "COMPLETE", "next_wave": "COMPLETE", "next_wave_name": "CP02 complete", "last_updated_date": DATE})
    write_json("iterations/02/STATE.json", i02)

    i03 = load_json("iterations/03/STATE.json")
    i03.update({"status": "IN_PROGRESS", "active_subcheckpoint": "I03.0", "next_wave": "CP03-W00", "next_wave_name": "Hermetic OpenJarvis baseline", "last_updated_date": DATE})
    write_json("iterations/03/STATE.json", i03)

    execution = load_json("EXECUTION_STATE.json")
    completed = list(execution.get("completed_waves", []))
    if "CP02-W06" not in completed:
        completed.append("CP02-W06")
    execution.update({
        "current_checkpoint": "CP03",
        "active_iteration": "I03",
        "active_subcheckpoint": "I03.0",
        "next_wave": "CP03-W00",
        "next_wave_name": "Hermetic OpenJarvis baseline",
        "next_checkpoint": "CP04",
        "mode": "openjarvis-adapter",
        "completed_waves": completed,
        "required_next_outputs": [
            "hermetic OpenJarvis baseline",
            "646-capability OpenJarvis obligation manifest",
            "supervised adapter transport and registry bridge",
            "behavioral parity evidence overlay",
            "OpenJarvis security/recovery gauntlet",
        ],
    })
    write_json("EXECUTION_STATE.json", execution)

    goal = load_json("GOAL_STATE.json")
    goal.update({"active_checkpoint": "CP03", "active_iteration": "I03", "frontier": "Execute /empezarproyecto at CP03-W00 and execute CP03-000 hermetic OpenJarvis baseline before adapter implementation.", "last_updated_date": DATE})
    write_json("GOAL_STATE.json", goal)

    plan = cp03_plan()
    write_json(".agentic/context/NEXT_ACTIONS.json", plan)
    update_config()

    (ROOT / "STATE.md").write_text(
        "# STATE — Clever-Agent live pointer\n\n## Current\n\n- Goal: `CLEVER-JARVIS-001`\n- Global status: `IN_PROGRESS`\n- Active checkpoint: `CP03 — OpenJarvis cognitive adapter`\n- Active iteration: `I03 — OpenJarvis Cognitive Adapter`\n- Active subcheckpoint: `I03.0`\n- Next executable wave: `CP03-W00 — Hermetic OpenJarvis baseline`\n- Capability denominator: `7565`\n- OpenJarvis obligations: `646`\n- Clever VERIFIED parity: `0 / 7565`\n\n## Canonical frontier\n\nRun `/empezarproyecto`, claim `CP03-W00`, establish executable upstream truth in a hermetic sandbox, then continue `iterations/03/METAPROMPT.md`.\n",
        encoding="utf-8",
    )
    (ROOT / "HANDOFF.md").write_text(
        "# HANDOFF — Clever-Agent\n\n- Checkpoint: `CP03`\n- Iteration: `I03`\n- CP02 release evidence: `EVID-0012`\n- OpenJarvis pin: `72033b8ec288aa067ce4530ff9d96bf231e9c4e5`\n- Frozen obligations: `646`\n- Next task: `CP03-000`\n- Next wave: `CP03-W00`\n\nRun `/empezarproyecto`, validate state/context/parity ledgers, execute the hermetic upstream baseline, and do not claim adapter parity from mocks.\n",
        encoding="utf-8",
    )
    (ROOT / "TASKS.md").write_text(render_tasks(plan), encoding="utf-8")

    checkpoints = ROOT / "CHECKPOINTS.md"
    text = checkpoints.read_text(encoding="utf-8")
    text = text.replace("| CP02 | Canonical contracts + Rust kernel scaffold | PENDING |", "| CP02 | Canonical contracts + Rust kernel scaffold | COMPLETE |")
    text = text.replace("| CP02 | Canonical contracts + Rust kernel scaffold | IN_PROGRESS |", "| CP02 | Canonical contracts + Rust kernel scaffold | COMPLETE |")
    text = text.replace("| CP03 | OpenJarvis cognitive adapter | PENDING |", "| CP03 | OpenJarvis cognitive adapter | IN_PROGRESS |")
    checkpoints.write_text(text, encoding="utf-8")

    append_jsonl("ledgers/EVIDENCE_LEDGER.ndjson", {"schema_version":1,"date":DATE,"evidence_id":"EVID-0012","status":"VERIFIED","type":"cp02_release","claim":"CP02 contracts, cross-runtime bindings, Rust kernel/action/audit/memory security and recovery gauntlet are release-consistent; CP03 OpenJarvis obligation set is frozen at 646 without denominator mutation.","github_actions_run_id":int(run_id) if str(run_id).isdigit() else run_id,"validated_head":source_sha,"wave_id":"CP02-W06"}, "evidence_id")
    append_jsonl("ledgers/WAVE_LEDGER.ndjson", {"schema_version":1,"date":DATE,"wave_id":"CP02-W06","event":"RELEASE_RECONCILIATION","status":"COMPLETE","evidence_id":"EVID-0012","next_wave":"CP03-W00"})
    append_jsonl("ledgers/WAVE_LEDGER.ndjson", {"schema_version":1,"date":DATE,"wave_id":"CP03-W00","iteration":"I03","checkpoint":"CP03","objective":"Run hermetic pinned OpenJarvis baseline and classify gated tests.","status":"PROPOSED"})
    append_jsonl("ledgers/RUN_LOG.ndjson", {"schema_version":1,"date":DATE,"event":"CP02_RELEASE_TRANSITION","goal_id":"CLEVER-JARVIS-001","checkpoint":"CP03","iteration":"I03","wave_id":"CP03-W00","status":"ADVANCED","evidence_id":"EVID-0012","source_sha":source_sha,"run_id":int(run_id) if str(run_id).isdigit() else run_id,"denominator":7565,"openjarvis_obligations":646})

    changelog = ROOT / "CHANGELOG.md"
    changelog.write_text(changelog.read_text(encoding="utf-8") + "\n## 2026-09-01 — CP02 release / CP03 entry\n\n- Closed CP02 from EVID-0007..EVID-0012.\n- Froze 646 OpenJarvis obligations without changing the global 7565 denominator.\n- Added append-only parity overlay and entered I03 at CP03-W00 hermetic baseline.\n", encoding="utf-8")

    from scripts.context.build_context_pack import CONTEXT_JSON, CONTEXT_MD, build_context_pack, render_markdown
    pack = build_context_pack(ROOT)
    (ROOT / CONTEXT_JSON).write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / CONTEXT_MD).write_text(render_markdown(pack), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    finalize(args.source_sha, args.run_id)
    print("CP02 COMPLETE -> CP03 IN_PROGRESS; next=CP03-W00")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
