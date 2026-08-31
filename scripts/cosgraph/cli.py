from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.cosgraph.engine import build_cos_hypergraph


def main() -> int:
    parser = argparse.ArgumentParser(prog="cosgraphengine", description="Fuse Graphify outputs into a non-destructive COS integration hypergraph")
    parser.add_argument("--graph", action="append", required=True, help="Repository graph JSON; repeat for each upstream")
    parser.add_argument("--output", default="graphs/cos_hypergraph.json")
    args = parser.parse_args()
    graphs = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.graph]
    hypergraph = build_cos_hypergraph(graphs)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(hypergraph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"cosgraphengine: {len(hypergraph['source_nodes'])} source nodes / {len(hypergraph['canonical_components'])} canonical components -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
