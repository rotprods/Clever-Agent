from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from scripts.upstream.ledger import UpstreamPin, load_upstream_pins, normalize_github_remote


def _git(*args: str, cwd: Path | None = None) -> str:
    env = dict(os.environ)
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"})
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _assert_remote(pin: UpstreamPin, checkout: Path) -> None:
    actual = normalize_github_remote(_git("remote", "get-url", "origin", cwd=checkout))
    expected = normalize_github_remote(pin.url)
    if actual != expected:
        raise RuntimeError(f"{pin.id}: origin mismatch: expected {expected}, got {actual}")


def acquire(pin: UpstreamPin, cache_root: Path) -> dict[str, str]:
    checkout = cache_root / pin.id
    cache_root.mkdir(parents=True, exist_ok=True)
    if checkout.exists() and not (checkout / ".git").is_dir():
        shutil.rmtree(checkout)
    if not checkout.exists():
        _git("clone", "--no-checkout", "--filter=blob:none", pin.url, str(checkout))
    _assert_remote(pin, checkout)

    try:
        _git("cat-file", "-e", f"{pin.pinned_commit}^{{commit}}", cwd=checkout)
    except RuntimeError:
        _git("fetch", "--no-tags", "origin", pin.pinned_commit, cwd=checkout)
    _git("cat-file", "-e", f"{pin.pinned_commit}^{{commit}}", cwd=checkout)
    _git("-c", "advice.detachedHead=false", "checkout", "--detach", "--force", pin.pinned_commit, cwd=checkout)
    head = _git("rev-parse", "HEAD", cwd=checkout)
    if head != pin.pinned_commit:
        raise RuntimeError(f"{pin.id}: pin verification failed: {head} != {pin.pinned_commit}")
    return {
        "id": pin.id,
        "repository": pin.repository,
        "expected_remote": normalize_github_remote(pin.url),
        "pinned_commit": pin.pinned_commit,
        "actual_head": head,
        "checkout": checkout.as_posix(),
        "status": "VERIFIED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire exact Clever-Agent upstream SHAs")
    parser.add_argument("--ledger", default="UPSTREAM_LEDGER.yaml")
    parser.add_argument("--cache", default=".cache/upstreams")
    parser.add_argument("--output", default="evidence/cp01/acquisition/acquisition_manifest.json")
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args()

    pins = load_upstream_pins(args.ledger)
    selected = {value for value in args.only}
    if selected:
        unknown = selected - {pin.id for pin in pins}
        if unknown:
            raise SystemExit(f"Unknown upstream ids: {', '.join(sorted(unknown))}")
        pins = tuple(pin for pin in pins if pin.id in selected)

    records = [acquire(pin, Path(args.cache)) for pin in pins]
    payload = {"schema_version": 1, "sources": sorted(records, key=lambda row: row["id"])}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
