"""Compile the CP03-W02 G6 proof plane without promoting parity.

The compiler is intentionally conservative. It joins the frozen K=47 W02 scope
with the immutable OpenJarvis obligation/capability ledgers, exposes an explicit
P0->P1->P2->P3 graph, and validates future per-capability evidence bindings.
No code path in this module writes the canonical capability ledger or changes a
parity status. A PASS receipt is evidence input, not parity by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
SCOPE_PATH = Path("inventory/cp03/W02_SCOPE_LOCK.json")
OBLIGATIONS_PATH = Path("inventory/cp03/openjarvis_obligations.jsonl")
CAPABILITY_LEDGER_PATH = Path("ledgers/CAPABILITY_LEDGER.jsonl")
EVIDENCE_LEDGER_PATH = Path("ledgers/EVIDENCE_LEDGER.ndjson")
TASK_GRAPH_PATH = Path("iterations/03/waves/CP03-W02/TASK_GRAPH.json")
BINDINGS_PATH = Path("inventory/cp03/w02_evidence_bindings.jsonl")

SUMMARY_PATH = Path("reports/cp03/w02_parity/SUMMARY.json")
MATRIX_PATH = Path("reports/cp03/w02_parity/PROOF_MATRIX.jsonl")
GRAPH_PATH = Path("graphs/cp03/w02_parity/PARITY_TEST_GRAPH.json")

EXPECTED_GLOBAL_DENOMINATOR = 7565
EXPECTED_OPENJARVIS_OBLIGATIONS = 646
EXPECTED_K = 47
EXPECTED_OWNED = 37
EXPECTED_SHARED = 10
EXPECTED_OPENJARVIS_COMMIT = "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"

NON_PROOF_STATES = {
    "NOT_RUN",
    "BLOCKED",
    "PLATFORM_GATED",
    "SKIPPED",
    "WAIVED",
    "UNKNOWN",
    "FAIL",
    "FAILED",
    "ERROR",
    "UNAVAILABLE",
}


class ParityGraphError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ParityGraphError(message)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_by(rows: Iterable[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if isinstance(value, str) and value:
            result[value] = row
    return result


def task_proofs_by_evidence(task_graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    proofs: dict[str, dict[str, Any]] = {}
    for task in task_graph.get("tasks", []):
        if task.get("status") != "COMPLETE":
            continue
        for proof in task.get("proof", []):
            evidence_id = proof.get("evidence_id")
            if not evidence_id:
                continue
            require(evidence_id not in proofs, f"duplicate task proof evidence_id: {evidence_id}")
            proofs[evidence_id] = {"task": task["id"], **proof}
    return proofs


def validate_authority(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    scope = read_json(root / SCOPE_PATH)
    task_graph = read_json(root / TASK_GRAPH_PATH)
    obligations = latest_by(read_jsonl(root / OBLIGATIONS_PATH), "capability_id")
    capability_rows = latest_by(read_jsonl(root / CAPABILITY_LEDGER_PATH), "capability_id")

    require(scope.get("global_denominator") == EXPECTED_GLOBAL_DENOMINATOR, "scope denominator drift")
    require(scope.get("openjarvis_obligations") == EXPECTED_OPENJARVIS_OBLIGATIONS, "scope OpenJarvis denominator drift")
    require(scope.get("source_commit") == EXPECTED_OPENJARVIS_COMMIT, "OpenJarvis source pin drift")
    require(scope.get("w02_proof_units") == EXPECTED_K, "W02 K drift")
    require(scope.get("w02_owned_capabilities") == EXPECTED_OWNED, "W02 owned count drift")
    require(scope.get("w02_shared_capabilities") == EXPECTED_SHARED, "W02 shared count drift")
    require(scope.get("semantics", {}).get("denominator_mutation_authorized") is False, "denominator mutation unexpectedly authorized")
    require(scope.get("semantics", {}).get("parity_promotions") == 0, "scope already promotes parity")
    require(scope.get("semantics", {}).get("shared_terminal_forbidden") is True, "shared terminal guard missing")

    proof_ids = scope.get("proof_unit_ids", [])
    owned_ids = scope.get("owned_ids", [])
    shared_ids = scope.get("shared_ids", [])
    require(len(proof_ids) == EXPECTED_K and len(set(proof_ids)) == EXPECTED_K, "W02 proof-unit ID drift")
    require(len(owned_ids) == EXPECTED_OWNED and len(set(owned_ids)) == EXPECTED_OWNED, "W02 owned ID drift")
    require(len(shared_ids) == EXPECTED_SHARED and len(set(shared_ids)) == EXPECTED_SHARED, "W02 shared ID drift")
    require(set(owned_ids).isdisjoint(shared_ids), "owned/shared overlap")
    require(set(proof_ids) == set(owned_ids) | set(shared_ids), "proof-unit ownership partition drift")

    require(len(obligations) == EXPECTED_OPENJARVIS_OBLIGATIONS, f"OpenJarvis obligation count drift: {len(obligations)}")
    require(set(proof_ids) <= set(obligations), "W02 proof unit missing from OpenJarvis obligation manifest")
    require(set(proof_ids) <= set(capability_rows), "W02 proof unit missing from capability ledger")

    for cid in proof_ids:
        obligation = obligations[cid]
        capability = capability_rows[cid]
        require(obligation.get("source_repo") == "openjarvis", f"non-OpenJarvis obligation in W02: {cid}")
        require(obligation.get("source_commit") == EXPECTED_OPENJARVIS_COMMIT, f"obligation source pin drift: {cid}")
        require(capability.get("source_commit") == EXPECTED_OPENJARVIS_COMMIT, f"capability source pin drift: {cid}")
        require(capability.get("parity_status") == "UNVERIFIED", f"unexpected pre-G6 parity state for {cid}")
        for field in ("contract_fingerprint", "name", "source_path", "source_line", "surface_kind"):
            require(obligation.get(field) == capability.get(field), f"P0 provenance drift {cid}:{field}")

    require(task_graph.get("global_denominator") == EXPECTED_GLOBAL_DENOMINATOR, "task graph denominator drift")
    require(task_graph.get("openjarvis_obligations") == EXPECTED_OPENJARVIS_OBLIGATIONS, "task graph OpenJarvis denominator drift")
    require(task_graph.get("w02_obligation_count") == EXPECTED_K, "task graph K drift")
    require(task_graph.get("first_executable_task") == "W02-17", "unexpected G6 frontier")
    tasks = {task["id"]: task for task in task_graph["tasks"]}
    require(tasks["W02-17"]["status"] in {"READY", "IN_PROGRESS"}, "W02-17 must be active frontier")
    require(tasks["W02-18"]["status"] == "BLOCKED" and tasks["W02-19"]["status"] == "BLOCKED", "future G7 task opened early")
    require(all(tasks[dep]["status"] == "COMPLETE" for dep in tasks["W02-17"]["depends_on"]), "W02-17 dependency incomplete")
    return scope, obligations, capability_rows, task_graph


def validate_binding(
    binding: dict[str, Any],
    *,
    proof_unit_ids: set[str],
    shared_ids: set[str],
    evidence_catalog: dict[str, dict[str, Any]],
    task_proofs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Validate one future explicit evidence binding without changing parity."""
    cid = binding.get("capability_id")
    evidence_id = binding.get("evidence_id")
    require(cid in proof_unit_ids, f"binding capability outside frozen W02 scope: {cid}")
    require(isinstance(evidence_id, str) and evidence_id, "binding missing evidence_id")
    require(evidence_id in evidence_catalog, f"unknown/forged evidence_id: {evidence_id}")
    require(evidence_id in task_proofs, f"evidence not referenced by a completed task proof: {evidence_id}")

    evidence = evidence_catalog[evidence_id]
    proof = task_proofs[evidence_id]
    require(proof.get("result") == "PASS", f"task proof is not PASS: {evidence_id}")
    validated_head = binding.get("validated_head")
    require(isinstance(validated_head, str) and len(validated_head) == 40, "binding missing exact validated_head")
    proof_head = proof.get("validated_head") or proof.get("head")
    evidence_head = evidence.get("validated_head") or evidence.get("head")
    require(isinstance(proof_head, str) and len(proof_head) == 40, f"task proof lacks exact head: {evidence_id}")
    require(isinstance(evidence_head, str) and len(evidence_head) == 40, f"evidence ledger lacks exact head: {evidence_id}")
    require(validated_head == proof_head == evidence_head, f"foreign/stale evidence SHA: {evidence_id}")

    test_id = binding.get("test_id")
    require(isinstance(test_id, str) and test_id.strip(), "binding missing explicit test_id")
    expected_fields = binding.get("expected_fields")
    require(isinstance(expected_fields, dict) and expected_fields, "binding requires field-level proof expectations")
    for field, expected in expected_fields.items():
        observed = evidence.get(field)
        if isinstance(observed, str) and observed in NON_PROOF_STATES:
            raise ParityGraphError(f"non-proof state cannot satisfy binding {evidence_id}:{field}={observed}")
        require(observed == expected, f"evidence field mismatch {evidence_id}:{field}: expected={expected!r} observed={observed!r}")

    terminal = bool(binding.get("terminal", False))
    require(not (terminal and cid in shared_ids), f"shared W02 capability cannot be terminal: {cid}")
    require(binding.get("waiver") in (None, False), "waiver cannot satisfy parity evidence")
    return {
        "capability_id": cid,
        "evidence_id": evidence_id,
        "test_id": test_id,
        "validated_head": validated_head,
        "terminal": terminal,
        "binding_state": "EVIDENCE_BACKED_CANDIDATE",
        "parity_promotion": False,
    }


def compile_root(root: Path = ROOT) -> dict[str, Any]:
    scope, obligations, capabilities, task_graph = validate_authority(root)
    proof_ids = set(scope["proof_unit_ids"])
    shared_ids = set(scope["shared_ids"])
    owned_ids = set(scope["owned_ids"])
    evidence_catalog = latest_by(read_jsonl(root / EVIDENCE_LEDGER_PATH), "evidence_id")
    task_proofs = task_proofs_by_evidence(task_graph)
    raw_bindings = read_jsonl(root / BINDINGS_PATH)

    seen_caps: set[str] = set()
    validated_bindings: dict[str, dict[str, Any]] = {}
    for binding in raw_bindings:
        cid = binding.get("capability_id")
        require(cid not in seen_caps, f"duplicate W02 evidence binding for {cid}")
        seen_caps.add(cid)
        validated_bindings[cid] = validate_binding(
            binding,
            proof_unit_ids=proof_ids,
            shared_ids=shared_ids,
            evidence_catalog=evidence_catalog,
            task_proofs=task_proofs,
        )

    rows: list[dict[str, Any]] = []
    for cid in sorted(proof_ids):
        obligation = obligations[cid]
        capability = capabilities[cid]
        binding = validated_bindings.get(cid)
        ownership = "OWNED" if cid in owned_ids else "SHARED"
        rows.append(
            {
                "schema_version": 1,
                "capability_id": cid,
                "ownership": ownership,
                "source_repo": "openjarvis",
                "source_commit": obligation["source_commit"],
                "source_path": obligation["source_path"],
                "source_line": obligation["source_line"],
                "surface_kind": obligation["surface_kind"],
                "name": obligation["name"],
                "contract_fingerprint": obligation["contract_fingerprint"],
                "canonical_parity_status": capability["parity_status"],
                "w02_evidence_state": binding["binding_state"] if binding else "UNBOUND",
                "binding": binding,
                "terminal_eligible_in_w02": ownership == "OWNED",
                "verified": False,
                "parity_promotion": False,
            }
        )

    counts = {
        "UNBOUND": sum(row["w02_evidence_state"] == "UNBOUND" for row in rows),
        "EVIDENCE_BACKED_CANDIDATE": sum(row["w02_evidence_state"] == "EVIDENCE_BACKED_CANDIDATE" for row in rows),
    }
    summary = {
        "schema_version": 1,
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "wave": "CP03-W02",
        "task": "W02-17",
        "gate": "G6",
        "status": "PROOF_PLANE_COMPILED_NO_PARITY_PROMOTION",
        "global_denominator": EXPECTED_GLOBAL_DENOMINATOR,
        "openjarvis_obligations": EXPECTED_OPENJARVIS_OBLIGATIONS,
        "w02_proof_units": EXPECTED_K,
        "owned": EXPECTED_OWNED,
        "shared": EXPECTED_SHARED,
        "binding_counts": counts,
        "verified_capabilities": 0,
        "parity_promotions": 0,
        "source_commit": EXPECTED_OPENJARVIS_COMMIT,
        "input_sha256": {
            str(SCOPE_PATH): sha256_file(root / SCOPE_PATH),
            str(OBLIGATIONS_PATH): sha256_file(root / OBLIGATIONS_PATH),
            str(CAPABILITY_LEDGER_PATH): sha256_file(root / CAPABILITY_LEDGER_PATH),
            str(EVIDENCE_LEDGER_PATH): sha256_file(root / EVIDENCE_LEDGER_PATH),
            str(TASK_GRAPH_PATH): sha256_file(root / TASK_GRAPH_PATH),
            str(BINDINGS_PATH): sha256_file(root / BINDINGS_PATH) if (root / BINDINGS_PATH).is_file() else None,
        },
        "invariants": {
            "not_run_is_pass": False,
            "blocked_is_pass": False,
            "platform_gated_is_pass": False,
            "waiver_is_verified": False,
            "shared_terminal_forbidden": True,
            "denominator_mutation": False,
        },
    }

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for row in rows:
        cid = row["capability_id"]
        p0 = f"P0:{cid}"
        p1 = f"P1:{cid}"
        p2 = f"P2:{cid}"
        p3 = f"P3:{cid}"
        nodes.extend(
            [
                {"id": p0, "plane": "P0_SOURCE_EVIDENCE", "kind": "source_contract", "capability_id": cid, "contract_fingerprint": row["contract_fingerprint"]},
                {"id": p1, "plane": "P1_SEMANTIC_SURFACE", "kind": "openjarvis_obligation", "capability_id": cid, "state": "UNVERIFIED"},
                {"id": p2, "plane": "P2_COS20D_DECISION", "kind": "w02_evidence_overlay", "capability_id": cid, "state": row["w02_evidence_state"], "ownership": row["ownership"]},
                {"id": p3, "plane": "P3_AGENT_CONTEXT", "kind": "recovery_projection", "capability_id": cid, "state": "UNVERIFIED"},
            ]
        )
        edges.extend(
            [
                {"from": p0, "to": p1, "type": "grounds"},
                {"from": p1, "to": p2, "type": "candidate_for"},
                {"from": p2, "to": p3, "type": "projects_without_promotion"},
            ]
        )
        if row["binding"]:
            evidence_node = f"EVIDENCE:{row['binding']['evidence_id']}"
            nodes.append({"id": evidence_node, "plane": "P0_SOURCE_EVIDENCE", "kind": "test_evidence", "evidence_id": row["binding"]["evidence_id"], "validated_head": row["binding"]["validated_head"]})
            edges.append({"from": evidence_node, "to": p2, "type": "supports_candidate"})

    graph = {
        "schema_version": 1,
        "project_id": "CLEVER-JARVIS-001",
        "checkpoint": "CP03",
        "task": "W02-17",
        "gate": "G6",
        "authority_order": ["P0_SOURCE_EVIDENCE", "P1_SEMANTIC_SURFACE", "P2_COS20D_DECISION", "P3_AGENT_CONTEXT"],
        "nodes": nodes,
        "edges": edges,
        "parity_promotions": 0,
        "verified_capabilities": 0,
    }
    return {"summary": summary, "rows": rows, "graph": graph}


def products(result: dict[str, Any]) -> dict[Path, str]:
    return {
        SUMMARY_PATH: canonical(result["summary"]),
        MATRIX_PATH: "".join(canonical(row) for row in result["rows"]),
        GRAPH_PATH: canonical(result["graph"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = compile_root(ROOT)
        outputs = products(result)
        for relative, data in outputs.items():
            path = ROOT / relative
            if args.check:
                require(path.is_file(), f"generated product missing: {relative}")
                require(path.read_text(encoding="utf-8") == data, f"generated product drift: {relative}")
            elif args.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(data, encoding="utf-8")
        print(canonical(result["summary"]).strip())
        return 0
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(canonical({"status": "FAIL", "parity_promotions": 0, "error": str(exc)}).strip())
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
