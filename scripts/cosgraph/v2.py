from __future__ import annotations

from enum import Enum
import hashlib
import json
from typing import Any

from scripts.cosgraph.model import IntegrationDecision


class COS20Dimension(str, Enum):
    MISSION_GOAL = "D00_MISSION_GOAL"
    PROVENANCE_EVIDENCE = "D01_PROVENANCE_EVIDENCE"
    SOURCE_TOPOLOGY = "D02_SOURCE_TOPOLOGY"
    CAPABILITY_SEMANTICS = "D03_CAPABILITY_SEMANTICS"
    DEPENDENCY_GRAPH = "D04_DEPENDENCY_GRAPH"
    RUNTIME_OWNERSHIP = "D05_RUNTIME_OWNERSHIP"
    INTERFACE_CONTRACTS = "D06_INTERFACE_CONTRACTS"
    STATE_DATA = "D07_STATE_DATA"
    MEMORY_KNOWLEDGE = "D08_MEMORY_KNOWLEDGE"
    INTENT_CONTROL = "D09_INTENT_CONTROL"
    LIFECYCLE_CONCURRENCY = "D10_LIFECYCLE_CONCURRENCY"
    SIDE_EFFECT_IDEMPOTENCY = "D11_SIDE_EFFECT_IDEMPOTENCY"
    SECURITY_PERMISSION = "D12_SECURITY_PERMISSION"
    FAILURE_RECOVERY = "D13_FAILURE_RECOVERY"
    OBSERVABILITY_ECONOMICS = "D14_OBSERVABILITY_ECONOMICS"
    TEST_EVAL_PARITY = "D15_TEST_EVAL_PARITY"
    PLATFORM_DEVICE = "D16_PLATFORM_DEVICE"
    EMBODIMENT_UX = "D17_EMBODIMENT_UX"
    SUPPLY_CHAIN_DEPLOYMENT = "D18_SUPPLY_CHAIN_DEPLOYMENT"
    TEMPORAL_DRIFT = "D19_TEMPORAL_DRIFT"


DIMENSION_DESCRIPTIONS: dict[COS20Dimension, tuple[str, str]] = {
    COS20Dimension.MISSION_GOAL: ("Mission / goal", "Which durable goal, checkpoint and acceptance criterion does this decision advance?"),
    COS20Dimension.PROVENANCE_EVIDENCE: ("Provenance / evidence", "What source paths, commits, tests and evidence prove the modeled fact?"),
    COS20Dimension.SOURCE_TOPOLOGY: ("Source topology", "Where does this surface live across repositories, packages, modules and graphs?"),
    COS20Dimension.CAPABILITY_SEMANTICS: ("Capability semantics", "What behavior is actually provided, with what inputs, outputs and semantics?"),
    COS20Dimension.DEPENDENCY_GRAPH: ("Dependency graph", "What does this surface require and what depends on it?"),
    COS20Dimension.RUNTIME_OWNERSHIP: ("Runtime ownership", "Which runtime, process, adapter or device owns execution and lifecycle?"),
    COS20Dimension.INTERFACE_CONTRACTS: ("Interface contracts", "Which API, route, command, event, registry or protocol exposes the behavior?"),
    COS20Dimension.STATE_DATA: ("State / data", "What durable, cached or transactional state does the behavior read or mutate?"),
    COS20Dimension.MEMORY_KNOWLEDGE: ("Memory / knowledge", "How does the behavior create, retrieve, derive or consolidate memory/knowledge?"),
    COS20Dimension.INTENT_CONTROL: ("Intent / control", "How do goals, plans, routing and control flow reach this surface?"),
    COS20Dimension.LIFECYCLE_CONCURRENCY: ("Lifecycle / concurrency", "What startup, shutdown, leasing, scheduling and concurrency semantics apply?"),
    COS20Dimension.SIDE_EFFECT_IDEMPOTENCY: ("Side effect / idempotency", "What external effects occur and how are retries, receipts and idempotency handled?"),
    COS20Dimension.SECURITY_PERMISSION: ("Security / permission", "What trust boundary, permission, secret, sandbox or policy gate protects it?"),
    COS20Dimension.FAILURE_RECOVERY: ("Failure / recovery", "How does it fail, degrade, retry, roll back and recover after process or network loss?"),
    COS20Dimension.OBSERVABILITY_ECONOMICS: ("Observability / economics", "Which health, latency, cost, energy and telemetry signals make behavior observable?"),
    COS20Dimension.TEST_EVAL_PARITY: ("Test / eval / parity", "Which tests or evaluations prove behavior and parity rather than implementation presence?"),
    COS20Dimension.PLATFORM_DEVICE: ("Platform / device", "Which OS, hardware, device, BLE, firmware or platform constraints apply?"),
    COS20Dimension.EMBODIMENT_UX: ("Embodiment / UX", "How is the behavior presented or controlled through desktop, mobile, voice or visual embodiment?"),
    COS20Dimension.SUPPLY_CHAIN_DEPLOYMENT: ("Supply chain / deployment", "Which manifests, licenses, builds, releases, dependencies and deployment constraints apply?"),
    COS20Dimension.TEMPORAL_DRIFT: ("Temporal / drift", "How can upstream versions, state, capability availability or contracts drift over time?"),
}


def dimension_registry() -> list[dict[str, str]]:
    return [{"id": dimension.value, "name": DIMENSION_DESCRIPTIONS[dimension][0], "question": DIMENSION_DESCRIPTIONS[dimension][1]} for dimension in COS20Dimension]


_BASE_DIMENSIONS = {COS20Dimension.MISSION_GOAL, COS20Dimension.PROVENANCE_EVIDENCE, COS20Dimension.CAPABILITY_SEMANTICS, COS20Dimension.RUNTIME_OWNERSHIP, COS20Dimension.INTERFACE_CONTRACTS, COS20Dimension.TEST_EVAL_PARITY, COS20Dimension.TEMPORAL_DRIFT}

_FAMILY_DIMENSIONS: dict[str, set[COS20Dimension]] = {
    "memory": {COS20Dimension.STATE_DATA, COS20Dimension.MEMORY_KNOWLEDGE, COS20Dimension.FAILURE_RECOVERY},
    "persistence": {COS20Dimension.STATE_DATA, COS20Dimension.LIFECYCLE_CONCURRENCY, COS20Dimension.FAILURE_RECOVERY},
    "gateway_channel": {COS20Dimension.INTENT_CONTROL, COS20Dimension.LIFECYCLE_CONCURRENCY, COS20Dimension.SECURITY_PERMISSION, COS20Dimension.FAILURE_RECOVERY},
    "agent_orchestration": {COS20Dimension.INTENT_CONTROL, COS20Dimension.MEMORY_KNOWLEDGE, COS20Dimension.SIDE_EFFECT_IDEMPOTENCY, COS20Dimension.SECURITY_PERMISSION},
    "inference": {COS20Dimension.DEPENDENCY_GRAPH, COS20Dimension.OBSERVABILITY_ECONOMICS, COS20Dimension.SECURITY_PERMISSION},
    "device": {COS20Dimension.PLATFORM_DEVICE, COS20Dimension.LIFECYCLE_CONCURRENCY, COS20Dimension.SECURITY_PERMISSION, COS20Dimension.FAILURE_RECOVERY},
    "capture_voice": {COS20Dimension.PLATFORM_DEVICE, COS20Dimension.EMBODIMENT_UX, COS20Dimension.SECURITY_PERMISSION, COS20Dimension.FAILURE_RECOVERY},
    "embodiment": {COS20Dimension.PLATFORM_DEVICE, COS20Dimension.EMBODIMENT_UX, COS20Dimension.SECURITY_PERMISSION},
    "security": {COS20Dimension.SECURITY_PERMISSION, COS20Dimension.SIDE_EFFECT_IDEMPOTENCY, COS20Dimension.FAILURE_RECOVERY},
    "extension_tooling": {COS20Dimension.DEPENDENCY_GRAPH, COS20Dimension.LIFECYCLE_CONCURRENCY, COS20Dimension.SIDE_EFFECT_IDEMPOTENCY, COS20Dimension.SECURITY_PERMISSION, COS20Dimension.SUPPLY_CHAIN_DEPLOYMENT},
    "api_surface": {COS20Dimension.INTENT_CONTROL, COS20Dimension.SECURITY_PERMISSION, COS20Dimension.FAILURE_RECOVERY},
    "dependency": {COS20Dimension.DEPENDENCY_GRAPH, COS20Dimension.SUPPLY_CHAIN_DEPLOYMENT},
    "build_workspace": {COS20Dimension.SOURCE_TOPOLOGY, COS20Dimension.DEPENDENCY_GRAPH, COS20Dimension.SUPPLY_CHAIN_DEPLOYMENT},
    "structural": {COS20Dimension.SOURCE_TOPOLOGY},
}


def _stable(prefix: str, *parts: object) -> str:
    raw = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}:{hashlib.sha256(raw.encode()).hexdigest()[:20]}"


def dimensions_for_component(component: dict[str, Any]) -> list[str]:
    family = str(component.get("family") or "structural")
    selected = set(_BASE_DIMENSIONS)
    selected.add(COS20Dimension.SOURCE_TOPOLOGY)
    selected.update(_FAMILY_DIMENSIONS.get(family, set()))
    decision = str(component.get("decision") or IntegrationDecision.ADAPT.value)
    if decision == IntegrationDecision.MERGE_STATE.value:
        selected.update({COS20Dimension.STATE_DATA, COS20Dimension.MEMORY_KNOWLEDGE, COS20Dimension.LIFECYCLE_CONCURRENCY, COS20Dimension.FAILURE_RECOVERY})
    if decision in {IntegrationDecision.CANONICALIZE.value, IntegrationDecision.REWRITE_LATER.value}:
        selected.update({COS20Dimension.DEPENDENCY_GRAPH, COS20Dimension.SIDE_EFFECT_IDEMPOTENCY, COS20Dimension.SUPPLY_CHAIN_DEPLOYMENT})
    return sorted(d.value for d in selected)


def build_cos20d_decision_graph(cos_hypergraph: dict[str, Any], *, goal_id: str = "CLEVER-JARVIS-001", checkpoint_id: str = "CP01", wave_id: str | None = None) -> dict[str, Any]:
    if cos_hypergraph.get("graph_type") != "cos_hypergraph":
        raise ValueError("COS Graph Engine V2 accepts only cos_hypergraph input")
    decisions: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    for component in sorted(cos_hypergraph.get("canonical_components", []), key=lambda row: row["id"]):
        dimensions = dimensions_for_component(component)
        required_promotions = ["W03 behavioral/registration evidence", "W04 canonical contract mapping", "behavioral test mapping", "capability-ledger parity row"]
        if any(value in dimensions for value in (COS20Dimension.SECURITY_PERMISSION.value, COS20Dimension.SIDE_EFFECT_IDEMPOTENCY.value)):
            required_promotions.append("security/side-effect review")
        decision = {"id": _stable("cos20d-decision", component["id"], component.get("decision"), dimensions), "source_component_id": component["id"], "goal_id": goal_id, "checkpoint_id": checkpoint_id, "wave_id": wave_id, "family": component.get("family"), "interface_kind": component.get("interface_kind"), "source_repositories": sorted(component.get("source_repositories", [])), "source_nodes": sorted(component.get("source_nodes", [])), "proposed_decision": component.get("decision"), "status": "PROVISIONAL", "confidence": "UNVERIFIED", "promotion_status": "DISCOVERED_CANDIDATE", "dimensions": dimensions, "rewrite_allowed": False, "migration_authorized": False, "required_promotions": required_promotions}
        decisions.append(decision)
        relations.append({"id": _stable("cos20d-edge", decision["id"], component["id"]), "relation": "proposes_integration_for", "source": decision["id"], "target": component["id"]})
    counts: dict[str, int] = {}
    for decision in decisions:
        key = str(decision.get("proposed_decision") or "UNKNOWN")
        counts[key] = counts.get(key, 0) + 1
    return {"schema_version": 1, "graph_type": "cos20d_decision_graph", "engine_version": "COS-GRAPH-ENGINE-V2", "dimension_model": "COS-20D-v2", "source_cos_model": cos_hypergraph.get("cos_model"), "source_graphs": sorted(cos_hypergraph.get("source_graphs", [])), "dimension_registry": dimension_registry(), "invariants": {"dimension_count": len(COS20Dimension), "source_graph_is_immutable": True, "automatic_rewrite_forbidden": True, "provisional_decisions_cannot_authorize_migration": True, "raw_graph_is_not_capability_denominator": True}, "summary": {"decision_count": len(decisions), "decision_counts": dict(sorted(counts.items()))}, "decisions": decisions, "relations": sorted(relations, key=lambda row: row["id"])}
