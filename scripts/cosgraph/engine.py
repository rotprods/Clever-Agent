from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from scripts.cosgraph.model import COSLayer, IntegrationDecision


def _stable(prefix: str, *parts: object) -> str:
    raw = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}:{hashlib.sha256(raw.encode()).hexdigest()[:20]}"


def _tokens(node: dict[str, Any]) -> str:
    return " ".join(
        str(value).lower()
        for value in (node.get("kind"), node.get("name"), node.get("path"), node.get("language"))
        if value
    )


def classify_family(node: dict[str, Any]) -> str:
    text = _tokens(node)
    kind = str(node.get("kind", ""))

    # Explicit extractor types outrank lexical hints. This matters for state
    # convergence: a MemoryStore explicitly classified as persistence must not
    # be split away from a SessionStore merely because its name contains
    # "memory".
    if kind == "persistence":
        return "persistence"
    if kind == "channel":
        return "gateway_channel"
    if kind == "agent":
        return "agent_orchestration"
    if kind == "provider":
        return "inference"
    if kind == "device":
        return "device"
    if kind == "media":
        return "capture_voice"
    if kind == "security":
        return "security"
    if kind in {"tool", "plugin", "command", "registry"}:
        return "extension_tooling"
    if kind == "route":
        return "api_surface"
    if kind == "dependency":
        return "dependency"
    if kind == "manifest":
        return "build_workspace"

    if any(token in text for token in ("memory", "vector", "embedding", "knowledge", "qdrant", "neo4j", "faiss")):
        return "memory"
    if any(token in text for token in ("database", "sqlite", "redis", "firestore", "store", "repository")):
        return "persistence"
    if any(token in text for token in ("gateway", "channel", "discord", "slack", "telegram", "whatsapp", "websocket")):
        return "gateway_channel"
    if any(token in text for token in ("agent", "orchestrator", "planner", "react")):
        return "agent_orchestration"
    if any(token in text for token in ("inference", "provider", "model", "llm")):
        return "inference"
    if any(token in text for token in ("firmware", "bluetooth", "ble", "wearable", "esp32", "zephyr")):
        return "device"
    if any(token in text for token in ("audio", "speech", "voice", "capture", "transcri", "tts", "microphone")):
        return "capture_voice"
    if any(token in text for token in ("swiftui", "appkit", "overlay", "cursor", "screen", "desktop")):
        return "embodiment"
    if any(token in text for token in ("auth", "permission", "sandbox", "policy", "security", "pairing")):
        return "security"
    return "structural"


def classify_layer(node: dict[str, Any], family: str) -> COSLayer:
    mapping = {
        "memory": COSLayer.MEMORY_KNOWLEDGE,
        "persistence": COSLayer.DURABLE_STATE,
        "gateway_channel": COSLayer.CHANNEL_GATEWAY,
        "agent_orchestration": COSLayer.INTENT_ROUTING,
        "inference": COSLayer.PROVIDER_BOUNDARY,
        "device": COSLayer.DEVICE_RUNTIME,
        "capture_voice": COSLayer.CAPABILITY,
        "embodiment": COSLayer.EMBODIMENT_EXPERIENCE,
        "security": COSLayer.GOVERNANCE_SECURITY,
        "extension_tooling": COSLayer.CAPABILITY,
        "api_surface": COSLayer.INVOCATION,
        "dependency": COSLayer.PROVIDER_BOUNDARY,
        "build_workspace": COSLayer.PROVIDER_BOUNDARY,
        "structural": COSLayer.CAPABILITY,
    }
    return mapping[family]


def _decision(family: str, source_repos: set[str], nodes: list[dict[str, Any]]) -> IntegrationDecision:
    languages = {node.get("language") for node in nodes if node.get("language")}
    text = " ".join(_tokens(node) for node in nodes)
    platform_specialized = bool(languages & {"swift", "dart", "c", "cpp"}) or any(
        token in text for token in ("firmware", "appkit", "swiftui", "screenkit", "bluetooth", "ble", "wearable")
    )
    if family in {"device", "embodiment", "capture_voice"} and platform_specialized:
        return IntegrationDecision.KEEP_NATIVE
    if family in {"memory", "persistence"} and len(source_repos) > 1:
        return IntegrationDecision.MERGE_STATE
    if len(source_repos) > 1 and family not in {"structural", "dependency", "build_workspace"}:
        return IntegrationDecision.CANONICALIZE
    return IntegrationDecision.ADAPT


def build_cos_hypergraph(repository_graphs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    graphs = list(repository_graphs)
    source_nodes: list[dict[str, Any]] = []
    source_edges: list[dict[str, Any]] = []
    for graph in graphs:
        if graph.get("graph_type") != "repository_graph":
            raise ValueError("COSGraphEngine accepts only repository_graph inputs")
        source_nodes.extend(graph.get("nodes", []))
        source_edges.extend(graph.get("edges", []))

    facets: list[dict[str, Any]] = []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for node in source_nodes:
        family = classify_family(node)
        layer = classify_layer(node, family)
        facet = {
            "id": _stable("facet", node["id"], family, layer.value),
            "source_node": node["id"],
            "source_repo": node["source_repo"],
            "family": family,
            "cos_layer": layer.value,
        }
        facets.append(facet)
        if node.get("kind") not in {"file", "repository", "dependency", "manifest"}:
            interface_kind = str(node.get("kind") or "unknown")
            groups.setdefault((family, interface_kind), []).append(node)

    components: list[dict[str, Any]] = []
    for (family, interface_kind), nodes in sorted(groups.items()):
        repos = {str(node["source_repo"]) for node in nodes}
        decision = _decision(family, repos, nodes)
        components.append(
            {
                "id": _stable("component", family, interface_kind, sorted(node["id"] for node in nodes)),
                "family": family,
                "interface_kind": interface_kind,
                "source_repositories": sorted(repos),
                "source_nodes": sorted(node["id"] for node in nodes),
                "decision": decision.value,
                "rewrite_allowed": False,
                "rule": "preserve every upstream implementation; canonical components are integration overlays, not destructive deduplication",
            }
        )

    relations = [
        {
            "id": _stable("hyperedge", facet["source_node"], facet["id"]),
            "relation": "classified_as",
            "members": [facet["source_node"], facet["id"]],
        }
        for facet in facets
    ]
    return {
        "schema_version": 1,
        "graph_type": "cos_hypergraph",
        "cos_model": "COS-20L-v0.1-CP01",
        "source_graphs": sorted(
            {f"{graph['repo_id']}@{graph['source_commit']}" for graph in graphs}
        ),
        "invariants": {
            "source_nodes_preserved": len(source_nodes),
            "automatic_rewrite_forbidden": True,
            "canonicalization_is_non_destructive": True,
        },
        "source_nodes": sorted(source_nodes, key=lambda node: node["id"]),
        "source_edges": sorted(source_edges, key=lambda edge: edge["id"]),
        "cos_facets": sorted(facets, key=lambda facet: facet["id"]),
        "canonical_components": components,
        "hyperedges": sorted(relations, key=lambda edge: edge["id"]),
    }
