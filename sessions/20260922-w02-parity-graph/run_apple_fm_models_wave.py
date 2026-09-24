from __future__ import annotations

import hashlib
import json
import os
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

SOURCE_PATH = "src/openjarvis/engine/apple_fm_shim.py"
SOURCE_BLOB_SHA1 = "1b1bad436c65395df80e7e06cd2cc2aaf4330708"
PROBE_PATH = "evidence/cp03/cp03-w02/W02-17/binding_apple_fm_models_source_probe.json"
REPORT_PATH = "evidence/cp03/cp03-w02/W02-17/binding_apple_fm_models_report.json"


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


def replace_once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new, 1)


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def exact_main() -> None:
    run("git", "fetch", "origin", "main")
    assert run("git", "rev-parse", "origin/main").stdout.strip() == EXPECTED_MAIN
    assert run("git", "merge-base", "origin/main", "HEAD").stdout.strip() == EXPECTED_MAIN


def preflight() -> None:
    exact_main()
    g = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    tasks = {x["id"]: x for x in g["tasks"]}
    assert g["first_executable_task"] == "W02-17"
    assert tasks["W02-17"]["status"] == "IN_PROGRESS"
    assert tasks["W02-17"]["depends_on"] == ["W02-01", "W02-13", "W02-14", "W02-16"]
    assert all(tasks[d]["status"] == "COMPLETE" and tasks[d]["proof"] for d in tasks["W02-17"]["depends_on"])
    assert tasks["W02-18"]["status"] == "BLOCKED" and tasks["W02-19"]["status"] == "BLOCKED"
    assert g["global_denominator"] == 7565
    assert g["openjarvis_obligations"] == 646
    assert g["w02_obligation_count"] == 47

    context = read_json(".agentic/context/CURRENT_CONTEXT.json")
    active = [x for x in context["active_claims"] if x["status"] == "ACTIVE"]
    assert len(active) == 1 and active[0]["claim_id"] == CLAIM_ID
    assert active[0]["wave_id"] == WAVE_ID and active[0]["owner"] == "chatgpt-gpt-5.6-sol"

    latest: dict[str, dict] = {}
    for row in read_jsonl("ledgers/CLAIM_LEDGER.ndjson"):
        if row.get("claim_id"):
            latest[row["claim_id"]] = row
    active_ledger = {cid: row for cid, row in latest.items() if row.get("status") == "ACTIVE"}
    assert set(active_ledger) == {CLAIM_ID}, active_ledger
    assert active_ledger[CLAIM_ID]["wave_id"] == WAVE_ID

    summary = read_json("reports/cp03/w02_parity/SUMMARY.json")
    assert summary["binding_counts"] == {"EVIDENCE_BACKED_CANDIDATE": 25, "UNBOUND": 22}
    assert summary["verified_capabilities"] == 0 and summary["parity_promotions"] == 0
    assert summary["global_denominator"] == 7565 and summary["openjarvis_obligations"] == 646

    matrix = read_jsonl("reports/cp03/w02_parity/PROOF_MATRIX.jsonl")
    target = next(x for x in matrix if x["capability_id"] == CAPABILITY_ID)
    assert target["name"] == "GET /v1/models"
    assert target["surface_kind"] == "http_route"
    assert target["source_path"] == SOURCE_PATH
    assert target["source_line"] == 150
    assert target["ownership"] == "OWNED" and target["terminal_eligible_in_w02"] is True
    assert target["w02_evidence_state"] == "UNBOUND" and target["binding"] is None
    assert target["canonical_parity_status"] == "UNVERIFIED"
    assert target["verified"] is False and target["parity_promotion"] is False

    # Preserve the known AFM in-process blocker and extant parallel branches.
    for cid in (
        "cap_ac38bf813e130d14927723d8",
        "cap_a97068215f50aeff0353f6e9",
        "cap_098f4d18aa8447bd4e8150ab",
    ):
        row = next(x for x in matrix if x["capability_id"] == cid)
        assert row["w02_evidence_state"] == "UNBOUND" and row["binding"] is None


def probe_source_and_patch_test() -> None:
    src = UPSTREAM / SOURCE_PATH
    raw = src.read_bytes()
    text = raw.decode("utf-8")
    assert git_blob_sha(raw) == SOURCE_BLOB_SHA1
    lines = text.splitlines()
    line = next(i + 1 for i, x in enumerate(lines) if x.strip() == "def list_models() -> JSONResponse:")
    assert line == 150
    assert lines[line - 2].strip() == '@app.get("/v1/models")'
    function = "\n".join(lines[line - 1 : line + 15])
    assert '"id": MODEL_ID' in function
    assert '"object": "model"' in function
    assert '"owned_by": "apple"' in function
    assert '"object": "list"' in function
    assert 'entry["context_length"]' in function
    assert 'MODEL_ID = "apple-fm"' in text
    assert 'only runs on macOS 26+' in text.lower()

    probe = {
        "schema_version": 1,
        "date": "2026-09-24",
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "task": "W02-17",
        "gate": "G6",
        "capability_id": CAPABILITY_ID,
        "capability_name": "GET /v1/models",
        "surface_kind": "http_route",
        "ownership": "OWNED",
        "terminal_eligible_in_w02": True,
        "upstream_commit": UPSTREAM_COMMIT,
        "source_path": SOURCE_PATH,
        "source_line": line,
        "source_blob_sha1": git_blob_sha(raw),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_probe": "PASS",
        "source_execution": False,
        "http_method": "GET",
        "http_path": "/v1/models",
        "response_object": "list",
        "model_id": "apple-fm",
        "model_object": "model",
        "owned_by": "apple",
        "context_length_optional": True,
        "platform_requirement": "macOS 26+ with Apple Intelligence enabled",
        "apple_fm_models_runtime_execution": "NOT_RUN",
        "apple_fm_sdk_execution": "NOT_RUN",
        "http_listener_execution": "NOT_RUN",
        "afm_inprocess_execution": "NOT_RUN",
        "model_executions": 0,
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "canonical_parity_status": "UNVERIFIED",
        "parity_promotions": 0,
    }
    p = ROOT / PROBE_PATH
    p.write_text(json.dumps(probe, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    path = ROOT / "tests/test_cp03_w02_parity_graph.py"
    t = path.read_text(encoding="utf-8")
    assert "APPLE_FM_SHIM_MODELS_CAPABILITY_ID" not in t
    t = replace_once(
        t,
        'NEXA_MODELS_CAPABILITY_ID = "cap_8dbeb91d13034dded222493b"\n',
        'NEXA_MODELS_CAPABILITY_ID = "cap_8dbeb91d13034dded222493b"\nAPPLE_FM_SHIM_MODELS_CAPABILITY_ID = "cap_188be06cddde484a5bb440c7"\n',
    )
    marker = 'NEXA_MODELS_TEST_ID = ('
    start = t.index(marker)
    end = t.index('\n)\n', start) + 3
    new_block = (
        'APPLE_FM_SHIM_MODELS_TEST_ID = (\n'
        '    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n'
        '    "test_apple_fm_shim_models_binding_is_capability_specific_and_source_backed"\n'
        ')\n'
    )
    t = t[:end] + new_block + t[end:]
    t = replace_once(
        t,
        "def test_current_matrix_has_twenty_five_candidates_and_no_parity_promotion",
        "def test_current_matrix_has_twenty_six_candidates_and_no_parity_promotion",
    )
    t = replace_once(t, '== "EVIDENCE_BACKED_CANDIDATE" for row in rows), 25)', '== "EVIDENCE_BACKED_CANDIDATE" for row in rows), 26)')
    t = replace_once(t, '== "UNBOUND" for row in rows), 22)', '== "UNBOUND" for row in rows), 21)')
    t = replace_once(
        t,
        "INFERENCE_END_EVENT_PROTOCOL_CAPABILITY_ID, NEXA_HEALTH_CAPABILITY_ID, NEXA_MODELS_CAPABILITY_ID},",
        "INFERENCE_END_EVENT_PROTOCOL_CAPABILITY_ID, NEXA_HEALTH_CAPABILITY_ID, NEXA_MODELS_CAPABILITY_ID, APPLE_FM_SHIM_MODELS_CAPABILITY_ID},",
    )
    candidate_marker = (
        '        nexa_models = candidates[NEXA_MODELS_CAPABILITY_ID]\n'
        '        self.assertEqual(nexa_models["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")\n'
        '        self.assertFalse(nexa_models["binding"]["terminal"])\n'
    )
    candidate_add = (
        '        apple_fm_shim_models = candidates[APPLE_FM_SHIM_MODELS_CAPABILITY_ID]\n'
        '        self.assertEqual(apple_fm_shim_models["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")\n'
        '        self.assertFalse(apple_fm_shim_models["binding"]["terminal"])\n'
    )
    t = replace_once(t, candidate_marker, candidate_marker + candidate_add)

    method = '''    def test_apple_fm_shim_models_binding_is_capability_specific_and_source_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == APPLE_FM_SHIM_MODELS_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "http_route")
        self.assertEqual(row["source_path"], "src/openjarvis/engine/apple_fm_shim.py")
        self.assertEqual(row["source_line"], 150)
        self.assertEqual(row["name"], "GET /v1/models")
        self.assertTrue(row["terminal_eligible_in_w02"])
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["w02_evidence_state"], "EVIDENCE_BACKED_CANDIDATE")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], APPLE_FM_SHIM_MODELS_TEST_ID)
        self.assertFalse(binding["terminal"])

        receipt = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["native_model_count"], 69)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog = json.loads((ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8"))
        matches = [engine for engine in catalog["engines"] if engine["key"] == "apple_fm"]
        self.assertEqual(matches, [{"implementation":"abc.AppleFmEngine","key":"apple_fm","native_type":"ABCMeta","state":"REGISTERED"}])

        probe = json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_apple_fm_models_source_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["capability_id"], APPLE_FM_SHIM_MODELS_CAPABILITY_ID)
        self.assertEqual(probe["source_line"], 150)
        self.assertEqual(probe["source_probe"], "PASS")
        self.assertFalse(probe["source_execution"])
        self.assertEqual(probe["http_method"], "GET")
        self.assertEqual(probe["http_path"], "/v1/models")
        self.assertEqual(probe["response_object"], "list")
        self.assertEqual(probe["model_id"], "apple-fm")
        self.assertEqual(probe["model_object"], "model")
        self.assertEqual(probe["owned_by"], "apple")
        self.assertTrue(probe["context_length_optional"])
        self.assertEqual(probe["apple_fm_models_runtime_execution"], "NOT_RUN")
        self.assertEqual(probe["apple_fm_sdk_execution"], "NOT_RUN")
        self.assertEqual(probe["http_listener_execution"], "NOT_RUN")
        self.assertEqual(probe["afm_inprocess_execution"], "NOT_RUN")
        self.assertEqual(probe["model_executions"], 0)
        self.assertEqual(probe["provider_egress_executions"], 0)
        self.assertEqual(probe["tool_executions"], 0)
        self.assertEqual(probe["parity_promotions"], 0)

        afm = next(row for row in self.result["rows"] if row["capability_id"] == AFM_INPROCESS_CAPABILITY_ID)
        self.assertEqual(afm["w02_evidence_state"], "UNBOUND")
        self.assertIsNone(afm["binding"])
        self.assertEqual(afm["canonical_parity_status"], "UNVERIFIED")

'''
    anchor = "    def test_graph_projects_all_four_planes_without_promotion(self) -> None:\n"
    t = replace_once(t, anchor, method + anchor)
    path.write_text(t, encoding="utf-8")


def red_then_green() -> None:
    red = run("python", "-m", "unittest", "-v", TEST_ID, check=False)
    assert red.returncode != 0, "target test unexpectedly passed before binding"
    red_text = red.stdout + red.stderr
    assert "FAIL" in red_text or "ERROR" in red_text

    receipt = next(x for x in read_jsonl("ledgers/EVIDENCE_LEDGER.ndjson") if x.get("evidence_id") == SOURCE_EVIDENCE_ID)
    assert receipt["status"] == "VERIFIED"
    assert receipt["validated_head"] == SOURCE_EVIDENCE_HEAD
    for key, expected in {
        "native_engine_count": 15,
        "native_import_failure_count": 0,
        "native_model_count": 69,
        "model_executions": 0,
        "provider_egress_executions": 0,
        "parity_promotions": 0,
    }.items():
        assert receipt[key] == expected, (key, receipt[key])

    binding = {
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
    with (ROOT / "inventory/cp03/w02_evidence_bindings.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(binding, sort_keys=True, separators=(",", ":")) + "\n")

    run("python", "scripts/cp03/w02_parity_graph.py", "--write")
    run("python", "-m", "unittest", "-v", TEST_ID)


def persist() -> None:
    exact_main()
    summary = read_json("reports/cp03/w02_parity/SUMMARY.json")
    assert summary["binding_counts"] == {"EVIDENCE_BACKED_CANDIDATE": 26, "UNBOUND": 21}
    assert summary["verified_capabilities"] == 0 and summary["parity_promotions"] == 0
    assert summary["global_denominator"] == 7565 and summary["openjarvis_obligations"] == 646

    probe = read_json(PROBE_PATH)
    probe_sha256 = hashlib.sha256((ROOT / PROBE_PATH).read_bytes()).hexdigest()
    report = {
        "schema_version": 1,
        "date": "2026-09-24",
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "task": "W02-17",
        "gate": "G6",
        "claim_id": CLAIM_ID,
        "evidence_id": EVIDENCE_ID,
        "binding_capability_id": CAPABILITY_ID,
        "binding_capability_name": "GET /v1/models",
        "binding_ownership": "OWNED",
        "binding_surface_kind": "http_route",
        "binding_source_evidence_id": SOURCE_EVIDENCE_ID,
        "binding_source_validated_head": SOURCE_EVIDENCE_HEAD,
        "binding_source_run_id": 35552788123,
        "executed_test_id": TEST_ID,
        "github_actions_run_id": RUN_ID,
        "validated_base_head": EXPECTED_MAIN,
        "bindings_added_this_slice": 1,
        "bindings_validated_total": 26,
        "unbound_remaining": 21,
        "source_probe_path": PROBE_PATH,
        "source_probe_sha256": probe_sha256,
        "source_execution": False,
        "apple_fm_models_runtime_execution": "NOT_RUN",
        "apple_fm_sdk_execution": "NOT_RUN",
        "http_listener_execution": "NOT_RUN",
        "afm_inprocess_execution": "NOT_RUN",
        "real_openjarvis_fallback_model_execution": "NOT_RUN",
        "cloud_reload_binding": "UNBOUND_UNTOUCHED_COLLISION_AVOIDED",
        "inference_start_event_binding": "UNBOUND_UNTOUCHED_COLLISION_AVOIDED",
        "model_executions": 0,
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "verified_capabilities": 0,
        "parity_promotions": 0,
        "terminal_eligible_in_w02": True,
        "status": "PASS",
        "next_slice": "Continue W02-17 with another non-conflicting proof unit only when capability-specific executed or exact pinned-source evidence can be paired with an existing completed-task PASS receipt; preserve AFM/fallback NOT_RUN and avoid cloud-reload/InferenceStartEvent branches.",
    }
    (ROOT / REPORT_PATH).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    append_once(
        "ledgers/CLAIM_LEDGER.ndjson",
        "event_id",
        "CLAIM-CONTINUE-W02-G6-APPLE-FM-MODELS-20260924",
        {
            "schema_version": 1,
            "date": "2026-09-24",
            "event": "CONTINUE",
            "event_id": "CLAIM-CONTINUE-W02-G6-APPLE-FM-MODELS-20260924",
            "project_id": "CLEVER-JARVIS-001",
            "checkpoint": "CP03",
            "parent_wave": "CP03-W02",
            "canonical_task": "W02-17",
            "claim_id": CLAIM_ID,
            "owner": "chatgpt-gpt-5.6-sol",
            "status": "ACTIVE",
            "wave_id": WAVE_ID,
            "base_head": EXPECTED_MAIN,
            "coordination": "Continue the sole active W02-17 G6 claim for the branch-free Apple FM shim GET /v1/models source-proof unit only. The in-process afm blocker and existing cloud-reload/InferenceStartEvent branches are excluded; Apple FM SDK/listener/route execution remains NOT_RUN; no parity or denominator transition is authorized.",
        },
    )
    append_once(
        "ledgers/DECISION_LEDGER.ndjson",
        "decision_id",
        DECISION_ID,
        {
            "schema_version": 1,
            "date": "2026-09-24",
            "checkpoint": "CP03",
            "task": "W02-17",
            "decision_id": DECISION_ID,
            "decision": "Bind the frozen OpenJarvis Apple FM shim GET /v1/models route as a non-terminal EVIDENCE_BACKED_CANDIDATE only.",
            "context": "Exact pinned source proves the route declaration and response schema; completed W02-08 proves the distinct apple_fm shim engine registration at its exact receipt. Apple FM SDK, HTTP listener and route runtime are NOT_RUN, and the separate in-process afm capability remains UNBOUND. Existing cloud-reload and InferenceStartEvent branches remain untouched.",
            "evidence_id": EVIDENCE_ID,
            "parity_promotions": 0,
            "status": "ACCEPTED",
        },
    )
    evidence_row = dict(report)
    evidence_row["type"] = "CP03_W02_G6_CAPABILITY_BINDING"
    evidence_row["path"] = REPORT_PATH
    append_once("ledgers/EVIDENCE_LEDGER.ndjson", "evidence_id", EVIDENCE_ID, evidence_row)
    append_once(
        "ledgers/RISK_LEDGER.ndjson",
        "event_id",
        "RISK-UPDATE-W02-G6-K47-BINDINGS-APPLE-FM-MODELS-20260924",
        {
            "schema_version": 1,
            "date": "2026-09-24",
            "event_id": "RISK-UPDATE-W02-G6-K47-BINDINGS-APPLE-FM-MODELS-20260924",
            "risk_id": "RISK-W02-G6-K47-BINDINGS-PENDING-20260922",
            "task": "W02-17",
            "severity": "P1",
            "status": "OPEN",
            "evidence_id": EVIDENCE_ID,
            "risk": "G6 remains incomplete: 21/47 frozen W02 proof units remain UNBOUND. Apple FM shim GET /v1/models is source-backed only; macOS/Apple Intelligence SDK, listener and route runtime behavior are NOT_RUN, and in-process afm remains separately blocked.",
            "mitigation": "Keep W02-17 IN_PROGRESS, VERIFIED=0 and W02-18 BLOCKED; require capability-specific runtime evidence before terminal parity and preserve all NOT_RUN/platform-gated states.",
        },
    )
    append_once(
        "ledgers/RUN_LOG.ndjson",
        "event_id",
        "RUN-W02-G6-APPLE-FM-MODELS-20260924",
        {
            "schema_version": 1,
            "date": "2026-09-24",
            "event": "CP03_W02_G6_CAPABILITY_BINDING",
            "event_id": "RUN-W02-G6-APPLE-FM-MODELS-20260924",
            "goal_id": "CLEVER-JARVIS-001",
            "checkpoint": "CP03",
            "iteration": "I03",
            "wave_id": "CP03-W02",
            "canonical_task": "W02-17",
            "claim_id": CLAIM_ID,
            "evidence_id": EVIDENCE_ID,
            "bindings_validated_total": 26,
            "unbound_remaining": 21,
            "verified_capabilities": 0,
            "parity_promotions": 0,
            "status": "ADVANCED",
        },
    )
    append_once(
        "ledgers/WAVE_LEDGER.ndjson",
        "event_id",
        "WAVE-W02-G6-APPLE-FM-MODELS-20260924",
        {
            "schema_version": 1,
            "date": "2026-09-24",
            "event": "WAVE_PROGRESS",
            "event_id": "WAVE-W02-G6-APPLE-FM-MODELS-20260924",
            "goal_id": "CLEVER-JARVIS-001",
            "checkpoint": "CP03",
            "wave_id": "CP03-W02",
            "canonical_task": "W02-17",
            "claim_id": CLAIM_ID,
            "evidence_id": EVIDENCE_ID,
            "gate": "G6",
            "bindings_validated_total": 26,
            "unbound_remaining": 21,
            "verified_capabilities": 0,
            "parity_promotions": 0,
            "status": "IN_PROGRESS",
        },
    )

    state_path = ROOT / "STATE.md"
    state = state_path.read_text(encoding="utf-8")
    state = replace_once(
        state,
        "- G6 explicit binding progress: `25/47` evidence-backed candidates; `22` UNBOUND; VERIFIED capabilities `0`; parity promotions `0`.",
        "- G6 explicit binding progress: `26/47` evidence-backed candidates; `21` UNBOUND; VERIFIED capabilities `0`; parity promotions `0`.",
    )
    state_path.write_text(state, encoding="utf-8")

    handoff_path = ROOT / "HANDOFF.md"
    handoff = handoff_path.read_text(encoding="utf-8").rstrip()
    handoff += "\n\n## W02-17 Apple FM shim GET /v1/models binding — source-backed partial verified\n\n"
    handoff += f"- `{EVIDENCE_ID}`: `{CAPABILITY_ID}` (`GET /v1/models`, OWNED route at `{SOURCE_PATH}:150`) is now a non-terminal `EVIDENCE_BACKED_CANDIDATE`.\n"
    handoff += f"- Exact pinned source `{UPSTREAM_COMMIT}` proves the FastAPI GET route and model-list schema (`object=list`, model id `apple-fm`, object `model`, owner `apple`, optional `context_length`). Apple FM SDK initialization, HTTP listener and route runtime remain `NOT_RUN`.\n"
    handoff += f"- Formal G6 binding is anchored to completed W02-08 `{SOURCE_EVIDENCE_ID}` at exact SHA `{SOURCE_EVIDENCE_HEAD}`; that receipt records the distinct `apple_fm` shim engine as `REGISTERED`, with zero model/provider execution. The separate in-process `afm` capability remains `UNBOUND` and `NOT_RUN`; candidate evidence only, VERIFIED parity remains 0.\n"
    handoff += "- Collision avoidance: extant cloud-reload and InferenceStartEvent branches were not touched; both capabilities remain `UNBOUND`. Real fallback remains `NOT_RUN`.\n"
    handoff += "- G6 is now 26 `EVIDENCE_BACKED_CANDIDATE` / 21 `UNBOUND`; parity promotions 0; denominator 7565 and OpenJarvis obligations 646 unchanged. W02-17 remains `IN_PROGRESS`; W02-18/W02-19 remain `BLOCKED`.\n"
    handoff += "- Exact next slice: another branch-free W02-17 proof unit with capability-specific executed or exact pinned-source evidence paired to an exact completed-task PASS receipt.\n"
    handoff_path.write_text(handoff, encoding="utf-8")

    (ROOT / "sessions/20260922-w02-parity-graph/RESULT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    run("python", "scripts/context/build_context_pack.py")


def gauntlet() -> None:
    exact_main()
    run("python", "scripts/validate_agentic_state.py")
    run("python", "scripts/context/validate_context_pack.py")
    run("python", "scripts/context/build_context_pack.py", "--check")
    run("python", "scripts/context/validate_next_actions.py")
    run("python", "scripts/cp03/validate_w02_plan.py")
    run("python", "-m", "scripts.parity.ledger", "--check", "--source-repo", "openjarvis")
    run("python", "scripts/cp03/w02_parity_graph.py", "--check")
    run("python", "-m", "unittest", "-v", TEST_ID)
    run("python", "-m", "unittest", "-v", "tests.test_cp03_w02_parity_graph")
    run("git", "diff", "--check")

    g = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    tasks = {x["id"]: x for x in g["tasks"]}
    assert tasks["W02-17"]["status"] == "IN_PROGRESS"
    assert tasks["W02-18"]["status"] == "BLOCKED" and tasks["W02-19"]["status"] == "BLOCKED"
    ctx = read_json(".agentic/context/CURRENT_CONTEXT.json")
    claim = next(x for x in ctx["active_claims"] if x["claim_id"] == CLAIM_ID)
    assert claim["wave_id"] == WAVE_ID and claim["status"] == "ACTIVE"
    assert EVIDENCE_ID in set(ctx["evidence_ids"])
    assert DECISION_ID in set(ctx["accepted_decision_ids"])
    assert read_json(PROBE_PATH)["afm_inprocess_execution"] == "NOT_RUN"
    assert read_json(REPORT_PATH)["parity_promotions"] == 0


if __name__ == "__main__":
    preflight()
    probe_source_and_patch_test()
    red_then_green()
    persist()
    gauntlet()
