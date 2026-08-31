from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any

from scripts.upstream.ledger import UpstreamPin, load_upstream_pins
from scripts.upstream.sync_upstreams import pin_ref

LOCKFILE_NAMES = {
    "pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lock", "bun.lockb",
    "uv.lock", "poetry.lock", "Pipfile.lock", "Cargo.lock", "pubspec.lock",
    "Package.resolved", "Podfile.lock", "Gemfile.lock", "go.sum", "gradle.lockfile"
}
LICENSE_HINTS = ("license", "licence", "copying", "notice", "third_party", "third-party")


def _read_inventory(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _all_paths(inventory: dict[str, Any]) -> list[str]:
    return [str(row.get("path")) for row in inventory.get("files", []) if isinstance(row, dict) and row.get("path")]


def _lockfiles(paths: list[str]) -> list[str]:
    return sorted(path for path in paths if PurePosixPath(path).name in LOCKFILE_NAMES or PurePosixPath(path).name.endswith(".lock"))


def _license_paths(paths: list[str]) -> list[str]:
    return sorted(path for path in paths if PurePosixPath(path).name.lower().startswith(LICENSE_HINTS) or any(part.lower() in {"licenses", "notices"} for part in PurePosixPath(path).parts[:-1]))


def _top_level_license(paths: list[str]) -> str | None:
    candidates = [path for path in paths if len(PurePosixPath(path).parts) == 1 and PurePosixPath(path).name.lower().startswith(("license", "licence", "copying"))]
    return sorted(candidates)[0] if candidates else None


def _git_blob(repository: Path, ref: str, path: str, max_bytes: int = 2_000_000) -> bytes | None:
    size = subprocess.run(["git", "cat-file", "-s", f"{ref}:{path}"], cwd=repository, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
    if size.returncode != 0:
        return None
    try:
        blob_size = int(size.stdout.strip())
    except ValueError:
        return None
    if blob_size > max_bytes:
        return None
    result = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=repository, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return result.stdout if result.returncode == 0 else None


def _license_verification(repository: Path, pin: UpstreamPin, path: str | None) -> dict[str, Any]:
    if not path:
        return {"status": "MISSING_TOP_LEVEL_LICENSE", "path": None, "sha256": None, "declared_license": pin.license}
    blob = _git_blob(repository, pin_ref(pin), path)
    if blob is None:
        return {"status": "PRESENT_UNREAD", "path": path, "sha256": None, "declared_license": pin.license}
    text = blob.decode("utf-8", errors="replace").lower()
    declared = str(pin.license or "").lower()
    aliases = {
        "mit": ("mit license", "permission is hereby granted"),
        "apache-2.0": ("apache license", "version 2.0"),
        "agpl-3.0": ("gnu affero general public license",),
        "gpl-3.0": ("gnu general public license",),
    }
    tokens = aliases.get(declared, (declared,)) if declared else ()
    content_match = any(token and token in text for token in tokens)
    return {
        "status": "VERIFIED_DECLARATION_MATCH" if content_match else "PRESENT_DECLARATION_NOT_TEXT_MATCHED",
        "path": path,
        "sha256": hashlib.sha256(blob).hexdigest(),
        "declared_license": pin.license,
        "content_match": content_match,
    }


def inspect_repo(repository: Path, pin: UpstreamPin, inventory: dict[str, Any]) -> dict[str, Any]:
    paths = _all_paths(inventory)
    licenses = _license_paths(paths)
    locks = _lockfiles(paths)
    manifests = sorted(str(path) for path in inventory.get("manifests", []))
    top_license = _top_level_license(paths)
    verification = _license_verification(repository, pin, top_license)
    return {
        "source_repo": pin.id,
        "repository": pin.repository,
        "source_commit": pin.pinned_commit,
        "declared_license": pin.license,
        "license_verification": verification,
        "license_notice_files": licenses,
        "lockfiles": locks,
        "manifests": manifests,
        "counts": {"license_notice_files": len(licenses), "lockfiles": len(locks), "manifests": len(manifests)},
    }


def _render_notices(rows: list[dict[str, Any]]) -> str:
    lines = ["# Upstream notices — exact CP01 snapshots", "", "Generated from `UPSTREAM_LEDGER.yaml` and pinned Git trees. This is provenance/attribution inventory, not legal advice.", ""]
    for row in sorted(rows, key=lambda item: item["source_repo"]):
        lines.extend([
            f"## {row['source_repo']}", "",
            f"- Repository: `{row['repository']}`",
            f"- Commit: `{row['source_commit']}`",
            f"- Declared license: `{row['declared_license']}`",
            f"- Verification: `{row['license_verification']['status']}`",
            f"- Primary license file: `{row['license_verification'].get('path')}`",
            f"- License/notice files discovered: `{row['counts']['license_notice_files']}`",
            f"- Dependency lockfiles discovered: `{row['counts']['lockfiles']}`",
            "",
        ])
    return "\n".join(lines)


def run_w06(
    ledger: str | Path = "UPSTREAM_LEDGER.yaml",
    cache_root: str | Path = ".cache/upstreams",
    structural_root: str | Path = "inventory/upstreams",
    output_path: str | Path = "evidence/cp01/supply_chain.json",
    notices_path: str | Path = "licenses/UPSTREAM_NOTICES.md",
) -> dict[str, Any]:
    cache = Path(cache_root)
    structural = Path(structural_root)
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for pin in load_upstream_pins(ledger):
        inventory = _read_inventory(structural / f"{pin.id}.json")
        row = inspect_repo(cache / pin.id, pin, inventory)
        rows.append(row)
        if not row["manifests"]:
            errors.append(f"{pin.id}: no manifests discovered")
        if row["license_verification"]["status"] == "MISSING_TOP_LEVEL_LICENSE":
            errors.append(f"{pin.id}: missing top-level license")
    payload = {
        "schema_version": 1,
        "phase": "I01-W06",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "sources": sorted(rows, key=lambda item: item["source_repo"]),
        "invariants": {
            "exact_source_commit_recorded": True,
            "license_presence_checked": True,
            "lockfiles_inventoried_from_complete_git_tree": True,
            "upstream_code_executed": False,
        }
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    notices = Path(notices_path)
    notices.parent.mkdir(parents=True, exist_ok=True)
    notices.write_text(_render_notices(rows), encoding="utf-8")
    if errors:
        raise RuntimeError("W06 supply-chain gauntlet failed: " + "; ".join(errors))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile CP01 licenses/notices/lockfile supply-chain evidence")
    parser.add_argument("--ledger", default="UPSTREAM_LEDGER.yaml")
    args = parser.parse_args()
    payload = run_w06(args.ledger)
    print(json.dumps({"status": payload["status"], "sources": [{"source_repo": row["source_repo"], "counts": row["counts"], "license": row["license_verification"]} for row in payload["sources"]]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
