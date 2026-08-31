from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from scripts.upstream.ledger import UpstreamPin, load_upstream_pins, normalize_github_remote


PIN_REF_PREFIX = "refs/clever-agent/pinned"


def pin_ref(pin: UpstreamPin) -> str:
    return f"{PIN_REF_PREFIX}/{pin.id}"


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


def _assert_remote(pin: UpstreamPin, repository: Path) -> None:
    actual = normalize_github_remote(_git("remote", "get-url", "origin", cwd=repository))
    expected = normalize_github_remote(pin.url)
    if actual != expected:
        raise RuntimeError(f"{pin.id}: origin mismatch: expected {expected}, got {actual}")


def _has_commit(repository: Path, commit: str) -> bool:
    try:
        _git("cat-file", "-e", f"{commit}^{{commit}}", cwd=repository)
        return True
    except RuntimeError:
        return False


def _ensure_repository(pin: UpstreamPin, repository: Path) -> None:
    if repository.exists() and not (repository / ".git").is_dir():
        shutil.rmtree(repository)
    if not repository.exists():
        repository.mkdir(parents=True)
        _git("init", "--quiet", cwd=repository)
        _git("remote", "add", "origin", pin.url, cwd=repository)
    _assert_remote(pin, repository)
    # Mark origin as a promisor remote so later sparse materialization can lazily
    # obtain source blobs without downloading unrelated binary assets.
    _git("config", "remote.origin.promisor", "true", cwd=repository)
    _git("config", "remote.origin.partialclonefilter", "blob:none", cwd=repository)


def _worktree_materialized(repository: Path) -> bool:
    return any(path.name != ".git" for path in repository.iterdir())


def acquire(pin: UpstreamPin, cache_root: Path) -> dict[str, object]:
    """Acquire an exact commit into a minimal partial-clone object store.

    No worktree checkout is performed here. The source-only projection used by
    Graphify is a separate, explicit phase (`source_projection.py`).
    """
    repository = cache_root / pin.id
    cache_root.mkdir(parents=True, exist_ok=True)
    _ensure_repository(pin, repository)

    if not _has_commit(repository, pin.pinned_commit):
        direct_error: RuntimeError | None = None
        try:
            _git(
                "fetch",
                "--no-tags",
                "--depth=1",
                "--filter=blob:none",
                "origin",
                pin.pinned_commit,
                cwd=repository,
            )
        except RuntimeError as exc:
            direct_error = exc

        if not _has_commit(repository, pin.pinned_commit):
            # Some servers disallow direct unadvertised SHA wants. Fetching the
            # declared branch without blobs is slower but remains bounded to
            # commit/tree metadata and provides a deterministic fallback.
            try:
                _git(
                    "fetch",
                    "--no-tags",
                    "--filter=blob:none",
                    "origin",
                    pin.branch,
                    cwd=repository,
                )
            except RuntimeError:
                if direct_error is not None:
                    raise direct_error
                raise

    if not _has_commit(repository, pin.pinned_commit):
        raise RuntimeError(f"{pin.id}: pinned commit is not reachable after acquisition")

    ref = pin_ref(pin)
    _git("update-ref", ref, pin.pinned_commit, cwd=repository)
    actual = _git("rev-parse", ref, cwd=repository)
    if actual != pin.pinned_commit:
        raise RuntimeError(f"{pin.id}: pin ref mismatch: {actual} != {pin.pinned_commit}")

    return {
        "id": pin.id,
        "repository": pin.repository,
        "expected_remote": normalize_github_remote(pin.url),
        "pinned_commit": pin.pinned_commit,
        "pinned_ref": ref,
        "actual_commit": actual,
        "cache_path": repository.as_posix(),
        "worktree_materialized": _worktree_materialized(repository),
        "acquisition_mode": "partial-object-store",
        "status": "VERIFIED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire exact Clever-Agent upstream SHAs without full worktrees")
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
    payload = {"schema_version": 2, "sources": sorted(records, key=lambda row: str(row["id"]))}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
