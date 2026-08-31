from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from scripts.cp01.capabilities import read_jsonl


def _load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _contract_requirements(capabilities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    families = Counter(row["family"] for row in capabilities)
    requirements: list[dict[str, Any]] = [
        {"id": "C02-IDENTITY", "contract": "identity/device/session/goal", "reason": "cross-runtime continuity requires one subject/device/session/goal namespace", "pressure_families": ["session_identity", "device_wearable", "agent"]},
        {"id": "C02-EVENT", "contract": "event envelope + provenance/correlation/causation", "reason": "federated runtimes need causal, replayable event semantics", "pressure_families": ["channel_gateway", "scheduler_automation", "worker_service"]},
        {"id": "C02-CAPABILITY", "contract": "capability contribution registry", "reason": "combine OpenJarvis typed primitives with OpenClaw contribution/lifecycle/rollback semantics", "pressure_families": ["agent", "tool", "inference", "plugin_extension", "channel_gateway"]},
        {"id": "C02-ACTION", "contract": "policy/action/authorization/idempotency/receipt", "reason": "side effects require explicit policy and replay-safe receipts", "pressure_families": ["tool", "channel_gateway", "scheduler_automation", "device_wearable"]},
        {"id": "C02-MEMORY", "contract": "memory provenance/retention/access/state ownership", "reason": "memory and persistence must converge without silent state loss", "pressure_families": ["memory_persistence"]},
        {"id": "C02-RUNTIME", "contract": "runtime health/degradation/lifecycle/recovery", "reason": "native adapters remain specialized and need observable lifecycle contracts", "pressure_families": ["worker_service", "plugin_extension", "device_wearable"]},
        {"id": "C02-TRACE", "contract": "trace/evidence/evaluation", "reason": "parity and learning need correlation from invocation through evidence", "pressure_families": ["learning_evaluation", "agent", "inference"]},
        {"id": "C02-EMBODIMENT", "contract": "perception/device/embodiment handoff", "reason": "Omi ambient perception and Clicky desktop embodiment must share identity/session while preserving native UX", "pressure_families": ["capture_perception", "speech_audio", "embodiment", "device_wearable"]},
    ]
    for row in requirements:
        row["evidence_count"] = sum(families.get(family, 0) for family in row["pressure_families"])
        row["required"] = row["evidence_count"] > 0 or row["id"] in {"C02-IDENTITY", "C02-EVENT", "C02-CAPABILITY", "C02-ACTION", "C02-TRACE"}
    return requirements


def _render_report(candidate_sha: str, w03: dict[str, Any], denominator: dict[str, Any], baseline: dict[str, Any], supply: dict[str, Any], w07: dict[str, Any]) -> str:
    lines = [
        "# CP01 Capability Report", "",
        f"- Candidate SHA: `{candidate_sha}`",
        f"- W03 total semantic surfaces: `{w03['surface_summary']['surface_count']}`",
        f"- W03 behavior-mapped / denominator-eligible: `{denominator['denominator_eligible_surface_count']}`",
        f"- W03 candidate-only definitions retained outside denominator: `{denominator['deferred_candidate_surface_count']}`",
        f"- W04 capability denominator: `{denominator['denominator']}`",
        f"- Clever VERIFIED at CP01: `{denominator['verified']}`",
        f"- Denominator status: `{denominator['denominator_status']}`",
        f"- W07 graph nodes/edges: `{w07['counts']['nodes']}` / `{w07['counts']['edges']}`",
        "", "## Capability denominator by upstream", "", "| Upstream | Capabilities |", "|---|---:|",
    ]
    for repo, count in denominator["by_repo"].items():
        lines.append(f"| {repo} | {count} |")
    lines.extend(["", "## Capability families", "", "| Family | Count |", "|---|---:|"])
    for family, count in denominator["by_family"].items():
        lines.append(f"| {family} | {count} |")
    lines.extend(["", "## Baseline status", "", "Upstream commands were discovered and gated. CP01 does **not** execute untrusted upstream code without a hardened hermetic sandbox; `NOT_RUN` is never PASS.", ""])
    for source in baseline["sources"]:
        lines.append(f"- `{source['source_repo']}`: {source['candidate_count']} candidates · {source['classifications']}")
    lines.extend(["", "## Supply-chain status", ""])
    for source in supply["sources"]:
        lines.append(f"- `{source['source_repo']}`: license `{source['declared_license']}` → `{source['license_verification']['status']}`; {source['counts']['lockfiles']} lockfiles; {source['counts']['manifests']} manifests")
    lines.extend(["", "## Release interpretation", "", "CP01 proves a reproducible behavior-mapped capability denominator and retains candidate-only symbol evidence outside that denominator. It does **not** claim Clever-Agent adapter parity is complete. Candidate definitions remain available for future gauntlets; they are not silently discarded. No capability may be removed from the denominator because it is inconvenient to integrate.", ""])
    return "\n".join(lines)


def _render_contracts(requirements: list[dict[str, Any]]) -> str:
    lines = ["# CP02 Contract Requirements — derived from CP01", "", "These requirements are generated from the CP01 capability families. They define contract pressure, not final API syntax.", ""]
    for row in requirements:
        lines.extend([f"## {row['id']} — {row['contract']}", "", f"- Required: `{str(row['required']).lower()}`", f"- Evidence pressure count: `{row['evidence_count']}`", f"- Families: `{', '.join(row['pressure_families'])}`", f"- Reason: {row['reason']}", ""])
    lines.extend(["## CP02 implementation gate", "", "Define versioned schemas first, generate Rust/Python/TypeScript/Swift bindings, then require round-trip and version-skew tests before implementing the Rust kernel scaffold. Native upstream runtimes stay behind adapters until parity evidence permits convergence.", ""])
    return "\n".join(lines)


def run_w08(candidate_sha: str = "UNKNOWN") -> dict[str, Any]:
    w03 = _load("reports/cp01/w03_surface_summary.json")
    denominator = _load("reports/cp01/capability_denominator.json")
    w04 = _load("evidence/cp01/gauntlet/w04_denominator.json")
    baseline = _load("evidence/cp01/baselines/baseline_matrix.json")
    supply = _load("evidence/cp01/supply_chain.json")
    w07 = _load("evidence/cp01/gauntlet/w07_complete.json")
    capabilities = read_jsonl("ledgers/CAPABILITY_LEDGER.jsonl")
    errors: list[str] = []
    if denominator.get("denominator", 0) <= 0:
        errors.append("capability denominator is empty")
    if denominator.get("denominator") != len(capabilities):
        errors.append("denominator does not match capability ledger")
    if w03.get("surface_summary", {}).get("surface_count") != denominator.get("source_surface_count"):
        errors.append("W03 total surface count is not fully accounted by W04")
    if denominator.get("source_surface_count") != denominator.get("denominator") + denominator.get("deferred_candidate_surface_count"):
        errors.append("eligible + deferred surface partition does not close")
    for name, phase in (("W04", w04), ("W05", baseline), ("W06", supply), ("W07", w07)):
        if phase.get("status") != "PASS":
            errors.append(f"{name} not PASS")
    if set(denominator.get("by_repo", {})) != {"openjarvis", "openclaw", "omi", "clicky"}:
        errors.append("denominator does not cover all upstreams")
    requirements = _contract_requirements(capabilities)
    candidate = {
        "schema_version": 1, "phase": "I01-W08", "status": "PASS" if not errors else "FAIL",
        "candidate_sha": candidate_sha, "cp01_ready_for_state_transition": not errors, "errors": errors,
        "source_surface_count": denominator["source_surface_count"], "denominator": denominator["denominator"],
        "deferred_candidate_surface_count": denominator["deferred_candidate_surface_count"], "verified": denominator["verified"],
        "source_counts": denominator["by_repo"], "contract_requirement_ids": [row["id"] for row in requirements if row["required"]],
        "hard_invariants": {"not_run_is_not_pass": baseline["execution_policy"]["not_run_is_pass"] is False, "candidate_definition_is_not_capability": denominator["rules"]["candidate_definition_is_not_capability"], "cross_repo_auto_dedupe": denominator["rules"]["cross_repo_auto_dedupe"], "migration_authorized": False, "cp01_parity_claimed_complete": False}
    }
    Path("reports").mkdir(parents=True, exist_ok=True)
    Path("reports/CP01_CAPABILITY_REPORT.md").write_text(_render_report(candidate_sha, w03, denominator, baseline, supply, w07), encoding="utf-8")
    Path("reports/CP02_CONTRACT_REQUIREMENTS.md").write_text(_render_contracts(requirements), encoding="utf-8")
    Path("evidence/cp01").mkdir(parents=True, exist_ok=True)
    Path("evidence/cp01/CP01_RELEASE_CANDIDATE.json").write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        raise RuntimeError("CP01 release candidate failed: " + "; ".join(errors))
    return {"candidate": candidate, "requirements": requirements}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile CP01 release candidate and CP02 evidence-derived requirements")
    parser.add_argument("--candidate-sha", default="UNKNOWN")
    args = parser.parse_args()
    result = run_w08(args.candidate_sha)
    print(json.dumps(result["candidate"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
