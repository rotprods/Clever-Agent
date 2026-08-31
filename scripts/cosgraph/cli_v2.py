from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.cosgraph.v2 import build_cos20d_decision_graph


def main() -> int:
    parser = argparse.ArgumentParser(description="Build COS Graph Engine V2 20D decision graph")
    parser.add_argument("cos_hypergraph")
    parser.add_argument("--output", required=True)
    parser.add_argument("--goal-id", default="CLEVER-JARVIS-001")
    parser.add_argument("--checkpoint-id", default="CP01")
    parser.add_argument("--wave-id")
    args = parser.parse_args()
    source = json.loads(Path(args.cos_hypergraph).read_text(encoding="utf-8"))
    result = build_cos20d_decision_graph(source, goal_id=args.goal_id, checkpoint_id=args.checkpoint_id, wave_id=args.wave_id)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
