"""Compile reviewed CP03-W02 facets over the immutable OpenJarvis denominator.

This is a P2 decision projection. It never mutates CP01 capability rows or parity.
"""
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
POLICY = Path("inventory/cp03/w02_facet_policy.json")
SCOPE_ENGINE = Path("reports/cp03/w02_scope/ENGINE_CONTRACT.json")
WAVES = {"W02","W03","W04","W05","W06","W07","W08"}

from scripts.cp03 import w02_scope

class FacetError(ValueError):
    pass

def require(ok: bool, msg: str) -> None:
    if not ok:
        raise FacetError(msg)

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",",":")) + "\n"

def validate_policy(policy: dict[str, Any], scope: dict[str, Any]) -> None:
    require(type(policy.get("schema_version")) is int and policy["schema_version"] == 1, "invalid facet schema")
    require(policy.get("authority") == "DERIVED_FACET_ASSIGNMENT_NOT_PARITY", "invalid facet authority")
    require(policy.get("source_commit") == scope["summary"]["upstream_commit"], "pin drift")
    require(policy.get("global_denominator") == 7565 and policy.get("openjarvis_obligations") == 646, "denominator drift")
    require(type(policy.get("parity_promotions")) is int and policy["parity_promotions"] == 0, "facet policy cannot promote parity")
    require(set(policy.get("facet_waves", [])) == WAVES, "wave set drift")
    route_mounts = policy.get("route_mounts")
    explicit = policy.get("explicit")
    require(isinstance(route_mounts, dict) and isinstance(explicit, dict), "missing facet mappings")
    require(set(route_mounts).isdisjoint(explicit), "duplicate mapping authority")
    require(len(route_mounts) == 29, "route mount review must cover 29 records")
    require(len(explicit) == 23, "explicit shared review must cover 23 records")
    all_specs = list(route_mounts.values()) + list(explicit.values()) + list(policy.get("additional_w02_dependencies",{}).values())
    for spec in all_specs:
        facets = spec.get("facets")
        require(isinstance(facets, list) and facets and len(facets)==len(set(facets)), "invalid facets")
        require(set(facets) <= WAVES, "unknown facet wave")
    contract = policy.get("engine_contract", {})
    require(contract.get("source_blob_sha") == "cd7dc0d4cc16d54058caa9af492f70d4b0ef76b2", "engine ABC blob drift")
    require(set(contract.get("methods",{})) == {"generate","stream","stream_full","list_models","health","can_serve","close","prepare"}, "engine method-set drift")
    test_ids = [v.get("test_id") for v in contract["methods"].values()]
    require(len(test_ids)==len(set(test_ids)) and all(isinstance(v,str) and v.startswith("W02-METHOD-") for v in test_ids), "method tests must be distinct")
    require(contract.get("stream_chunk_fields") == ["content","tool_calls","finish_reason","usage","content_blocks","tool_results"], "StreamChunk field drift")
    require(contract.get("response_format_fields") == ["type","schema"], "ResponseFormat field drift")

def compile_from(scope: dict[str, Any], policy: dict[str, Any], engine_source: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy, scope)
    allocations = {row["capability_id"]:row for row in scope["allocations"]}
    cross = {cid for cid,row in allocations.items() if row["disposition"]=="CROSS_WAVE_REVIEW"}
    mapped = set(policy["route_mounts"]) | set(policy["explicit"])
    require(mapped == cross, f"shared review mismatch missing={sorted(cross-mapped)} extra={sorted(mapped-cross)}")

    rows: list[dict[str, Any]] = []
    for cid in sorted(cross):
        source = allocations[cid]
        spec = policy["route_mounts"].get(cid) or policy["explicit"][cid]
        if cid in policy["route_mounts"]:
            require(source["surface_kind"]=="route_mount", f"route map points at non-mount {cid}")
            require(source["source_line"] == spec["line"], f"route mount line drift: {cid}")
            reason = f"mount resolves to {spec['router']}"
            router = spec["router"]
        else:
            require(source["surface_kind"]!="route_mount", f"explicit map hides route mount {cid}")
            require(isinstance(spec.get("reason"),str) and spec["reason"], f"missing reason {cid}")
            reason = spec["reason"]; router = None
        facets = spec["facets"]
        w02 = "W02" in facets
        rows.append({
            "capability_id":cid, "source_disposition":"CROSS_WAVE_REVIEW",
            "source_surface_id":source["source_surface_id"], "source_path":source["source_path"],
            "source_line":source["source_line"], "name":source["name"], "family_at_cp01":source["family_at_cp01"],
            "facets":facets, "router":router, "reason":reason,
            "w02_facet_required":w02,
            "w02_terminal_ownership":"OWNED" if facets==["W02"] else ("SHARED" if w02 else "NONE"),
            "full_capability_verified_in_w02_allowed": facets==["W02"],
            "parity_status":"UNVERIFIED"
        })

    additional: list[dict[str, Any]] = []
    for cid,spec in sorted(policy["additional_w02_dependencies"].items()):
        require(cid in allocations, f"additional dependency absent from denominator: {cid}")
        source=allocations[cid]
        require(source["disposition"] == spec["expected_original_disposition"], f"unexpected original allocation: {cid}")
        require(source["source_path"] == spec["source_path"] and source["source_line"] == spec["source_line"], f"additional dependency provenance drift: {cid}")
        require("W02" in spec["facets"], "additional W02 dependency must contain W02")
        additional.append({
            "capability_id":cid,"source_disposition":source["disposition"],"source_surface_id":source["source_surface_id"],
            "source_path":source["source_path"],"source_line":source["source_line"],"name":source["name"],
            "family_at_cp01":source["family_at_cp01"],"facets":spec["facets"],"reason":spec["reason"],
            "w02_facet_required":True,"w02_terminal_ownership":"SHARED",
            "full_capability_verified_in_w02_allowed":False,"parity_status":"UNVERIFIED",
            "review_delta":"ADDED_AS_W02_EVIDENCE_DEPENDENCY_NOT_DENOMINATOR_MUTATION"
        })

    core = [row for row in scope["allocations"] if row["disposition"]=="W02_CORE"]
    owned_review = [r for r in rows if r["w02_terminal_ownership"]=="OWNED"]
    shared_review = [r for r in rows if r["w02_terminal_ownership"]=="SHARED"]
    w02_ids = sorted({r["capability_id"] for r in core} |
                     {r["capability_id"] for r in rows if r["w02_facet_required"]} |
                     {r["capability_id"] for r in additional})
    require(len(w02_ids)==47, f"W02 proof-unit drift: expected 47 got {len(w02_ids)}")
    require(len(core)==32 and len(owned_review)==5 and len(shared_review)==9 and len(additional)==1, "review bucket drift")
    owned_ids = sorted({r["capability_id"] for r in core} | {r["capability_id"] for r in owned_review})
    shared_ids = sorted({r["capability_id"] for r in shared_review} | {r["capability_id"] for r in additional})
    require(len(owned_ids)==37 and len(shared_ids)==10 and not set(owned_ids)&set(shared_ids), "ownership count drift")
    facet_counts=Counter(f for r in rows+additional for f in r["facets"])

    methods_by_name={m["name"]:m for m in engine_source["methods"]}
    contract_policy=policy["engine_contract"]
    method_matrix=[]
    for name,spec in sorted(contract_policy["methods"].items()):
        observed=methods_by_name[name]
        expected_kind = ("abstract" if observed["abstract"] else
                         "default_true" if observed["default_returns_true"] else
                         "default_noop" if observed["default_noop"] else
                         "default_wrapper" if name=="stream_full" else "concrete_default")
        require(expected_kind==spec["kind"], f"engine method semantic drift: {name}")
        lanes=["L0_CONTRACT","L1_PINNED_NATIVE"]
        if name in {"generate","stream","stream_full","list_models","health","can_serve","prepare"}:
            lanes.append("L2_REAL_MODEL")
        method_matrix.append({
            "method":name,"source_line":observed["line"],"semantic_kind":spec["kind"],
            "canonical_test_id":spec["test_id"],"required_proof":spec["proof"],
            "required_lanes":lanes,
            "cp01_individual_surface_ids":observed["cp01_candidate_surface_ids"],
            "denominator_mutation_required":False,
            "parity_promotion_before_test":False
        })

    return {
      "summary":{
        "schema_version":1,"status":"FACET_REVIEW_COMPLETE_SCOPE_LOCK_CANDIDATE",
        "source_commit":scope["summary"]["upstream_commit"],"global_denominator":7565,
        "openjarvis_obligations":646,"original_w02_core":32,"cross_wave_review_resolved":52,
        "additional_w02_evidence_dependencies":1,
        "K_w02_proof_units":len(w02_ids),"K_w02_owned_capabilities":len(owned_ids),
        "K_w02_shared_capabilities":len(shared_ids),
        "scope_frozen":False,"freeze_ready":True,"independent_review_observed":False,
        "parity_promotions":0,"verified":0,
        "rule":"W02 may fully verify only owned capabilities; shared capabilities receive facet evidence and remain non-terminal until their other facets are proven."
      },
      "facet_rows":rows+additional,
      "w02_ids":w02_ids,"owned_ids":owned_ids,"shared_ids":shared_ids,
      "facet_counts":dict(sorted(facet_counts.items())),
      "method_matrix":method_matrix
    }

def compile_facets(root: Path = ROOT) -> dict[str, Any]:
    scope = w02_scope.compile_root(root)
    policy = load_json(root / POLICY)
    engine_source = load_json(root / SCOPE_ENGINE)
    return compile_from(scope, policy, engine_source)

def products(result: dict[str, Any]) -> dict[str,str]:
    base="reports/cp03/w02_facets/"
    return {
      base+"SUMMARY.json":canonical(result["summary"]),
      base+"FACETS.jsonl":"".join(canonical(r) for r in sorted(result["facet_rows"], key=lambda x:x["capability_id"])),
      base+"W02_PROOF_UNITS.json":canonical({"schema_version":1,"ids":result["w02_ids"],"count":len(result["w02_ids"])}),
      base+"W02_OWNED.json":canonical({"schema_version":1,"ids":result["owned_ids"],"count":len(result["owned_ids"])}),
      base+"W02_SHARED.json":canonical({"schema_version":1,"ids":result["shared_ids"],"count":len(result["shared_ids"])}),
      base+"ENGINE_METHOD_MATRIX.json":canonical({"schema_version":1,"methods":result["method_matrix"],"parity_promotions":0}),
      "graphs/cp03/w02_facets/FACET_GRAPH.json":canonical({
        "schema_version":1,"plane":"P2_COS20D_DECISION","promotion":"PROVISIONAL_REVIEWED",
        "nodes":[{"id":r["capability_id"],"kind":"capability"} for r in result["facet_rows"]]
              + [{"id":w,"kind":"wave_facet"} for w in sorted(WAVES)],
        "edges":[{"from":r["capability_id"],"to":f,"type":"requires_facet_evidence"} for r in result["facet_rows"] for f in r["facets"]],
        "parity_promotions":0
      })
    }

def main() -> int:
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--write",action="store_true")
    mode.add_argument("--check",action="store_true")
    args=parser.parse_args()
    try:
        result=compile_facets(ROOT); outputs=products(result)
        for rel,data in outputs.items():
            path=ROOT/rel
            if args.check:
                require(path.is_file() and path.read_text(encoding="utf-8")==data, f"generated drift: {rel}")
            elif args.write:
                path.parent.mkdir(parents=True,exist_ok=True); path.write_text(data,encoding="utf-8")
        print(json.dumps(result["summary"],sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print(json.dumps({"status":"FAIL","scope_frozen":False,"parity_promotions":0,"error":str(exc)},sort_keys=True))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
