from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from scripts.upstream.ledger import load_upstream_pins, normalize_github_remote


def _git(checkout: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=checkout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def verify(ledger: Path, cache: Path) -> dict[str, object]:
    rows: list[dict[str, str]] = []
    for pin in load_upstream_pins(ledger):
        checkout = cache / pin.id
        if not (checkout / ".git").is_dir():
            raise RuntimeError(f"{pin.id}: missing git checkout at {checkout}")
        head = _git(checkout, "rev-parse", "HEAD")
        remote = normalize_github_remote(_git(checkout, "remote", "get-url", "origin"))
        expected_remote = normalize_github_remote(pin.url)
        status = "VERIFIED" if head == pin.pinned_commit and remote == expected_remote else "MISMATCH"
        rows.append(
            {
                "id": pin.id,
                "pinned_commit": pin.pinned_commit,
                "actual_head": head,
                "expected_remote": expected_remote,
                "actual_remote": remote,
                "status": status,
            }
        )
    if any(row["status"] != "VERIFIED" for row in rows):
        raise RuntimeError("one or more upstream pins do not match")
    return {"schema_version": 1, "sources": sorted(rows, key=lambda row: row["id"])}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify cached upstreams against UPSTREAM_LEDGER")
    parser.add_argument("--ledger", default="UPSTREAM_LEDGER.yaml")
    parser.add_argument("--cache", default=".cache/upstreams")
    parser.add_argument("--output", default="evidence/cp01/acquisition/pin_verification.json")
    args = parser.parse_args()
    payload = verify(Path(args.ledger), Path(args.cache))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
