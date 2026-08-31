from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.context.iteration import iteration_state_path
from scripts.upstream.ledger import load_upstream_pins

CONTEXT_JSON = Path(".agentic/context/CURRENT_CONTEXT.json")
CONTEXT_MD = Path(".agentic/context/CURRENT_CONTEXT.md")
DIMENSIONS_JSON = Path(".agentic/context/COS20D.json")
NEXT_ACTIONS_JSON = Path(".agentic/context/NEXT_ACTIONS.json")

BASE_AUTHORITY_READ_ORDER = [
    "GOAL.md", "SECURITY_MODEL.md", "AGENTS.md", "ARCHITECTURE.md", "CAPABILITY_PARITY.md",
    "docs/ACTA_DE_CONSCIENCIA.md", "docs/COS_GRAPH_ENGINE_V2.md", "docs/GRAPH_ENGINEERING_PROTOCOL.md",
    "CHECKPOINT_REGISTRY.json", "STATE.md", "GOAL_STATE.json", "EXECUTION_STATE.json",
    "IMPLEMENTATION_PLAN.md", "TASKS.md", ".agentic/context/NEXT_ACTIONS.json",
    ".agentic/context/CURRENT_CONTEXT.json", "HANDOFF.md",
]

GRAPH_PLANES = [
    {"id":"P0_SOURCE_EVIDENCE","authority":"PRIMARY_EVIDENCE","mutable_by_higher_planes":False,"products":["pinned Git trees","repository_graph v1","structural inventories","source/test/docs evidence"]},
    {"id":"P1_SEMANTIC_SURFACE","authority":"DERIVED_CANDIDATES","mutable_by_higher_planes":False,"products":["Graphify V2 semantic_surface_projection","registered/executable behavioral surfaces"]},
    {"id":"P2_COS20D_DECISION","authority":"DERIVED_PROVISIONAL_DECISIONS","mutable_by_higher_planes":False,"products":["COS-20L runtime facets","COS-20D decision graph","promotion requirements"]},
    {"id":"P3_AGENT_CONTEXT","authority":"DERIVED_RECOVERY_VIEW","mutable_by_higher_planes":False,"products":["CURRENT_CONTEXT.json","CURRENT_CONTEXT.md","NEXT_ACTIONS pointers","HANDOFF pointers"]},
]


def authority_read_order(iteration_id: str) -> list[str]:
    iteration_state = str(iteration_state_path(iteration_id))
    return BASE_AUTHORITY_READ_ORDER[:12] + [iteration_state] + BASE_AUTHORITY_READ_ORDER[12:]


def _load_json(root: Path, relative: str | Path) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _read_jsonl(root: Path, relative: str) -> list[dict[str, Any]]:
    path = root / relative
    if not path.exists():
        return []
    return [json.loads(raw) for raw in path.read_text(encoding="utf-8").splitlines() if raw.strip()]


def _latest_by_id(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if value:
            latest[str(value)] = row
    return latest


def build_context_pack(root: Path = ROOT) -> dict[str, Any]:
    goal = _load_json(root, "GOAL_STATE.json")
    execution = _load_json(root, "EXECUTION_STATE.json")
    active_iteration = str(execution["active_iteration"])
    iteration_path = iteration_state_path(active_iteration)
    iteration = _load_json(root, iteration_path)
    dimensions = _load_json(root, DIMENSIONS_JSON)
    plan = _load_json(root, NEXT_ACTIONS_JSON)
    risks = _latest_by_id(_read_jsonl(root, "ledgers/RISK_LEDGER.ndjson"), "risk_id")
    decisions = _latest_by_id(_read_jsonl(root, "ledgers/DECISION_LEDGER.ndjson"), "decision_id")
    claims = _latest_by_id(_read_jsonl(root, "ledgers/CLAIM_LEDGER.ndjson"), "claim_id")
    evidence_rows = _latest_by_id(_read_jsonl(root, "ledgers/EVIDENCE_LEDGER.ndjson"), "evidence_id")

    active_claims = [
        {"claim_id":row["claim_id"],"wave_id":row.get("wave_id"),"owner":row.get("owner"),"status":row.get("status")}
        for row in claims.values() if row.get("status") == "ACTIVE"
    ]
    open_risks = [
        {"risk_id":row["risk_id"],"severity":row.get("severity"),"status":row.get("status")}
        for row in risks.values() if row.get("status") in {"OPEN", "MITIGATING"}
    ]
    accepted_decisions = sorted(row["decision_id"] for row in decisions.values() if row.get("status") == "ACCEPTED")
    pins = {pin.id: pin.pinned_commit for pin in load_upstream_pins(root / "UPSTREAM_LEDGER.yaml")}
    read_order = authority_read_order(active_iteration)

    pack = {
        "schema_version":1,
        "protocol":"COS-GRAPH-ENGINE-V2-20D",
        "project":{"project_id":execution["goal_id"],"repository":"rotprods/Clever-Agent"},
        "frontier":{
            "checkpoint":execution["current_checkpoint"],"iteration":active_iteration,
            "subcheckpoint":execution["active_subcheckpoint"],"next_wave":execution["next_wave"],
            "next_wave_name":execution["next_wave_name"],"completed_waves":execution.get("completed_waves",[]),
            "parity_denominator_status":iteration.get("parity_denominator_status"),
            "blocking_issues":execution.get("blocking_issues",[]),
        },
        "upstream_refs":dict(sorted(pins.items())),
        "authority_read_order":read_order,
        "graph_planes":GRAPH_PLANES,
        "dimension_model":{"id":dimensions["dimension_model"],"count":len(dimensions["dimensions"]),"registry_path":str(DIMENSIONS_JSON)},
        "hard_invariants":{
            "chat_is_authority":False,"raw_graph_is_not_parity_denominator":True,"candidate_is_not_capability":True,
            "source_graph_is_immutable":True,"cos_decisions_are_provisional_until_promoted":True,
            "automatic_destructive_merge_forbidden":True,"migration_requires_behavioral_equivalence_evidence":True,
            "context_pack_is_derived_not_primary_truth":True,"max_context_loss_interactions":1,
        },
        "active_claims":sorted(active_claims,key=lambda row:row["claim_id"]),
        "open_risks":sorted(open_risks,key=lambda row:row["risk_id"]),
        "accepted_decision_ids":accepted_decisions,
        "evidence_ids":sorted(evidence_rows),
        "ledger_pointers":{
            "claims":"ledgers/CLAIM_LEDGER.ndjson","risks":"ledgers/RISK_LEDGER.ndjson",
            "decisions":"ledgers/DECISION_LEDGER.ndjson","evidence":"ledgers/EVIDENCE_LEDGER.ndjson",
            "capabilities":"ledgers/CAPABILITY_LEDGER.jsonl",
        },
        "planning":{
            "regression":"docs/REGRESSION_2026-08-31.md","consciousness_act":"docs/ACTA_DE_CONSCIENCIA.md",
            "implementation_plan":"IMPLEMENTATION_PLAN.md","tasks":"TASKS.md","next_actions":str(NEXT_ACTIONS_JSON),
            "first_executable_task":plan["first_executable_task"],"task_count":len(plan["tasks"]),
            "active_iteration_state":str(iteration_path),
        },
        "required_next_outputs":execution.get("required_next_outputs",[]),
        "recovery_commands":[
            "python scripts/validate_agentic_state.py","python scripts/context/validate_context_pack.py",
            "python scripts/context/build_context_pack.py --check","python scripts/context/validate_next_actions.py","/empezarproyecto",
        ],
    }
    if goal.get("active_checkpoint") != pack["frontier"]["checkpoint"]:
        raise ValueError("GOAL_STATE/EXECUTION_STATE checkpoint drift while building ContextPack")
    if goal.get("active_iteration") != active_iteration:
        raise ValueError("GOAL_STATE/EXECUTION_STATE iteration drift while building ContextPack")
    if iteration.get("checkpoint_id") != pack["frontier"]["checkpoint"]:
        raise ValueError("active iteration/checkpoint drift while building ContextPack")
    if plan.get("frontier_wave") != pack["frontier"]["next_wave"]:
        raise ValueError("NEXT_ACTIONS/EXECUTION_STATE frontier drift while building ContextPack")
    return pack


def render_markdown(pack: dict[str, Any]) -> str:
    frontier = pack["frontier"]
    lines = [
        "# CURRENT CONTEXT — Clever-Agent", "",
        "> Deterministic derived recovery view. It is never a primary source of truth; Git, canonical state and evidence outrank it.", "",
        "## Frontier", "", f"- Project: `{pack['project']['project_id']}`",
        f"- Checkpoint: `{frontier['checkpoint']}`", f"- Iteration: `{frontier['iteration']}` / `{frontier['subcheckpoint']}`",
        f"- Next wave: `{frontier['next_wave']} — {frontier['next_wave_name']}`",
        f"- Parity denominator: `{frontier['parity_denominator_status']}`", f"- Protocol: `{pack['protocol']}`",
        f"- 20D model: `{pack['dimension_model']['id']}` ({pack['dimension_model']['count']} dimensions)", "",
        "## Planning", "", f"- First executable task: `{pack['planning']['first_executable_task']}`",
        f"- Active iteration state: `{pack['planning']['active_iteration_state']}`",
        f"- Machine task graph: `{pack['planning']['next_actions']}`", f"- Implementation plan: `{pack['planning']['implementation_plan']}`",
        f"- Regression: `{pack['planning']['regression']}`", f"- Acta de consciencia: `{pack['planning']['consciousness_act']}`", "",
        "## Hard invariants", "",
    ]
    for key, value in pack["hard_invariants"].items():
        lines.append(f"- `{key}` = `{str(value).lower() if isinstance(value, bool) else value}`")
    lines.extend(["", "## Active claims", ""])
    for row in pack["active_claims"]:
        lines.append(f"- `{row['claim_id']}` → `{row.get('wave_id')}` · `{row.get('owner')}`")
    lines.extend(["", "## Open / mitigating risks", ""])
    for row in pack["open_risks"]:
        lines.append(f"- `{row['risk_id']}` · `{row.get('severity')}` · `{row.get('status')}` · detail in `ledgers/RISK_LEDGER.ndjson`")
    lines.extend(["", "## Recovery order", ""])
    for index, path in enumerate(pack["authority_read_order"], start=1):
        lines.append(f"{index}. `{path}`")
    lines.extend(["", "## Resume", ""])
    for command in pack["recovery_commands"]:
        lines.append(f"- `{command}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic COS V2 future-agent ContextPack")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    pack = build_context_pack(ROOT)
    expected_json = json.dumps(pack, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(pack)
    json_path, md_path = ROOT / CONTEXT_JSON, ROOT / CONTEXT_MD
    if args.check:
        if json_path.read_text(encoding="utf-8") != expected_json:
            raise SystemExit("CURRENT_CONTEXT.json drift: regenerate ContextPack")
        if md_path.read_text(encoding="utf-8") != expected_md:
            raise SystemExit("CURRENT_CONTEXT.md drift: regenerate ContextPack")
        print("OK: deterministic ContextPack matches canonical state")
        return 0
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(expected_json, encoding="utf-8")
    md_path.write_text(expected_md, encoding="utf-8")
    print(f"Wrote {json_path.relative_to(ROOT)} and {md_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
