from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PIN = "72033b8ec288aa067ce4530ff9d96bf231e9c4e5"

GATED_MARKERS = {
    "live": "NETWORK_OR_RUNTIME_GATED",
    "cloud": "CREDENTIAL_NETWORK_GATED",
    "hub": "NETWORK_DATASET_GATED",
    "docker": "DOCKER_SOCKET_GATED",
    "apple": "APPLE_HARDWARE_GATED",
    "macos15": "APPLE_PLATFORM_GATED",
    "nvidia": "NVIDIA_HARDWARE_GATED",
    "amd": "AMD_HARDWARE_GATED",
    "live_channel": "CHANNEL_CREDENTIAL_GATED",
    "live_external": "EXTERNAL_FRAMEWORK_GATED",
    "modal": "REMOTE_CREDENTIAL_GATED",
}


def _int(value: str | None) -> int:
    return int(value or 0)


def parse_junit(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time_seconds": 0.0}
    for suite in suites:
        totals["tests"] += _int(suite.get("tests"))
        totals["failures"] += _int(suite.get("failures"))
        totals["errors"] += _int(suite.get("errors"))
        totals["skipped"] += _int(suite.get("skipped"))
        totals["time_seconds"] += float(suite.get("time") or 0.0)
    return totals


def build_report(*, junit: Path, metadata: dict[str, Any], exit_code: int) -> dict[str, Any]:
    results = parse_junit(junit)
    errors: list[str] = []
    if metadata.get("source_commit") != PIN:
        errors.append("upstream pin mismatch")
    if metadata.get("network_mode") != "none":
        errors.append("test execution was not network-disabled")
    if not metadata.get("read_only_root"):
        errors.append("test execution root was not read-only")
    if metadata.get("secrets_forwarded"):
        errors.append("secrets were forwarded to upstream test process")
    if results["tests"] <= 0:
        errors.append("hermetic baseline executed zero tests")
    if exit_code != 0 or results["failures"] or results["errors"]:
        errors.append("hermetic upstream test subset failed")
    selected = list(metadata.get("selected_tests", []))
    if not selected:
        errors.append("no baseline scopes selected")
    return {
        "schema_version": 1,
        "checkpoint": "CP03",
        "wave": "CP03-W00",
        "source_repo": "openjarvis",
        "source_commit": PIN,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "execution": {
            "container_image_id": metadata.get("container_image_id", ""),
            "python": metadata.get("python", "3.12"),
            "network_mode": metadata.get("network_mode"),
            "read_only_root": bool(metadata.get("read_only_root")),
            "cap_drop_all": bool(metadata.get("cap_drop_all")),
            "no_new_privileges": bool(metadata.get("no_new_privileges")),
            "secrets_forwarded": bool(metadata.get("secrets_forwarded")),
            "selected_tests": selected,
            "marker_expression": metadata.get("marker_expression", ""),
            "exit_code": exit_code,
        },
        "results": results,
        "gated_markers": [
            {"marker": marker, "classification": classification, "execution_status": "NOT_RUN"}
            for marker, classification in sorted(GATED_MARKERS.items())
        ],
        "invariants": {
            "not_run_is_not_pass": True,
            "network_disabled_during_tests": metadata.get("network_mode") == "none",
            "secret_free": not bool(metadata.get("secrets_forwarded")),
            "read_only_source": bool(metadata.get("read_only_root")),
            "platform_gaps_do_not_count_as_verified": True,
        },
    }


def materialize(junit: Path, metadata_path: Path, exit_code: int, root: Path = ROOT) -> dict[str, Any]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    report = build_report(junit=junit, metadata=metadata, exit_code=exit_code)
    evidence = root / "evidence/cp03/baseline/OPENJARVIS_HERMETIC_BASELINE.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    reports = root / "reports/cp03"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "OPENJARVIS_BASELINE.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (reports / "OPENJARVIS_PLATFORM_GAPS.json").write_text(json.dumps({"schema_version":1,"source_commit":PIN,"gated_markers":report["gated_markers"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    r = report["results"]
    (reports / "OPENJARVIS_BASELINE.md").write_text(
        "# OpenJarvis Hermetic Baseline\n\n"
        f"- Pin: `{PIN}`\n"
        f"- Status: `{report['status']}`\n"
        f"- Tests: `{r['tests']}`; failures `{r['failures']}`; errors `{r['errors']}`; skipped `{r['skipped']}`\n"
        f"- Network during tests: `{report['execution']['network_mode']}`\n"
        f"- Read-only root: `{report['execution']['read_only_root']}`\n"
        f"- Secrets forwarded: `{report['execution']['secrets_forwarded']}`\n\n"
        "Gated hardware/cloud/live suites remain NOT_RUN and do not count as parity.\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--exit-code", required=True, type=int)
    args = parser.parse_args()
    report = materialize(Path(args.junit), Path(args.metadata), args.exit_code)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
