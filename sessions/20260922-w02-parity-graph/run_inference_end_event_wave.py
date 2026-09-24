from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = Path("/tmp/openjarvis")
EXPECTED_MAIN = os.environ["EXPECTED_MAIN"]
UPSTREAM_COMMIT = os.environ["UPSTREAM_COMMIT"]
CLAIM_ID = os.environ["CLAIM_ID"]
WAVE_ID = os.environ["WAVE_ID"]
CAPABILITY_ID = os.environ["CAPABILITY_ID"]
EVIDENCE_ID = os.environ["EVIDENCE_ID"]
DECISION_ID = os.environ["DECISION_ID"]
SOURCE_EVIDENCE_ID = os.environ["SOURCE_EVIDENCE_ID"]
SOURCE_EVIDENCE_HEAD = os.environ["SOURCE_EVIDENCE_HEAD"]
TEST_ID = os.environ["TEST_ID"]
RUN_ID = int(os.environ["GITHUB_RUN_ID"])


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, text=True, capture_output=True)


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_jsonl(path: str) -> list[dict]:
    return [json.loads(x) for x in (ROOT / path).read_text(encoding="utf-8").splitlines() if x.strip()]


def append_once(path: str, key: str, value: str, row: dict) -> None:
    p = ROOT / path
    rows = read_jsonl(path)
    assert all(x.get(key) != value for x in rows), (path, key, value)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def preflight() -> None:
    g = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    tasks = {x["id"]: x for x in g["tasks"]}
    assert g["first_executable_task"] == "W02-17"
    assert tasks["W02-17"]["status"] == "IN_PROGRESS"
    assert tasks["W02-17"]["depends_on"] == ["W02-01", "W02-13", "W02-14", "W02-16"]
    assert all(tasks[d]["status"] == "COMPLETE" and tasks[d]["proof"] for d in tasks["W02-17"]["depends_on"])
    assert tasks["W02-18"]["status"] == "BLOCKED" and tasks["W02-19"]["status"] == "BLOCKED"
    assert g["global_denominator"] == 7565 and g["openjarvis_obligations"] == 646 and g["w02_obligation_count"] == 47

    claim = read_json("sessions/20260922-w02-parity-graph/CLAIM.json")
    assert claim["claim_id"] == CLAIM_ID and claim["wave_id"] == WAVE_ID
    assert claim["canonical_task"] == "W02-17" and claim["status"] == "ACTIVE" and claim["owner"] == "chatgpt-gpt-5.6-sol"
    for p in (
        ".github/workflows/cp03-w02-parity-graph.yml",
        "tests/test_cp03_w02_parity_graph.py",
        "inventory/cp03/w02_evidence_bindings.jsonl",
        "evidence/cp03/cp03-w02/W02-17/**",
        "STATE.md",
        "HANDOFF.md",
        "sessions/20260922-w02-parity-graph/**",
    ):
        assert p in claim["scope"]

    latest: dict[str, dict] = {}
    for row in read_jsonl("ledgers/CLAIM_LEDGER.ndjson"):
        if row.get("claim_id"):
            latest[row["claim_id"]] = row
    active = latest[CLAIM_ID]
    assert active["status"] == "ACTIVE" and active["wave_id"] == WAVE_ID and active["owner"] == "chatgpt-gpt-5.6-sol"

    summary = read_json("reports/cp03/w02_parity/SUMMARY.json")
    assert summary["binding_counts"] == {"EVIDENCE_BACKED_CANDIDATE": 22, "UNBOUND": 25}
    assert summary["verified_capabilities"] == 0 and summary["parity_promotions"] == 0
    assert summary["global_denominator"] == 7565 and summary["openjarvis_obligations"] == 646

    matrix = read_jsonl("reports/cp03/w02_parity/PROOF_MATRIX.jsonl")
    target = next(x for x in matrix if x["capability_id"] == CAPABILITY_ID)
    assert target["name"] == "InferenceEndEvent" and target["surface_kind"] == "protocol_contract"
    assert target["source_path"] == "frontend/src/types/index.ts" and target["source_line"] == 19
    assert target["ownership"] == "OWNED" and target["terminal_eligible_in_w02"] is True
    assert target["w02_evidence_state"] == "UNBOUND" and target["binding"] is None
    assert target["canonical_parity_status"] == "UNVERIFIED" and target["verified"] is False and target["parity_promotion"] is False
    afm = next(x for x in matrix if x["capability_id"] == "cap_ac38bf813e130d14927723d8")
    assert afm["w02_evidence_state"] == "UNBOUND" and afm["binding"] is None
    start = next(x for x in matrix if x["capability_id"] == "cap_a97068215f50aeff0353f6e9")
    assert start["w02_evidence_state"] == "UNBOUND" and start["binding"] is None


def probe_and_add_red_test() -> None:
    src = UPSTREAM / "frontend/src/types/index.ts"
    raw = src.read_bytes()
    text = raw.decode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    assert sha == "45e499e92306e7387ab99b2ee52f89fe18a63dd3f8bc8d33b7325582bf24e242"
    line = next(i + 1 for i, x in enumerate(text.splitlines()) if x.strip() == "export interface InferenceEndEvent {")
    assert line == 19
    match = re.search(r"export interface InferenceEndEvent \{\n(?P<body>.*?)\n\}", text, flags=re.S)
    assert match
    fields: list[dict[str, str]] = []
    for item in match.group("body").splitlines():
        q = re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_]*):\s*([^;]+);\s*", item)
        if q:
            fields.append({"name": q.group(1), "type": q.group(2)})
    expected = [
        {"name": "model", "type": "string"},
        {"name": "engine", "type": "string"},
        {"name": "turn", "type": "number"},
    ]
    assert fields == expected
    probe = {
        "schema_version": 1,
        "date": "2026-09-24",
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "task": "W02-17",
        "gate": "G6",
        "capability_id": CAPABILITY_ID,
        "capability_name": "InferenceEndEvent",
        "surface_kind": "protocol_contract",
        "ownership": "OWNED",
        "terminal_eligible_in_w02": True,
        "upstream_commit": UPSTREAM_COMMIT,
        "source_path": "frontend/src/types/index.ts",
        "source_line": line,
        "source_sha256": sha,
        "source_probe": "PASS",
        "source_execution": False,
        "interface_fields": fields,
        "inference_end_event_runtime_execution": "NOT_RUN",
        "model_executions": 0,
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "canonical_parity_status": "UNVERIFIED",
        "parity_promotions": 0,
    }
    (ROOT / "evidence/cp03/cp03-w02/W02-17/binding_inference_end_event_protocol_source_probe.json").write_text(
        json.dumps(probe, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    p = ROOT / "tests/test_cp03_w02_parity_graph.py"
    t = p.read_text(encoding="utf-8")
    assert "INFERENCE_END_EVENT_PROTOCOL_CAPABILITY_ID" not in t
    old = 'PROVIDER_SAVINGS_PROTOCOL_CAPABILITY_ID = "cap_56d79a86da34eeeacdf49427"\n'
    assert old in t
    t = t.replace(old, old + 'INFERENCE_END_EVENT_PROTOCOL_CAPABILITY_ID = "cap_a2a75f0ee048f59cf65c028b"\n', 1)
    marker = (
        'PROVIDER_SAVINGS_PROTOCOL_TEST_ID = (\n'
        '    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n'
        '    "test_provider_savings_protocol_binding_is_capability_specific_and_source_backed"\n'
        ')\n'
    )
    assert marker in t
    t = t.replace(
        marker,
        marker
        + 'INFERENCE_END_EVENT_PROTOCOL_TEST_ID = (\n'
        + '    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n'
        + '    "test_inference_end_event_protocol_binding_is_capability_specific_and_source_backed"\n'
        + ')\n',
        1,
    )
    assert "def test_current_matrix_has_twenty_two_candidates_and_no_parity_promotion" in t
    t = t.replace(
        "def test_current_matrix_has_twenty_two_candidates_and_no_parity_promotion",
        "def test_current_matrix_has_twenty_three_candidates_and_no_parity_promotion",
        1,
    )
    assert '== "EVIDENCE_BACKED_CANDIDATE" for row in rows), 22)' in t
    assert '== "UNBOUND" for row in rows), 25)' in t
    t = t.replace('== "EVIDENCE_BACKED_CANDIDATE" for row in rows), 22)', '== "EVIDENCE_BACKED_CANDIDATE" for row in rows), 23)', 1)
    t = t.replace('== "UNBOUND" for row in rows), 25)', '== "UNBOUND" for row in rows), 24)', 1)
    tail = "CLI_SERVE_COMMAND_CAPABILITY_ID, PROVIDER_SAVINGS_PROTOCOL_CAPABILITY_ID},"
    assert tail in t
    t = t.replace(tail, "CLI_SERVE_COMMAND_CAPABILITY_ID, PROVIDER_SAVINGS_PROTOCOL_CAPABILITY_ID, INFERENCE_END_EVENT_PROTOCOL_CAPABILITY_ID},", 1)
    block = (
        '        provider_savings_protocol = candidates[PROVIDER_SAVINGS_PROTOCOL_CAPABILITY_ID]\n'
        '        self.assertEqual(provider_savings_protocol["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")\n'
        '        self.assertFalse(provider_savings_protocol["binding"]["terminal"])\n'
    )
    assert block in t
    t = t.replace(
        block,
        block
        + '        inference_end_event_protocol = candidates[INFERENCE_END_EVENT_PROTOCOL_CAPABILITY_ID]\n'
        + '        self.assertEqual(inference_end_event_protocol["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")\n'
        + '        self.assertFalse(inference_end_event_protocol["binding"]["terminal"])\n',
        1,
    )
    method_lines = [
        "    def test_inference_end_event_protocol_binding_is_capability_specific_and_source_backed(self) -> None:",
        '        row = next(row for row in self.result["rows"] if row["capability_id"] == INFERENCE_END_EVENT_PROTOCOL_CAPABILITY_ID)',
        '        self.assertEqual(row["ownership"], "OWNED")',
        '        self.assertEqual(row["surface_kind"], "protocol_contract")',
        '        self.assertEqual(row["source_path"], "frontend/src/types/index.ts")',
        '        self.assertEqual(row["source_line"], 19)',
        '        self.assertEqual(row["name"], "InferenceEndEvent")',
        '        self.assertTrue(row["terminal_eligible_in_w02"])',
        '        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")',
        '        self.assertEqual(row["w02_evidence_state"], "EVIDENCE_BACKED_CANDIDATE")',
        '        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")',
        '        self.assertFalse(row["verified"])',
        '        self.assertFalse(row["parity_promotion"])',
        '        binding = row["binding"]',
        '        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")',
        '        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")',
        '        self.assertEqual(binding["test_id"], INFERENCE_END_EVENT_PROTOCOL_TEST_ID)',
        '        self.assertFalse(binding["terminal"])',
        '        receipt = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")["EVID-W02-MODEL-BRIDGE-20260921"]',
        '        self.assertEqual(receipt["status"], "VERIFIED")',
        '        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")',
        '        self.assertEqual(receipt["native_engine_count"], 15)',
        '        self.assertEqual(receipt["native_import_failure_count"], 0)',
        '        self.assertEqual(receipt["native_model_count"], 69)',
        '        self.assertEqual(receipt["model_executions"], 0)',
        '        self.assertEqual(receipt["provider_egress_executions"], 0)',
        '        self.assertEqual(receipt["parity_promotions"], 0)',
        '        probe = json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_inference_end_event_protocol_source_probe.json").read_text(encoding="utf-8"))',
        '        self.assertEqual(probe["capability_id"], INFERENCE_END_EVENT_PROTOCOL_CAPABILITY_ID)',
        '        self.assertEqual(probe["source_line"], 19)',
        '        self.assertEqual(probe["source_probe"], "PASS")',
        '        self.assertFalse(probe["source_execution"])',
        '        self.assertEqual(probe["inference_end_event_runtime_execution"], "NOT_RUN")',
        '        self.assertEqual(probe["interface_fields"], [{"name":"model","type":"string"},{"name":"engine","type":"string"},{"name":"turn","type":"number"}])',
        '        self.assertEqual(probe["model_executions"], 0)',
        '        self.assertEqual(probe["provider_egress_executions"], 0)',
        '        self.assertEqual(probe["tool_executions"], 0)',
        '        self.assertEqual(probe["parity_promotions"], 0)',
        "",
    ]
    method = "\n".join(method_lines) + "\n"
    insert = "    def test_cli_model_list_command_binding_is_capability_specific_and_source_backed(self) -> None:\n"
    assert insert in t
    t = t.replace(insert, method + insert, 1)
    p.write_text(t, encoding="utf-8")


def red_then_bind_green() -> None:
    red = run("python", "-m", "unittest", "-v", TEST_ID, check=False)
    assert red.returncode != 0, red.stdout + red.stderr
    red_text = red.stdout + red.stderr
    assert any(token in red_text for token in ("AssertionError", "EVIDENCE_BACKED_CANDIDATE", "NoneType")), red_text

    path = ROOT / "inventory/cp03/w02_evidence_bindings.jsonl"
    rows = read_jsonl("inventory/cp03/w02_evidence_bindings.jsonl")
    assert len(rows) == 22 and all(x["capability_id"] != CAPABILITY_ID for x in rows)
    rows.append(
        {
            "capability_id": CAPABILITY_ID,
            "evidence_id": SOURCE_EVIDENCE_ID,
            "test_id": TEST_ID,
            "validated_head": SOURCE_EVIDENCE_HEAD,
            "expected_fields": {
                "status": "VERIFIED",
                "native_engine_count": 15,
                "native_import_failure_count": 0,
                "native_model_count": 69,
                "model_executions": 0,
                "provider_egress_executions": 0,
                "parity_promotions": 0,
            },
            "terminal": False,
        }
    )
    path.write_text("".join(json.dumps(x, separators=(",", ":")) + "\n" for x in rows), encoding="utf-8")
    run("python", "scripts/cp03/w02_parity_graph.py", "--write")
    green = run("python", "-m", "unittest", "-v", TEST_ID)
    assert green.returncode == 0


def persist() -> None:
    probe_path = ROOT / "evidence/cp03/cp03-w02/W02-17/binding_inference_end_event_protocol_source_probe.json"
    report = {
        "schema_version": 1,
        "date": "2026-09-24",
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "task": "W02-17",
        "gate": "G6",
        "claim_id": CLAIM_ID,
        "evidence_id": EVIDENCE_ID,
        "status": "PASS",
        "validated_base_head": EXPECTED_MAIN,
        "github_actions_run_id": RUN_ID,
        "binding_capability_id": CAPABILITY_ID,
        "binding_capability_name": "InferenceEndEvent",
        "binding_surface_kind": "protocol_contract",
        "binding_ownership": "OWNED",
        "terminal_eligible_in_w02": True,
        "binding_source_evidence_id": SOURCE_EVIDENCE_ID,
        "binding_source_validated_head": SOURCE_EVIDENCE_HEAD,
        "binding_source_run_id": 35552788123,
        "executed_test_id": TEST_ID,
        "source_probe_path": str(probe_path.relative_to(ROOT)),
        "source_probe_sha256": hashlib.sha256(probe_path.read_bytes()).hexdigest(),
        "source_execution": False,
        "inference_end_event_runtime_execution": "NOT_RUN",
        "bindings_added_this_slice": 1,
        "bindings_validated_total": 23,
        "unbound_remaining": 24,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "verified_capabilities": 0,
        "parity_promotions": 0,
        "model_executions": 0,
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "afm_inprocess_execution": "NOT_RUN",
        "real_openjarvis_fallback_model_execution": "NOT_RUN",
        "inference_start_event_binding": "UNBOUND_UNTOUCHED",
        "next_slice": "Continue W02-17 with another non-conflicting proof unit only when capability-specific executed or exact pinned-source evidence can be paired with an existing completed-task PASS receipt. AFM/fallback stay NOT_RUN and InferenceStartEvent remains outside this slice.",
    }
    report_path = ROOT / "evidence/cp03/cp03-w02/W02-17/binding_inference_end_event_protocol_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    append_once(
        "ledgers/CLAIM_LEDGER.ndjson",
        "event_id",
        "CLAIM-CONTINUE-W02-G6-INFERENCE-END-EVENT-PROTOCOL-20260924",
        {
            "schema_version": 1,
            "date": "2026-09-24",
            "event": "CONTINUE",
            "event_id": "CLAIM-CONTINUE-W02-G6-INFERENCE-END-EVENT-PROTOCOL-20260924",
            "claim_id": CLAIM_ID,
            "owner": "chatgpt-gpt-5.6-sol",
            "checkpoint": "CP03",
            "canonical_task": "W02-17",
            "wave_id": WAVE_ID,
            "status": "ACTIVE",
            "base_head": EXPECTED_MAIN,
            "coordination": "Continue the existing non-conflicting W02-17 G6 claim for one OWNED InferenceEndEvent source-proof unit only; runtime event behavior remains NOT_RUN, terminal attribution remains false, and parity/denominators/task frontier do not advance.",
        },
    )
    append_once("ledgers/EVIDENCE_LEDGER.ndjson", "evidence_id", EVIDENCE_ID, {**report, "type": "CP03_W02_G6_CAPABILITY_BINDING", "path": str(report_path.relative_to(ROOT))})
    append_once(
        "ledgers/DECISION_LEDGER.ndjson",
        "decision_id",
        DECISION_ID,
        {
            "schema_version": 1,
            "date": "2026-09-24",
            "decision_id": DECISION_ID,
            "status": "ACCEPTED",
            "checkpoint": "CP03",
            "task": "W02-17",
            "decision": "Bind the frozen OpenJarvis InferenceEndEvent protocol contract as a non-terminal EVIDENCE_BACKED_CANDIDATE only.",
            "context": "Exact pinned source proves only the TypeScript interface shape. W02-08 supplies the completed model-registration bridge receipt required by the G6 proof compiler. Runtime event emission/consumption remains NOT_RUN and no behavioral parity is inferred.",
            "evidence_id": EVIDENCE_ID,
            "parity_promotions": 0,
        },
    )
    append_once(
        "ledgers/RISK_LEDGER.ndjson",
        "event_id",
        "RISK-UPDATE-W02-G6-K47-BINDINGS-INFERENCE-END-EVENT-20260924",
        {
            "schema_version": 1,
            "date": "2026-09-24",
            "event_id": "RISK-UPDATE-W02-G6-K47-BINDINGS-INFERENCE-END-EVENT-20260924",
            "risk_id": "RISK-W02-G6-K47-BINDINGS-PENDING-20260922",
            "severity": "P1",
            "status": "OPEN",
            "task": "W02-17",
            "evidence_id": EVIDENCE_ID,
            "risk": "G6 remains incomplete: 24/47 frozen W02 proof units are UNBOUND. Source-backed InferenceEndEvent evidence does not prove runtime event emission, ordering, consumption or behavioral parity.",
            "mitigation": "Keep W02-17 IN_PROGRESS, VERIFIED=0 and W02-18 BLOCKED; require capability-specific runtime evidence before terminal parity and preserve all NOT_RUN/platform-gated states.",
        },
    )
    append_once(
        "ledgers/RUN_LOG.ndjson",
        "event_id",
        "RUN-W02-G6-INFERENCE-END-EVENT-PROTOCOL-20260924",
        {
            "schema_version": 1,
            "date": "2026-09-24",
            "event": "CP03_W02_G6_CAPABILITY_BINDING",
            "event_id": "RUN-W02-G6-INFERENCE-END-EVENT-PROTOCOL-20260924",
            "goal_id": "CLEVER-JARVIS-001",
            "checkpoint": "CP03",
            "iteration": "I03",
            "wave_id": "CP03-W02",
            "canonical_task": "W02-17",
            "claim_id": CLAIM_ID,
            "evidence_id": EVIDENCE_ID,
            "status": "ADVANCED",
            "bindings_validated_total": 23,
            "unbound_remaining": 24,
            "verified_capabilities": 0,
            "parity_promotions": 0,
        },
    )
    append_once(
        "ledgers/WAVE_LEDGER.ndjson",
        "event_id",
        "WAVE-W02-G6-INFERENCE-END-EVENT-PROTOCOL-20260924",
        {
            "schema_version": 1,
            "date": "2026-09-24",
            "event": "WAVE_PROGRESS",
            "event_id": "WAVE-W02-G6-INFERENCE-END-EVENT-PROTOCOL-20260924",
            "checkpoint": "CP03",
            "iteration": "I03",
            "parent_wave": "CP03-W02",
            "wave_id": WAVE_ID,
            "canonical_task": "W02-17",
            "claim_id": CLAIM_ID,
            "gate": "G6",
            "evidence_id": EVIDENCE_ID,
            "status": "IN_PROGRESS",
            "bindings_validated_total": 23,
            "unbound_remaining": 24,
            "parity_promotions": 0,
        },
    )

    state = ROOT / "STATE.md"
    text = state.read_text(encoding="utf-8")
    old = "- G6 explicit binding progress: `22/47` evidence-backed candidates; `25` UNBOUND; VERIFIED capabilities `0`; parity promotions `0`."
    new = "- G6 explicit binding progress: `23/47` evidence-backed candidates; `24` UNBOUND; VERIFIED capabilities `0`; parity promotions `0`."
    assert text.count(old) == 1
    state.write_text(text.replace(old, new, 1), encoding="utf-8")

    handoff = ROOT / "HANDOFF.md"
    h = handoff.read_text(encoding="utf-8").rstrip() + "\n\n"
    section = [
        "## W02-17 InferenceEndEvent protocol binding — source-backed partial verified",
        "",
        "- `EVID-W02-PARITY-BINDING-INFERENCE-END-EVENT-PROTOCOL-20260924`: `cap_a2a75f0ee048f59cf65c028b` (`InferenceEndEvent`, OWNED protocol contract at `frontend/src/types/index.ts:19`) is now a non-terminal `EVIDENCE_BACKED_CANDIDATE`.",
        "- Exact pinned source `72033b8ec288aa067ce4530ff9d96bf231e9c4e5` proves only the three-field TypeScript contract (`model:string`, `engine:string`, `turn:number`). Source execution and runtime event emission/consumption remain `NOT_RUN`.",
        "- Formal G6 binding remains anchored to completed W02-08 `EVID-W02-MODEL-BRIDGE-20260921` at exact SHA `a866c335a0f9cad75122c8eb7c5310d358f6aad4` plus `tests.test_cp03_w02_parity_graph.W02ParityGraphTests.test_inference_end_event_protocol_binding_is_capability_specific_and_source_backed`. Candidate evidence only: no terminal attribution, VERIFIED parity or promotion.",
        "- G6 is now 23 `EVIDENCE_BACKED_CANDIDATE` / 24 `UNBOUND`; VERIFIED 0; parity promotions 0; denominator 7565 and OpenJarvis obligations 646 unchanged. AFM/fallback remain `NOT_RUN`; InferenceStartEvent remains untouched; W02-18/W02-19 stay `BLOCKED`.",
        "- Exact next slice: another W02-17 proof unit with capability-specific executed or exact pinned-source evidence plus a completed-task receipt; do not infer runtime event semantics from this source contract.",
        "",
    ]
    handoff.write_text(h + "\n".join(section), encoding="utf-8")

    claim_path = ROOT / "sessions/20260922-w02-parity-graph/CLAIM.json"
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    assert claim["claim_id"] == CLAIM_ID and claim["status"] == "ACTIVE"
    claim["continuation_base_head"] = EXPECTED_MAIN
    claim_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
    (ROOT / "sessions/20260922-w02-parity-graph/RESULT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # EVIDENCE_LEDGER is an input hash for the proof plane, so regenerate after the append.
    run("python", "scripts/cp03/w02_parity_graph.py", "--write")
    run("python", "scripts/context/build_context_pack.py")


def gauntlet() -> None:
    run("python", "-m", "unittest", "-v", TEST_ID)
    run("python", "-m", "unittest", "-v", "tests.test_cp03_w02_parity_graph")
    run("python", "scripts/validate_agentic_state.py")
    run("python", "scripts/context/validate_context_pack.py")
    run("python", "scripts/context/build_context_pack.py", "--check")
    run("python", "scripts/context/validate_next_actions.py")
    run("python", "scripts/cp03/validate_w02_plan.py")
    run("python", "-m", "scripts.parity.ledger", "--check", "--source-repo", "openjarvis")
    run("python", "scripts/cp03/w02_parity_graph.py", "--check")

    s = read_json("reports/cp03/w02_parity/SUMMARY.json")
    assert s["binding_counts"] == {"EVIDENCE_BACKED_CANDIDATE": 23, "UNBOUND": 24}
    assert s["verified_capabilities"] == 0 and s["parity_promotions"] == 0
    assert s["global_denominator"] == 7565 and s["openjarvis_obligations"] == 646 and s["w02_proof_units"] == 47
    matrix = read_jsonl("reports/cp03/w02_parity/PROOF_MATRIX.jsonl")
    target = next(x for x in matrix if x["capability_id"] == CAPABILITY_ID)
    assert target["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE"
    assert target["canonical_parity_status"] == "UNVERIFIED" and target["verified"] is False and target["parity_promotion"] is False
    assert target["binding"]["terminal"] is False and target["binding"]["test_id"] == TEST_ID
    afm = next(x for x in matrix if x["capability_id"] == "cap_ac38bf813e130d14927723d8")
    assert afm["w02_evidence_state"] == "UNBOUND" and afm["binding"] is None
    start = next(x for x in matrix if x["capability_id"] == "cap_a97068215f50aeff0353f6e9")
    assert start["w02_evidence_state"] == "UNBOUND" and start["binding"] is None
    g = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    tasks = {x["id"]: x for x in g["tasks"]}
    assert g["first_executable_task"] == "W02-17" and tasks["W02-17"]["status"] == "IN_PROGRESS"
    assert tasks["W02-18"]["status"] == "BLOCKED" and tasks["W02-19"]["status"] == "BLOCKED"
    ctx = read_json(".agentic/context/CURRENT_CONTEXT.json")
    claim = next(x for x in ctx["active_claims"] if x["claim_id"] == CLAIM_ID)
    assert claim["wave_id"] == WAVE_ID and claim["status"] == "ACTIVE"
    assert EVIDENCE_ID in set(ctx["evidence_ids"])
    assert DECISION_ID in set(ctx["accepted_decision_ids"])
    probe = read_json("evidence/cp03/cp03-w02/W02-17/binding_inference_end_event_protocol_source_probe.json")
    assert probe["source_execution"] is False and probe["inference_end_event_runtime_execution"] == "NOT_RUN"
    assert probe["model_executions"] == 0 and probe["provider_egress_executions"] == 0 and probe["tool_executions"] == 0 and probe["parity_promotions"] == 0
    fallback = next(x for x in read_jsonl("ledgers/EVIDENCE_LEDGER.ndjson") if x.get("evidence_id") == "EVID-W02-FALLBACK-ADAPTER-20260922")
    assert fallback["real_openjarvis_fallback_model_execution"] == "NOT_RUN"


def main() -> None:
    preflight()
    probe_and_add_red_test()
    red_then_bind_green()
    persist()
    gauntlet()
    print(json.dumps({"status": "PASS", "capability_id": CAPABILITY_ID, "bindings_validated_total": 23, "unbound_remaining": 24, "verified_capabilities": 0, "parity_promotions": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
