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

BASE_HEAD = "35c1589e14b3d10b9e17e81070307ad816a1863d"
UPSTREAM_COMMIT = "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"
CAPABILITY_ID = "cap_1defee98e7075463dcf65434"
EVIDENCE_ID = "EVID-W02-PARITY-BINDING-HEURISTIC-ROUTER-20260924"
DECISION_ID = "DEC-W02-G6-HEURISTIC-ROUTER-BINDING-20260924"
TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_heuristic_router_binding_is_capability_specific_and_source_backed"
)
CLAIM_ID = "CLAIM-CP03-W02-PARITY-GRAPH-20260922"
CLAIM_EVENT_ID = "CLAIM-CONTINUE-W02-G6-HEURISTIC-ROUTER-20260924"
RUN_EVENT_ID = "RUN-W02-G6-HEURISTIC-ROUTER-20260924"
WAVE_EVENT_ID = "WAVE-W02-G6-HEURISTIC-ROUTER-20260924"
RISK_EVENT_ID = "RISK-UPDATE-W02-G6-K47-BINDINGS-HEURISTIC-ROUTER-20260924"
SOURCE_EVIDENCE_ID = "EVID-W02-MODEL-BRIDGE-20260921"
SOURCE_EVIDENCE_HEAD = "a866c335a0f9cad75122c8eb7c5310d358f6aad4"
SOURCE_PATH = "src/openjarvis/learning/routing/heuristic_policy.py"
SOURCE_LINE = 12
SOURCE_BLOB_SHA1 = "fcb58471f501a602b452e6020928fc24addcef09"
BINDINGS_BEFORE = 31
BINDINGS_AFTER = 32
UNBOUND_BEFORE = 16
UNBOUND_AFTER = 15
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
    assert task["depends_on"] == ["W02-01", "W02-13", "W02-14", "W02-16"]
    assert all(statuses[d] == "COMPLETE" for d in task["depends_on"])
    assert statuses["W02-18"] == "BLOCKED" and statuses["W02-19"] == "BLOCKED"
    assert summary["binding_counts"] == {"EVIDENCE_BACKED_CANDIDATE": BINDINGS_BEFORE, "UNBOUND": UNBOUND_BEFORE}
    assert summary["verified_capabilities"] == 0
    assert summary["parity_promotions"] == 0
    assert summary["global_denominator"] == 7565
    assert summary["openjarvis_obligations"] == 646
    state = (ROOT / "STATE.md").read_text(encoding="utf-8")
    assert "31/47" in state and "16` UNBOUND" in state
    row = next(item for item in graph.compile_root(ROOT)["rows"] if item["capability_id"] == CAPABILITY_ID)
    assert row["w02_evidence_state"] == "UNBOUND"
    assert row["canonical_parity_status"] == "UNVERIFIED"
    assert row["ownership"] == "OWNED"
    assert row["surface_kind"] == "registry_registration"
    assert row["terminal_eligible_in_w02"] is True
    assert row["verified"] is False and row["parity_promotion"] is False
    claims = [item for item in read_jsonl(ROOT / "ledgers/CLAIM_LEDGER.ndjson") if item.get("claim_id") == CLAIM_ID]
    assert claims and claims[-1]["status"] == "ACTIVE"
    assert claims[-1]["owner"] == "chatgpt-gpt-5.6-sol"


def prove_red() -> None:
    result = run([sys.executable, "-m", "unittest", "-v", TEST_ID], expect_success=False)
    assert result.returncode != 0, "new capability test unexpectedly existed/passed before mutation"


def build_source_probe() -> dict:
    source = Path("/tmp/openjarvis") / SOURCE_PATH
    raw = source.read_bytes()
    blob = subprocess.check_output(["git", "-C", "/tmp/openjarvis", "hash-object", SOURCE_PATH], text=True).strip()
    assert blob == SOURCE_BLOB_SHA1, (blob, SOURCE_BLOB_SHA1)
    text = raw.decode("utf-8")
    required = [
        "from openjarvis.core.registry import RouterPolicyRegistry",
        "from openjarvis.learning.routing.router import HeuristicRouter",
        "def ensure_registered() -> None:",
        'if not RouterPolicyRegistry.contains("heuristic"):',
        'RouterPolicyRegistry.register_value("heuristic", HeuristicRouter)',
        "ensure_registered()",
    ]
    for needle in required:
        assert needle in text, needle
    return {
        "canonical_parity_status": "UNVERIFIED",
        "capability_id": CAPABILITY_ID,
        "capability_name": "heuristic",
        "checkpoint": "CP03",
        "date": "2026-09-24",
        "model_executions": 0,
        "ownership": "OWNED",
        "parity_promotions": 0,
        "project_id": "CLEVER-JARVIS-001",
        "provider_egress_executions": 0,
        "router_policy_execution": "NOT_RUN",
        "schema_version": 1,
        "source_blob_sha1": SOURCE_BLOB_SHA1,
        "source_execution": False,
        "source_line": SOURCE_LINE,
        "source_path": SOURCE_PATH,
        "source_probe": "PASS",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "surface_kind": "registry_registration",
        "task": "W02-17",
        "terminal_eligible_in_w02": True,
        "tool_executions": 0,
        "upstream_commit": UPSTREAM_COMMIT,
        "w02_source_facts": [
            "router_policy_registry_import",
            "heuristic_router_import",
            "contains_guard",
            "heuristic_register_value",
            "import_time_ensure_registered",
        ],
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
        'CLI_ASK_COMMAND_CAPABILITY_ID = "cap_ce98b24c0ed43607f27027a3"\n',
        'CLI_ASK_COMMAND_CAPABILITY_ID = "cap_ce98b24c0ed43607f27027a3"\nHEURISTIC_ROUTER_CAPABILITY_ID = "cap_1defee98e7075463dcf65434"\n',
    )
    replace_once(
        tests,
        'CLI_ASK_COMMAND_TEST_ID = (\n    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n    "test_cli_ask_command_binding_is_capability_specific_and_source_backed"\n)\n',
        'CLI_ASK_COMMAND_TEST_ID = (\n    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n    "test_cli_ask_command_binding_is_capability_specific_and_source_backed"\n)\nHEURISTIC_ROUTER_TEST_ID = (\n    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n    "test_heuristic_router_binding_is_capability_specific_and_source_backed"\n)\n',
    )
    replace_once(
        tests,
        "    def test_current_matrix_has_thirty_one_candidates_and_no_parity_promotion(self) -> None:\n",
        "    def test_current_matrix_has_thirty_two_candidates_and_no_parity_promotion(self) -> None:\n",
    )
    replace_once(
        tests,
        '        self.assertEqual(sum(row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE" for row in rows), 31)\n        self.assertEqual(sum(row["w02_evidence_state"] == "UNBOUND" for row in rows), 16)\n',
        '        self.assertEqual(sum(row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE" for row in rows), 32)\n        self.assertEqual(sum(row["w02_evidence_state"] == "UNBOUND" for row in rows), 15)\n',
    )
    replace_once(
        tests,
        "SERVER_MODEL_PULL_CAPABILITY_ID, SERVER_INFO_CAPABILITY_ID},",
        "SERVER_MODEL_PULL_CAPABILITY_ID, SERVER_INFO_CAPABILITY_ID, HEURISTIC_ROUTER_CAPABILITY_ID},",
    )

    marker = "    def test_nexa_chat_completions_binding_is_capability_specific_and_source_backed(self) -> None:\n"
    method = '''    def test_heuristic_router_binding_is_capability_specific_and_source_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == HEURISTIC_ROUTER_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/learning/routing/heuristic_policy.py")
        self.assertEqual(row["source_line"], 12)
        self.assertEqual(row["name"], "heuristic")
        self.assertTrue(row["terminal_eligible_in_w02"])
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["w02_evidence_state"], "EVIDENCE_BACKED_CANDIDATE")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], HEURISTIC_ROUTER_TEST_ID)
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
        probe = json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_heuristic_router_source_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["capability_id"], HEURISTIC_ROUTER_CAPABILITY_ID)
        self.assertEqual(probe["source_line"], 12)
        self.assertEqual(probe["source_probe"], "PASS")
        self.assertFalse(probe["source_execution"])
        self.assertEqual(probe["router_policy_execution"], "NOT_RUN")
        self.assertEqual(probe["model_executions"], 0)
        self.assertEqual(probe["provider_egress_executions"], 0)
        self.assertEqual(probe["tool_executions"], 0)
        self.assertEqual(probe["parity_promotions"], 0)

'''
    text = tests.read_text(encoding="utf-8")
    if "def test_heuristic_router_binding_is_capability_specific_and_source_backed" not in text:
        if marker not in text:
            raise RuntimeError("heuristic-router test insertion marker missing")
        tests.write_text(text.replace(marker, method + marker, 1), encoding="utf-8")

    write_json(ROOT / "evidence/cp03/cp03-w02/W02-17/binding_heuristic_router_source_probe.json", probe)


def persist(probe: dict) -> None:
    probe_path = "evidence/cp03/cp03-w02/W02-17/binding_heuristic_router_source_probe.json"
    probe_sha256 = hashlib.sha256((ROOT / probe_path).read_bytes()).hexdigest()
    report = {
        "binding_capability_id": CAPABILITY_ID,
        "binding_capability_name": "heuristic",
        "binding_ownership": "OWNED",
        "binding_source_evidence_id": SOURCE_EVIDENCE_ID,
        "binding_source_run_id": 35552788123,
        "binding_source_validated_head": SOURCE_EVIDENCE_HEAD,
        "binding_surface_kind": "registry_registration",
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
        "model_executions": 0,
        "next_slice": "Continue W02-17 with one non-conflicting proof unit only when capability-specific execution or exact pinned-source evidence can be paired with an exact completed-task PASS receipt. Preserve AFM/fallback NOT_RUN and avoid extant branches.",
        "openjarvis_obligations": 646,
        "parity_promotions": 0,
        "path": "evidence/cp03/cp03-w02/W02-17/binding_heuristic_router_report.json",
        "project_id": "CLEVER-JARVIS-001",
        "provider_egress_executions": 0,
        "real_openjarvis_fallback_model_execution": "NOT_RUN",
        "router_policy_execution": "NOT_RUN",
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
    write_json(ROOT / "evidence/cp03/cp03-w02/W02-17/binding_heuristic_router_report.json", report)
    write_json(ROOT / "sessions/20260922-w02-parity-graph/RESULT.json", report)

    append_jsonl_once(ROOT / "ledgers/CLAIM_LEDGER.ndjson", {
        "base_head": BASE_HEAD,
        "canonical_task": "W02-17",
        "checkpoint": "CP03",
        "claim_id": CLAIM_ID,
        "coordination": "Continue the sole active W02-17 G6 claim for the branch-free heuristic RouterPolicyRegistry source-proof unit only. Existing AFM, Apple-FM, cloud-reload, InferenceStartEvent and server-delete-model branches remain excluded. No router execution, model/provider/tool execution, parity promotion, denominator mutation, or W02-18 transition is authorized.",
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
        "context": "Exact pinned OpenJarvis source proves import-time guarded registration of the heuristic RouterPolicyRegistry entry. The completed W02-08 receipt remains the exact binding receipt used by the G6 compiler, but router execution is NOT_RUN. This slice therefore records source-backed candidate evidence only and cannot establish behavioral parity.",
        "date": "2026-09-24",
        "decision": "Bind the frozen heuristic router-policy registration as a non-terminal EVIDENCE_BACKED_CANDIDATE only.",
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
        "mitigation": "Keep W02-17 IN_PROGRESS, VERIFIED parity at 0 and W02-18 BLOCKED. Static registration proof does not prove router-policy execution or selection semantics; continue one non-conflicting proof unit at a time.",
        "risk_id": "RISK-W02-G6-K47-BINDINGS-PENDING-20260922",
        "schema_version": 1,
        "severity": "P1",
        "status": "MITIGATING",
        "unbound_remaining": UNBOUND_AFTER,
    }, "event_id")

    replace_once(
        ROOT / "STATE.md",
        "G6 explicit binding progress: `31/47` evidence-backed candidates; `16` UNBOUND",
        "G6 explicit binding progress: `32/47` evidence-backed candidates; `15` UNBOUND",
    )
    append_section_once(
        ROOT / "HANDOFF.md",
        "## W02-17 heuristic router binding — source-backed partial verified",
        f'''## W02-17 heuristic router binding — source-backed partial verified

- `{EVIDENCE_ID}`: `{CAPABILITY_ID}` (`heuristic`, OWNED at `{SOURCE_PATH}:{SOURCE_LINE}`) is now a non-terminal `EVIDENCE_BACKED_CANDIDATE`.
- Exact pinned OpenJarvis `{UPSTREAM_COMMIT}` proves guarded import-time `RouterPolicyRegistry.register_value("heuristic", HeuristicRouter)` registration. Router-policy execution remains `NOT_RUN`; model/provider/tool executions remain 0.
- Binding is anchored to completed W02-08 `{SOURCE_EVIDENCE_ID}` at exact SHA `{SOURCE_EVIDENCE_HEAD}`. This is candidate evidence only: VERIFIED parity remains 0.
- G6 is now 32 `EVIDENCE_BACKED_CANDIDATE` / 15 `UNBOUND`; parity promotions 0; denominator 7565 and OpenJarvis obligations 646 unchanged. W02-17 remains `IN_PROGRESS`; W02-18/W02-19 remain `BLOCKED`.
- Existing AFM/Apple-FM/cloud-reload/InferenceStartEvent/server-delete-model branches were not touched.
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
    row = next(item for item in graph.compile_root(ROOT)["rows"] if item["capability_id"] == CAPABILITY_ID)
    assert row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE"
    assert row["canonical_parity_status"] == "UNVERIFIED"
    assert row["verified"] is False and row["parity_promotion"] is False
    task_graph = load_json(ROOT / "iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    assert task_graph["first_executable_task"] == "W02-17"
    assert next(t for t in task_graph["tasks"] if t["id"] == "W02-17")["status"] == "IN_PROGRESS"
    assert next(t for t in task_graph["tasks"] if t["id"] == "W02-18")["status"] == "BLOCKED"
    assert next(t for t in task_graph["tasks"] if t["id"] == "W02-19")["status"] == "BLOCKED"


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
