"""Validate the evidence-backed CP03-W02 scope lock.

The lock freezes a proof scope, not the CP01 denominator and not parity.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = Path("inventory/cp03/W02_SCOPE_LOCK.json")
RECEIPT_PATH = Path("evidence/cp03/cp03-w02/W02-01/SCOPE_LOCK_RECEIPT.json")

from scripts.cp03 import w02_facets

class ScopeLockError(ValueError):
    pass

def require(ok: bool, message: str) -> None:
    if not ok:
        raise ScopeLockError(message)

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def load_lock(root: Path = ROOT) -> dict[str, Any]:
    value = json.loads((root / LOCK_PATH).read_text(encoding="utf-8"))
    require(isinstance(value, dict), "scope lock must be an object")
    return value

def validate_lock(lock: dict[str, Any], facets: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "schema_version": 1, "lock_id": "CP03-W02-SCOPE-LOCK-v1",
        "goal_id": "CLEVER-JARVIS-001", "checkpoint": "CP03", "iteration": "I03",
        "wave": "CP03-W02", "source_repo": "openjarvis",
        "source_commit": "72033b8ec288aa067ce4530ff9d96bf231e9c4e5",
        "global_denominator": 7565, "openjarvis_obligations": 646,
        "w02_proof_units": 47, "w02_owned_capabilities": 37, "w02_shared_capabilities": 10,
    }
    for key, value in expected.items():
        require(lock.get(key) == value, f"lock field drift: {key}")
    semantics = lock.get("semantics")
    require(isinstance(semantics, dict), "missing lock semantics")
    require(semantics.get("scope_frozen") is True, "lock must freeze scope")
    require(type(semantics.get("parity_promotions")) is int and semantics["parity_promotions"] == 0, "scope lock cannot promote parity")
    require(semantics.get("shared_terminal_forbidden") is True, "shared terminal guard missing")
    require(semantics.get("denominator_mutation_authorized") is False, "denominator mutation forbidden")
    review = lock.get("review")
    require(isinstance(review, dict), "missing review receipt")
    require(review.get("type") == "DETERMINISTIC_CLEAN_ROOM_VALIDATION", "invalid review type")
    require(review.get("human_review") is False and review.get("independent_human_review") is False, "do not fabricate human review")
    require(review.get("source_facet_evidence_id") == "EVID-W02-FACETS-20260907", "facet evidence drift")
    require(review.get("source_facet_run_id") == 34157458150, "facet run drift")
    require(review.get("source_facet_artifact_id") == 10031446909, "facet artifact drift")
    proof_ids, owned_ids, shared_ids = facets["w02_ids"], facets["owned_ids"], facets["shared_ids"]
    require(lock.get("proof_unit_ids") == proof_ids, "proof-unit ID drift")
    require(lock.get("owned_ids") == owned_ids, "owned-ID drift")
    require(lock.get("shared_ids") == shared_ids, "shared-ID drift")
    require(len(proof_ids) == 47 and len(owned_ids) == 37 and len(shared_ids) == 10, "scope count drift")
    require(not set(owned_ids) & set(shared_ids), "owned/shared overlap")
    require(set(owned_ids) | set(shared_ids) == set(proof_ids), "owned/shared union drift")
    products = w02_facets.products(facets)
    expected_hashes = lock.get("artifact_product_hashes")
    require(isinstance(expected_hashes, dict), "missing product hashes")
    mapping = {
        "W02_PROOF_UNITS.json": "reports/cp03/w02_facets/W02_PROOF_UNITS.json",
        "W02_OWNED.json": "reports/cp03/w02_facets/W02_OWNED.json",
        "W02_SHARED.json": "reports/cp03/w02_facets/W02_SHARED.json",
        "ENGINE_METHOD_MATRIX.json": "reports/cp03/w02_facets/ENGINE_METHOD_MATRIX.json",
        "FACET_SUMMARY.json": "reports/cp03/w02_facets/SUMMARY.json",
    }
    observed_hashes = {}
    for label, rel in mapping.items():
        require(rel in products, f"missing facet product: {rel}")
        digest = sha256_text(products[rel])
        observed_hashes[label] = digest
        require(expected_hashes.get(label) == digest, f"product hash drift: {label}")
    shared_rows = [r for r in facets["facet_rows"] if r["capability_id"] in set(shared_ids)]
    require(len(shared_rows) == 10, "shared row count drift")
    require(all(r["w02_terminal_ownership"] == "SHARED" for r in shared_rows), "shared capability became W02-owned")
    require(all(r["full_capability_verified_in_w02_allowed"] is False for r in shared_rows), "shared capability may not become terminal in W02")
    require(all(r["parity_status"] == "UNVERIFIED" for r in facets["facet_rows"]), "facet review cannot alter parity")
    method_rows = facets["method_matrix"]
    require(len(method_rows) == 8, "engine method count drift")
    require(len({row["canonical_test_id"] for row in method_rows}) == 8, "engine method test IDs collide")
    require(all(row["parity_promotion_before_test"] is False for row in method_rows), "method map cannot self-promote parity")
    return {
        "schema_version": 1, "status": "PASS", "lock_id": lock["lock_id"], "scope_frozen": True,
        "global_denominator": 7565, "openjarvis_obligations": 646, "w02_proof_units": 47,
        "w02_owned_capabilities": 37, "w02_shared_capabilities": 10,
        "shared_terminal_forbidden": True, "parity_promotions": 0, "verified": 0,
        "human_review": False, "review_type": "DETERMINISTIC_CLEAN_ROOM_VALIDATION",
        "product_hashes": observed_hashes,
        "lock_sha256": sha256_text(json.dumps(lock, indent=2, sort_keys=True) + "\n"),
    }

def validate_root(root: Path = ROOT) -> dict[str, Any]:
    return validate_lock(load_lock(root), w02_facets.compile_facets(root))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    try:
        receipt = validate_root(ROOT)
        if args.write_receipt:
            path = ROOT / RECEIPT_PATH
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "scope_frozen": False, "parity_promotions": 0, "error": str(exc)}, sort_keys=True))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
