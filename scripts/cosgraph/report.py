from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any


def summarize_hypergraph(hypergraph: dict[str, Any]) -> dict[str, Any]:
    by_repo: dict[str, Counter[str]] = defaultdict(Counter)
    kinds: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    for node in hypergraph.get("source_nodes", []):
        repo = str(node.get("source_repo") or "unknown")
        kind = str(node.get("kind") or "unknown")
        by_repo[repo][kind] += 1
        kinds[kind] += 1
        if node.get("language"):
            languages[str(node["language"])] += 1

    families = Counter(str(item["family"]) for item in hypergraph.get("cos_facets", []))
    layers = Counter(str(item["cos_layer"]) for item in hypergraph.get("cos_facets", []))
    decisions = Counter(str(item["decision"]) for item in hypergraph.get("canonical_components", []))
    cross_repo = []
    for component in hypergraph.get("canonical_components", []):
        repos = component.get("source_repositories", [])
        if len(repos) > 1:
            cross_repo.append(
                {
                    "id": component["id"],
                    "family": component["family"],
                    "interface_kind": component["interface_kind"],
                    "decision": component["decision"],
                    "source_repositories": repos,
                    "source_node_count": len(component.get("source_nodes", [])),
                }
            )
    cross_repo.sort(key=lambda item: (-len(item["source_repositories"]), item["family"], item["interface_kind"]))

    return {
        "schema_version": 1,
        "cos_model": hypergraph.get("cos_model"),
        "source_graphs": hypergraph.get("source_graphs", []),
        "totals": {
            "source_nodes": len(hypergraph.get("source_nodes", [])),
            "source_edges": len(hypergraph.get("source_edges", [])),
            "cos_facets": len(hypergraph.get("cos_facets", [])),
            "canonical_components": len(hypergraph.get("canonical_components", [])),
            "cross_repo_components": len(cross_repo),
        },
        "node_kinds": dict(sorted(kinds.items())),
        "languages": dict(sorted(languages.items())),
        "cos_families": dict(sorted(families.items())),
        "cos_layers": dict(sorted(layers.items())),
        "integration_decisions": dict(sorted(decisions.items())),
        "repositories": {
            repo: dict(sorted(counter.items())) for repo, counter in sorted(by_repo.items())
        },
        "cross_repo_components": cross_repo,
        "invariants": hypergraph.get("invariants", {}),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Summarize a COS hypergraph")
    parser.add_argument("hypergraph")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    hypergraph = json.loads(Path(args.hypergraph).read_text(encoding="utf-8"))
    summary = summarize_hypergraph(hypergraph)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
