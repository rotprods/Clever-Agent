from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

from scripts.upstream.ledger import UpstreamPin, load_upstream_pins

INTERESTING_SCRIPT = re.compile(r"(?:^|:)(test|check|lint|typecheck|build|verify|bench|e2e|integration)(?:$|:|-)", re.IGNORECASE)
HARDWARE_TOKENS = ("firmware", "wearable", "device", "ble", "bluetooth", "zephyr", "esp32")
CREDENTIAL_TOKENS = ("api_key", "apikey", "token", "credential", "secret", "oauth", "auth")
NETWORK_TOKENS = ("integration", "e2e", "live", "remote", "network")
PLATFORM_COMMAND_TOKENS = ("xcodebuild", "simctl", "ios", "macos", "swift test", "flutter test", "dart test")


def _classify(pin: UpstreamPin, path: str, command: str) -> tuple[str, str]:
    value = f"{path} {command}".lower()
    if any(token in value for token in HARDWARE_TOKENS):
        return "HARDWARE_GATED", "requires device/firmware/wearable toolchain or hardware"
    if any(token in value for token in CREDENTIAL_TOKENS):
        return "CREDENTIAL_GATED", "command or path indicates credentials/auth requirements"
    if pin.id == "clicky" and (path.endswith(".swift") or "xcode" in value or "swift" in value):
        return "PLATFORM_GATED", "macOS/Apple-native baseline cannot run on Ubuntu CP01 runner"
    if any(token in value for token in PLATFORM_COMMAND_TOKENS):
        return "PLATFORM_GATED", "platform/toolchain-specific baseline"
    if any(token in value for token in NETWORK_TOKENS):
        return "NETWORK_GATED", "integration/live baseline may contact external services"
    return "UNTRUSTED_EXECUTION_GATED", "upstream code is untrusted; CP01 runner has no hardened hermetic execution sandbox"


def _candidate(pin: UpstreamPin, path: str, name: str, command: str, source: str) -> dict[str, Any]:
    classification, reason = _classify(pin, path, command)
    return {
        "source_repo": pin.id,
        "source_commit": pin.pinned_commit,
        "manifest_path": path,
        "name": name,
        "command": command,
        "source": source,
        "classification": classification,
        "execution_status": "NOT_RUN",
        "gate_reason": reason,
    }


def _package_json_candidates(root: Path, pin: UpstreamPin) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(root.rglob("package.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        scripts = payload.get("scripts", {})
        if not isinstance(scripts, dict):
            continue
        relative = path.relative_to(root).as_posix()
        for name, command in sorted(scripts.items()):
            if isinstance(command, str) and INTERESTING_SCRIPT.search(str(name)):
                out.append(_candidate(pin, relative, str(name), command, "package.json:scripts"))
    return out


def _python_candidates(root: Path, pin: UpstreamPin, structural: dict[str, Any]) -> list[dict[str, Any]]:
    tests = structural.get("test_files", [])
    if not any(str(path).endswith((".py", ".pyi")) for path in tests):
        return []
    manifests = [
        str(path)
        for path in structural.get("manifests", [])
        if str(path).endswith(("pyproject.toml", "requirements.txt")) or "requirements" in Path(str(path)).name
    ]
    manifest = next((path for path in manifests if path.endswith("pyproject.toml")), manifests[0] if manifests else "<inferred-from-python-tests>")
    return [_candidate(pin, manifest, "python-tests", "python -m pytest", "structural:test_files")]


def _xcode_project_path(manifest: str) -> str | None:
    suffix = ".xcodeproj/project.pbxproj"
    if not manifest.endswith(suffix):
        return None
    return manifest[: -len("/project.pbxproj")] if manifest.endswith("/project.pbxproj") else None


def _toolchain_candidates(root: Path, pin: UpstreamPin, structural: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    manifests = {str(path) for path in structural.get("manifests", [])}
    for manifest in sorted(manifests):
        name = PurePosixPath(manifest).name
        xcode_project = _xcode_project_path(manifest)
        if xcode_project:
            out.append(_candidate(pin, manifest, "xcode-project", f"xcodebuild -project {xcode_project} -list", "xcodeproj:project.pbxproj"))
        elif name == "Cargo.toml":
            out.append(_candidate(pin, manifest, "rust-tests", "cargo test --workspace", "Cargo.toml"))
        elif name == "pubspec.yaml":
            command = "flutter test" if "app" in manifest.lower() else "dart test"
            out.append(_candidate(pin, manifest, "dart-flutter-tests", command, "pubspec.yaml"))
        elif name == "Package.swift":
            out.append(_candidate(pin, manifest, "swift-tests", "swift test", "Package.swift"))
        elif name in {"west.yml", "platformio.ini"}:
            out.append(_candidate(pin, manifest, "firmware-build", "platform-specific firmware build/test", name))
    return out


def discover_repo_baselines(root: Path, pin: UpstreamPin, structural: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _package_json_candidates(root, pin)
    rows.extend(_python_candidates(root, pin, structural))
    rows.extend(_toolchain_candidates(root, pin, structural))
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        unique[(row["manifest_path"], row["name"], row["command"])] = row
    return [unique[key] for key in sorted(unique)]


def run_w05(
    ledger: str | Path = "UPSTREAM_LEDGER.yaml",
    source_root: str | Path = ".cache/upstreams",
    structural_root: str | Path = "inventory/upstreams",
    output_path: str | Path = "evidence/cp01/baselines/baseline_matrix.json",
) -> dict[str, Any]:
    source = Path(source_root)
    structural = Path(structural_root)
    all_rows: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []
    for pin in load_upstream_pins(ledger):
        inventory_path = structural / f"{pin.id}.json"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        rows = discover_repo_baselines(source / pin.id, pin, inventory)
        if not rows:
            rows = [_candidate(pin, "<structural-inventory>", "no-runnable-baseline-discovered", "<none>", "structural")]
            rows[0]["classification"] = "NOT_APPLICABLE"
            rows[0]["gate_reason"] = "no test/build command discovered from supported manifests"
        all_rows.extend(rows)
        counts = Counter(row["classification"] for row in rows)
        source_summaries.append({"source_repo": pin.id, "candidate_count": len(rows), "classifications": dict(sorted(counts.items()))})
    errors: list[str] = []
    if {row["source_repo"] for row in all_rows} != {"openjarvis", "openclaw", "omi", "clicky"}:
        errors.append("baseline matrix does not cover all four upstreams")
    if any(row["execution_status"] == "PASS" for row in all_rows):
        errors.append("W05 discovery must never fabricate upstream PASS")
    clicky_rows = [row for row in all_rows if row["source_repo"] == "clicky"]
    if clicky_rows and all(row["classification"] == "NOT_APPLICABLE" for row in clicky_rows):
        errors.append("clicky has Apple project metadata but no platform-gated baseline candidate")
    payload = {
        "schema_version": 1,
        "phase": "I01-W05",
        "status": "PASS" if not errors else "FAIL",
        "execution_policy": {
            "upstream_code_execution_authorized": False,
            "reason": "SECURITY_MODEL treats third-party upstream/plugin code as untrusted; no hardened hermetic sandbox is configured in CP01 CI",
            "not_run_is_pass": False,
            "future_execution_requirement": "execute applicable baselines in isolated, network/secret-constrained runtime before adapter parity/release",
        },
        "errors": errors,
        "sources": sorted(source_summaries, key=lambda row: row["source_repo"]),
        "baselines": sorted(all_rows, key=lambda row: (row["source_repo"], row["manifest_path"], row["name"])),
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errors:
        raise RuntimeError("W05 baseline gauntlet failed: " + "; ".join(errors))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover and classify exact-upstream baseline commands without executing untrusted code")
    parser.add_argument("--ledger", default="UPSTREAM_LEDGER.yaml")
    args = parser.parse_args()
    payload = run_w05(args.ledger)
    print(json.dumps({"status": payload["status"], "sources": payload["sources"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
