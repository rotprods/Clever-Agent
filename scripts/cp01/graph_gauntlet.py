from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

from scripts.cp01.capabilities import read_jsonl

SUPPORTED_EDGE_TYPES = [
    "requires", "exposes", "implemented_by", "registered_via", "persists_to",
    "executes_on", "permissioned_by", "tested_by", "owned_by", "emits",
    "consumes", "recovers_via", "sourced_from", "classified_as", "has_baseline_candidate",
    "described_by_supply_chain"
]
CORE_20D = {
    "D00_MISSION_GOAL", "D01_PROVENANCE_EVIDENCE", "D02_SOURCE_TOPOLOGY",
    "D03_CAPABILITY_SEMANTICS", "D04_DEPENDENCY_GRAPH", "D05_RUNTIME_OWNERSHIP",
    "D06_INTERFACE_CONTRACTS", "D14_OBSERVABILITY_ECONOMICS", "D15_TEST_EVAL_PARITY",
    "D18_SUPPLY_CHAIN_DEPLOYMENT", "D19_TEMPORAL_DRIFT"
}


def _node_id(kind: str, value: str) -> str:
    safe = value.replace(" ", "_").replace("/", "_").replace(":", "_")
    return f"{kind}:{safe}"


def _required_dimensions(cap: dict[str, Any], surface: dict[str, Any]) -> list[str]:
    dims = set(CORE_20D)
    family = str(cap["family"])
    kind = str(cap["surface_kind"])
    if surface.get("state_effects"):
        dims.add("D07_STATE_DATA")
    if family == "memory_persistence":
        dims.update({"D07_STATE_DATA", "D08_MEMORY_KNOWLEDGE"})
    if family in {"agent", "tool", "inference", "scheduler_automation"}:
        dims.add("D09_INTENT_CONTROL")
    if surface.get("lifecycle") or kind in {"plugin_contribution", "lifecycle_hook", "registry_registration", "route_mount"}:
        dims.add("D10_LIFECYCLE_CONCURRENCY")
    if family in {"tool", "channel_gateway", "device_wearable", "worker_service", "scheduler_automation"} or kind in {"http_route", "websocket_route", "cli_command", "native_action"}:
        dims.add("D11_SIDE_EFFECT_IDEMPOTENCY")
    if surface.get("permissions") or family == "security_policy":
        dims.add("D12_SECURITY_PERMISSION")
    if surface.get("failure_semantics"):
        dims.add("D13_FAILURE_RECOVERY")
    if surface.get("platform_constraints"):
        dims.add("D16_PLATFORM_DEVICE")
    if family in {"embodiment", "capture_perception", "speech_audio", "device_wearable", "channel_gateway"}:
        dims.add("D17_EMBODIMENT_UX")
    return sorted(dims)


def build_graph(
    capabilities: list[dict[str, Any]],
    surfaces: list[dict[str, Any]],
    baselines: dict[str, Any],
    supply_chain: dict[str, Any],
) -> dict[str, Any]:
    surface_map = {row["surface_id"]: row for row in surfaces}
    nodes: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str, str]] = set()
    dimension_pressure: dict[str, list[str]] = {}

    def add_node(node_id: str, kind: str, **attrs: Any) -> None:
        nodes.setdefault(node_id, {"id": node_id, "kind": kind, **attrs})

    def add_edge(source: str, relation: str, target: str) -> None:
        if relation not in SUPPORTED_EDGE_TYPES:
            raise ValueError(f"unsupported edge relation: {relation}")
        edges.add((source, relation, target))

    repos = sorted({row["source_repo"] for row in capabilities})
    for repo in repos:
        add_node(_node_id("repo", repo), "source_repo", source_repo=repo)

    for surface in surfaces:
        sid = surface["surface_id"]
        surface_node = _node_id("surface", sid)
        repo_node = _node_id("repo", surface["source_repo"])
        add_node(surface_node, "behavioral_surface", surface_id=sid, family=surface["family"], surface_kind=surface["surface_kind"], source_path=surface["source_path"], evidence_strength=surface["evidence_strength"])
        add_edge(surface_node, "sourced_from", repo_node)

    for cap in capabilities:
        cid = cap["capability_id"]
        cap_node = _node_id("capability", cid)
        surface = surface_map[cap["source_surface_id"]]
        surface_node = _node_id("surface", cap["source_surface_id"])
        repo_node = _node_id("repo", cap["source_repo"])
        owner_node = _node_id("owner", cap["runtime_owner"])
        family_node = _node_id("family", cap["family"])
        add_node(cap_node, "capability", capability_id=cid, family=cap["family"], surface_kind=cap["surface_kind"], source_repo=cap["source_repo"], parity_status=cap["parity_status"], equivalence_status=cap["equivalence_status"])
        add_node(owner_node, "runtime_owner", runtime_owner=cap["runtime_owner"])
        add_node(family_node, "capability_family", family=cap["family"])
        add_edge(repo_node, "exposes", cap_node)
        add_edge(cap_node, "implemented_by", surface_node)
        add_edge(cap_node, "owned_by", owner_node)
        add_edge(cap_node, "classified_as", family_node)
        if cap["evidence_strength"] in {"REGISTRATION", "ROUTE_OR_PROTOCOL", "BEHAVIOR_TEST"}:
            add_edge(cap_node, "registered_via", surface_node)
        if cap["evidence_strength"] == "BEHAVIOR_TEST":
            add_edge(cap_node, "tested_by", surface_node)
        for token in surface.get("state_effects", []):
            state_node = _node_id("state", str(token))
            add_node(state_node, "state_facet", name=token)
            add_edge(cap_node, "persists_to", state_node)
        for token in surface.get("permissions", []):
            permission_node = _node_id("permission", str(token))
            add_node(permission_node, "permission_facet", name=token)
            add_edge(cap_node, "permissioned_by", permission_node)
        for platform in surface.get("platform_constraints", []):
            platform_node = _node_id("platform", str(platform))
            add_node(platform_node, "platform", name=platform)
            add_edge(cap_node, "executes_on", platform_node)
        for failure in surface.get("failure_semantics", []):
            if failure in {"retry", "rollback", "fallback"}:
                recovery_node = _node_id("recovery", str(failure))
                add_node(recovery_node, "recovery_mechanism", name=failure)
                add_edge(cap_node, "recovers_via", recovery_node)
        event = (surface.get("interface") or {}).get("event")
        if event:
            event_node = _node_id("event", str(event))
            add_node(event_node, "event", name=event)
            add_edge(cap_node, "consumes", event_node)
        dimension_pressure[cid] = _required_dimensions(cap, surface)

    for baseline in baselines.get("baselines", []):
        repo = baseline["source_repo"]
        baseline_id = _node_id("baseline", f"{repo}:{baseline['manifest_path']}:{baseline['name']}")
        add_node(baseline_id, "baseline_candidate", classification=baseline["classification"], execution_status=baseline["execution_status"], command=baseline["command"])
        add_edge(_node_id("repo", repo), "has_baseline_candidate", baseline_id)

    for source in supply_chain.get("sources", []):
        repo = source["source_repo"]
        supply_node = _node_id("supply", repo)
        add_node(supply_node, "supply_chain_evidence", declared_license=source["declared_license"], license_status=source["license_verification"]["status"], lockfile_count=source["counts"]["lockfiles"])
        add_edge(_node_id("repo", repo), "described_by_supply_chain", supply_node)

    return {
        "schema_version": 1,
        "graph_type": "cp01_capability_dependency_graph",
        "supported_edge_types": SUPPORTED_EDGE_TYPES,
        "nodes": [nodes[key] for key in sorted(nodes)],
        "edges": [{"source": source, "relation": relation, "target": target} for source, relation, target in sorted(edges)],
        "cos20d_pressure": {key: dimension_pressure[key] for key in sorted(dimension_pressure)},
        "invariants": {
            "source_evidence_immutable": True,
            "provisional_decisions_cannot_authorize_migration": True,
            "cross_repo_capability_merge_performed": False,
            "all_capabilities_unverified": all(row["parity_status"] == "UNVERIFIED" for row in capabilities),
        }
    }


def gauntlet(graph: dict[str, Any], capabilities: list[dict[str, Any]], surfaces: list[dict[str, Any]], baselines: dict[str, Any], supply_chain: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    node_ids = {node["id"] for node in graph["nodes"]}
    edge_tuples = {(edge["source"], edge["relation"], edge["target"]) for edge in graph["edges"]}
    surface_ids = {row["surface_id"] for row in surfaces}
    capability_ids = {row["capability_id"] for row in capabilities}
    repos = {row["source_repo"] for row in capabilities}
    if repos != {"openjarvis", "openclaw", "omi", "clicky"}:
        errors.append(f"capability graph repo coverage mismatch: {sorted(repos)}")
    if len(capabilities) != len(surface_ids):
        errors.append("capability/surface count mismatch")
    for cap in capabilities:
        cap_node = _node_id("capability", cap["capability_id"])
        surface_node = _node_id("surface", cap["source_surface_id"])
        if cap_node not in node_ids or surface_node not in node_ids:
            errors.append(f"orphan capability mapping: {cap['capability_id']}")
            continue
        if (cap_node, "implemented_by", surface_node) not in edge_tuples:
            errors.append(f"missing implemented_by: {cap['capability_id']}")
        required = set(graph["cos20d_pressure"].get(cap["capability_id"], []))
        missing_core = CORE_20D - required
        if missing_core:
            errors.append(f"missing core COS20D pressure for {cap['capability_id']}: {sorted(missing_core)}")
        if cap["parity_status"] != "UNVERIFIED" or cap["equivalence_status"] != "UNPROVEN":
            errors.append(f"premature verification/equivalence: {cap['capability_id']}")
    baseline_repos = {row["source_repo"] for row in baselines.get("sources", [])}
    supply_repos = {row["source_repo"] for row in supply_chain.get("sources", [])}
    if baseline_repos != repos:
        errors.append("baseline coverage does not match capability repos")
    if supply_repos != repos:
        errors.append("supply-chain coverage does not match capability repos")
    if baselines.get("status") != "PASS":
        errors.append("W05 baseline matrix not PASS")
    if supply_chain.get("status") != "PASS":
        errors.append("W06 supply chain not PASS")
    for edge in graph["edges"]:
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            errors.append(f"edge points to missing node: {edge}")
    counts = Counter(edge["relation"] for edge in graph["edges"])
    return {
        "schema_version": 1,
        "phase": "I01-W07",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "counts": {
            "capabilities": len(capabilities),
            "surfaces": len(surfaces),
            "nodes": len(graph["nodes"]),
            "edges": len(graph["edges"]),
            "relations": dict(sorted(counts.items())),
        },
        "supported_edge_types": SUPPORTED_EDGE_TYPES,
        "invariants": graph["invariants"],
    }


def run_w07(
    capabilities_path: str | Path = "ledgers/CAPABILITY_LEDGER.jsonl",
    surfaces_path: str | Path = "inventory/surfaces/all.jsonl",
    baselines_path: str | Path = "evidence/cp01/baselines/baseline_matrix.json",
    supply_path: str | Path = "evidence/cp01/supply_chain.json",
    graph_path: str | Path = "graphs/capability_graph.json",
    gauntlet_path: str | Path = "evidence/cp01/gauntlet/w07_complete.json",
) -> dict[str, Any]:
    capabilities = read_jsonl(capabilities_path)
    surfaces = read_jsonl(surfaces_path)
    baselines = json.loads(Path(baselines_path).read_text(encoding="utf-8"))
    supply = json.loads(Path(supply_path).read_text(encoding="utf-8"))
    graph = build_graph(capabilities, surfaces, baselines, supply)
    check = gauntlet(graph, capabilities, surfaces, baselines, supply)
    graph_output = Path(graph_path)
    graph_output.parent.mkdir(parents=True, exist_ok=True)
    graph_output.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    gauntlet_output = Path(gauntlet_path)
    gauntlet_output.parent.mkdir(parents=True, exist_ok=True)
    gauntlet_output.write_text(json.dumps(check, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if check["status"] != "PASS":
        raise RuntimeError("W07 gauntlet failed: " + "; ".join(check["errors"]))
    return {"graph": graph, "gauntlet": check}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build CP01 capability dependency graph and COS20D completeness gauntlet")
    parser.parse_args()
    result = run_w07()
    print(json.dumps(result["gauntlet"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
