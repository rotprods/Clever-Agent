from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

from scripts.upstream.ledger import UpstreamPin, load_upstream_pins
from scripts.upstream.sync_upstreams import _git, pin_ref


# Non-cone sparse-checkout patterns. They intentionally select source/config
# semantics across arbitrary directory depth while excluding binary assets,
# model weights, media and generated build output.
SOURCE_PATTERNS = (
    "*.py",
    "*.pyi",
    "*.ts",
    "*.tsx",
    "*.mts",
    "*.cts",
    "*.js",
    "*.jsx",
    "*.mjs",
    "*.cjs",
    "*.swift",
    "*.dart",
    "*.rs",
    "*.c",
    "*.h",
    "*.cc",
    "*.cpp",
    "*.cxx",
    "*.hpp",
    "*.m",
    "*.mm",
    "*.kt",
    "*.java",
    "*.go",
    "*.sh",
    "*.proto",
    "*.sql",
    "*.graphql",
    "*.gql",
    "*.vue",
    "*.svelte",
    "*.html",
    "*.css",
    "*.scss",
    "*.metal",
    "*.toml",
    "*.yaml",
    "*.yml",
    "*.json",
    "package.json",
    "pyproject.toml",
    "requirements*.txt",
    "Cargo.toml",
    "pubspec.yaml",
    "Package.swift",
    "Package.resolved",
    "go.mod",
    "go.sum",
    "pnpm-workspace.yaml",
    "wrangler.toml",
    "Podfile",
    "Podfile.lock",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "gradle.properties",
    "CMakeLists.txt",
    "west.yml",
    "platformio.ini",
    "Dockerfile*",
    "docker-compose*.yml",
    "docker-compose*.yaml",
    "Makefile",
    "Gemfile",
    "Gemfile.lock",
    "**/*.xcodeproj/project.pbxproj",
)


def _git_with_input(repository: Path, args: list[str], text: str) -> str:
    env = dict(os.environ)
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"})
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        env=env,
        input=text,
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


def materialize_pin(pin: UpstreamPin, cache_root: Path) -> dict[str, object]:
    repository = cache_root / pin.id
    if not (repository / ".git").is_dir():
        raise RuntimeError(f"{pin.id}: object store missing at {repository}")
    ref = pin_ref(pin)
    actual = _git("rev-parse", ref, cwd=repository)
    if actual != pin.pinned_commit:
        raise RuntimeError(f"{pin.id}: refusing projection from mismatched pin {actual}")

    _git("sparse-checkout", "init", "--no-cone", cwd=repository)
    _git_with_input(
        repository,
        ["sparse-checkout", "set", "--no-cone", "--stdin"],
        "\n".join(SOURCE_PATTERNS) + "\n",
    )
    _git("-c", "advice.detachedHead=false", "checkout", "--detach", "--force", ref, cwd=repository)
    head = _git("rev-parse", "HEAD", cwd=repository)
    if head != pin.pinned_commit:
        raise RuntimeError(f"{pin.id}: sparse projection HEAD mismatch {head}")
    tracked = _git("ls-files", cwd=repository).splitlines()
    return {
        "id": pin.id,
        "pinned_commit": pin.pinned_commit,
        "worktree_head": head,
        "projection_mode": "sparse-source-only",
        "materialized_tracked_files": len(tracked),
        "status": "VERIFIED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize source-only sparse worktrees for pinned upstreams")
    parser.add_argument("--ledger", default="UPSTREAM_LEDGER.yaml")
    parser.add_argument("--cache", default=".cache/upstreams")
    parser.add_argument("--output", default="evidence/cp01/acquisition/source_projection.json")
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args()

    pins = load_upstream_pins(args.ledger)
    selected = set(args.only)
    if selected:
        unknown = selected - {pin.id for pin in pins}
        if unknown:
            raise SystemExit(f"Unknown upstream ids: {', '.join(sorted(unknown))}")
        pins = tuple(pin for pin in pins if pin.id in selected)
    rows = [materialize_pin(pin, Path(args.cache)) for pin in pins]
    payload = {"schema_version": 1, "patterns": list(SOURCE_PATTERNS), "sources": rows}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
