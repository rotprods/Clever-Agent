from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cp03 import w02_parity_graph as graph

BASE_HEAD = "457a6c07634bc8e47d8708a8dbc244744fb126b5"
UPSTREAM_COMMIT = "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"
CAPABILITY_ID = "cap_46e5a39cd2e2af9c6cf8eba7"
EVIDENCE_ID = "EVID-W02-PARITY-BINDING-SERVER-MODEL-DELETE-20260924"
DECISION_ID = "DEC-W02-G6-SERVER-MODEL-DELETE-BINDING-20260924"
TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_server_delete_model_binding_is_capability_specific_and_source_backed"
)
CLAIM_ID = "CLAIM-CP03-W02-PARITY-GRAPH-20260922"
CLAIM_EVENT_ID = "CLAIM-CONTINUE-W02-G6-SERVER-MODEL-DELETE-20260924"
RUN_EVENT_ID = "RUN-W02-G6-SERVER-MODEL-DELETE-20260924"
WAVE_EVENT_ID = "WAVE-W02-G6-SERVER-MODEL-DELETE-20260924"
RISK_EVENT_ID = "RISK-UPDATE-W02-G6-K47-BINDINGS-SERVER-MODEL-DELETE-20260924"
SOURCE_EVIDENCE_ID = "EVID-W02-MODEL-BRIDGE-20260921"
SOURCE_EVIDENCE_HEAD = "a866c335a0f9cad75122c8eb7c5310d358f6aad4"
SOURCE_PATH = "src/openjarvis/server/routes.py"
SOURCE_LINE = 1189
SOURCE_SHA256 = "70d3baebabe7cda294d8419a0f3be8c9b25ba7851901136b95afa1497aed6c56"
SOURCE_BLOB_SHA1 = "16b584c21320d292cc2f0f99d1d0f6d0f40e6f3d"
BINDINGS_BEFORE = 28
BINDINGS_AFTER = 29
UNBOUND_BEFORE = 19
UNBOUND_AFTER = 18
RUN_ID = int(os.environ.get("GITHUB_RUN_ID", "0"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl_once(path: Path, row: dict, key: str) -> None:
    rows = read_jsonl(path)
    if any(item.get(key) == row.get(key) for item in rows):
        return
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if text and not text.endswith("\n"):
        text += "\n"
    text += json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one replacement in {path}: got {count} for {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_section_once(path: Path, marker: str, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n" + section.rstrip() + "\n", encoding="utf-8")


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def verify_base() -> None:
    summary = load_json(ROOT / "reports/cp03/w02_parity/SUMMARY.json")
    task_graph = load_json(ROOT / "iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    tasks = {task["id"]: task for task in task_graph["tasks"]}
    task = tasks["W02-17"]
    assert task_graph["first_executable_task"] == "W02-17"
    assert task["status"] == "IN_PROGRESS"
    assert all(tasks[dep]["status"] == "COMPLETE" for dep in task["depends_on"])
    assert tasks["W02-18"]["status"] == "BLOCKED"
    assert tasks["W02-19"]["status"] == "BLOCKED"
    assert summary["binding_counts"] == {
        "EVIDENCE_BACKED_CANDIDATE": BINDINGS_BEFORE,
        "UNBOUND": UNBOUND_BEFORE,
    }
    assert summary["verified_capabilities"] == 0
    assert summary["parity_promotions"] == 0
    assert summary["global_denominator"] == 7565
    assert summary["openjarvis_obligations"] == 646
    state = (ROOT / "STATE.md").read_text(encoding="utf-8")
    assert "28/47" in state and "`19` UNBOUND" in state
    rows = graph.compile_root(ROOT)["rows"]
    row = next(item for item in rows if item["capability_id"] == CAPABILITY_ID)
    assert row["w02_evidence_state"] == "UNBOUND"
    assert row["canonical_parity_status"] == "UNVERIFIED"
    assert row["verified"] is False
    assert row["parity_promotion"] is False
    active = [
        item
        for item in read_jsonl(ROOT / "ledgers/CLAIM_LEDGER.ndjson")
        if item.get("claim_id") == CLAIM_ID
    ]
    assert active and active[-1]["status"] == "ACTIVE"


def build_source_probe() -> dict:
    source = Path("/tmp/openjarvis") / SOURCE_PATH
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == SOURCE_SHA256, (digest, SOURCE_SHA256)
    text = raw.decode("utf-8")
    required = [
        '@router.delete("/v1/models/{model_name:path}")',
        "async def delete_model(model_name: str, request: Request):",
        'if engine_name != "ollama" and getattr(engine, "engine_id", "") != "ollama":',
        'host = getattr(engine, "_host", "http://localhost:11434")',
        'async with _httpx.AsyncClient(base_url=host, timeout=30.0) as client:',
        '"DELETE",',
        '"/api/delete",',
        'json={"name": model_name},',
        'return {"status": "deleted", "model": model_name}',
    ]
    for needle in required:
        assert needle in text, needle
    return {
        "canonical_parity_status": "UNVERIFIED",
        "capability_id": CAPABILITY_ID,
        "capability_name": "DELETE /v1/models/{model_name:path}",
        "checkpoint": "CP03",
        "date": "2026-09-24",
        "http_listener_execution": "NOT_RUN",
        "http_method": "DELETE",
        "http_path": "/v1/models/{model_name:path}",
        "model_delete_execution": "NOT_RUN",
        "model_executions": 0,
        "ollama_api_path": "/api/delete",
        "ollama_delete_execution": "NOT_RUN",
        "ollama_engine_gate_present": True,
        "ownership": "OWNED",
        "parity_promotions": 0,
        "project_id": "CLEVER-JARVIS-001",
        "provider_egress_executions": 0,
        "request_timeout_seconds": 30.0,
        "schema_version": 1,
        "source_blob_sha1": SOURCE_BLOB_SHA1,
        "source_execution": False,
        "source_line": SOURCE_LINE,
        "source_path": SOURCE_PATH,
        "source_probe": "PASS",
        "surface_kind": "http_route",
        "task": "W02-17",
        "terminal_eligible_in_w02": True,
        "tool_executions": 0,
        "upstream_commit": UPSTREAM_COMMIT,
    }


def patch_binding_and_tests(probe: dict) -> None:
    append_jsonl_once(
        ROOT / "inventory/cp03/w02_evidence_bindings.jsonl",
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
        },
        "capability_id",
    )

    tests = ROOT / "tests/test_cp03_w02_parity_graph.py"
    replace_once(
        tests,
        'SERVER_MODEL_PULL_CAPABILITY_ID = "cap_abafd7c735464aaecfe109d7"\n',
        'SERVER_MODEL_PULL_CAPABILITY_ID = "cap_abafd7c735464aaecfe109d7"\nSERVER_MODEL_DELETE_CAPABILITY_ID = "cap_46e5a39cd2e2af9c6cf8eba7"\n',
    )
    replace_once(
        tests,
        'SERVER_MODEL_PULL_TEST_ID = (\n    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n    "test_server_model_pull_binding_is_capability_specific_and_source_backed"\n)\n',
        'SERVER_MODEL_PULL_TEST_ID = (\n    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n    "test_server_model_pull_binding_is_capability_specific_and_source_backed"\n)\nSERVER_MODEL_DELETE_TEST_ID = (\n    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n    "test_server_delete_model_binding_is_capability_specific_and_source_backed"\n)\n',
    )
    replace_once(
        tests,
        "    def test_current_matrix_has_twenty_eight_candidates_and_no_parity_promotion(self) -> None:\n",
        "    def test_current_matrix_has_twenty_nine_candidates_and_no_parity_promotion(self) -> None:\n",
    )
    replace_once(
        tests,
        '        self.assertEqual(sum(row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE" for row in rows), 28)\n        self.assertEqual(sum(row["w02_evidence_state"] == "UNBOUND" for row in rows), 19)\n',
        '        self.assertEqual(sum(row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE" for row in rows), 29)\n        self.assertEqual(sum(row["w02_evidence_state"] == "UNBOUND" for row in rows), 18)\n',
    )
    replace_once(
        tests,
        "SERVER_MODELS_CAPABILITY_ID, SERVER_MODEL_PULL_CAPABILITY_ID},\n",
        "SERVER_MODELS_CAPABILITY_ID, SERVER_MODEL_PULL_CAPABILITY_ID, SERVER_MODEL_DELETE_CAPABILITY_ID},\n",
    )

    insertion_marker = "    def test_cli_model_list_command_binding_is_capability_specific_and_source_backed(self) -> None:\n"
    method = '''    def test_server_delete_model_binding_is_capability_specific_and_source_backed(self) -> None:\n        row = next(row for row in self.result["rows"] if row["capability_id"] == SERVER_MODEL_DELETE_CAPABILITY_ID)\n        self.assertEqual(row["ownership"], "OWNED")\n        self.assertEqual(row["surface_kind"], "http_route")\n        self.assertEqual(row["source_path"], "src/openjarvis/server/routes.py")\n        self.assertEqual(row["source_line"], 1189)\n        self.assertEqual(row["name"], "DELETE /v1/models/{model_name:path}")\n        self.assertTrue(row["terminal_eligible_in_w02"])\n        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")\n        self.assertEqual(row["w02_evidence_state"], "EVIDENCE_BACKED_CANDIDATE")\n        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")\n        self.assertFalse(row["verified"])\n        self.assertFalse(row["parity_promotion"])\n        binding = row["binding"]\n        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")\n        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")\n        self.assertEqual(binding["test_id"], SERVER_MODEL_DELETE_TEST_ID)\n        self.assertFalse(binding["terminal"])\n        receipt = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")["EVID-W02-MODEL-BRIDGE-20260921"]\n        self.assertEqual(receipt["status"], "VERIFIED")\n        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")\n        self.assertEqual(receipt["native_engine_count"], 15)\n        self.assertEqual(receipt["native_import_failure_count"], 0)\n        self.assertEqual(receipt["native_model_count"], 69)\n        self.assertEqual(receipt["model_executions"], 0)\n        self.assertEqual(receipt["provider_egress_executions"], 0)\n        self.assertEqual(receipt["parity_promotions"], 0)\n        probe = json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_model_delete_source_probe.json").read_text(encoding="utf-8"))\n        self.assertEqual(probe["capability_id"], SERVER_MODEL_DELETE_CAPABILITY_ID)\n        self.assertEqual(probe["source_line"], 1189)\n        self.assertEqual(probe["source_probe"], "PASS")\n        self.assertFalse(probe["source_execution"])\n        self.assertEqual(probe["http_method"], "DELETE")\n        self.assertEqual(probe["http_path"], "/v1/models/{model_name:path}")\n        self.assertTrue(probe["ollama_engine_gate_present"])\n        self.assertEqual(probe["ollama_api_path"], "/api/delete")\n        self.assertEqual(probe["request_timeout_seconds"], 30.0)\n        self.assertEqual(probe["ollama_delete_execution"], "NOT_RUN")\n        self.assertEqual(probe["model_delete_execution"], "NOT_RUN")\n        self.assertEqual(probe["http_listener_execution"], "NOT_RUN")\n        self.assertEqual(probe["model_executions"], 0)\n        self.assertEqual(probe["provider_egress_executions"], 0)\n        self.assertEqual(probe["tool_executions"], 0)\n        self.assertEqual(probe["parity_promotions"], 0)\n\n'''
    text = tests.read_text(encoding="utf-8")
    if "def test_server_delete_model_binding_is_capability_specific_and_source_backed" not in text:
        if insertion_marker not in text:
            raise RuntimeError("server-model-delete test insertion marker missing")
        tests.write_text(text.replace(insertion_marker, method + insertion_marker, 1), encoding="utf-8")

    write_json(
        ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_model_delete_source_probe.json",
        probe,
    )


def persist(probe: dict) -> None:
    probe_path = "evidence/cp03/cp03-w02/W02-17/binding_server_model_delete_source_probe.json"
    probe_sha256 = hashlib.sha256((ROOT / probe_path).read_bytes()).hexdigest()
    report = {
        "binding_capability_id": CAPABILITY_ID,
        "binding_capability_name": "DELETE /v1/models/{model_name:path}",
        "binding_ownership": "OWNED",
        "binding_source_evidence_id": SOURCE_EVIDENCE_ID,
        "binding_source_run_id": 35552788123,
        "binding_source_validated_head": SOURCE_EVIDENCE_HEAD,
        "binding_surface_kind": "http_route",
        "bindings_added_this_slice": 1,
        "bindings_validated_total": BINDINGS_AFTER,
        "checkpoint": "CP03",
        "claim_id": CLAIM_ID,
        "date": "2026-09-24",
        "evidence_id": EVIDENCE_ID,
        "executed_test_id": TEST_ID,
        "gate": "G6",
        "github_actions_run_id": RUN_ID,
        "global_denominator": 7565,
        "http_listener_execution": "NOT_RUN",
        "model_delete_execution": "NOT_RUN",
        "model_executions": 0,
        "next_slice": "Continue W02-17 with one non-conflicting UNBOUND proof unit only when capability-specific execution or exact pinned-source evidence can be paired with an existing completed-task PASS receipt. Preserve AFM/fallback NOT_RUN and avoid active parallel scopes.",
        "ollama_delete_execution": "NOT_RUN",
        "openjarvis_obligations": 646,
        "parity_promotions": 0,
        "path": "evidence/cp03/cp03-w02/W02-17/binding_server_model_delete_report.json",
        "project_id": "CLEVER-JARVIS-001",
        "provider_egress_executions": 0,
        "real_openjarvis_fallback_model_execution": "NOT_RUN",
        "schema_version": 1,
        "source_execution": False,
        "source_probe_path": probe_path,
        "source_probe_sha256": probe_sha256,
        "status": "PASS",
        "task": "W02-17",
        "terminal_eligible_in_w02": True,
        "tool_executions": 0,
        "type": "CP03_W02_G6_CAPABILITY_BINDING",
        "unbound_remaining": UNBOUND_AFTER,
        "validated_base_head": BASE_HEAD,
        "verified_capabilities": 0,
    }
    write_json(
        ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_model_delete_report.json",
        report,
    )
    write_json(ROOT / "sessions/20260922-w02-parity-graph/RESULT.json", report)

    append_jsonl_once(
        ROOT / "ledgers/CLAIM_LEDGER.ndjson",
        {
            "base_head": BASE_HEAD,
            "canonical_task": "W02-17",
            "checkpoint": "CP03",
            "claim_id": CLAIM_ID,
            "coordination": "Continue the sole active W02-17 G6 claim for the non-conflicting core server DELETE /v1/models/{model_name:path} proof unit only. No HTTP listener, model deletion, Ollama side effect, provider/tool side effect, parity promotion, denominator mutation, or W02-18 transition is authorized.",
            "date": "2026-09-24",
            "event": "CONTINUE",
            "event_id": CLAIM_EVENT_ID,
            "owner": "chatgpt-gpt-5.6-sol",
            "schema_version": 1,
            "status": "ACTIVE",
            "wave_id": "CP03-W02-PARITY-GRAPH-20260922",
        },
        "event_id",
    )
    append_jsonl_once(
        ROOT / "ledgers/DECISION_LEDGER.ndjson",
        {
            "checkpoint": "CP03",
            "context": "Exact pinned source proves the core DELETE /v1/models/{model_name:path} route, Ollama-only gate, bounded /api/delete request shape and error mapping. W02-08 provides the exact model/engine bridge receipt, but HTTP listener and actual model deletion remain NOT_RUN; this evidence cannot promote parity.",
            "date": "2026-09-24",
            "decision": "Bind the frozen OpenJarvis model-delete route as a non-terminal EVIDENCE_BACKED_CANDIDATE only.",
            "decision_id": DECISION_ID,
            "evidence_id": EVIDENCE_ID,
            "parity_promotions": 0,
            "schema_version": 1,
            "status": "ACCEPTED",
            "task": "W02-17",
        },
        "decision_id",
    )
    append_jsonl_once(ROOT / "ledgers/EVIDENCE_LEDGER.ndjson", report, "evidence_id")
    append_jsonl_once(
        ROOT / "ledgers/RUN_LOG.ndjson",
        {
            "bindings_validated_total": BINDINGS_AFTER,
            "canonical_task": "W02-17",
            "checkpoint": "CP03",
            "claim_id": CLAIM_ID,
            "date": "2026-09-24",
            "event": "CP03_W02_G6_CAPABILITY_BINDING",
            "event_id": RUN_EVENT_ID,
            "evidence_id": EVIDENCE_ID,
            "goal_id": "CLEVER-JARVIS-001",
            "iteration": "I03",
            "parity_promotions": 0,
            "schema_version": 1,
            "status": "ADVANCED",
            "unbound_remaining": UNBOUND_AFTER,
            "verified_capabilities": 0,
            "wave_id": "CP03-W02",
        },
        "event_id",
    )
    append_jsonl_once(
        ROOT / "ledgers/WAVE_LEDGER.ndjson",
        {
            "bindings_validated_total": BINDINGS_AFTER,
            "canonical_task": "W02-17",
            "checkpoint": "CP03",
            "claim_id": CLAIM_ID,
            "date": "2026-09-24",
            "event": "WAVE_PROGRESS",
            "event_id": WAVE_EVENT_ID,
            "evidence_id": EVIDENCE_ID,
            "parity_promotions": 0,
            "project_id": "CLEVER-JARVIS-001",
            "schema_version": 1,
            "status": "IN_PROGRESS",
            "unbound_remaining": UNBOUND_AFTER,
            "verified_capabilities": 0,
            "wave_id": "CP03-W02",
        },
        "event_id",
    )
    append_jsonl_once(
        ROOT / "ledgers/RISK_LEDGER.ndjson",
        {
            "date": "2026-09-24",
            "event_id": RISK_EVENT_ID,
            "evidence_id": EVIDENCE_ID,
            "mitigation": "Keep W02-17 IN_PROGRESS, verified parity at 0 and W02-18 BLOCKED. This slice proves route/source shape only; destructive model deletion and Ollama side effects stay NOT_RUN. Continue one capability-specific proof unit at a time.",
            "risk_id": "RISK-W02-G6-K47-BINDINGS-PENDING-20260922",
            "schema_version": 1,
            "severity": "P1",
            "status": "MITIGATING",
            "unbound_remaining": UNBOUND_AFTER,
        },
        "event_id",
    )

    replace_once(
        ROOT / "STATE.md",
        "G6 explicit binding progress: `28/47` evidence-backed candidates; `19` UNBOUND",
        "G6 explicit binding progress: `29/47` evidence-backed candidates; `18` UNBOUND",
    )
    append_section_once(
        ROOT / "HANDOFF.md",
        "## W02-17 core server DELETE /v1/models/{model_name:path} binding — source-backed partial verified",
        f'''## W02-17 core server DELETE /v1/models/{{model_name:path}} binding — source-backed partial verified

- `{EVIDENCE_ID}`: `{CAPABILITY_ID}` (`DELETE /v1/models/{{model_name:path}}`, OWNED route at `src/openjarvis/server/routes.py:1189`) is now a non-terminal `EVIDENCE_BACKED_CANDIDATE`.
- Exact pinned source `{UPSTREAM_COMMIT}` proves Ollama-only engine gating, bounded `/api/delete` DELETE request shape and explicit HTTP error mapping. HTTP listener, actual model deletion and Ollama delete execution remain `NOT_RUN`.
- Binding is anchored to completed W02-08 `{SOURCE_EVIDENCE_ID}` at exact SHA `{SOURCE_EVIDENCE_HEAD}`. This is candidate evidence only: VERIFIED parity remains 0.
- G6 is now 29 `EVIDENCE_BACKED_CANDIDATE` / 18 `UNBOUND`; parity promotions 0; denominator 7565 and OpenJarvis obligations 646 unchanged. W02-17 remains `IN_PROGRESS`; W02-18/W02-19 remain `BLOCKED`.
- Exact next slice: another non-conflicting W02-17 proof unit with capability-specific execution or exact pinned-source evidence paired to an exact completed-task PASS receipt; AFM compatible-host proof and real fallback-model execution remain unresolved.''',
    )


def regenerate_and_validate() -> None:
    run(sys.executable, "scripts/context/build_context_pack.py")
    commands = [
        [sys.executable, "scripts/validate_agentic_state.py"],
        [sys.executable, "scripts/context/validate_context_pack.py"],
        [sys.executable, "scripts/context/build_context_pack.py", "--check"],
        [sys.executable, "scripts/context/validate_next_actions.py"],
        [sys.executable, "scripts/cp03/validate_w02_plan.py"],
        [sys.executable, "-m", "scripts.parity.ledger", "--check", "--source-repo", "openjarvis"],
        [sys.executable, "scripts/cp03/w02_parity_graph.py", "--check"],
        [sys.executable, "-m", "unittest", TEST_ID, "-v"],
        [sys.executable, "-m", "unittest", "tests.test_cp03_w02_parity_graph", "-v"],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)


def main() -> int:
    verify_base()
    probe = build_source_probe()
    patch_binding_and_tests(probe)

    # First narrow GREEN gate after the explicit binding/probe mutation.
    run(sys.executable, "scripts/cp03/w02_parity_graph.py", "--write")
    run(sys.executable, "-m", "unittest", TEST_ID, "-v")
    run(sys.executable, "scripts/cp03/w02_parity_graph.py", "--check")

    persist(probe)
    regenerate_and_validate()

    result = graph.compile_root(ROOT)
    assert result["summary"]["binding_counts"] == {
        "EVIDENCE_BACKED_CANDIDATE": BINDINGS_AFTER,
        "UNBOUND": UNBOUND_AFTER,
    }
    assert result["summary"]["verified_capabilities"] == 0
    assert result["summary"]["parity_promotions"] == 0
    assert result["summary"]["global_denominator"] == 7565
    assert result["summary"]["openjarvis_obligations"] == 646
    task_graph = load_json(ROOT / "iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    tasks = {task["id"]: task for task in task_graph["tasks"]}
    assert tasks["W02-17"]["status"] == "IN_PROGRESS"
    assert tasks["W02-18"]["status"] == "BLOCKED"
    assert tasks["W02-19"]["status"] == "BLOCKED"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
