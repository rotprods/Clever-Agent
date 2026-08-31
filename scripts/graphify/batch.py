from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.cosgraph.engine import build_cos_hypergraph
from scripts.cosgraph.report import summarize_hypergraph
from scripts.graphify.engine import graphify_repository
from scripts.upstream.ledger import load_upstream_pins


def main() -> int:
    parser = argparse.ArgumentParser(description="Graphify every pinned upstream and build the COS hypergraph")
    parser.add_argument("--ledger", default="UPSTREAM_LEDGER.yaml")
    parser.add_argument("--cache", default=".cache/upstreams")
    parser.add_argument("--graphs", default="graphs/upstreams")
    parser.add_argument("--cos-output", default="graphs/cos_hypergraph.json")
    parser.add_argument("--report", default="reports/cp01/cos_graph_summary.json")
    args = parser.parse_args()

    graph_dir = Path(args.graphs)
    graph_dir.mkdir(parents=True, exist_ok=True)
    graph_payloads: list[dict] = []
    for pin in load_upstream_pins(args.ledger):
        repository = Path(args.cache) / pin.id
        graph = graphify_repository(repository, pin.id, pin.pinned_commit)
        payload = graph.to_dict()
        output = graph_dir / f"{pin.id}.json"
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        graph_payloads.append(payload)
        print(f"graphify: {pin.id}: {len(payload['nodes'])} nodes / {len(payload['edges'])} edges")

    hypergraph = build_cos_hypergraph(graph_payloads)
    cos_output = Path(args.cos_output)
    cos_output.parent.mkdir(parents=True, exist_ok=True)
    cos_output.write_text(json.dumps(hypergraph, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = summarize_hypergraph(hypergraph)
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
