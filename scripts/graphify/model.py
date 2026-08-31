from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any


def stable_id(namespace: str, *parts: object) -> str:
    payload = json.dumps(parts, ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return f"{namespace}:{digest}"


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    kind: str
    name: str
    source_repo: str
    source_commit: str
    path: str | None = None
    line: int | None = None
    language: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "name": self.name,
            "source_repo": self.source_repo,
            "source_commit": self.source_commit,
            "path": self.path,
            "line": self.line,
            "language": self.language,
            "metadata": dict(sorted(self.metadata.items())),
        }


@dataclass(frozen=True, slots=True)
class Edge:
    id: str
    relation: str
    source: str
    target: str
    evidence_path: str | None = None
    evidence_line: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "relation": self.relation,
            "source": self.source,
            "target": self.target,
            "evidence_path": self.evidence_path,
            "evidence_line": self.evidence_line,
            "metadata": dict(sorted(self.metadata.items())),
        }


class RepositoryGraph:
    def __init__(self, repo_id: str, source_commit: str) -> None:
        self.repo_id = repo_id
        self.source_commit = source_commit
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, Edge] = {}
        self.metadata: dict[str, Any] = {}

    def add_node(self, node: Node) -> None:
        existing = self.nodes.get(node.id)
        if existing is not None and existing != node:
            raise ValueError(f"node id collision: {node.id}")
        self.nodes[node.id] = node

    def add_edge(self, relation: str, source: str, target: str, *, path: str | None = None, line: int | None = None, metadata: dict[str, Any] | None = None) -> Edge:
        if source not in self.nodes or target not in self.nodes:
            raise ValueError(f"edge references missing node: {source} -> {target}")
        edge_id = stable_id("edge", relation, source, target, path, line, metadata or {})
        edge = Edge(edge_id, relation, source, target, path, line, metadata or {})
        self.edges[edge.id] = edge
        return edge

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "graph_type": "repository_graph",
            "repo_id": self.repo_id,
            "source_commit": self.source_commit,
            "metadata": dict(sorted(self.metadata.items())),
            "nodes": [self.nodes[key].to_dict() for key in sorted(self.nodes)],
            "edges": [self.edges[key].to_dict() for key in sorted(self.edges)],
        }
