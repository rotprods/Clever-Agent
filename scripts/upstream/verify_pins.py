from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

from scripts.upstream.ledger import load_upstream_pins, normalize_github_remote
from scripts.upstream.sync_upstreams import pin_ref


def _git(repository: Path, *args: str) -> str:
    env = dict(os.environ)
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"})
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _optional_head(repository: Path) -> str | None:
    try:
        return _git(repository, "rev-parse", "--verify", "HEAD")
    except RuntimeError:
        return None


def verify(ledger: Path, cache: Path) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for pin in load_upstream_pins(ledger):
        repository = cache / pin.id
        if not (repository / ".git").is_dir():
            raise RuntimeError(f"{pin.id}: missing git object store at {repository}")
        ref = pin_ref(pin)
        actual = _git(repository, "rev-parse", ref)
        remote = normalize_github_remote(_git(repository, "remote", "get-url", "origin"))
        expected_remote = normalize_github_remote(pin.url)
        head = _optional_head(repository)
        status = "VERIFIED" if actual == pin.pinned_commit and remote == expected_remote else "MISMATCH"
        rows.append(
            {
                "id": pin.id,
                "pinned_commit": pin.pinned_commit,
                "pinned_ref": ref,
                "actual_commit": actual,
                "worktree_head": head,
                "expected_remote": expected_remote,
                "actual_remote": remote,
                "status": status,
            }
        )
    if any(row["status"] != "VERIFIED" for row in rows):
        raise RuntimeError("one or more upstream pins do not match")
    return {"schema_version": 2, "sources": sorted(rows, key=lambda row: str(row["id"]))}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify cached object stores against UPSTREAM_LEDGER")
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
