"""Finalize the CP03-W02 scope-lock support transaction after verified CI evidence.

This advances only the subordinate W02 task graph from W02-00/01 to W02-02.
It does not close CP03-W02 and does not change parity.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-09-07"
EVID = "EVID-W02-SCOPE-LOCK-20260907"
CLAIM = "CLAIM-CP03-W02-SCOPE-LOCK-001"
LOCK_RUN = 34158286005
LOCK_HEAD = "04dc2964d249a569255dc7bca43ee357b5e589cb"
LOCK_ARTIFACT = 10031706982
LOCK_DIGEST = "sha256:fe0c60231a84be51b647417136abe9d3687f374da630d323c16ad28af388d2f9"
AGENTIC_RUN = 34158285968

def read_json(path: str) -> dict[str, Any]: return json.loads((ROOT/path).read_text(encoding="utf-8"))
def write_json(path: str, value: dict[str, Any]) -> None: (ROOT/path).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def read_rows(path: str) -> list[dict[str, Any]]: return [json.loads(line) for line in (ROOT/path).read_text(encoding="utf-8").splitlines() if line.strip()]
def append_unique(path: str, key: str, value: str, row: dict[str, Any]) -> None:
    if any(r.get(key)==value for r in read_rows(path)): return
    with (ROOT/path).open("a",encoding="utf-8") as h: h.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")
def latest_claim_status(claim_id: str) -> str | None:
    status=None
    for row in read_rows("ledgers/CLAIM_LEDGER.ndjson"):
        if row.get("claim_id")==claim_id and row.get("status"): status=str(row["status"])
    return status

def finalize() -> None:
    from scripts.cp03.w02_scope_lock import validate_root
    receipt=validate_root(ROOT)
    if receipt["status"]!="PASS" or receipt["w02_proof_units"]!=47: raise RuntimeError("scope lock proof is not valid")
    if receipt["parity_promotions"]!=0 or receipt["verified"]!=0: raise RuntimeError("scope lock attempted parity advancement")
    plan=read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    if plan.get("wave")!="CP03-W02" or plan.get("global_denominator")!=7565 or plan.get("openjarvis_obligations")!=646: raise RuntimeError("subordinate task graph authority drift")
    if plan.get("w02_obligation_count") not in (None,47): raise RuntimeError("unexpected existing W02 count")
    plan["status"]="IN_PROGRESS"; plan["w02_obligation_count"]=47; plan["first_executable_task"]="W02-02"
    tasks={row["id"]:row for row in plan["tasks"]}
    if set(("W02-00","W02-01","W02-02"))-set(tasks): raise RuntimeError("required subordinate tasks missing")
    tasks["W02-00"]["status"]="COMPLETE"
    tasks["W02-00"]["proof"]=[
      {"type":"agentic_contract","run_id":34157768857,"head":"47bfb577a83bc894db96412f056f876bf36d3273","result":"PASS"},
      {"type":"scope_lock_preflight","run_id":LOCK_RUN,"head":LOCK_HEAD,"result":"PASS"}]
    tasks["W02-01"]["status"]="COMPLETE"
    tasks["W02-01"]["proof"]=[
      {"evidence_id":"EVID-W02-FACETS-20260907","run_id":34157458150,"result":"PASS"},
      {"evidence_id":EVID,"run_id":LOCK_RUN,"artifact_id":LOCK_ARTIFACT,"result":"PASS","K":47,"owned":37,"shared":10}]
    tasks["W02-02"]["status"]="READY"; tasks["W02-02"]["proof"]=[]
    write_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json",plan)
    append_unique("ledgers/EVIDENCE_LEDGER.ndjson","evidence_id",EVID,{"schema_version":1,"date":DATE,"evidence_id":EVID,"status":"VERIFIED","type":"cp03_w02_scope_lock","wave_id":"CP03-W02","claim":"Clean-room recomputation freezes the W02 proof scope at 47 units (37 owned, 10 shared) without denominator mutation or parity promotion; shared capabilities cannot become terminal from W02 evidence alone.","github_actions_run_id":LOCK_RUN,"agentic_run_id":AGENTIC_RUN,"validated_head":LOCK_HEAD,"artifact_id":LOCK_ARTIFACT,"artifact_digest":LOCK_DIGEST,"global_denominator":7565,"openjarvis_obligations":646,"w02_proof_units":47,"w02_owned_capabilities":37,"w02_shared_capabilities":10,"shared_terminal_forbidden":True,"human_review":False,"review_type":"DETERMINISTIC_CLEAN_ROOM_VALIDATION","parity_promotions":0})
    if latest_claim_status(CLAIM)!="RELEASED":
        with (ROOT/"ledgers/CLAIM_LEDGER.ndjson").open("a",encoding="utf-8") as h: h.write(json.dumps({"schema_version":1,"date":DATE,"claim_id":CLAIM,"event":"RELEASE","wave_id":"CP03-W02-SCOPE-LOCK-20260907","owner":"chatgpt-gpt-5.6-sol","status":"RELEASED","release_evidence_id":EVID},sort_keys=True,separators=(",",":"))+"\n")
    append_unique("ledgers/RUN_LOG.ndjson","event_id","RUN-W02-SCOPE-LOCK-20260907",{"schema_version":1,"date":DATE,"event_id":"RUN-W02-SCOPE-LOCK-20260907","event":"CP03_W02_SCOPE_LOCKED","goal_id":"CLEVER-JARVIS-001","checkpoint":"CP03","iteration":"I03","wave_id":"CP03-W02","support_wave":"CP03-W02-SCOPE-LOCK-20260907","status":"ADVANCED","evidence_id":EVID,"next_task":"W02-02","K":47,"parity_promotions":0})
    append_unique("ledgers/WAVE_LEDGER.ndjson","event_id","WAVE-W02-SCOPE-LOCK-20260907",{"schema_version":1,"date":DATE,"event_id":"WAVE-W02-SCOPE-LOCK-20260907","wave_id":"CP03-W02-SCOPE-LOCK-20260907","parent_wave":"CP03-W02","iteration":"I03","checkpoint":"CP03","event":"VERIFICATION","status":"COMPLETE","evidence_id":EVID,"next_task":"W02-02"})
    (ROOT/"HANDOFF.md").write_text("# HANDOFF — CP03-W02\n\n- Checkpoint: `CP03`\n- Iteration: `I03`\n- Parent wave: `CP03-W02` remains `IN_PROGRESS`.\n- Scope lock: `COMPLETE` — `EVID-W02-SCOPE-LOCK-20260907`.\n- Frozen W02 proof scope: **47 units = 37 owned + 10 shared**; global denominator 7,565 / OpenJarvis 646 / VERIFIED 0.\n- Shared capabilities are non-terminal in W02 until their other CP03 facets are proven.\n- Subordinate complete: `W02-00`, `W02-01`.\n- Next executable: `W02-02 — Eliminate false-green harness behavior`.\n\nRun `/empezarproyecto`, validate ContextPack/state, then read `iterations/03/waves/CP03-W02/METAPROMPT.md`. PR #15 and its publication boundary remain independent and untouched. W02-02/03+ are not complete; no inference or model parity has been claimed.\n",encoding="utf-8")

if __name__=="__main__":
    finalize(); print(json.dumps({"status":"ADVANCED","parent_wave":"CP03-W02","scope_locked":True,"K":47,"owned":37,"shared":10,"next_task":"W02-02","parity_promotions":0},sort_keys=True))
