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


def preflight() -> None:
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

    claim = read_json("sessions/20260922-w02-parity-graph/CLAIM.json")
    assert claim["claim_id"] == CLAIM_ID and claim["wave_id"] == WAVE_ID
    assert claim["canonical_task"] == "W02-17"
    assert claim["status"] == "ACTIVE" and claim["owner"] == "chatgpt-gpt-5.6-sol"
    for p in (
        ".github/workflows/cp03-w02-parity-graph.yml",
        "tests/test_cp03_w02_parity_graph.py",
        "inventory/cp03/w02_evidence_bindings.jsonl",
        "evidence/cp03/cp03-w02/W02-17/**",
        "STATE.md",
        "HANDOFF.md",
        "sessions/20260922-w02-parity-graph/**",
        "ledgers/CLAIM_LEDGER.ndjson",
        "ledgers/EVIDENCE_LEDGER.ndjson",
        "ledgers/DECISION_LEDGER.ndjson",
        "ledgers/RISK_LEDGER.ndjson",
        "ledgers/RUN_LOG.ndjson",
        "ledgers/WAVE_LEDGER.ndjson",
        ".agentic/context/CURRENT_CONTEXT.json",
        ".agentic/context/CURRENT_CONTEXT.md",
    ):
        assert p in claim["scope"], p

    latest: dict[str, dict] = {}
    for row in read_jsonl("ledgers/CLAIM_LEDGER.ndjson"):
        if row.get("claim_id"):
            latest[row["claim_id"]] = row
    active = {cid: row for cid, row in latest.items() if row.get("status") == "ACTIVE"}
    assert set(active) == {CLAIM_ID}, active
    assert active[CLAIM_ID]["wave_id"] == WAVE_ID
    assert active[CLAIM_ID]["owner"] == "chatgpt-gpt-5.6-sol"

    summary = read_json("reports/cp03/w02_parity/SUMMARY.json")
    assert summary["binding_counts"] == {"EVIDENCE_BACKED_CANDIDATE": 25, "UNBOUND": 22}
    assert summary["verified_capabilities"] == 0 and summary["parity_promotions"] == 0
    assert summary["global_denominator"] == 7565 and summary["openjarvis_obligations"] == 646

    matrix = read_jsonl("reports/cp03/w02_parity/PROOF_MATRIX.jsonl")
    target = next(x for x in matrix if x["capability_id"] == CAPABILITY_ID)
    assert target["name"] == "GET /health"
    assert target["surface_kind"] == "http_route"
    assert target["source_path"] == "src/openjarvis/server/routes.py"
    assert target["source_line"] == 1389
    assert target["ownership"] == "OWNED" and target["terminal_eligible_in_w02"] is True
    assert target["w02_evidence_state"] == "UNBOUND" and target["binding"] is None
    assert target["canonical_parity_status"] == "UNVERIFIED"
    assert target["verified"] is False and target["parity_promotion"] is False

    for cid in (
        "cap_ac38bf813e130d14927723d8",
        "cap_a97068215f50aeff0353f6e9",
        "cap_098f4d18aa8447bd4e8150ab",
        "cap_188be06cddde484a5bb440c7",
        "cap_a451181be18c365d8639a3f5",
        "cap_4d86f46add938a2d9d59e82c",
    ):
        row = next(x for x in matrix if x["capability_id"] == cid)
        assert row["w02_evidence_state"] == "UNBOUND" and row["binding"] is None


def probe_and_add_red_test() -> None:
    src = UPSTREAM / "src/openjarvis/server/routes.py"
    raw = src.read_bytes()
    text = raw.decode("utf-8")
    assert git_blob_sha(raw) == "16b584c21320d292cc2f0f99d1d0f6d0f40e6f3d"
    lines = text.splitlines()
    line = next(i + 1 for i, x in enumerate(lines) if x.strip() == "async def health(request: Request):")
    assert line == 1389
    assert lines[line - 2].strip() == '@router.get("/health")'
    function = "\n".join(lines[line - 1 : line + 9])
    assert "engine = request.app.state.engine" in function
    assert "healthy = engine.health()" in function
    assert "if not healthy:" in function
    assert 'raise HTTPException(status_code=503, detail="Engine unhealthy")' in function
    assert 'return {"status": "ok"}' in function

    probe = {
        "schema_version": 1,
        "date": "2026-09-24",
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "task": "W02-17",
        "gate": "G6",
        "capability_id": CAPABILITY_ID,
        "capability_name": "GET /health",
        "surface_kind": "http_route",
        "ownership": "OWNED",
        "terminal_eligible_in_w02": True,
        "upstream_commit": UPSTREAM_COMMIT,
        "source_path": "src/openjarvis/server/routes.py",
        "source_line": line,
        "source_blob_sha1": git_blob_sha(raw),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_probe": "PASS",
        "source_execution": False,
        "http_method": "GET",
        "http_path": "/health",
        "engine_health_call_present": True,
        "unhealthy_status_code": 503,
        "healthy_response": {"status": "ok"},
        "server_health_runtime_execution": "NOT_RUN",
        "engine_health_execution": "NOT_RUN",
        "http_listener_execution": "NOT_RUN",
        "model_executions": 0,
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "canonical_parity_status": "UNVERIFIED",
        "parity_promotions": 0,
    }
    probe_path = ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_health_source_probe.json"
    probe_path.write_text(json.dumps(probe, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    p = ROOT / "tests/test_cp03_w02_parity_graph.py"
    t = p.read_text(encoding="utf-8")
    assert "SERVER_HEALTH_CAPABILITY_ID" not in t
    t = replace_once(
        t,
        'NEXA_MODELS_CAPABILITY_ID = "cap_8dbeb91d13034dded222493b"\n',
        'NEXA_MODELS_CAPABILITY_ID = "cap_8dbeb91d13034dded222493b"\nSERVER_HEALTH_CAPABILITY_ID = "cap_575541e84f43f012a9239ad2"\n',
    )
    nexa_models_test_block = (
        'NEXA_MODELS_TEST_ID = (\n'
        '    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n'
        '    "test_nexa_models_binding_is_capability_specific_and_source_backed"\n'
        ')\n'
    )
    server_health_test_block = (
        'SERVER_HEALTH_TEST_ID = (\n'
        '    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n'
        '    "test_server_health_binding_is_capability_specific_and_source_backed"\n'
        ')\n'
    )
    t = replace_once(t, nexa_models_test_block, nexa_models_test_block + server_health_test_block)
    t = replace_once(
        t,
        "def test_current_matrix_has_twenty_five_candidates_and_no_parity_promotion",
        "def test_current_matrix_has_twenty_six_candidates_and_no_parity_promotion",
    )
    t = replace_once(
        t,
        '== "EVIDENCE_BACKED_CANDIDATE" for row in rows), 25)',
        '== "EVIDENCE_BACKED_CANDIDATE" for row in rows), 26)',
    )
    t = replace_once(t, '== "UNBOUND" for row in rows), 22)', '== "UNBOUND" for row in rows), 21)')
    t = replace_once(
        t,
        "NEXA_HEALTH_CAPABILITY_ID, NEXA_MODELS_CAPABILITY_ID},",
        "NEXA_HEALTH_CAPABILITY_ID, NEXA_MODELS_CAPABILITY_ID, SERVER_HEALTH_CAPABILITY_ID},",
    )
    nexa_models_candidate = (
        '        nexa_models = candidates[NEXA_MODELS_CAPABILITY_ID]\n'
        '        self.assertEqual(nexa_models["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")\n'
        '        self.assertFalse(nexa_models["binding"]["terminal"])\n'
    )
    server_health_candidate = (
        '        server_health = candidates[SERVER_HEALTH_CAPABILITY_ID]\n'
        '        self.assertEqual(server_health["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")\n'
        '        self.assertFalse(server_health["binding"]["terminal"])\n'
    )
    t = replace_once(t, nexa_models_candidate, nexa_models_candidate + server_health_candidate)

    method = '''    def test_server_health_binding_is_capability_specific_and_source_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == SERVER_HEALTH_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "http_route")
        self.assertEqual(row["source_path"], "src/openjarvis/server/routes.py")
        self.assertEqual(row["source_line"], 1389)
        self.assertEqual(row["name"], "GET /health")
        self.assertTrue(row["terminal_eligible_in_w02"])
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["w02_evidence_state"], "EVIDENCE_BACKED_CANDIDATE")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], SERVER_HEALTH_TEST_ID)
        self.assertFalse(binding["terminal"])
        receipt = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["lifecycle_tests"], 9)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)
        probe = json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_health_source_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["capability_id"], SERVER_HEALTH_CAPABILITY_ID)
        self.assertEqual(probe["source_line"], 1389)
        self.assertEqual(probe["source_probe"], "PASS")
        self.assertFalse(probe["source_execution"])
        self.assertEqual(probe["http_method"], "GET")
        self.assertEqual(probe["http_path"], "/health")
        self.assertTrue(probe["engine_health_call_present"])
        self.assertEqual(probe["unhealthy_status_code"], 503)
        self.assertEqual(probe["healthy_response"], {"status": "ok"})
        self.assertEqual(probe["server_health_runtime_execution"], "NOT_RUN")
        self.assertEqual(probe["engine_health_execution"], "NOT_RUN")
        self.assertEqual(probe["http_listener_execution"], "NOT_RUN")
        self.assertEqual(probe["model_executions"], 0)
        self.assertEqual(probe["provider_egress_executions"], 0)
        self.assertEqual(probe["tool_executions"], 0)
        self.assertEqual(probe["parity_promotions"], 0)

'''
    marker = "    def test_cli_model_list_command_binding_is_capability_specific_and_source_backed(self) -> None:\n"
    t = replace_once(t, marker, method + marker)
    p.write_text(t, encoding="utf-8")


def red_then_bind_green() -> None:
    red = run("python", "-m", "unittest", "-v", TEST_ID, check=False)
    assert red.returncode != 0, red.stdout + red.stderr
    red_text = red.stdout + red.stderr
    assert any(token in red_text for token in ("AssertionError", "EVIDENCE_BACKED_CANDIDATE", "NoneType")), red_text

    path = ROOT / "inventory/cp03/w02_evidence_bindings.jsonl"
    rows = read_jsonl("inventory/cp03/w02_evidence_bindings.jsonl")
    assert len(rows) == 25 and all(x["capability_id"] != CAPABILITY_ID for x in rows)
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
    run("python", "-m", "unittest", "-v", TEST_ID)


def persist() -> None:
    probe_path = ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_health_source_probe.json"
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
        "binding_capability_name": "GET /health",
        "binding_surface_kind": "http_route",
        "binding_ownership": "OWNED",
        "terminal_eligible_in_w02": True,
        "binding_source_evidence_id": SOURCE_EVIDENCE_ID,
        "binding_source_validated_head": SOURCE_EVIDENCE_HEAD,
        "binding_source_run_id": 35552788123,
        "executed_test_id": TEST_ID,
        "source_probe_path": str(probe_path.relative_to(ROOT)),
        "source_probe_sha256": hashlib.sha256(probe_path.read_bytes()).hexdigest(),
        "source_execution": False,
        "server_health_runtime_execution": "NOT_RUN",
        "engine_health_execution": "NOT_RUN",
        "http_listener_execution": "NOT_RUN",
        "bindings_added_this_slice": 1,
        "bindings_validated_total": 26,
        "unbound_remaining": 21,
        "global_denominator": 7565,
        "openjarvis_obligations": 646,
        "verified_capabilities": 0,
        "parity_promotions": 0,
        "model_executions": 0,
        "provider_egress_executions": 0,
        "tool_executions": 0,
        "afm_inprocess_execution": "NOT_RUN",
        "real_openjarvis_fallback_model_execution": "NOT_RUN",
        "inference_start_event_binding": "UNBOUND_UNTOUCHED_COLLISION_AVOIDED",
        "cloud_reload_binding": "UNBOUND_UNTOUCHED_COLLISION_AVOIDED",
        "apple_fm_binding_family": "UNBOUND_UNTOUCHED_COLLISION_AVOIDED",
        "next_slice": "Continue W02-17 with another non-conflicting proof unit only when capability-specific executed or exact pinned-source evidence can be paired with an existing completed-task PASS receipt; preserve AFM/fallback NOT_RUN and avoid overlapping extant branches.",
    }
    report_path = ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_health_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    append_once("ledgers/CLAIM_LEDGER.ndjson", "event_id", "CLAIM-CONTINUE-W02-G6-SERVER-HEALTH-20260924", {
        "schema_version": 1,
        "date": "2026-09-24",
        "event": "CONTINUE",
        "event_id": "CLAIM-CONTINUE-W02-G6-SERVER-HEALTH-20260924",
        "claim_id": CLAIM_ID,
        "owner": "chatgpt-gpt-5.6-sol",
        "checkpoint": "CP03",
        "canonical_task": "W02-17",
        "wave_id": WAVE_ID,
        "status": "ACTIVE",
        "base_head": EXPECTED_MAIN,
        "coordination": "Continue the sole active W02-17 G6 claim for the branch-free core server GET /health source-proof unit only. Cloud-reload, InferenceStartEvent and Apple FM branches are excluded; route/engine/listener execution remains NOT_RUN; no parity or denominator transition is authorized.",
    })
    append_once("ledgers/EVIDENCE_LEDGER.ndjson", "evidence_id", EVIDENCE_ID, {**report, "type": "CP03_W02_G6_CAPABILITY_BINDING", "path": str(report_path.relative_to(ROOT))})
    append_once("ledgers/DECISION_LEDGER.ndjson", "decision_id", DECISION_ID, {
        "schema_version": 1,
        "date": "2026-09-24",
        "decision_id": DECISION_ID,
        "status": "ACCEPTED",
        "checkpoint": "CP03",
        "task": "W02-17",
        "decision": "Bind the frozen OpenJarvis core server GET /health route as a non-terminal EVIDENCE_BACKED_CANDIDATE only.",
        "context": "Exact pinned source proves route declaration, engine.health delegation, 503 unhealthy semantics and healthy response. Completed W02-08 supplies the exact model/engine bridge receipt and lifecycle regression, but server listener and route runtime execution are deliberately NOT_RUN, so this is not behavioral parity.",
        "evidence_id": EVIDENCE_ID,
        "parity_promotions": 0,
    })
    append_once("ledgers/RISK_LEDGER.ndjson", "event_id", "RISK-UPDATE-W02-G6-K47-BINDINGS-SERVER-HEALTH-20260924", {
        "schema_version": 1,
        "date": "2026-09-24",
        "event_id": "RISK-UPDATE-W02-G6-K47-BINDINGS-SERVER-HEALTH-20260924",
        "risk_id": "RISK-W02-G6-K47-BINDINGS-PENDING-20260922",
        "severity": "P1",
        "status": "OPEN",
        "task": "W02-17",
        "evidence_id": EVIDENCE_ID,
        "risk": "G6 remains incomplete: 21/47 frozen W02 proof units remain UNBOUND. Core server GET /health is source-backed only; HTTP listener, route runtime and engine.health invocation are NOT_RUN in this slice.",
        "mitigation": "Keep W02-17 IN_PROGRESS, VERIFIED=0 and W02-18 BLOCKED; require capability-specific runtime evidence before terminal parity and preserve NOT_RUN/platform-gated states.",
    })
    append_once("ledgers/RUN_LOG.ndjson", "event_id", "RUN-W02-G6-SERVER-HEALTH-20260924", {
        "schema_version": 1,
        "date": "2026-09-24",
        "event": "CP03_W02_G6_CAPABILITY_BINDING",
        "event_id": "RUN-W02-G6-SERVER-HEALTH-20260924",
        "goal_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "iteration": "I03",
        "wave_id": "CP03-W02",
        "canonical_task": "W02-17",
        "claim_id": CLAIM_ID,
        "evidence_id": EVIDENCE_ID,
        "status": "ADVANCED",
        "bindings_validated_total": 26,
        "unbound_remaining": 21,
        "verified_capabilities": 0,
        "parity_promotions": 0,
    })
    append_once("ledgers/WAVE_LEDGER.ndjson", "event_id", "WAVE-W02-G6-SERVER-HEALTH-20260924", {
        "schema_version": 1,
        "date": "2026-09-24",
        "event": "WAVE_PROGRESS",
        "event_id": "WAVE-W02-G6-SERVER-HEALTH-20260924",
        "checkpoint": "CP03",
        "iteration": "I03",
        "parent_wave": "CP03-W02",
        "wave_id": WAVE_ID,
        "canonical_task": "W02-17",
        "claim_id": CLAIM_ID,
        "gate": "G6",
        "evidence_id": EVIDENCE_ID,
        "status": "IN_PROGRESS",
        "bindings_validated_total": 26,
        "unbound_remaining": 21,
        "parity_promotions": 0,
    })

    state = ROOT / "STATE.md"
    text = state.read_text(encoding="utf-8")
    old = "- G6 explicit binding progress: `25/47` evidence-backed candidates; `22` UNBOUND; VERIFIED capabilities `0`; parity promotions `0`."
    new = "- G6 explicit binding progress: `26/47` evidence-backed candidates; `21` UNBOUND; VERIFIED capabilities `0`; parity promotions `0`."
    assert text.count(old) == 1
    state.write_text(text.replace(old, new, 1), encoding="utf-8")

    handoff = ROOT / "HANDOFF.md"
    h = handoff.read_text(encoding="utf-8").rstrip() + "\n\n"
    section = [
        "## W02-17 core server GET /health binding — source-backed partial verified",
        "",
        "- `EVID-W02-PARITY-BINDING-SERVER-HEALTH-20260924`: `cap_575541e84f43f012a9239ad2` (`GET /health`, OWNED route at `src/openjarvis/server/routes.py:1389`) is now a non-terminal `EVIDENCE_BACKED_CANDIDATE`.",
        "- Exact pinned source `72033b8ec288aa067ce4530ff9d96bf231e9c4e5` proves the route, delegation to `engine.health()`, HTTP 503 on unhealthy engine and `{status: ok}` on healthy source path. HTTP listener, route runtime and engine-health execution remain `NOT_RUN`.",
        "- Formal G6 binding is anchored to completed W02-08 `EVID-W02-MODEL-BRIDGE-20260921` at exact SHA `a866c335a0f9cad75122c8eb7c5310d358f6aad4`; candidate evidence only: VERIFIED parity remains 0.",
        "- Collision avoidance: cloud-reload, InferenceStartEvent and Apple FM parallel branches were not touched. AFM compatible-host proof and real fallback model execution remain `NOT_RUN`.",
        "- G6 is now 26 `EVIDENCE_BACKED_CANDIDATE` / 21 `UNBOUND`; parity promotions 0; denominator 7565 and OpenJarvis obligations 646 unchanged. W02-17 remains `IN_PROGRESS`; W02-18/W02-19 remain `BLOCKED`.",
        "- Exact next slice: another branch-free W02-17 proof unit with capability-specific executed or exact pinned-source evidence paired to an exact completed-task PASS receipt.",
        "",
    ]
    handoff.write_text(h + "\n".join(section), encoding="utf-8")

    claim_path = ROOT / "sessions/20260922-w02-parity-graph/CLAIM.json"
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    assert claim["claim_id"] == CLAIM_ID and claim["status"] == "ACTIVE"
    claim["continuation_base_head"] = EXPECTED_MAIN
    claim_path.write_text(json.dumps(claim, indent=2) + "\n", encoding="utf-8")
    (ROOT / "sessions/20260922-w02-parity-graph/RESULT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    run("python", "scripts/cp03/w02_parity_graph.py", "--write")
    run("python", "scripts/context/build_context_pack.py")


def gauntlet() -> None:
    run("python", "-m", "unittest", "-v", TEST_ID)
    run("python", "-m", "unittest", "-v", "tests.test_cp03_w02_parity_graph")
    run("python", "-m", "unittest", "-v", "tests.test_cp03_w02_scope_lock")
    run("python", "scripts/validate_agentic_state.py")
    run("python", "scripts/context/validate_context_pack.py")
    run("python", "scripts/context/build_context_pack.py", "--check")
    run("python", "scripts/context/validate_next_actions.py")
    run("python", "scripts/cp03/validate_w02_plan.py")
    run("python", "-m", "scripts.parity.ledger", "--check", "--source-repo", "openjarvis")
    run("python", "scripts/cp03/w02_parity_graph.py", "--check")

    s = read_json("reports/cp03/w02_parity/SUMMARY.json")
    assert s["binding_counts"] == {"EVIDENCE_BACKED_CANDIDATE": 26, "UNBOUND": 21}
    assert s["verified_capabilities"] == 0 and s["parity_promotions"] == 0
    assert s["global_denominator"] == 7565 and s["openjarvis_obligations"] == 646
    assert s["w02_proof_units"] == 47
    matrix = read_jsonl("reports/cp03/w02_parity/PROOF_MATRIX.jsonl")
    target = next(x for x in matrix if x["capability_id"] == CAPABILITY_ID)
    assert target["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE"
    assert target["canonical_parity_status"] == "UNVERIFIED"
    assert target["verified"] is False and target["parity_promotion"] is False
    assert target["binding"]["terminal"] is False and target["binding"]["test_id"] == TEST_ID
    for cid in (
        "cap_ac38bf813e130d14927723d8",
        "cap_a97068215f50aeff0353f6e9",
        "cap_098f4d18aa8447bd4e8150ab",
        "cap_188be06cddde484a5bb440c7",
        "cap_a451181be18c365d8639a3f5",
        "cap_4d86f46add938a2d9d59e82c",
    ):
        row = next(x for x in matrix if x["capability_id"] == cid)
        assert row["w02_evidence_state"] == "UNBOUND" and row["binding"] is None
    g = read_json("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    tasks = {x["id"]: x for x in g["tasks"]}
    assert g["first_executable_task"] == "W02-17"
    assert tasks["W02-17"]["status"] == "IN_PROGRESS"
    assert tasks["W02-18"]["status"] == "BLOCKED" and tasks["W02-19"]["status"] == "BLOCKED"
    ctx = read_json(".agentic/context/CURRENT_CONTEXT.json")
    claim = next(x for x in ctx["active_claims"] if x["claim_id"] == CLAIM_ID)
    assert claim["wave_id"] == WAVE_ID and claim["status"] == "ACTIVE"
    assert EVIDENCE_ID in set(ctx["evidence_ids"])
    assert DECISION_ID in set(ctx["accepted_decision_ids"])
    probe = read_json("evidence/cp03/cp03-w02/W02-17/binding_server_health_source_probe.json")
    assert probe["source_execution"] is False
    assert probe["server_health_runtime_execution"] == "NOT_RUN"
    assert probe["engine_health_execution"] == "NOT_RUN"
    assert probe["http_listener_execution"] == "NOT_RUN"
    assert probe["model_executions"] == 0
    assert probe["provider_egress_executions"] == 0
    assert probe["tool_executions"] == 0 and probe["parity_promotions"] == 0
    fallback = next(x for x in read_jsonl("ledgers/EVIDENCE_LEDGER.ndjson") if x.get("evidence_id") == "EVID-W02-FALLBACK-ADAPTER-20260922")
    assert fallback["real_openjarvis_fallback_model_execution"] == "NOT_RUN"


def main() -> None:
    preflight()
    probe_and_add_red_test()
    red_then_bind_green()
    persist()
    gauntlet()
    print(json.dumps({
        "status": "PASS",
        "capability_id": CAPABILITY_ID,
        "bindings_validated_total": 26,
        "unbound_remaining": 21,
        "verified_capabilities": 0,
        "parity_promotions": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
