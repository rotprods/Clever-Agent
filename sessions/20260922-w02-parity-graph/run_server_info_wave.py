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
CAPABILITY_ID = "cap_64144d3f18be9d9652e0be6e"
EVIDENCE_ID = "EVID-W02-PARITY-BINDING-SERVER-INFO-20260924"
DECISION_ID = "DEC-W02-G6-SERVER-INFO-BINDING-20260924"
TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_server_info_binding_is_capability_specific_and_source_backed"
)
CLAIM_ID = "CLAIM-CP03-W02-PARITY-GRAPH-20260922"
CLAIM_EVENT_ID = "CLAIM-CONTINUE-W02-G6-SERVER-INFO-20260924"
RUN_EVENT_ID = "RUN-W02-G6-SERVER-INFO-20260924"
WAVE_EVENT_ID = "WAVE-W02-G6-SERVER-INFO-20260924"
RISK_EVENT_ID = "RISK-UPDATE-W02-G6-K47-BINDINGS-SERVER-INFO-20260924"
SOURCE_EVIDENCE_ID = "EVID-W02-MODEL-BRIDGE-20260921"
SOURCE_EVIDENCE_HEAD = "a866c335a0f9cad75122c8eb7c5310d358f6aad4"
SOURCE_PATH = "src/openjarvis/server/routes.py"
SOURCE_LINE = 1374
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


def run(command: list[str], *, expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if expect_success and result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise subprocess.CalledProcessError(result.returncode, command)
    return result


def verify_base() -> None:
    summary = load_json(ROOT / "reports/cp03/w02_parity/SUMMARY.json")
    task_graph = load_json(ROOT / "iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    task = next(t for t in task_graph["tasks"] if t["id"] == "W02-17")
    statuses = {t["id"]: t["status"] for t in task_graph["tasks"]}
    assert task_graph["first_executable_task"] == "W02-17"
    assert task["status"] == "IN_PROGRESS"
    assert all(statuses[d] == "COMPLETE" for d in task["depends_on"])
    assert next(t for t in task_graph["tasks"] if t["id"] == "W02-18")["status"] == "BLOCKED"
    assert next(t for t in task_graph["tasks"] if t["id"] == "W02-19")["status"] == "BLOCKED"
    assert summary["binding_counts"] == {"EVIDENCE_BACKED_CANDIDATE": BINDINGS_BEFORE, "UNBOUND": UNBOUND_BEFORE}
    assert summary["verified_capabilities"] == 0
    assert summary["parity_promotions"] == 0
    assert summary["global_denominator"] == 7565
    assert summary["openjarvis_obligations"] == 646
    state = (ROOT / "STATE.md").read_text(encoding="utf-8")
    assert "28/47" in state and "19` UNBOUND" in state
    rows = graph.compile_root(ROOT)["rows"]
    row = next(item for item in rows if item["capability_id"] == CAPABILITY_ID)
    assert row["w02_evidence_state"] == "UNBOUND"
    assert row["canonical_parity_status"] == "UNVERIFIED"
    assert row["ownership"] == "SHARED"
    assert row["terminal_eligible_in_w02"] is False
    assert row["verified"] is False and row["parity_promotion"] is False
    active = [
        item for item in read_jsonl(ROOT / "ledgers/CLAIM_LEDGER.ndjson")
        if item.get("claim_id") == CLAIM_ID
    ]
    assert active and active[-1]["status"] == "ACTIVE"
    assert active[-1]["owner"] == "chatgpt-gpt-5.6-sol"


def prove_red() -> None:
    result = run([sys.executable, "-m", "unittest", "-v", TEST_ID], expect_success=False)
    assert result.returncode != 0, "new capability test unexpectedly existed/passed before mutation"


def build_source_probe() -> dict:
    source = Path("/tmp/openjarvis") / SOURCE_PATH
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == SOURCE_SHA256, (digest, SOURCE_SHA256)
    text = raw.decode("utf-8")
    required = [
        '@router.get("/v1/info")',
        "async def server_info(request: Request):",
        'agent = getattr(request.app.state, "agent", None)',
        'agent_id = getattr(agent, "agent_id", None) if agent else None',
        'agent_id = getattr(request.app.state, "agent_name", None)',
        '"model": getattr(request.app.state, "model", "")',
        '"agent": agent_id',
        '"engine": getattr(request.app.state, "engine_name", "")',
    ]
    for needle in required:
        assert needle in text, needle
    return {
        "app_state_execution": "NOT_RUN",
        "canonical_parity_status": "UNVERIFIED",
        "capability_id": CAPABILITY_ID,
        "capability_name": "GET /v1/info",
        "checkpoint": "CP03",
        "date": "2026-09-24",
        "http_listener_execution": "NOT_RUN",
        "http_method": "GET",
        "http_path": "/v1/info",
        "model_executions": 0,
        "ownership": "SHARED",
        "parity_promotions": 0,
        "project_id": "CLEVER-JARVIS-001",
        "provider_egress_executions": 0,
        "reported_fields": ["model", "agent", "engine"],
        "schema_version": 1,
        "source_blob_sha1": SOURCE_BLOB_SHA1,
        "source_execution": False,
        "source_line": SOURCE_LINE,
        "source_path": SOURCE_PATH,
        "source_probe": "PASS",
        "surface_kind": "http_route",
        "task": "W02-17",
        "terminal_eligible_in_w02": False,
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
        'SERVER_MODEL_PULL_CAPABILITY_ID = "cap_abafd7c735464aaecfe109d7"\nSERVER_INFO_CAPABILITY_ID = "cap_64144d3f18be9d9652e0be6e"\n',
    )
    replace_once(
        tests,
        'SERVER_MODEL_PULL_TEST_ID = (\n    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n    "test_server_model_pull_binding_is_capability_specific_and_source_backed"\n)\n',
        'SERVER_MODEL_PULL_TEST_ID = (\n    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n    "test_server_model_pull_binding_is_capability_specific_and_source_backed"\n)\nSERVER_INFO_TEST_ID = (\n    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n    "test_server_info_binding_is_capability_specific_and_source_backed"\n)\n',
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
        "SERVER_HEALTH_CAPABILITY_ID, SERVER_MODELS_CAPABILITY_ID, SERVER_MODEL_PULL_CAPABILITY_ID},\n",
        "SERVER_HEALTH_CAPABILITY_ID, SERVER_MODELS_CAPABILITY_ID, SERVER_MODEL_PULL_CAPABILITY_ID, SERVER_INFO_CAPABILITY_ID},\n",
    )

    insertion_marker = "    def test_cli_model_list_command_binding_is_capability_specific_and_source_backed(self) -> None:\n"
    method = '''    def test_server_info_binding_is_capability_specific_and_source_backed(self) -> None:\n        row = next(row for row in self.result["rows"] if row["capability_id"] == SERVER_INFO_CAPABILITY_ID)\n        self.assertEqual(row["ownership"], "SHARED")\n        self.assertEqual(row["surface_kind"], "http_route")\n        self.assertEqual(row["source_path"], "src/openjarvis/server/routes.py")\n        self.assertEqual(row["source_line"], 1374)\n        self.assertEqual(row["name"], "GET /v1/info")\n        self.assertFalse(row["terminal_eligible_in_w02"])\n        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")\n        self.assertEqual(row["w02_evidence_state"], "EVIDENCE_BACKED_CANDIDATE")\n        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")\n        self.assertFalse(row["verified"])\n        self.assertFalse(row["parity_promotion"])\n        binding = row["binding"]\n        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")\n        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")\n        self.assertEqual(binding["test_id"], SERVER_INFO_TEST_ID)\n        self.assertFalse(binding["terminal"])\n        receipt = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")["EVID-W02-MODEL-BRIDGE-20260921"]\n        self.assertEqual(receipt["status"], "VERIFIED")\n        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")\n        self.assertEqual(receipt["native_engine_count"], 15)\n        self.assertEqual(receipt["native_import_failure_count"], 0)\n        self.assertEqual(receipt["native_model_count"], 69)\n        self.assertEqual(receipt["model_executions"], 0)\n        self.assertEqual(receipt["provider_egress_executions"], 0)\n        self.assertEqual(receipt["parity_promotions"], 0)\n        probe = json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_info_source_probe.json").read_text(encoding="utf-8"))\n        self.assertEqual(probe["capability_id"], SERVER_INFO_CAPABILITY_ID)\n        self.assertEqual(probe["source_line"], 1374)\n        self.assertEqual(probe["source_probe"], "PASS")\n        self.assertFalse(probe["source_execution"])\n        self.assertEqual(probe["http_method"], "GET")\n        self.assertEqual(probe["http_path"], "/v1/info")\n        self.assertEqual(probe["reported_fields"], ["model", "agent", "engine"])\n        self.assertEqual(probe["app_state_execution"], "NOT_RUN")\n        self.assertEqual(probe["http_listener_execution"], "NOT_RUN")\n        self.assertEqual(probe["model_executions"], 0)\n        self.assertEqual(probe["provider_egress_executions"], 0)\n        self.assertEqual(probe["tool_executions"], 0)\n        self.assertEqual(probe["parity_promotions"], 0)\n\n'''
    text = tests.read_text(encoding="utf-8")
    if "def test_server_info_binding_is_capability_specific_and_source_backed" not in text:
        if insertion_marker not in text:
            raise RuntimeError("server-info test insertion marker missing")
        tests.write_text(text.replace(insertion_marker, method + insertion_marker, 1), encoding="utf-8")

    write_json(ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_info_source_probe.json", probe)


def persist(probe: dict) -> None:
    probe_path = "evidence/cp03/cp03-w02/W02-17/binding_server_info_source_probe.json"
    probe_sha256 = hashlib.sha256((ROOT / probe_path).read_bytes()).hexdigest()
    report = {
        "app_state_execution": "NOT_RUN",
        "binding_capability_id": CAPABILITY_ID,
        "binding_capability_name": "GET /v1/info",
        "binding_ownership": "SHARED",
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
        "model_executions": 0,
        "next_slice": "Continue W02-17 with one non-conflicting proof unit only when capability-specific executed or exact pinned-source evidence can be paired with an existing completed-task PASS receipt. Preserve AFM/fallback NOT_RUN and avoid extant branches.",
        "openjarvis_obligations": 646,
        "parity_promotions": 0,
        "path": "evidence/cp03/cp03-w02/W02-17/binding_server_info_report.json",
        "project_id": "CLEVER-JARVIS-001",
        "provider_egress_executions": 0,
        "real_openjarvis_fallback_model_execution": "NOT_RUN",
        "schema_version": 1,
        "source_execution": False,
        "source_probe_path": probe_path,
        "source_probe_sha256": probe_sha256,
        "status": "PASS",
        "task": "W02-17",
        "terminal_eligible_in_w02": False,
        "tool_executions": 0,
        "type": "CP03_W02_G6_CAPABILITY_BINDING",
        "unbound_remaining": UNBOUND_AFTER,
        "validated_base_head": BASE_HEAD,
        "verified_capabilities": 0,
    }
    write_json(ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_info_report.json", report)
    write_json(ROOT / "sessions/20260922-w02-parity-graph/RESULT.json", report)

    append_jsonl_once(ROOT / "ledgers/CLAIM_LEDGER.ndjson", {
        "base_head": BASE_HEAD,
        "canonical_task": "W02-17",
        "checkpoint": "CP03",
        "claim_id": CLAIM_ID,
        "coordination": "Continue the sole active W02-17 G6 claim for the branch-free shared core server GET /v1/info proof unit only. No HTTP listener/model/provider/tool execution, parity promotion, denominator mutation, or W02-18 transition is authorized.",
        "date": "2026-09-24",
        "event": "CONTINUE",
        "event_id": CLAIM_EVENT_ID,
        "owner": "chatgpt-gpt-5.6-sol",
        "schema_version": 1,
        "status": "ACTIVE",
        "wave_id": "CP03-W02-PARITY-GRAPH-20260922",
    }, "event_id")
    append_jsonl_once(ROOT / "ledgers/DECISION_LEDGER.ndjson", {
        "checkpoint": "CP03",
        "context": "Exact pinned source proves the shared GET /v1/info route and its model/agent/engine projection from app state. W02-08 provides the exact model/engine bridge receipt, but HTTP listener and app-state route execution remain NOT_RUN; this shared W02/W03 surface is non-terminal and cannot promote parity.",
        "date": "2026-09-24",
        "decision": "Bind the frozen OpenJarvis GET /v1/info route as a non-terminal EVIDENCE_BACKED_CANDIDATE only.",
        "decision_id": DECISION_ID,
        "evidence_id": EVIDENCE_ID,
        "parity_promotions": 0,
        "schema_version": 1,
        "status": "ACCEPTED",
        "task": "W02-17",
    }, "decision_id")
    append_jsonl_once(ROOT / "ledgers/EVIDENCE_LEDGER.ndjson", report, "evidence_id")
    append_jsonl_once(ROOT / "ledgers/RUN_LOG.ndjson", {
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
    }, "event_id")
    append_jsonl_once(ROOT / "ledgers/WAVE_LEDGER.ndjson", {
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
    }, "event_id")
    append_jsonl_once(ROOT / "ledgers/RISK_LEDGER.ndjson", {
        "date": "2026-09-24",
        "event_id": RISK_EVENT_ID,
        "evidence_id": EVIDENCE_ID,
        "mitigation": "Keep W02-17 IN_PROGRESS, verified parity at 0 and W02-18 BLOCKED. This shared slice proves source projection only; route/app-state runtime execution stays NOT_RUN. Continue one capability-specific proof unit at a time.",
        "risk_id": "RISK-W02-G6-K47-BINDINGS-PENDING-20260922",
        "schema_version": 1,
        "severity": "P1",
        "status": "MITIGATING",
        "unbound_remaining": UNBOUND_AFTER,
    }, "event_id")

    replace_once(
        ROOT / "STATE.md",
        "G6 explicit binding progress: `28/47` evidence-backed candidates; `19` UNBOUND",
        "G6 explicit binding progress: `29/47` evidence-backed candidates; `18` UNBOUND",
    )
    append_section_once(
        ROOT / "HANDOFF.md",
        "## W02-17 core server GET /v1/info binding — source-backed partial verified",
        f'''## W02-17 core server GET /v1/info binding — source-backed partial verified

- `{EVIDENCE_ID}`: `{CAPABILITY_ID}` (`GET /v1/info`, SHARED W02/W03 route at `src/openjarvis/server/routes.py:1374`) is now a non-terminal `EVIDENCE_BACKED_CANDIDATE`.
- Exact pinned source `{UPSTREAM_COMMIT}` proves the route projects model, agent and engine identifiers from app state, including configured-agent fallback. HTTP listener and app-state route execution remain `NOT_RUN`.
- Binding is anchored to completed W02-08 `{SOURCE_EVIDENCE_ID}` at exact SHA `{SOURCE_EVIDENCE_HEAD}`. This is candidate evidence only: VERIFIED parity remains 0.
- G6 is now 29 `EVIDENCE_BACKED_CANDIDATE` / 18 `UNBOUND`; parity promotions 0; denominator 7565 and OpenJarvis obligations 646 unchanged. W02-17 remains `IN_PROGRESS`; W02-18/W02-19 remain `BLOCKED`.
- Exact next slice: another branch-free W02-17 proof unit with capability-specific execution or exact pinned-source evidence paired to an exact completed-task PASS receipt; AFM compatible-host proof and real fallback-model execution remain unresolved.''',
    )


def regenerate_and_validate() -> None:
    commands = [
        [sys.executable, "scripts/cp03/w02_parity_graph.py", "--write"],
        [sys.executable, "scripts/context/build_context_pack.py"],
        [sys.executable, "scripts/validate_agentic_state.py"],
        [sys.executable, "scripts/context/validate_context_pack.py"],
        [sys.executable, "scripts/context/build_context_pack.py", "--check"],
        [sys.executable, "scripts/context/validate_next_actions.py"],
        [sys.executable, "scripts/cp03/validate_w02_plan.py"],
        [sys.executable, "-m", "scripts.parity.ledger", "--check", "--source-repo", "openjarvis"],
        [sys.executable, "scripts/cp03/w02_parity_graph.py", "--check"],
        [sys.executable, "-m", "unittest", "-v", TEST_ID],
        [sys.executable, "-m", "unittest", "-v", "tests.test_cp03_w02_parity_graph"],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
    summary = load_json(ROOT / "reports/cp03/w02_parity/SUMMARY.json")
    assert summary["binding_counts"] == {"EVIDENCE_BACKED_CANDIDATE": BINDINGS_AFTER, "UNBOUND": UNBOUND_AFTER}
    assert summary["global_denominator"] == 7565
    assert summary["openjarvis_obligations"] == 646
    assert summary["verified_capabilities"] == 0
    assert summary["parity_promotions"] == 0
    rows = graph.compile_root(ROOT)["rows"]
    row = next(item for item in rows if item["capability_id"] == CAPABILITY_ID)
    assert row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE"
    assert row["canonical_parity_status"] == "UNVERIFIED"
    assert row["ownership"] == "SHARED"
    assert row["terminal_eligible_in_w02"] is False
    assert row["verified"] is False and row["parity_promotion"] is False
    graph_state = load_json(ROOT / "iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    assert graph_state["first_executable_task"] == "W02-17"
    assert next(t for t in graph_state["tasks"] if t["id"] == "W02-17")["status"] == "IN_PROGRESS"
    assert next(t for t in graph_state["tasks"] if t["id"] == "W02-18")["status"] == "BLOCKED"
    assert next(t for t in graph_state["tasks"] if t["id"] == "W02-19")["status"] == "BLOCKED"


def main() -> None:
    verify_base()
    prove_red()
    probe = build_source_probe()
    patch_binding_and_tests(probe)
    run([sys.executable, "-m", "unittest", "-v", TEST_ID])
    persist(probe)
    regenerate_and_validate()
    print(json.dumps({
        "status": "ADVANCED",
        "task": "W02-17",
        "capability_id": CAPABILITY_ID,
        "bindings": BINDINGS_AFTER,
        "unbound": UNBOUND_AFTER,
        "verified_capabilities": 0,
        "parity_promotions": 0,
        "evidence_id": EVIDENCE_ID,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
