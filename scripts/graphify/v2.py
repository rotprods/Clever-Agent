from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SURFACE_KINDS = {"route", "command", "registry", "plugin", "tool", "channel", "provider", "agent", "persistence", "memory", "media", "device", "security", "scheduler", "workflow", "service", "rpc", "mcp"}


def build_semantic_surface_projection(repository_graph: dict[str, Any]) -> dict[str, Any]:
    if repository_graph.get("graph_type") != "repository_graph":
        raise ValueError("Graphify V2 expects repository_graph input")
    nodes = {node["id"]: node for node in repository_graph.get("nodes", [])}
    declared_by: dict[str, list[dict[str, Any]]] = {}
    for edge in repository_graph.get("edges", []):
        if edge.get("relation") == "declares":
            declared_by.setdefault(str(edge["target"]), []).append({"path": edge.get("evidence_path"), "line": edge.get("evidence_line"), "edge_id": edge.get("id")})
    surfaces: list[dict[str, Any]] = []
    for node_id in sorted(nodes):
        node = nodes[node_id]
        kind = str(node.get("kind") or "")
        if kind not in SURFACE_KINDS:
            continue
        evidence = sorted(declared_by.get(node_id, []), key=lambda row: (str(row.get("path") or ""), int(row.get("line") or 0), str(row.get("edge_id") or "")))
        surfaces.append({"id": node["id"], "kind": kind, "name": node.get("name"), "source_repo": node.get("source_repo"), "source_commit": node.get("source_commit"), "path": node.get("path"), "line": node.get("line"), "language": node.get("language"), "metadata": node.get("metadata", {}), "evidence": evidence, "promotion_status": "DISCOVERED_CANDIDATE", "behavioral_evidence_required": True})
    kind_counts: dict[str, int] = {}
    for surface in surfaces:
        kind_counts[surface["kind"]] = kind_counts.get(surface["kind"], 0) + 1
    return {"schema_version": 1, "graph_type": "semantic_surface_projection", "projection_version": "GRAPHIFY-V2", "repo_id": repository_graph["repo_id"], "source_commit": repository_graph["source_commit"], "source_repository_graph_stats": {"node_count": len(repository_graph.get("nodes", [])), "edge_count": len(repository_graph.get("edges", []))}, "invariants": {"raw_repository_graph_unchanged": True, "candidate_is_not_capability": True, "promotion_requires_behavioral_evidence": True, "provenance_preserved": True}, "counts": {"surface_candidates": len(surfaces), "by_kind": dict(sorted(kind_counts.items()))}, "surfaces": surfaces}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compact Graphify V2 semantic surface projection")
    parser.add_argument("repository_graph")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    graph = json.loads(Path(args.repository_graph).read_text(encoding="utf-8"))
    projection = build_semantic_surface_projection(graph)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(projection["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
