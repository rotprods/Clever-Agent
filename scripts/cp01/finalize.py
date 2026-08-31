from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from typing import Any

from scripts.context.build_context_pack import main as _unused_context_main  # ensures importability
from scripts.context.iteration import iteration_state_path

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-09-01"


def _load(path: str | Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _write(path: str | Path, payload: dict[str, Any]) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_jsonl(path: str, row: dict[str, Any], *, id_key: str | None = None) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if id_key and target.exists():
        for raw in target.read_text(encoding="utf-8").splitlines():
            if raw.strip() and json.loads(raw).get(id_key) == row.get(id_key):
                return
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def _release_active_claims() -> None:
    path = ROOT / "ledgers/CLAIM_LEDGER.ndjson"
    latest: dict[str, dict[str, Any]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            row = json.loads(raw)
            if row.get("claim_id"):
                latest[str(row["claim_id"])] = row
    for claim_id, row in latest.items():
        if row.get("status") == "ACTIVE":
            _append_jsonl("ledgers/CLAIM_LEDGER.ndjson", {
                "schema_version":1,"date":DATE,"claim_id":claim_id,"event":"RELEASED_AT_CP01_TRANSITION",
                "wave_id":row.get("wave_id"),"owner":row.get("owner"),"status":"RELEASED","release_evidence_id":"EVID-0006"
            })


def _update_config() -> None:
    path = ROOT / ".agentic/CONFIG.yaml"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^  active_iteration: I[0-9]+$", "  active_iteration: I02", text, count=1)
    text = re.sub(r"(?m)^  active_checkpoint: CP[0-9]+$", "  active_checkpoint: CP02", text, count=1)
    text = re.sub(
        r"(?ms)^current_iteration:\n(?:  .*\n?)*\Z",
        "current_iteration:\n  id: I02\n  metaprompt: iterations/02/METAPROMPT.md\n  plan: iterations/02/ITERATION.md\n  state: iterations/02/STATE.json\n  next_wave: CP02-W01\n",
        text,
    )
    path.write_text(text, encoding="utf-8")


def _update_checkpoints() -> None:
    registry = _load("CHECKPOINT_REGISTRY.json")
    for row in registry["checkpoints"]:
        if row["id"] == "CP01":
            row["status"] = "COMPLETE"
        elif row["id"] == "CP02":
            row["status"] = "IN_PROGRESS"
    _write("CHECKPOINT_REGISTRY.json", registry)
    path = ROOT / "CHECKPOINTS.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("| CP01 | Forensic upstream inventory | IN_PROGRESS |", "| CP01 | Forensic upstream inventory | COMPLETE |")
    text = text.replace("| CP02 | Canonical contracts + Rust kernel scaffold | PENDING |", "| CP02 | Canonical contracts + Rust kernel scaffold | IN_PROGRESS |")
    if "## CP01 release — COMPLETE" not in text:
        text += "\n## CP01 release — COMPLETE\n\nCP01 closed from exact-source release evidence. The generated denominator is a behavior-mapped integration denominator, not a claim of Clever adapter parity. CP02 is now active.\n"
    path.write_text(text, encoding="utf-8")


def _update_plan() -> None:
    plan = _load(".agentic/context/NEXT_ACTIONS.json")
    for row in plan["tasks"]:
        if row["id"].startswith(("W03-","W04-","W05-","W06-","W07-","W08-")):
            row["status"] = "COMPLETE"
        if row["id"] == "CP02-001":
            row["status"] = "READY"
            row["wave"] = "CP02-W01"
    existing = {row["id"] for row in plan["tasks"]}
    extra = [
        {"id":"CP02-002","priority":"P4","wave":"CP02-W02","status":"BLOCKED","depends_on":["CP02-001"],"owner_role":"protocol_engineer","objective":"Create cross-runtime canonical fixtures/binding strategy and round-trip/version-skew tests.","outputs":["contracts/fixtures/**","tests/contracts/**"],"gates":["round-trip","unknown-version fail-safe","version-skew tests"]},
        {"id":"CP02-003","priority":"P4","wave":"CP02-W03","status":"BLOCKED","depends_on":["CP02-002"],"owner_role":"rust_lead","objective":"Scaffold Rust kernel identity/event/capability/policy primitives behind canonical contracts.","outputs":["kernel/Cargo.toml","kernel/crates/**"],"gates":["cargo test","no provider-specific kernel coupling"]},
        {"id":"CP02-004","priority":"P4","wave":"CP02-W04","status":"BLOCKED","depends_on":["CP02-003"],"owner_role":"rust_lead","objective":"Implement action receipts/idempotency, lifecycle health and append-only audit primitives.","outputs":["kernel/crates/**"],"gates":["replay/idempotency tests","false-green health tests"]},
        {"id":"CP02-005","priority":"P4","wave":"CP02-W05","status":"BLOCKED","depends_on":["CP02-004"],"owner_role":"reviewer_gauntlet","objective":"Run contract/kernel security, malformed-input, version-skew and recovery gauntlet.","outputs":["evidence/cp02/gauntlet/**"],"gates":["no critical contract/security/recovery defect"]},
        {"id":"CP02-006","priority":"P4","wave":"CP02-W06","status":"BLOCKED","depends_on":["CP02-005"],"owner_role":"release_reconciler","objective":"Reconcile CP02 evidence and advance to CP03 only if checkpoint exit criteria pass.","outputs":["CHECKPOINT_REGISTRY.json","STATE.md","HANDOFF.md"],"gates":["CP02 exit criteria proven"]},
    ]
    for row in extra:
        if row["id"] not in existing:
            plan["tasks"].append(row)
    plan["checkpoint"] = "CP02"
    plan["iteration"] = "I02"
    plan["frontier_wave"] = "CP02-W01"
    plan["first_executable_task"] = "CP02-001"
    _write(".agentic/context/NEXT_ACTIONS.json", plan)


def _update_human_docs(source_sha: str, denominator: int, surface_count: int) -> None:
    state = f"""# STATE — Clever-Agent live pointer\n\n> Machine mirrors and evidence outrank this human-readable pointer if drift is detected.\n\n## Current\n\n- Goal: `CLEVER-JARVIS-001`\n- Global status: `IN_PROGRESS`\n- Active checkpoint: `CP02 — Canonical contracts and Rust kernel scaffold`\n- Active iteration: `I02 — Canonical Contracts + Rust Kernel Scaffold`\n- Completed checkpoint: `CP01 — Forensic upstream inventory`\n- Next executable wave: `CP02-W01 — Canonical contract schemas`\n- First executable task: `CP02-001`\n- CP01 behavior-mapped denominator: `{denominator}`\n- Clever VERIFIED parity: `0 / {denominator}` (expected; adapter parity begins later)\n\n## CP01 release evidence\n\n- Exact compiler source SHA: `{source_sha}`\n- Semantic surfaces accounted: `{surface_count}`\n- Behavior-mapped denominator: `{denominator}`\n- Migration authorized: `false`\n- Cross-repo automatic dedupe: `false`\n- `NOT_RUN` treated as PASS: `false`\n\n## Canonical frontier\n\nExecute `/empezarproyecto`, claim `CP02-W01`, read `reports/CP01_CAPABILITY_REPORT.md` and `reports/CP02_CONTRACT_REQUIREMENTS.md`, then define the versioned contract schemas before writing kernel behavior.\n"""
    (ROOT / "STATE.md").write_text(state, encoding="utf-8")
    handoff = f"""# HANDOFF — Clever-Agent\n\n## Transition\n\n- Source checkpoint: `CP01` — COMPLETE\n- Active checkpoint: `CP02` — IN_PROGRESS\n- Iteration: `I02`\n- Next wave: `CP02-W01`\n- First task: `CP02-001`\n- CP01 source SHA: `{source_sha}`\n- Denominator: `{denominator}` behavior-mapped capabilities\n- Clever VERIFIED: `0`\n\n## What CP01 proved\n\nExact-source acquisition, structural census, behavioral-surface extraction, denominator generation, baseline classification, supply-chain inventory, capability graph/COS20D gauntlet and evidence-derived CP02 requirements all passed. CP01 did not claim adapter parity or authorize migration.\n\n## Next action\n\n1. `/empezarproyecto`.\n2. Read `iterations/02/METAPROMPT.md`.\n3. Claim `CP02-W01`.\n4. Read `reports/CP02_CONTRACT_REQUIREMENTS.md` and the CP01 capability report.\n5. Implement versioned Protobuf + JSON Schema contracts and contract fixtures before the Rust kernel scaffold.\n"""
    (ROOT / "HANDOFF.md").write_text(handoff, encoding="utf-8")
    tasks = """# TASKS — CLEVER-JARVIS-001 executable backlog\n\nMachine authority: `.agentic/context/NEXT_ACTIONS.json`.\n\n## CP01 — COMPLETE\n\n- [x] W03 behavioral surfaces\n- [x] W04 capability denominator\n- [x] W05 baseline classification\n- [x] W06 supply-chain/license inventory\n- [x] W07 capability graph + COS20D gauntlet\n- [x] W08 release candidate + CP02 requirements\n\n## CP02 — ACTIVE\n\n- [ ] **CP02-001 / CP02-W01 — Canonical schema contracts.**\n- [ ] **CP02-002 / CP02-W02 — Cross-runtime fixtures/bindings + round-trip/version-skew tests.**\n- [ ] **CP02-003 / CP02-W03 — Rust kernel identity/event/capability/policy scaffold.**\n- [ ] **CP02-004 / CP02-W04 — Action receipts/idempotency/lifecycle/audit.**\n- [ ] **CP02-005 / CP02-W05 — Security/recovery/version-skew gauntlet.**\n- [ ] **CP02-006 / CP02-W06 — Reconcile and close CP02.**\n\nNo native upstream implementation is removed in CP02.\n"""
    (ROOT / "TASKS.md").write_text(tasks, encoding="utf-8")
    implementation = """# IMPLEMENTATION PLAN — CLEVER-JARVIS-001\n\n## Current position\n\n- CP01: COMPLETE.\n- CP02: IN_PROGRESS.\n- Iteration: I02.\n- Frontier: `CP02-W01 / CP02-001`.\n- CP01 denominator: generated and unverified at Clever adapter level.\n\n## CP02 sequence\n\n1. **CP02-W01:** versioned Protobuf + JSON Schema contracts for identity, events, capabilities, actions/policy/receipts, memory/state, lifecycle/health, traces/evaluation and perception/embodiment.\n2. **CP02-W02:** canonical fixtures + Rust/Python/TypeScript/Swift binding/codegen strategy; round-trip, malformed payload and version-skew tests.\n3. **CP02-W03:** Rust kernel scaffold for identity/event/capability/policy only.\n4. **CP02-W04:** idempotent action receipts, lifecycle/health and append-only audit.\n5. **CP02-W05:** adversarial security/recovery/version-skew gauntlet.\n6. **CP02-W06:** evidence reconciliation and CP02 close.\n\n## Stop conditions\n\n- Contracts before kernel implementation.\n- No provider/channel/device-specific logic in the kernel.\n- No state migration or upstream deletion in CP02.\n- Unknown contract versions fail safely.\n- Side effects require policy correlation + idempotency + receipts.\n"""
    (ROOT / "IMPLEMENTATION_PLAN.md").write_text(implementation, encoding="utf-8")


def finalize(source_sha: str, run_id: str) -> None:
    candidate = _load("evidence/cp01/CP01_RELEASE_CANDIDATE.json")
    denominator = _load("reports/cp01/capability_denominator.json")
    if candidate.get("status") != "PASS" or not candidate.get("cp01_ready_for_state_transition"):
        raise RuntimeError("CP01 release candidate is not transition-ready")
    if candidate.get("candidate_sha") != source_sha:
        raise RuntimeError(f"release candidate/source SHA mismatch: {candidate.get('candidate_sha')} != {source_sha}")
    denom = int(denominator["denominator"])
    surface_count = int(denominator["source_surface_count"])
    if denom <= 0 or int(denominator.get("verified", -1)) != 0:
        raise RuntimeError("unexpected CP01 denominator/parity state")

    _update_checkpoints()
    goal = _load("GOAL_STATE.json")
    goal.update({
        "status":"IN_PROGRESS","active_checkpoint":"CP02","active_iteration":"I02",
        "frontier":"Execute /empezarproyecto at CP02-W01 and implement CP02-001 canonical versioned contracts before the Rust kernel scaffold.",
        "parity":{"verified":0,"total":denom,"ratio":0.0,"denominator_status":"GENERATED_UNVERIFIED"},
        "last_updated_date":DATE,
    })
    _write("GOAL_STATE.json", goal)

    execution = _load("EXECUTION_STATE.json")
    execution.update({
        "branch":"main","mode":"canonical-contracts","current_checkpoint":"CP02","active_iteration":"I02",
        "active_subcheckpoint":"I02.1","next_wave":"CP02-W01","next_wave_name":"Canonical contract schemas",
        "completed_waves":["I01-W00","I01-W01","I01-W02","I01-W03","I01-W04","I01-W05","I01-W06","I01-W07","I01-W08"],
        "next_checkpoint":"CP03","blocking_issues":[],
        "required_next_outputs":["versioned canonical Protobuf and JSON Schema contracts","canonical cross-runtime fixtures","Rust/Python/TypeScript/Swift compatibility strategy","round-trip and version-skew tests","Rust kernel identity/event/capability/policy scaffold"],
    })
    _write("EXECUTION_STATE.json", execution)

    i01 = _load("iterations/01/STATE.json")
    i01.update({"status":"COMPLETE","completed_subcheckpoints":[f"I01.{index}" for index in range(9)],"active_subcheckpoint":"COMPLETE","next_wave":None,"next_wave_name":None,"blocking_issues":[],"parity_denominator_status":"GENERATED_UNVERIFIED","last_updated_date":DATE})
    _write("iterations/01/STATE.json", i01)
    i02 = _load("iterations/02/STATE.json")
    i02.update({"status":"IN_PROGRESS","completed_subcheckpoints":["I02.0"],"active_subcheckpoint":"I02.1","next_wave":"CP02-W01","next_wave_name":"Canonical contract schemas","parity_denominator_status":"GENERATED_UNVERIFIED","last_updated_date":DATE})
    _write("iterations/02/STATE.json", i02)

    _update_config()
    _update_plan()
    _release_active_claims()

    _append_jsonl("ledgers/EVIDENCE_LEDGER.ndjson", {
        "schema_version":1,"date":DATE,"evidence_id":"EVID-0006","status":"VERIFIED","type":"cp01_full_release_compiler",
        "claim":"W01-W08 compiled from one exact source candidate and satisfied the CP01 release invariants before state transition.",
        "github_actions_run_id":int(run_id) if str(run_id).isdigit() else run_id,"source_sha":source_sha,
        "denominator":denom,"source_surface_count":surface_count,"clever_verified":0,
        "paths":["evidence/cp01/**","inventory/surfaces/**","ledgers/CAPABILITY_LEDGER.jsonl","graphs/capability_graph.json","reports/CP01_CAPABILITY_REPORT.md","reports/CP02_CONTRACT_REQUIREMENTS.md","licenses/UPSTREAM_NOTICES.md"]
    }, id_key="evidence_id")
    _append_jsonl("ledgers/DECISION_LEDGER.ndjson", {
        "schema_version":1,"date":DATE,"decision_id":"D-0011","status":"ACCEPTED",
        "decision":"Close CP01 and enter CP02 from the exact-source full-compiler release candidate while preserving VERIFIED parity at zero and forbidding migration.",
        "context":"CP01 release candidate passed all W03-W08 invariants and produced a non-empty behavior-mapped denominator."
    }, id_key="decision_id")
    _append_jsonl("ledgers/RUN_LOG.ndjson", {"schema_version":1,"date":DATE,"event":"CP01_RELEASE_TRANSITION","goal_id":"CLEVER-JARVIS-001","checkpoint":"CP02","iteration":"I02","wave_id":"CP02-W01","status":"ADVANCED","source_sha":source_sha,"run_id":run_id,"denominator":denom})
    for wave in ("I01-W03","I01-W04","I01-W05","I01-W06","I01-W07","I01-W08"):
        _append_jsonl("ledgers/WAVE_LEDGER.ndjson", {"schema_version":1,"date":DATE,"wave_id":wave,"event":"RELEASE_RECONCILIATION","status":"COMPLETE","evidence_id":"EVID-0006"})
    _append_jsonl("ledgers/WAVE_LEDGER.ndjson", {"schema_version":1,"date":DATE,"wave_id":"CP02-W01","iteration":"I02","checkpoint":"CP02","objective":"Compile versioned canonical contracts from CP01 evidence.","status":"PROPOSED"})

    _update_human_docs(source_sha, denom, surface_count)
    _update_config()
    changelog = ROOT / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8")
    marker = "### CP01 forensic compiler release"
    if marker not in text:
        text += f"\n{marker}\n\n- W03-W08 full compiler passed from exact source `{source_sha}`.\n- Persisted `{denom}`-row behavior-mapped capability denominator; Clever VERIFIED parity remains 0.\n- Closed CP01 and opened CP02 / I02 with contract-first Rust-kernel frontier.\n"
        changelog.write_text(text, encoding="utf-8")

    act = ROOT / "docs/ACTA_DE_CONSCIENCIA.md"
    act_text = act.read_text(encoding="utf-8")
    if "## CP01 cerrado — 2026-09-01" not in act_text:
        act_text += f"\n## CP01 cerrado — 2026-09-01\n\nEl compilador W01–W08 pasó sobre `{source_sha}` y produjo un denominador behavior-mapped de `{denom}` capacidades. Esto **no** significa 100% de parity implementada en Clever-Agent: `VERIFIED=0` al entrar en CP02. La siguiente misión es convertir la presión real del corpus en contratos canónicos antes del kernel Rust.\n"
        act.write_text(act_text, encoding="utf-8")

    from scripts.context.build_context_pack import build_context_pack, render_markdown, CONTEXT_JSON, CONTEXT_MD
    pack = build_context_pack(ROOT)
    (ROOT / CONTEXT_JSON).write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / CONTEXT_MD).write_text(render_markdown(pack), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist exact-source CP01 release outputs and atomically enter CP02")
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    args = parser.parse_args()
    finalize(args.source_sha, str(args.run_id))
    print(f"CP01 finalized from {args.source_sha}; CP02-W01 is now the durable frontier")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
