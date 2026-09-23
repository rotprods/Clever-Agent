from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from scripts.cp03 import w02_parity_graph as graph

ROOT = Path(__file__).resolve().parents[1]
SEED_CAPABILITY_ID = "cap_49014a3c03b104c8ec2f4ca1"
OLLAMA_CAPABILITY_ID = "cap_a5ae164f941b35e6fafd357c"
LITELLM_CAPABILITY_ID = "cap_149d7cf3bf745e7bea3fa1b0"
CLOUD_CAPABILITY_ID = "cap_49e508ee1377a8861a33b2f0"
NIM_CAPABILITY_ID = "cap_fa50b5646f0cfab91c7efec5"
GEMMA_CPP_CAPABILITY_ID = "cap_5cf599d5c98778fc324cbd0c"
OPENAI_COMPAT_REGISTER_CAPABILITY_ID = "cap_5411f850a1935d329d2c53a0"
MODEL_REGISTER_VALUE_CAPABILITY_ID = "cap_1d68bea6da6cb4c552cee405"
MODEL_REGISTER_VALUE_1088_CAPABILITY_ID = "cap_d0bb7e74057a2b59835f2143"
CLI_MODEL_LIST_REGISTER_BUILTIN_CAPABILITY_ID = "cap_a1156e1a8626c074910758f9"
CLI_MODEL_INFO_REGISTER_BUILTIN_CAPABILITY_ID = "cap_bdc045630a6fcf4735394782"
CLI_CHAT_REGISTER_BUILTIN_CAPABILITY_ID = "cap_63d29e906eae343ae8c88a05"
CLI_ASK_REGISTER_BUILTIN_CAPABILITY_ID = "cap_e0f19ffe0e3814a158b2f56d"
CLI_SERVE_REGISTER_BUILTIN_CAPABILITY_ID = "cap_e924254fa9cf1fde7a4f78b8"
AFM_INPROCESS_CAPABILITY_ID = "cap_ac38bf813e130d14927723d8"
CLI_MODEL_INFO_COMMAND_CAPABILITY_ID = "cap_075a2380f9db372754f08116"
MODEL_INFO_PROTOCOL_CAPABILITY_ID = "cap_048295582ec38991a9519378"
CLI_MODEL_LIST_COMMAND_CAPABILITY_ID = "cap_0ca72684c7cad5e160373532"
CLI_MODEL_GROUP_COMMAND_CAPABILITY_ID = "cap_263641071dc7bb5251e3339b"
CLI_MODEL_PULL_COMMAND_CAPABILITY_ID = "cap_69723ff5986f70a048ed98fe"
OLLAMA_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_ollama_registry_binding_is_capability_specific_and_evidence_backed"
)
LITELLM_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_litellm_registry_binding_is_capability_specific_and_evidence_backed"
)
CLOUD_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_cloud_registry_binding_is_capability_specific_and_evidence_backed"
)
NIM_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_nim_registry_binding_is_capability_specific_and_evidence_backed"
)
GEMMA_CPP_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_gemma_cpp_registry_binding_is_capability_specific_and_evidence_backed"
)
OPENAI_COMPAT_REGISTER_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_openai_compat_register_binding_is_capability_specific_and_evidence_backed"
)
MODEL_REGISTER_VALUE_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_model_register_value_binding_is_capability_specific_and_evidence_backed"
)
MODEL_REGISTER_VALUE_1088_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_model_register_value_1088_binding_is_capability_specific_and_evidence_backed"
)
CLI_MODEL_LIST_REGISTER_BUILTIN_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_cli_model_list_register_builtin_binding_is_capability_specific_and_evidence_backed"
)
CLI_MODEL_INFO_REGISTER_BUILTIN_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_cli_model_info_register_builtin_binding_is_capability_specific_and_evidence_backed"
)
CLI_CHAT_REGISTER_BUILTIN_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_cli_chat_register_builtin_binding_is_capability_specific_and_evidence_backed"
)
CLI_ASK_REGISTER_BUILTIN_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_cli_ask_register_builtin_binding_is_capability_specific_and_evidence_backed"
)
CLI_SERVE_REGISTER_BUILTIN_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_cli_serve_register_builtin_binding_is_capability_specific_and_evidence_backed"
)
CLI_MODEL_INFO_COMMAND_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_cli_model_info_command_binding_is_capability_specific_and_runtime_backed"
)
MODEL_INFO_PROTOCOL_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_model_info_protocol_binding_is_capability_specific_and_source_backed"
)
CLI_MODEL_LIST_COMMAND_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_cli_model_list_command_binding_is_capability_specific_and_source_backed"
)
CLI_MODEL_GROUP_COMMAND_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_cli_model_group_command_binding_is_capability_specific_and_source_backed"
)
CLI_MODEL_PULL_COMMAND_TEST_ID = (
    "tests.test_cp03_w02_parity_graph.W02ParityGraphTests."
    "test_cli_model_pull_command_binding_is_capability_specific_and_source_backed"
)


class W02ParityGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = graph.compile_root(ROOT)

    def test_context_pack_preserves_active_claim_wave_id(self) -> None:
        context = json.loads((ROOT / ".agentic/context/CURRENT_CONTEXT.json").read_text(encoding="utf-8"))
        claims = [row for row in context["active_claims"] if row["claim_id"] == "CLAIM-CP03-W02-PARITY-GRAPH-20260922"]
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["status"], "ACTIVE")
        self.assertEqual(claims[0]["wave_id"], "CP03-W02-PARITY-GRAPH-20260922")

    def test_frozen_scope_and_denominators_are_preserved(self) -> None:
        summary = self.result["summary"]
        self.assertEqual(summary["global_denominator"], 7565)
        self.assertEqual(summary["openjarvis_obligations"], 646)
        self.assertEqual(summary["w02_proof_units"], 47)
        self.assertEqual(summary["owned"], 37)
        self.assertEqual(summary["shared"], 10)
        self.assertEqual(summary["parity_promotions"], 0)
        self.assertEqual(summary["verified_capabilities"], 0)
        self.assertEqual(len(self.result["rows"]), 47)

    def test_current_matrix_has_nineteen_candidates_and_no_parity_promotion(self) -> None:
        rows = self.result["rows"]
        self.assertTrue(all(row["canonical_parity_status"] == "UNVERIFIED" for row in rows))
        self.assertTrue(all(row["verified"] is False for row in rows))
        self.assertTrue(all(row["parity_promotion"] is False for row in rows))
        self.assertEqual(sum(row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE" for row in rows), 19)
        self.assertEqual(sum(row["w02_evidence_state"] == "UNBOUND" for row in rows), 28)
        self.assertEqual(sum(row["ownership"] == "OWNED" for row in rows), 37)
        self.assertEqual(sum(row["ownership"] == "SHARED" for row in rows), 10)
        candidates = {
            row["capability_id"]: row
            for row in rows
            if row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE"
        }
        self.assertEqual(
            set(candidates),
            {SEED_CAPABILITY_ID, OLLAMA_CAPABILITY_ID, LITELLM_CAPABILITY_ID, CLOUD_CAPABILITY_ID, NIM_CAPABILITY_ID, GEMMA_CPP_CAPABILITY_ID, OPENAI_COMPAT_REGISTER_CAPABILITY_ID, MODEL_REGISTER_VALUE_CAPABILITY_ID, MODEL_REGISTER_VALUE_1088_CAPABILITY_ID, CLI_MODEL_LIST_REGISTER_BUILTIN_CAPABILITY_ID, CLI_MODEL_INFO_REGISTER_BUILTIN_CAPABILITY_ID, CLI_CHAT_REGISTER_BUILTIN_CAPABILITY_ID, CLI_ASK_REGISTER_BUILTIN_CAPABILITY_ID, CLI_SERVE_REGISTER_BUILTIN_CAPABILITY_ID, CLI_MODEL_INFO_COMMAND_CAPABILITY_ID, MODEL_INFO_PROTOCOL_CAPABILITY_ID, CLI_MODEL_LIST_COMMAND_CAPABILITY_ID, CLI_MODEL_GROUP_COMMAND_CAPABILITY_ID, CLI_MODEL_PULL_COMMAND_CAPABILITY_ID},
        )
        seed = candidates[SEED_CAPABILITY_ID]
        self.assertEqual(seed["binding"]["evidence_id"], "EVID-W02-UNARY-INFERENCE-20260921")
        self.assertFalse(seed["binding"]["terminal"])
        ollama = candidates[OLLAMA_CAPABILITY_ID]
        self.assertEqual(ollama["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(ollama["binding"]["terminal"])
        litellm = candidates[LITELLM_CAPABILITY_ID]
        self.assertEqual(litellm["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(litellm["binding"]["terminal"])
        cloud = candidates[CLOUD_CAPABILITY_ID]
        self.assertEqual(cloud["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(cloud["binding"]["terminal"])
        nim = candidates[NIM_CAPABILITY_ID]
        self.assertEqual(nim["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(nim["binding"]["terminal"])
        gemma_cpp = candidates[GEMMA_CPP_CAPABILITY_ID]
        self.assertEqual(gemma_cpp["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(gemma_cpp["binding"]["terminal"])
        openai_compat_register = candidates[OPENAI_COMPAT_REGISTER_CAPABILITY_ID]
        self.assertEqual(openai_compat_register["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(openai_compat_register["binding"]["terminal"])
        model_register_value = candidates[MODEL_REGISTER_VALUE_CAPABILITY_ID]
        self.assertEqual(model_register_value["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(model_register_value["binding"]["terminal"])
        model_register_value_1088 = candidates[MODEL_REGISTER_VALUE_1088_CAPABILITY_ID]
        self.assertEqual(model_register_value_1088["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(model_register_value_1088["binding"]["terminal"])
        cli_model_list_register_builtin = candidates[CLI_MODEL_LIST_REGISTER_BUILTIN_CAPABILITY_ID]
        self.assertEqual(cli_model_list_register_builtin["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(cli_model_list_register_builtin["binding"]["terminal"])
        cli_model_info_register_builtin = candidates[CLI_MODEL_INFO_REGISTER_BUILTIN_CAPABILITY_ID]
        self.assertEqual(cli_model_info_register_builtin["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(cli_model_info_register_builtin["binding"]["terminal"])
        cli_chat_register_builtin = candidates[CLI_CHAT_REGISTER_BUILTIN_CAPABILITY_ID]
        self.assertEqual(cli_chat_register_builtin["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(cli_chat_register_builtin["binding"]["terminal"])
        cli_ask_register_builtin = candidates[CLI_ASK_REGISTER_BUILTIN_CAPABILITY_ID]
        self.assertEqual(cli_ask_register_builtin["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(cli_ask_register_builtin["binding"]["terminal"])
        cli_serve_register_builtin = candidates[CLI_SERVE_REGISTER_BUILTIN_CAPABILITY_ID]
        self.assertEqual(cli_serve_register_builtin["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(cli_serve_register_builtin["binding"]["terminal"])
        cli_model_info_command = candidates[CLI_MODEL_INFO_COMMAND_CAPABILITY_ID]
        self.assertEqual(cli_model_info_command["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(cli_model_info_command["binding"]["terminal"])
        model_info_protocol = candidates[MODEL_INFO_PROTOCOL_CAPABILITY_ID]
        self.assertEqual(model_info_protocol["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(model_info_protocol["binding"]["terminal"])
        cli_model_list_command = candidates[CLI_MODEL_LIST_COMMAND_CAPABILITY_ID]
        self.assertEqual(cli_model_list_command["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(cli_model_list_command["binding"]["terminal"])
        cli_model_group_command = candidates[CLI_MODEL_GROUP_COMMAND_CAPABILITY_ID]
        self.assertEqual(cli_model_group_command["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(cli_model_group_command["binding"]["terminal"])
        cli_model_pull_command = candidates[CLI_MODEL_PULL_COMMAND_CAPABILITY_ID]
        self.assertEqual(cli_model_pull_command["binding"]["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertFalse(cli_model_pull_command["binding"]["terminal"])

    def test_ollama_registry_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == OLLAMA_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/engine/ollama.py")
        self.assertEqual(row["source_line"], 106)
        self.assertEqual(row["name"], "ollama")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], OLLAMA_TEST_ID)
        self.assertFalse(binding["terminal"])

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog = json.loads(
            (ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8")
        )
        matches = [engine for engine in catalog["engines"] if engine["key"] == "ollama"]
        self.assertEqual(
            matches,
            [
                {
                    "implementation": "openjarvis.engine.ollama.OllamaEngine",
                    "key": "ollama",
                    "native_type": "ABCMeta",
                    "state": "REGISTERED",
                }
            ],
        )
        self.assertEqual(catalog["model_executions"], 0)
        self.assertEqual(catalog["provider_egress_executions"], 0)
        self.assertEqual(catalog["parity_promotions"], 0)

    def test_litellm_registry_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == LITELLM_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/engine/litellm.py")
        self.assertEqual(row["source_line"], 16)
        self.assertEqual(row["name"], "litellm")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], LITELLM_TEST_ID)
        self.assertFalse(binding["terminal"])

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog = json.loads(
            (ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8")
        )
        matches = [engine for engine in catalog["engines"] if engine["key"] == "litellm"]
        self.assertEqual(
            matches,
            [
                {
                    "implementation": "openjarvis.engine.litellm.LiteLLMEngine",
                    "key": "litellm",
                    "native_type": "ABCMeta",
                    "state": "REGISTERED",
                }
            ],
        )
        self.assertEqual(catalog["model_executions"], 0)
        self.assertEqual(catalog["provider_egress_executions"], 0)
        self.assertEqual(catalog["parity_promotions"], 0)

    def test_cloud_registry_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == CLOUD_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/engine/cloud.py")
        self.assertEqual(row["source_line"], 323)
        self.assertEqual(row["name"], "cloud")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], CLOUD_TEST_ID)
        self.assertFalse(binding["terminal"])

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["native_model_count"], 69)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog = json.loads(
            (ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8")
        )
        matches = [engine for engine in catalog["engines"] if engine["key"] == "cloud"]
        self.assertEqual(
            matches,
            [
                {
                    "implementation": "openjarvis.engine.cloud.CloudEngine",
                    "key": "cloud",
                    "native_type": "ABCMeta",
                    "state": "REGISTERED",
                }
            ],
        )
        self.assertEqual(catalog["model_executions"], 0)
        self.assertEqual(catalog["provider_egress_executions"], 0)
        self.assertEqual(catalog["parity_promotions"], 0)

    def test_nim_registry_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == NIM_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/engine/nim.py")
        self.assertEqual(row["source_line"], 26)
        self.assertEqual(row["name"], "nim")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], NIM_TEST_ID)
        self.assertFalse(binding["terminal"])
        raw_binding = next(
            item
            for item in graph.read_jsonl(ROOT / graph.BINDINGS_PATH)
            if item["capability_id"] == NIM_CAPABILITY_ID
        )
        self.assertEqual(
            raw_binding["expected_fields"],
            {
                "status": "VERIFIED",
                "native_engine_count": 15,
                "native_import_failure_count": 0,
                "native_model_count": 69,
                "model_executions": 0,
                "provider_egress_executions": 0,
                "parity_promotions": 0,
            },
        )

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["native_model_count"], 69)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog = json.loads(
            (ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8")
        )
        matches = [engine for engine in catalog["engines"] if engine["key"] == "nim"]
        self.assertEqual(
            matches,
            [
                {
                    "implementation": "openjarvis.engine.nim.NIMEngine",
                    "key": "nim",
                    "native_type": "ABCMeta",
                    "state": "REGISTERED",
                }
            ],
        )
        self.assertEqual(catalog["model_executions"], 0)
        self.assertEqual(catalog["provider_egress_executions"], 0)
        self.assertEqual(catalog["parity_promotions"], 0)

    def test_gemma_cpp_registry_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == GEMMA_CPP_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/engine/gemma_cpp.py")
        self.assertEqual(row["source_line"], 24)
        self.assertEqual(row["name"], "gemma_cpp")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], GEMMA_CPP_TEST_ID)
        self.assertFalse(binding["terminal"])

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["native_model_count"], 69)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog = json.loads(
            (ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8")
        )
        matches = [engine for engine in catalog["engines"] if engine["key"] == "gemma_cpp"]
        self.assertEqual(
            matches,
            [
                {
                    "implementation": "openjarvis.engine.gemma_cpp.GemmaCppEngine",
                    "key": "gemma_cpp",
                    "native_type": "ABCMeta",
                    "state": "REGISTERED",
                }
            ],
        )
        self.assertEqual(catalog["model_executions"], 0)
        self.assertEqual(catalog["provider_egress_executions"], 0)
        self.assertEqual(catalog["parity_promotions"], 0)

    def test_openai_compat_register_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == OPENAI_COMPAT_REGISTER_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/engine/openai_compat_engines.py")
        self.assertEqual(row["source_line"], 27)
        self.assertEqual(row["name"], "register")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], OPENAI_COMPAT_REGISTER_TEST_ID)
        self.assertFalse(binding["terminal"])

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["native_model_count"], 69)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog = json.loads(
            (ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8")
        )
        expected = {
            "apple_fm": "abc.AppleFmEngine",
            "exo": "abc.ExoEngine",
            "lemonade": "abc.LemonadeEngine",
            "llamacpp": "abc.LlamaCppEngine",
            "lmstudio": "abc.LMStudioEngine",
            "mlx": "abc.MLXEngine",
            "nexa": "abc.NexaEngine",
            "sglang": "abc.SGLangEngine",
            "uzu": "abc.UzuEngine",
            "vllm": "abc.VLLMEngine",
        }
        observed = {
            engine["key"]: engine["implementation"]
            for engine in catalog["engines"]
            if engine["key"] in expected
        }
        self.assertEqual(observed, expected)
        for engine in catalog["engines"]:
            if engine["key"] in expected:
                self.assertEqual(engine["state"], "REGISTERED")
                self.assertEqual(engine["native_type"], "ABCMeta")
        self.assertEqual(catalog["model_executions"], 0)
        self.assertEqual(catalog["provider_egress_executions"], 0)
        self.assertEqual(catalog["parity_promotions"], 0)

    def test_model_register_value_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == MODEL_REGISTER_VALUE_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/intelligence/model_catalog.py")
        self.assertEqual(row["source_line"], 1074)
        self.assertEqual(row["name"], "register_value")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], MODEL_REGISTER_VALUE_TEST_ID)
        self.assertFalse(binding["terminal"])

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["native_model_count"], 69)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        bridge_source = (ROOT / "adapters/openjarvis/model_bridge.py").read_text(encoding="utf-8")
        self.assertIn('register_builtin = getattr(module, "register_builtin_models", None)', bridge_source)
        self.assertIn("if callable(register_builtin):", bridge_source)
        self.assertIn("register_builtin()", bridge_source)

        catalog = json.loads(
            (ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8")
        )
        self.assertEqual(catalog["model_count"], 69)
        self.assertEqual(len(catalog["models"]), 69)
        self.assertEqual(catalog["import_failures"], [])
        self.assertTrue(all(model["state"] == "REGISTERED" for model in catalog["models"]))
        self.assertTrue(all(model["native_type"] == "ModelSpec" for model in catalog["models"]))
        self.assertTrue(all(model["implementation"] == "openjarvis.core.types.ModelSpec" for model in catalog["models"]))
        keys={model["key"] for model in catalog["models"]}
        for expected in ("qwen3:0.6b", "gpt-4o", "afm-3", "afm-3-core", "afm-3-core-advanced"):
            self.assertIn(expected, keys)
        self.assertEqual(catalog["model_executions"], 0)
        self.assertEqual(catalog["provider_egress_executions"], 0)
        self.assertEqual(catalog["parity_promotions"], 0)

    def test_model_register_value_1088_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == MODEL_REGISTER_VALUE_1088_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/intelligence/model_catalog.py")
        self.assertEqual(row["source_line"], 1088)
        self.assertEqual(row["name"], "register_value")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], MODEL_REGISTER_VALUE_1088_TEST_ID)
        self.assertFalse(binding["terminal"])

        obligation = next(
            item for item in graph.read_jsonl(ROOT / graph.OBLIGATIONS_PATH)
            if item["capability_id"] == MODEL_REGISTER_VALUE_1088_CAPABILITY_ID
        )
        self.assertEqual(obligation["interface"]["registrar"], "ModelRegistry.register_value")
        self.assertEqual(obligation["runtime_owner"], "openjarvis:intelligence")
        self.assertEqual(obligation["source_path"], "src/openjarvis/intelligence/model_catalog.py")
        self.assertEqual(obligation["source_line"], 1088)

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["native_model_count"], 69)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        bridge_source = (ROOT / "adapters/openjarvis/model_bridge.py").read_text(encoding="utf-8")
        self.assertIn('register_builtin = getattr(module, "register_builtin_models", None)', bridge_source)
        self.assertIn("register_builtin()", bridge_source)
        catalog = json.loads((ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["model_count"], 69)
        self.assertEqual(len(catalog["models"]), 69)
        self.assertEqual(catalog["import_failures"], [])
        self.assertTrue(all(model["state"] == "REGISTERED" for model in catalog["models"]))
        self.assertTrue(all(model["native_type"] == "ModelSpec" for model in catalog["models"]))
        self.assertTrue(all(model["implementation"] == "openjarvis.core.types.ModelSpec" for model in catalog["models"]))
        self.assertEqual(catalog["model_executions"], 0)
        self.assertEqual(catalog["provider_egress_executions"], 0)
        self.assertEqual(catalog["parity_promotions"], 0)

    def test_cli_model_list_register_builtin_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == CLI_MODEL_LIST_REGISTER_BUILTIN_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(row["source_line"], 38)
        self.assertEqual(row["name"], "register_builtin_models")
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], CLI_MODEL_LIST_REGISTER_BUILTIN_TEST_ID)
        self.assertFalse(binding["terminal"])

        obligation = next(
            item for item in graph.read_jsonl(ROOT / graph.OBLIGATIONS_PATH)
            if item["capability_id"] == CLI_MODEL_LIST_REGISTER_BUILTIN_CAPABILITY_ID
        )
        self.assertEqual(obligation["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(obligation["source_line"], 38)
        self.assertEqual(obligation["name"], "register_builtin_models")
        self.assertEqual(obligation["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")

        probe=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_cli_model_list_register_builtin_source_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["upstream_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(probe["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(probe["function"], "list_models")
        self.assertEqual(probe["registrar_call"], "register_builtin_models")
        self.assertEqual(probe["registrar_call_line"], 38)
        self.assertTrue(probe["registration_precedes_engine_discovery"])
        self.assertFalse(probe["source_execution"])
        self.assertFalse(probe["parity_promotion"])

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["native_model_count"], 69)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["model_count"],69)
        self.assertEqual(len(catalog["models"]),69)
        self.assertEqual(catalog["import_failures"],[])
        self.assertTrue(all(model["state"] == "REGISTERED" for model in catalog["models"]))
        self.assertEqual(catalog["model_executions"],0)
        self.assertEqual(catalog["provider_egress_executions"],0)
        self.assertEqual(catalog["parity_promotions"],0)

    def test_cli_model_info_register_builtin_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == CLI_MODEL_INFO_REGISTER_BUILTIN_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(row["source_line"], 90)
        self.assertEqual(row["name"], "register_builtin_models")
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], CLI_MODEL_INFO_REGISTER_BUILTIN_TEST_ID)
        self.assertFalse(binding["terminal"])

        obligation = next(
            item for item in graph.read_jsonl(ROOT / graph.OBLIGATIONS_PATH)
            if item["capability_id"] == CLI_MODEL_INFO_REGISTER_BUILTIN_CAPABILITY_ID
        )
        self.assertEqual(obligation["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(obligation["source_line"], 90)
        self.assertEqual(obligation["name"], "register_builtin_models")
        self.assertEqual(obligation["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")

        probe=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_cli_model_info_register_builtin_source_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["upstream_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(probe["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(probe["function"], "info")
        self.assertEqual(probe["registrar_call"], "register_builtin_models")
        self.assertEqual(probe["registrar_call_line"], 90)
        self.assertTrue(probe["registration_precedes_engine_discovery"])
        self.assertFalse(probe["source_execution"])
        self.assertFalse(probe["parity_promotion"])

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["native_model_count"], 69)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["model_count"],69)
        self.assertEqual(len(catalog["models"]),69)
        self.assertEqual(catalog["import_failures"],[])
        self.assertTrue(all(model["state"] == "REGISTERED" for model in catalog["models"]))
        self.assertEqual(catalog["model_executions"],0)
        self.assertEqual(catalog["provider_egress_executions"],0)
        self.assertEqual(catalog["parity_promotions"],0)

    def test_cli_chat_register_builtin_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == CLI_CHAT_REGISTER_BUILTIN_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/cli/chat_cmd.py")
        self.assertEqual(row["source_line"], 130)
        self.assertEqual(row["name"], "register_builtin_models")
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], CLI_CHAT_REGISTER_BUILTIN_TEST_ID)
        self.assertFalse(binding["terminal"])

        obligation = next(
            item for item in graph.read_jsonl(ROOT / graph.OBLIGATIONS_PATH)
            if item["capability_id"] == CLI_CHAT_REGISTER_BUILTIN_CAPABILITY_ID
        )
        self.assertEqual(obligation["source_path"], "src/openjarvis/cli/chat_cmd.py")
        self.assertEqual(obligation["source_line"], 130)
        self.assertEqual(obligation["name"], "register_builtin_models")
        self.assertEqual(obligation["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")

        probe=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_cli_chat_register_builtin_source_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["upstream_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(probe["source_path"], "src/openjarvis/cli/chat_cmd.py")
        self.assertEqual(probe["function"], "chat")
        self.assertEqual(probe["registrar_call"], "register_builtin_models")
        self.assertEqual(probe["registrar_call_line"], 130)
        self.assertTrue(probe["registration_precedes_get_engine"])
        self.assertFalse(probe["source_execution"])
        self.assertEqual(probe["chat_command_execution"], "NOT_RUN")
        self.assertFalse(probe["parity_promotion"])

        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt = evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"], 15)
        self.assertEqual(receipt["native_import_failure_count"], 0)
        self.assertEqual(receipt["native_model_count"], 69)
        self.assertEqual(receipt["model_executions"], 0)
        self.assertEqual(receipt["provider_egress_executions"], 0)
        self.assertEqual(receipt["parity_promotions"], 0)

        catalog=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["model_count"],69)
        self.assertEqual(len(catalog["models"]),69)
        self.assertEqual(catalog["import_failures"],[])
        self.assertTrue(all(model["state"] == "REGISTERED" for model in catalog["models"]))
        self.assertEqual(catalog["model_executions"],0)
        self.assertEqual(catalog["provider_egress_executions"],0)
        self.assertEqual(catalog["parity_promotions"],0)

    def test_cli_ask_register_builtin_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == CLI_ASK_REGISTER_BUILTIN_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/cli/ask.py")
        self.assertEqual(row["source_line"], 869)
        self.assertEqual(row["name"], "register_builtin_models")
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding=row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], CLI_ASK_REGISTER_BUILTIN_TEST_ID)
        self.assertFalse(binding["terminal"])
        obligation=next(item for item in graph.read_jsonl(ROOT / graph.OBLIGATIONS_PATH) if item["capability_id"] == CLI_ASK_REGISTER_BUILTIN_CAPABILITY_ID)
        self.assertEqual(obligation["source_path"], "src/openjarvis/cli/ask.py")
        self.assertEqual(obligation["source_line"], 869)
        self.assertEqual(obligation["name"], "register_builtin_models")
        probe=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_cli_ask_register_builtin_source_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["upstream_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(probe["source_path"], "src/openjarvis/cli/ask.py")
        self.assertEqual(probe["registrar_call"], "register_builtin_models")
        self.assertEqual(probe["registrar_call_line"], 869)
        self.assertTrue(probe["registration_precedes_engine_resolution"])
        self.assertFalse(probe["source_execution"])
        self.assertEqual(probe["ask_command_execution"], "NOT_RUN")
        self.assertFalse(probe["parity_promotion"])
        evidence=graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt=evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"],15)
        self.assertEqual(receipt["native_import_failure_count"],0)
        self.assertEqual(receipt["native_model_count"],69)
        self.assertEqual(receipt["model_executions"],0)
        self.assertEqual(receipt["provider_egress_executions"],0)
        self.assertEqual(receipt["parity_promotions"],0)
        catalog=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["model_count"],69)
        self.assertEqual(len(catalog["models"]),69)
        self.assertEqual(catalog["import_failures"],[])
        self.assertTrue(all(model["state"] == "REGISTERED" for model in catalog["models"]))
        self.assertEqual(catalog["model_executions"],0)
        self.assertEqual(catalog["provider_egress_executions"],0)
        self.assertEqual(catalog["parity_promotions"],0)

    def test_cli_serve_register_builtin_binding_is_capability_specific_and_evidence_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == CLI_SERVE_REGISTER_BUILTIN_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/cli/serve.py")
        self.assertEqual(row["source_line"], 162)
        self.assertEqual(row["name"], "register_builtin_models")
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding=row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], CLI_SERVE_REGISTER_BUILTIN_TEST_ID)
        self.assertFalse(binding["terminal"])
        obligation=next(item for item in graph.read_jsonl(ROOT / graph.OBLIGATIONS_PATH) if item["capability_id"] == CLI_SERVE_REGISTER_BUILTIN_CAPABILITY_ID)
        self.assertEqual(obligation["source_path"], "src/openjarvis/cli/serve.py")
        self.assertEqual(obligation["source_line"], 162)
        self.assertEqual(obligation["name"], "register_builtin_models")
        probe=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_cli_serve_register_builtin_source_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["upstream_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(probe["source_path"], "src/openjarvis/cli/serve.py")
        self.assertEqual(probe["registrar_call"], "register_builtin_models")
        self.assertEqual(probe["registrar_call_line"], 162)
        self.assertEqual(probe["next_engine_resolution_call"], "get_engine")
        self.assertTrue(probe["registration_precedes_engine_resolution"])
        self.assertFalse(probe["source_execution"])
        self.assertEqual(probe["serve_command_execution"], "NOT_RUN")
        self.assertFalse(probe["parity_promotion"])
        evidence=graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        receipt=evidence["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"],15)
        self.assertEqual(receipt["native_import_failure_count"],0)
        self.assertEqual(receipt["native_model_count"],69)
        self.assertEqual(receipt["model_executions"],0)
        self.assertEqual(receipt["provider_egress_executions"],0)
        self.assertEqual(receipt["parity_promotions"],0)
        catalog=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["model_count"],69)
        self.assertEqual(len(catalog["models"]),69)
        self.assertEqual(catalog["import_failures"],[])
        self.assertTrue(all(model["state"] == "REGISTERED" for model in catalog["models"]))
        self.assertEqual(catalog["model_executions"],0)
        self.assertEqual(catalog["provider_egress_executions"],0)
        self.assertEqual(catalog["parity_promotions"],0)

    def test_cli_model_info_command_binding_is_capability_specific_and_runtime_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == CLI_MODEL_INFO_COMMAND_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "cli_command")
        self.assertEqual(row["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(row["source_line"], 87)
        self.assertEqual(row["name"], "info")
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding = row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], CLI_MODEL_INFO_COMMAND_TEST_ID)
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

        probe = json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_cli_model_info_command_runtime_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["capability_id"], CLI_MODEL_INFO_COMMAND_CAPABILITY_ID)
        self.assertEqual(probe["upstream_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(probe["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(probe["source_line"], 87)
        self.assertEqual(probe["runtime"]["command"], ["model", "info", "qwen3:0.6b"])
        self.assertEqual(probe["runtime"]["command_execution"], "PASS")
        self.assertEqual(probe["runtime"]["exit_code"], 0)
        self.assertTrue(probe["runtime"]["output_contains_model_id"])
        self.assertEqual(probe["runtime"]["network_mode"], "none")
        self.assertEqual(probe["model_executions"], 0)
        self.assertEqual(probe["provider_egress_executions"], 0)
        self.assertEqual(probe["tool_executions"], 0)
        self.assertEqual(probe["parity_promotions"], 0)
        self.assertEqual(probe["canonical_parity_status"], "UNVERIFIED")

    def test_cli_model_list_command_binding_is_capability_specific_and_source_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == CLI_MODEL_LIST_COMMAND_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "cli_command")
        self.assertEqual(row["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(row["source_line"], 34)
        self.assertEqual(row["name"], "list")
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["w02_evidence_state"], "EVIDENCE_BACKED_CANDIDATE")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding=row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], CLI_MODEL_LIST_COMMAND_TEST_ID)
        self.assertFalse(binding["terminal"])
        receipt=graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"],15)
        self.assertEqual(receipt["native_import_failure_count"],0)
        self.assertEqual(receipt["native_model_count"],69)
        self.assertEqual(receipt["model_executions"],0)
        self.assertEqual(receipt["provider_egress_executions"],0)
        self.assertEqual(receipt["parity_promotions"],0)
        probe=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_cli_model_list_command_source_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["capability_id"], CLI_MODEL_LIST_COMMAND_CAPABILITY_ID)
        self.assertEqual(probe["upstream_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(probe["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(probe["source_line"],34)
        self.assertEqual(probe["source_probe"],"PASS")
        self.assertFalse(probe["source_execution"])
        self.assertEqual(probe["function"],"list_models")
        self.assertEqual(probe["command_name"],"list")
        self.assertEqual(probe["register_builtin_models_line"],38)
        self.assertTrue(probe["registration_precedes_engine_discovery"])
        self.assertEqual(probe["list_command_execution"],"NOT_RUN")
        self.assertEqual(probe["model_executions"],0)
        self.assertEqual(probe["provider_egress_executions"],0)
        self.assertEqual(probe["tool_executions"],0)
        self.assertEqual(probe["parity_promotions"],0)

    def test_cli_model_pull_command_binding_is_capability_specific_and_source_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == CLI_MODEL_PULL_COMMAND_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "cli_command")
        self.assertEqual(row["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(row["source_line"], 226)
        self.assertEqual(row["name"], "pull")
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["w02_evidence_state"], "EVIDENCE_BACKED_CANDIDATE")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding=row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], CLI_MODEL_PULL_COMMAND_TEST_ID)
        self.assertFalse(binding["terminal"])
        receipt=graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"],15)
        self.assertEqual(receipt["native_import_failure_count"],0)
        self.assertEqual(receipt["native_model_count"],69)
        self.assertEqual(receipt["model_executions"],0)
        self.assertEqual(receipt["provider_egress_executions"],0)
        self.assertEqual(receipt["parity_promotions"],0)
        probe=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_cli_model_pull_command_source_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["capability_id"], CLI_MODEL_PULL_COMMAND_CAPABILITY_ID)
        self.assertEqual(probe["upstream_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(probe["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(probe["source_line"],226)
        self.assertEqual(probe["source_probe"],"PASS")
        self.assertFalse(probe["source_execution"])
        self.assertEqual(probe["function"],"pull")
        self.assertEqual(probe["model_command_decorator_line"],223)
        self.assertEqual(probe["model_name_argument_line"],224)
        self.assertEqual(probe["engine_option_line"],225)
        self.assertEqual(probe["pull_command_execution"],"NOT_RUN")
        self.assertEqual(probe["network_acquisition_execution"],"NOT_RUN")
        self.assertEqual(probe["model_executions"],0)
        self.assertEqual(probe["provider_egress_executions"],0)
        self.assertEqual(probe["tool_executions"],0)
        self.assertEqual(probe["parity_promotions"],0)

    def test_cli_model_group_command_binding_is_capability_specific_and_source_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == CLI_MODEL_GROUP_COMMAND_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "cli_command")
        self.assertEqual(row["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(row["source_line"], 29)
        self.assertEqual(row["name"], "model")
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["w02_evidence_state"], "EVIDENCE_BACKED_CANDIDATE")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding=row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], CLI_MODEL_GROUP_COMMAND_TEST_ID)
        self.assertFalse(binding["terminal"])
        receipt=graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_engine_count"],15)
        self.assertEqual(receipt["native_import_failure_count"],0)
        self.assertEqual(receipt["native_model_count"],69)
        self.assertEqual(receipt["model_executions"],0)
        self.assertEqual(receipt["provider_egress_executions"],0)
        self.assertEqual(receipt["parity_promotions"],0)
        probe=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_cli_model_group_source_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["capability_id"], CLI_MODEL_GROUP_COMMAND_CAPABILITY_ID)
        self.assertEqual(probe["upstream_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(probe["source_path"], "src/openjarvis/cli/model.py")
        self.assertEqual(probe["source_line"],29)
        self.assertEqual(probe["source_probe"],"PASS")
        self.assertFalse(probe["source_execution"])
        self.assertEqual(probe["function"],"model")
        self.assertEqual(probe["click_group_decorator_line"],28)
        self.assertEqual(probe["model_group_execution"],"NOT_RUN")
        self.assertEqual(probe["model_executions"],0)
        self.assertEqual(probe["provider_egress_executions"],0)
        self.assertEqual(probe["tool_executions"],0)
        self.assertEqual(probe["parity_promotions"],0)

    def test_model_info_protocol_binding_is_capability_specific_and_source_backed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == MODEL_INFO_PROTOCOL_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "protocol_contract")
        self.assertEqual(row["source_path"], "frontend/src/types/index.ts")
        self.assertEqual(row["source_line"], 160)
        self.assertEqual(row["name"], "ModelInfo")
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])
        binding=row["binding"]
        self.assertEqual(binding["evidence_id"], "EVID-W02-MODEL-BRIDGE-20260921")
        self.assertEqual(binding["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(binding["test_id"], MODEL_INFO_PROTOCOL_TEST_ID)
        self.assertFalse(binding["terminal"])
        receipt=graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")["EVID-W02-MODEL-BRIDGE-20260921"]
        self.assertEqual(receipt["status"], "VERIFIED")
        self.assertEqual(receipt["validated_head"], "a866c335a0f9cad75122c8eb7c5310d358f6aad4")
        self.assertEqual(receipt["native_model_count"],69)
        self.assertEqual(receipt["model_executions"],0)
        self.assertEqual(receipt["provider_egress_executions"],0)
        self.assertEqual(receipt["parity_promotions"],0)
        probe=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/binding_model_info_protocol_source_probe.json").read_text())
        self.assertEqual(probe["capability_id"], MODEL_INFO_PROTOCOL_CAPABILITY_ID)
        self.assertEqual(probe["upstream_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(probe["source_path"], "frontend/src/types/index.ts")
        self.assertEqual(probe["source_line"],160)
        self.assertEqual(probe["source_probe"],"PASS")
        self.assertFalse(probe["source_execution"])
        self.assertEqual(probe["interface_fields"],[{"name":"id","type":"string"},{"name":"object","type":"string"},{"name":"created","type":"number"},{"name":"owned_by","type":"string"}])
        self.assertEqual(probe["model_executions"],0)
        self.assertEqual(probe["provider_egress_executions"],0)
        self.assertEqual(probe["tool_executions"],0)
        self.assertEqual(probe["parity_promotions"],0)

    def test_afm_inprocess_registry_remains_unbound_when_only_shim_catalog_is_observed(self) -> None:
        row = next(row for row in self.result["rows"] if row["capability_id"] == AFM_INPROCESS_CAPABILITY_ID)
        self.assertEqual(row["ownership"], "OWNED")
        self.assertEqual(row["surface_kind"], "registry_registration")
        self.assertEqual(row["source_path"], "src/openjarvis/engine/apple_fm.py")
        self.assertEqual(row["source_line"], 171)
        self.assertEqual(row["name"], "afm")
        self.assertEqual(row["source_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(row["w02_evidence_state"], "UNBOUND")
        self.assertIsNone(row["binding"])
        self.assertEqual(row["canonical_parity_status"], "UNVERIFIED")
        self.assertFalse(row["verified"])
        self.assertFalse(row["parity_promotion"])

        probe=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-17/afm_optional_engine_source_probe.json").read_text(encoding="utf-8"))
        self.assertEqual(probe["capability_id"], AFM_INPROCESS_CAPABILITY_ID)
        self.assertEqual(probe["upstream_commit"], "72033b8ec288aa067ce4530ff9d96bf231e9c4e5")
        self.assertEqual(probe["decorator_registry_key"], "afm")
        self.assertEqual(probe["decorator_line"], 171)
        self.assertEqual(probe["optional_import_module"], "apple_fm")
        self.assertEqual(probe["optional_import_exceptions_swallowed"], ["ImportError", "OSError"])
        self.assertFalse(probe["w02_catalog_has_afm"])
        self.assertTrue(probe["w02_catalog_has_apple_fm"])
        self.assertEqual(probe["capability_status"], "BLOCKED_UNOBSERVABLE_OPTIONAL_IMPORT")
        self.assertFalse(probe["binding_created"])
        self.assertEqual(probe["canonical_parity_status"], "UNVERIFIED")
        self.assertEqual(probe["afm_engine_execution"], "NOT_RUN")
        self.assertFalse(probe["source_execution"])
        self.assertEqual(probe["parity_promotions"], 0)

        catalog=json.loads((ROOT / "evidence/cp03/cp03-w02/W02-08/native_catalog.json").read_text(encoding="utf-8"))
        keys={engine["key"] for engine in catalog["engines"]}
        self.assertIn("apple_fm", keys)
        self.assertNotIn("afm", keys)
        self.assertEqual(catalog["import_failures"], [])
        self.assertEqual(catalog["model_executions"], 0)
        self.assertEqual(catalog["provider_egress_executions"], 0)
        self.assertEqual(catalog["parity_promotions"], 0)

    def test_graph_projects_all_four_planes_without_promotion(self) -> None:
        value = self.result["graph"]
        candidate_count = self.result["summary"]["binding_counts"]["EVIDENCE_BACKED_CANDIDATE"]
        self.assertEqual(
            value["authority_order"],
            ["P0_SOURCE_EVIDENCE", "P1_SEMANTIC_SURFACE", "P2_COS20D_DECISION", "P3_AGENT_CONTEXT"],
        )
        self.assertEqual(value["parity_promotions"], 0)
        self.assertEqual(value["verified_capabilities"], 0)
        self.assertEqual(len(value["nodes"]), 47 * 4 + candidate_count)
        self.assertEqual(len(value["edges"]), 47 * 3 + candidate_count)
        evidence_nodes = [node for node in value["nodes"] if node["id"].startswith("EVIDENCE:")]
        support_edges = [edge for edge in value["edges"] if edge["type"] == "supports_candidate"]
        self.assertEqual(len(evidence_nodes), candidate_count)
        self.assertEqual(len(support_edges), candidate_count)

    def test_seed_binding_preserves_real_fallback_not_run_lane(self) -> None:
        evidence = graph.latest_by(graph.read_jsonl(ROOT / graph.EVIDENCE_LEDGER_PATH), "evidence_id")
        fallback = evidence["EVID-W02-FALLBACK-ADAPTER-20260922"]
        self.assertEqual(fallback["real_openjarvis_fallback_model_execution"], "NOT_RUN")
        candidate = next(row for row in self.result["rows"] if row["capability_id"] == SEED_CAPABILITY_ID)
        self.assertEqual(candidate["w02_evidence_state"], "EVIDENCE_BACKED_CANDIDATE")
        self.assertNotEqual(candidate["binding"]["evidence_id"], "EVID-W02-FALLBACK-ADAPTER-20260922")

    def test_forged_evidence_id_is_rejected(self) -> None:
        cid = self.result["rows"][0]["capability_id"]
        binding = {
            "capability_id": cid,
            "evidence_id": "EVID-FORGED",
            "test_id": "E01",
            "validated_head": "a" * 40,
            "expected_fields": {"result": "PASS"},
        }
        with self.assertRaisesRegex(graph.ParityGraphError, "unknown/forged evidence_id"):
            graph.validate_binding(
                binding,
                proof_unit_ids={cid},
                shared_ids=set(),
                evidence_catalog={},
                task_proofs={},
            )

    def test_foreign_sha_is_rejected(self) -> None:
        cid = self.result["rows"][0]["capability_id"]
        evidence_id = "EVID-SYNTHETIC"
        binding = {
            "capability_id": cid,
            "evidence_id": evidence_id,
            "test_id": "E01",
            "validated_head": "b" * 40,
            "expected_fields": {"result": "PASS"},
        }
        evidence = {evidence_id: {"evidence_id": evidence_id, "result": "PASS", "validated_head": "a" * 40}}
        proofs = {evidence_id: {"evidence_id": evidence_id, "result": "PASS", "validated_head": "a" * 40}}
        with self.assertRaisesRegex(graph.ParityGraphError, "foreign/stale evidence SHA"):
            graph.validate_binding(
                binding,
                proof_unit_ids={cid},
                shared_ids=set(),
                evidence_catalog=evidence,
                task_proofs=proofs,
            )

    def test_not_run_blocked_platform_gated_and_waiver_never_satisfy_binding(self) -> None:
        cid = self.result["rows"][0]["capability_id"]
        for state in ("NOT_RUN", "BLOCKED", "PLATFORM_GATED", "SKIPPED", "WAIVED", "UNKNOWN"):
            with self.subTest(state=state):
                evidence_id = f"EVID-{state}"
                binding = {
                    "capability_id": cid,
                    "evidence_id": evidence_id,
                    "test_id": "E02",
                    "validated_head": "a" * 40,
                    "expected_fields": {"lane": "PASS"},
                }
                evidence = {
                    evidence_id: {
                        "evidence_id": evidence_id,
                        "result": "PASS",
                        "validated_head": "a" * 40,
                        "lane": state,
                    }
                }
                proofs = {evidence_id: {"evidence_id": evidence_id, "result": "PASS", "validated_head": "a" * 40}}
                with self.assertRaises(graph.ParityGraphError):
                    graph.validate_binding(
                        binding,
                        proof_unit_ids={cid},
                        shared_ids=set(),
                        evidence_catalog=evidence,
                        task_proofs=proofs,
                    )

    def test_shared_capability_cannot_be_terminal(self) -> None:
        shared = next(row for row in self.result["rows"] if row["ownership"] == "SHARED")
        cid = shared["capability_id"]
        evidence_id = "EVID-SHARED"
        binding = {
            "capability_id": cid,
            "evidence_id": evidence_id,
            "test_id": "E02",
            "validated_head": "a" * 40,
            "expected_fields": {"lane": "PASS"},
            "terminal": True,
        }
        evidence = {
            evidence_id: {
                "evidence_id": evidence_id,
                "result": "PASS",
                "validated_head": "a" * 40,
                "lane": "PASS",
            }
        }
        proofs = {evidence_id: {"evidence_id": evidence_id, "result": "PASS", "validated_head": "a" * 40}}
        with self.assertRaisesRegex(graph.ParityGraphError, "shared W02 capability cannot be terminal"):
            graph.validate_binding(
                binding,
                proof_unit_ids={cid},
                shared_ids={cid},
                evidence_catalog=evidence,
                task_proofs=proofs,
            )

    def test_positive_binding_is_only_a_candidate_not_a_promotion(self) -> None:
        owned = next(row for row in self.result["rows"] if row["ownership"] == "OWNED")
        cid = owned["capability_id"]
        evidence_id = "EVID-POSITIVE"
        binding = {
            "capability_id": cid,
            "evidence_id": evidence_id,
            "test_id": "G6-SYNTHETIC",
            "validated_head": "a" * 40,
            "expected_fields": {"lane": "PASS"},
            "terminal": True,
        }
        evidence = {
            evidence_id: {
                "evidence_id": evidence_id,
                "result": "PASS",
                "validated_head": "a" * 40,
                "lane": "PASS",
            }
        }
        proofs = {evidence_id: {"evidence_id": evidence_id, "result": "PASS", "validated_head": "a" * 40}}
        validated = graph.validate_binding(
            binding,
            proof_unit_ids={cid},
            shared_ids=set(),
            evidence_catalog=evidence,
            task_proofs=proofs,
        )
        self.assertEqual(validated["binding_state"], "EVIDENCE_BACKED_CANDIDATE")
        self.assertIs(validated["parity_promotion"], False)

    def test_compiler_does_not_mutate_capability_ledger(self) -> None:
        path = ROOT / graph.CAPABILITY_LEDGER_PATH
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        graph.compile_root(ROOT)
        after = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(before, after)

    def test_products_are_deterministic(self) -> None:
        first = graph.products(graph.compile_root(ROOT))
        second = graph.products(graph.compile_root(ROOT))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
