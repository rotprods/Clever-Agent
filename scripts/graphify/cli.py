from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.graphify.engine import graphify_repository


def main() -> int:
    parser = argparse.ArgumentParser(prog="graphify", description="Compile a pinned repository checkout into a deterministic evidence graph")
    parser.add_argument("root")
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    graph = graphify_repository(args.root, args.repo_id, args.commit)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"graphify: {args.repo_id}: {len(graph.nodes)} nodes / {len(graph.edges)} edges -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
