from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.context.build_context_pack import AUTHORITY_READ_ORDER, CONTEXT_JSON, DIMENSIONS_JSON, build_context_pack


def validate_context_pack(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    context_path, dimensions_path = root / CONTEXT_JSON, root / DIMENSIONS_JSON
    if not context_path.is_file():
        return [f"missing ContextPack: {CONTEXT_JSON}"]
    if not dimensions_path.is_file():
        return [f"missing dimension registry: {DIMENSIONS_JSON}"]
    actual = json.loads(context_path.read_text(encoding="utf-8"))
    expected = build_context_pack(root)
    for key in ("schema_version", "protocol", "project", "frontier", "upstream_refs", "hard_invariants", "active_claims", "open_risks", "accepted_decision_ids", "evidence_ids", "required_next_outputs"):
        if actual.get(key) != expected.get(key):
            errors.append(f"ContextPack drift at top-level key {key}")
    dimensions = json.loads(dimensions_path.read_text(encoding="utf-8"))
    rows = dimensions.get("dimensions", [])
    ids = [row.get("id") for row in rows if isinstance(row, dict)]
    if len(rows) != 20 or len(set(ids)) != 20:
        errors.append(f"COS-20D registry must contain exactly 20 unique dimensions; got {len(rows)}")
    if {str(value).split("_", 1)[0] for value in ids} != {f"D{index:02d}" for index in range(20)}:
        errors.append("COS-20D ids must cover D00 through D19 exactly")
    for path in AUTHORITY_READ_ORDER:
        if not (root / path).is_file():
            errors.append(f"Context authority path missing: {path}")
    hard = actual.get("hard_invariants", {})
    for required_true in ("raw_graph_is_not_parity_denominator", "candidate_is_not_capability", "source_graph_is_immutable", "cos_decisions_are_provisional_until_promoted", "automatic_destructive_merge_forbidden", "migration_requires_behavioral_equivalence_evidence", "context_pack_is_derived_not_primary_truth"):
        if hard.get(required_true) is not True:
            errors.append(f"hard invariant must be true: {required_true}")
    if hard.get("chat_is_authority") is not False:
        errors.append("chat_is_authority must remain false")
    config = (root / ".agentic/CONFIG.yaml").read_text(encoding="utf-8")
    for token in (f"next_wave: {expected['frontier']['next_wave']}", "context_manifest: .agentic/context/CURRENT_CONTEXT.json", "dimension_registry: .agentic/context/COS20D.json", "context_validator: python scripts/context/validate_context_pack.py", "graph_engine: /cos-graph-engineV2"):
        if token not in config:
            errors.append(f".agentic/CONFIG.yaml missing canonical context token: {token}")
    return errors


def main() -> int:
    errors = validate_context_pack(ROOT)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: COS Graph Engine V2 ContextPack is consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
