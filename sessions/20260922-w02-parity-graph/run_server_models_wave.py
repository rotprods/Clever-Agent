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

BASE_HEAD = "3e237c46577c9c3284e22403d71caa7a1362b20f"
UPSTREAM_COMMIT = "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"
CAPABILITY_ID = "cap_e54461a19afaa2112911c49b"
EVIDENCE_ID = "EVID-W02-PARITY-BINDING-SERVER-MODELS-20260924"
DECISION_ID = "DEC-W02-G6-SERVER-MODELS-BINDING-20260924"
TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_server_models_binding_is_capability_specific_and_source_backed"
)
CLAIM_ID = "CLAIM-CP03-W02-PARITY-GRAPH-20260922"
CLAIM_EVENT_ID = "CLAIM-CONTINUE-W02-G6-SERVER-MODELS-20260924"
RUN_EVENT_ID = "RUN-W02-G6-SERVER-MODELS-20260924"
WAVE_EVENT_ID = "WAVE-W02-G6-SERVER-MODELS-20260924"
RISK_EVENT_ID = "RISK-UPDATE-W02-G6-K47-BINDINGS-SERVER-MODELS-20260924"
SOURCE_EVIDENCE_ID = "EVID-W02-MODEL-BRIDGE-20260921"
SOURCE_EVIDENCE_HEAD = "a866c335a0f9cad75122c8eb7c5310d358f6aad4"
SOURCE_PATH = "src/openjarvis/server/routes.py"
SOURCE_LINE = 1107
SOURCE_SHA256 = "70d3baebabe7cda294d8419a0f3be8c9b25ba7851901136b95afa1497aed6c56"
SOURCE_BLOB_SHA1 = "16b584c21320d292cc2f0f99d1d0f6d0f40e6f3d"
BINDINGS_BEFORE = 26
BINDINGS_AFTER = 27
UNBOUND_BEFORE = 21
UNBOUND_AFTER = 20
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
    with path.open("a", encoding="utf-8") as fh:
        if path.stat().st_size and not path.read_bytes().endswith(b"\n"):
            fh.write("\n")
        fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one replacement target in {path}: got {count} for {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_section_once(path: Path, marker: str, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n" + section.rstrip() + "\n", encoding="utf-8")


def verify_base() -> None:
    state = (ROOT / "STATE.md").read_text(encoding="utf-8")
    summary = load_json(ROOT / "reports/cp03/w02_parity/SUMMARY.json")
    task_graph = load_json(ROOT / "iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    current = next(t for t in task_graph["tasks"] if t["id"] == "W02-17")
    deps = {t["id"]: t["status"] for t in task_graph["tasks"]}
    assert current["status"] == "IN_PROGRESS"
    assert all(deps[d] == "COMPLETE" for d in current["depends_on"]), current["depends_on"]
    assert summary["binding_counts"] == {"EVIDENCE_BACKED_CANDIDATE": BINDINGS_BEFORE, "UNBOUND": UNBOUND_BEFORE}
    assert summary["verified_capabilities"] == 0
    assert summary["parity_promotions"] == 0
    assert summary["global_denominator"] == 7565
    assert summary["openjarvis_obligations"] == 646
    assert "26/47" in state and "21` UNBOUND" in state
    rows = graph.compile_root(ROOT)["rows"]
    row = next(item for item in rows if item["capability_id"] == CAPABILITY_ID)
    assert row["w02_evidence_state"] == "UNBOUND"
    assert row["canonical_parity_status"] == "UNVERIFIED"
    assert row["verified"] is False and row["parity_promotion"] is False


def build_source_probe() -> dict:
    source = Path("/tmp/openjarvis") / SOURCE_PATH
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == SOURCE_SHA256, (digest, SOURCE_SHA256)
    text = raw.decode("utf-8")
    required = [
        '@router.get("/v1/models")',
        "async def list_models(request: Request) -> ModelListResponse:",
        "all_ids = await asyncio.to_thread(engine.list_models)",
        "if not model_ids:",
        "model_ids = await list_local_models()",
        "model_ids = [m for m in model_ids if not is_embed_only_model(m)]",
        "return ModelListResponse(",
    ]
    for needle in required:
        assert needle in text, needle
    return {
        "canonical_parity_status": "UNVERIFIED",
        "capability_id": CAPABILITY_ID,
        "capability_name": "GET /v1/models",
        "checkpoint": "CP03",
        "date": "2026-09-24",
        "engine_list_models_call_present": True,
        "engine_list_models_execution": "NOT_RUN",
        "fallback_list_local_models_present": True,
        "fallback_list_local_models_execution": "NOT_RUN",
        "http_listener_execution": "NOT_RUN",
        "http_method": "GET",
        "http_path": "/v1/models",
        "embed_only_filter_present": True,
        "model_executions": 0,
        "ownership": "OWNED",
        "parity_promotions": 0,
        "project_id": "CLEVER-JARVIS-001",
        "provider_egress_executions": 0,
        "schema_version": 1,
        "server_models_runtime_execution": "NOT_RUN",
        "source_blob_sha1": SOURCE_BLOB_SHA1,
        "source_execution": False,
        "source_line": SOURCE_LINE,
        "source_path": SOURCE_PATH,
        "source_probe": "PASS",
        "source_sha256": digest,
        "surface_kind": "http_route",
        "task": "W02-17",
        "terminal_eligible_in_w02": True,
        "tool_executions": 0,
        "upstream_commit": UPSTREAM_COMMIT,
    }


def patch_binding_and_tests(probe: dict) -> None:
    bindings = ROOT / "inventory/cp03/w02_evidence_bindings.jsonl"
    append_jsonl_once(
        bindings,
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
        'SERVER_HEALTH_CAPABILITY_ID = "cap_575541e84f43f012a9239ad2"\n',
        'SERVER_HEALTH_CAPABILITY_ID = "cap_575541e84f43f012a9239ad2"\nSERVER_MODELS_CAPABILITY_ID = "cap_e54461a19afaa2112911c49b"\n',
    )
    replace_once(
        tests,
        'SERVER_HEALTH_TEST_ID = (\n    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n    "test_server_health_binding_is_capability_specific_and_source_backed"\n)\n',
        'SERVER_HEALTH_TEST_ID = (\n    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n    "test_server_health_binding_is_capability_specific_and_source_backed"\n)\nSERVER_MODELS_TEST_ID = (\n    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."\n    "test_server_models_binding_is_capability_specific_and_source_backed"\n)\n',
    )
    replace_once(
        tests,
        "    def test_current_matrix_has_twenty_six_candidates_and_no_parity_promotion(self) -> None:\n",
        "    def test_current_matrix_has_twenty_seven_candidates_and_no_parity_promotion(self) -> None:\n",
    )
    replace_once(
        tests,
        '        self.assertEqual(sum(row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE" for row in rows), 26)\n        self.assertEqual(sum(row["w02_evidence_state"] == "UNBOUND" for row in rows), 21)\n',
        '        self.assertEqual(sum(row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE" for row in rows), 27)\n        self.assertEqual(sum(row["w02_evidence_state"] == "UNBOUND" for row in rows), 20)\n',
    )
    replace_once(
        tests,
        "SERVER_HEALTH_CAPABILITY_ID},\n",
        "SERVER_HEALTH_CAPABILITY_ID, SERVER_MODELS_CAPABILITY_ID},\n",
    )
    insertion_marker = "    def test_cli_model_list_command_binding_is_capability_specific_and_source_backed(self) -> None:\n"
    method = '''    def test_server_models_binding_is_capability_specific_and_source_backed(self) -> None:\n        row = next(row for row in self.result["rows"] if row["capability_id"] == SERVER_MODELS_CAPABILITY_ID)\n        self.assertEqual(row["ownership"], "OWNED")\n        self.assertEqual(row["surface_kind"], "http_route")\n        self.assertEqual(row["source_path"], "src/openjarvis/server/routes.py")\n        self.assertEqual(row["source_line"], 1107)\n        self.assertEqual(row["name"], "GET /v1/models")\n        self.assertTrue(row["terminal_eligible_in_w02"])\n        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")\n        self.assertEqual(row["w02_evidence_state"], "EVIDENCE_BACKED_CANDIDATE")\n        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")\n        self.assertFalse(row["verified"])\n        self.assertFalse(row["parity_promotion"])\n        binding = row["binding"]\n        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")\n        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")\n        self.assertEqual(binding["test_id"], SERVER_MODELS_TEST_ID)\n        self.assertFalse(binding["terminal"])\n        receipt = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")["EVID-W02-MODEL-BRIDGE-20260921"]\n        self.assertEqual(receipt["status"], "VERIFIED")\n        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")\n        self.assertEqual(receipt["native_engine_count"], 15)\n        self.assertEqual(receipt["native_import_failure_count"], 0)\n        self.assertEqual(receipt["native_model_count"], 69)\n        self.assertEqual(receipt["model_executions"], 0)\n        self.assertEqual(receipt["provider_egress_executions"], 0)\n        self.assertEqual(receipt["parity_promotions"], 0)\n        probe = json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_models_source_probe.json").read_text(encoding="utf-8"))\n        self.assertEqual(probe["capability_id"], SERVER_MODELS_CAPABILITY_ID)\n        self.assertEqual(probe["source_line"], 1107)\n        self.assertEqual(probe["source_probe"], "PASS")\n        self.assertFalse(probe["source_execution"])\n        self.assertEqual(probe["http_method"], "GET")\n        self.assertEqual(probe["http_path"], "/v1/models")\n        self.assertTrue(probe["engine_list_models_call_present"])\n        self.assertTrue(probe["fallback_list_local_models_present"])\n        self.assertTrue(probe["embed_only_filter_present"])\n        self.assertEqual(probe["server_models_runtime_execution"], "NOT_RUN")\n        self.assertEqual(probe["engine_list_models_execution"], "NOT_RUN")\n        self.assertEqual(probe["fallback_list_local_models_execution"], "NOT_RUN")\n        self.assertEqual(probe["http_listener_execution"], "NOT_RUN")\n        self.assertEqual(probe["model_executions"], 0)\n        self.assertEqual(probe["provider_egress_executions"], 0)\n        self.assertEqual(probe["tool_executions"], 0)\n        self.assertEqual(probe["parity_promotions"], 0)\n\n'''
    text = tests.read_text(encoding="utf-8")
    if "def test_server_models_binding_is_capability_specific_and_source_backed" not in text:
        if insertion_marker not in text:
            raise RuntimeError("server-models test insertion marker missing")
        tests.write_text(text.replace(insertion_marker, method + insertion_marker, 1), encoding="utf-8")

    write_json(ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_models_source_probe.json", probe)


def persist_ledgers_and_state(probe: dict) -> None:
    probe_path = "evidence/cp03/cp03-w02/W02-17/binding_server_models_source_probe.json"
    probe_sha256 = hashlib.sha256((ROOT / probe_path).read_bytes()).hexdigest()
    report = {
        "afm_inprocess_execution": "NOT_RUN",
        "apple_fm_binding_family": "UNBOUND_UNTOUCHED_COLLISION_AVOIDED",
        "binding_capability_id": CAPABILITY_ID,
        "binding_capability_name": "GET /v1/models",
        "binding_ownership": "OWNED",
        "binding_source_evidence_id": SOURCE_EVIDENCE_ID,
        "binding_source_run_id": 35552788123,
        "binding_source_validated_head": SOURCE_EVIDENCE_HEAD,
        "binding_surface_kind": "http_route",
        "bindings_added_this_slice": 1,
        "bindings_validated_total": BINDINGS_AFTER,
        "checkpoint": "CP03",
        "claim_id": CLAIM_ID,
        "cloud_reload_binding": "UNBOUND_UNTOUCHED_COLLISION_AVOIDED",
        "date": "2026-09-24",
        "engine_list_models_execution": "NOT_RUN",
        "evidence_id": EVIDENCE_ID,
        "executed_test_id": TEST_ID,
        "fallback_list_local_models_execution": "NOT_RUN",
        "gate": "G6",
        "github_actions_run_id": RUN_ID,
        "global_denominator": 7565,
        "http_listener_execution": "NOT_RUN",
        "inference_start_event_binding": "UNBOUND_UNTOUCHED_COLLISION_AVOIDED",
        "model_executions": 0,
        "next_slice": "Continue W02-17 with another non-conflicting proof unit only when capability-specific executed or exact pinned-source evidence can be paired with an existing completed-task PASS receipt; preserve AFM/fallback NOT_RUN and avoid overlapping extant branches.",
        "openjarvis_obligations": 646,
        "parity_promotions": 0,
        "path": "evidence/cp03/cp03-w02/W02-17/binding_server_models_report.json",
        "project_id": "CLEVER-JARVIS-001",
        "provider_egress_executions": 0,
        "real_openjarvis_fallback_model_execution": "NOT_RUN",
        "schema_version": 1,
        "server_models_runtime_execution": "NOT_RUN",
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
    write_json(ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_models_report.json", report)
    write_json(ROOT / "sessions/20260922-w02-parity-graph/RESULT.json", report)

    append_jsonl_once(ROOT / "ledgers/CLAIM_LEDGER.ndjson", {
        "base_head": BASE_HEAD,
        "canonical_task": "W02-17",
        "checkpoint": "CP03",
        "claim_id": CLAIM_ID,
        "coordination": "Continue the sole active W02-17 G6 claim for the branch-free core server GET /v1/models source-proof unit only. Cloud-reload, InferenceStartEvent and Apple FM branches are excluded; route/engine/listener execution remains NOT_RUN; no parity or denominator transition is authorized.",
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
        "context": "Exact pinned source proves the core server GET /v1/models route, engine.list_models delegation, direct-cloud filtering, local fallback and embed-only filtering. Completed W02-08 supplies the exact model/engine bridge receipt, but listener/route/engine list execution are deliberately NOT_RUN, so this is not behavioral parity.",
        "date": "2026-09-24",
        "decision": "Bind the frozen OpenJarvis core server GET /v1/models route as a non-terminal EVIDENCE_BACKED_CANDIDATE only.",
        "decision_id": DECISION_ID,
        "evidence_id": EVIDENCE_ID,
        "parity_promotions": 0,
        "schema_version": 1,
        "status": "ACCEPTED",
        "task": "W02-17",
    }, "decision_id")
    evidence_row = dict(report)
    evidence_row.pop("github_actions_run_id", None)
    evidence_row["github_actions_run_id"] = RUN_ID
    append_jsonl_once(ROOT / "ledgers/EVIDENCE_LEDGER.ndjson", evidence_row, "evidence_id")
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
        "mitigation": "Keep W02-17 IN_PROGRESS, verified parity at 0 and W02-18 BLOCKED. Continue one capability-specific proof unit at a time; preserve AFM/fallback NOT_RUN and avoid overlapping extant branches.",
        "risk_id": "RISK-W02-G6-K47-BINDINGS-PENDING-20260922",
        "schema_version": 1,
        "severity": "P1",
        "status": "MITIGATING",
        "unbound_remaining": UNBOUND_AFTER,
    }, "event_id")

    state = ROOT / "STATE.md"
    replace_once(state, "G6 explicit binding progress: `26/47` evidence-backed candidates; `21` UNBOUND", "G6 explicit binding progress: `27/47` evidence-backed candidates; `20` UNBOUND")
    append_section_once(ROOT / "HANDOFF.md", "## W02-17 core server GET /v1/models binding — source-backed partial verified", f'''## W02-17 core server GET /v1/models binding — source-backed partial verified

- `{EVIDENCE_ID}`: `{CAPABILITY_ID}` (`GET /v1/models`, OWNED route at `src/openjarvis/server/routes.py:1107`) is now a non-terminal `EVIDENCE_BACKED_CANDIDATE`.
- Exact pinned source `{UPSTREAM_COMMIT}` proves route declaration, `engine.list_models()` delegation, direct-cloud filtering, local fallback and embed-only filtering. HTTP listener, route runtime and engine/model-list execution remain `NOT_RUN`.
- Formal G6 binding is anchored to completed W02-08 `{SOURCE_EVIDENCE_ID}` at exact SHA `{SOURCE_EVIDENCE_HEAD}`; candidate evidence only: VERIFIED parity remains 0.
- Collision avoidance: cloud-reload, InferenceStartEvent and Apple FM parallel branches were not touched. AFM compatible-host proof and real fallback model execution remain `NOT_RUN`.
- G6 is now 27 `EVIDENCE_BACKED_CANDIDATE` / 20 `UNBOUND`; parity promotions 0; denominator 7565 and OpenJarvis obligations 646 unchanged. W02-17 remains `IN_PROGRESS`; W02-18/W02-19 remain `BLOCKED`.
- Exact next slice: another branch-free W02-17 proof unit with capability-specific executed or exact pinned-source evidence paired to an exact completed-task PASS receipt.''')


def regenerate_and_validate() -> None:
    subprocess.run([sys.executable, "scripts/cp03/w02_parity_graph.py", "--write"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/context/build_context_pack.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/validate_agentic_state.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/context/validate_context_pack.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/context/build_context_pack.py", "--check"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/context/validate_next_actions.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/cp03/validate_w02_plan.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "scripts.parity.ledger", "--check", "--source-repo", "openjarvis"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/cp03/w02_parity_graph.py", "--check"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "unittest", "-v", TEST_ID], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "unittest", "-v", "tests.test_cp03_w02_parity_graph"], cwd=ROOT, check=True)

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
    assert row["verified"] is False and row["parity_promotion"] is False
    task_graph = load_json(ROOT / "iterations/03/waves/CP03-W02/TASK_GRAPH.json")
    statuses = {t["id"]: t["status"] for t in task_graph["tasks"]}
    assert statuses["W02-17"] == "IN_PROGRESS"
    assert statuses["W02-18"] == "BLOCKED"
    assert statuses["W02-19"] == "BLOCKED"


def main() -> int:
    existing = {row.get("evidence_id") for row in read_jsonl(ROOT / "ledgers/EVIDENCE_LEDGER.ndjson")}
    if EVIDENCE_ID in existing:
        regenerate_and_validate()
        print("NO_CHANGE: server-models binding already persisted and validates")
        return 0

    verify_base()
    red = {
        "capability_id": CAPABILITY_ID,
        "canonical_parity_status": "UNVERIFIED",
        "date": "2026-09-24",
        "expected_pre_binding_state": "UNBOUND",
        "observed_pre_binding_state": "UNBOUND",
        "result": "RED_CHARACTERIZATION_CONFIRMED",
        "schema_version": 1,
        "task": "W02-17",
    }
    write_json(ROOT / "evidence/cp03/cp03-w02/W02-17/binding_server_models_red_characterization.json", red)
    probe = build_source_probe()
    patch_binding_and_tests(probe)
    persist_ledgers_and_state(probe)
    regenerate_and_validate()
    print("ADVANCED: 27/47 evidence-backed candidates; 20 UNBOUND; VERIFIED=0; parity promotions=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
