from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Iterable

from scripts.upstream.ledger import UpstreamPin
from scripts.upstream.sync_upstreams import pin_ref


SCHEMA_VERSION = 1

MANIFEST_NAMES = {
    "package.json",
    "pyproject.toml",
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
    "Makefile",
    "Gemfile",
    "Gemfile.lock",
    "meson.build",
    "WORKSPACE",
    "WORKSPACE.bazel",
    "BUILD",
    "BUILD.bazel",
}
RUNTIME_MARKERS = {
    "app",
    "apps",
    "backend",
    "frontend",
    "server",
    "servers",
    "src",
    "worker",
    "workers",
    "packages",
    "extensions",
    "plugins",
    "crates",
    "firmware",
    "device",
    "devices",
    "mobile",
    "desktop",
    "web",
    "api",
    "gateway",
}
TEST_DIR_MARKERS = {"test", "tests", "__tests__", "spec", "specs", "e2e", "integration", "bench", "benches", "benchmark", "benchmarks"}
DOC_DIR_MARKERS = {"doc", "docs", "documentation"}
CI_PREFIXES = (".github/workflows/", ".circleci/", ".buildkite/", ".azure-pipelines/")
CI_FILES = {".gitlab-ci.yml", ".gitlab-ci.yaml", "Jenkinsfile", "azure-pipelines.yml", "azure-pipelines.yaml", "bitrise.yml", "appveyor.yml"}
LICENSE_PREFIXES = ("license", "licence", "copying", "notice", "third_party", "third-party", "authors")

LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".swift": "swift",
    ".dart": "dart",
    ".rs": "rust",
    ".c": "c",
    ".h": "c-header",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp-header",
    ".m": "objective-c",
    ".mm": "objective-cpp",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".java": "java",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".fish": "shell",
    ".proto": "protobuf",
    ".sql": "sql",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".vue": "vue",
    ".svelte": "svelte",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".metal": "metal",
}


@dataclass(frozen=True, slots=True)
class TreeEntry:
    mode: str
    object_type: str
    object_id: str
    size: int | None
    path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "size": self.size,
            "path": self.path,
        }


def _git_bytes(repository: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip() or "git command failed")
    return result.stdout


def _git_text(repository: Path, *args: str) -> str:
    return _git_bytes(repository, *args).decode("utf-8", errors="strict").strip()


def read_tree(repository: Path, ref: str) -> tuple[TreeEntry, ...]:
    """Read the complete pinned Git tree without materializing file contents."""
    raw = _git_bytes(repository, "ls-tree", "-r", "-z", "-l", ref)
    entries: list[TreeEntry] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            header, raw_path = record.split(b"\t", 1)
            fields = header.decode("ascii").split()
            if len(fields) != 4:
                raise ValueError("unexpected ls-tree header")
            mode, object_type, object_id, raw_size = fields
            path = raw_path.decode("utf-8", errors="surrogateescape")
        except (ValueError, UnicodeDecodeError) as exc:
            raise RuntimeError("unable to parse git ls-tree record") from exc
        entries.append(
            TreeEntry(
                mode=mode,
                object_type=object_type,
                object_id=object_id,
                size=None if raw_size == "-" else int(raw_size),
                path=path,
            )
        )
    return tuple(sorted(entries, key=lambda entry: entry.path))


def _is_manifest(path: PurePosixPath) -> bool:
    name = path.name
    return (
        name in MANIFEST_NAMES
        or (name.startswith("requirements") and name.endswith(".txt"))
        or name.startswith("Dockerfile")
        or (name.startswith("docker-compose") and path.suffix.lower() in {".yml", ".yaml"})
        or path.as_posix().endswith(".xcodeproj/project.pbxproj")
    )


def _is_test(path: PurePosixPath) -> bool:
    parts = {part.lower() for part in path.parts[:-1]}
    name = path.name.lower()
    return (
        bool(parts & TEST_DIR_MARKERS)
        or name.startswith("test_")
        or name.endswith(("_test.py", ".test.ts", ".test.tsx", ".test.js", ".spec.ts", ".spec.tsx", ".spec.js"))
    )


def _is_doc(path: PurePosixPath) -> bool:
    parts = {part.lower() for part in path.parts[:-1]}
    name = path.name.lower()
    return bool(parts & DOC_DIR_MARKERS) or name.startswith(("readme", "contributing", "architecture", "changelog"))


def _is_ci_release(path: PurePosixPath) -> bool:
    value = path.as_posix()
    name = path.name
    lowered = value.lower()
    return (
        value.startswith(CI_PREFIXES)
        or name in CI_FILES
        or "/release/" in lowered
        or "/releases/" in lowered
        or name.lower().startswith("release")
    )


def _is_license_notice(path: PurePosixPath) -> bool:
    lowered_name = path.name.lower()
    parts = {part.lower() for part in path.parts[:-1]}
    return lowered_name.startswith(LICENSE_PREFIXES) or bool(parts & {"licenses", "license", "notices"})


def _package_root(path: PurePosixPath) -> str:
    parent = path.parent.as_posix()
    return "." if parent == "." else parent


def _boundary_candidates(entries: Iterable[TreeEntry], manifests: list[str]) -> list[dict[str, object]]:
    signals: dict[str, set[str]] = defaultdict(set)
    for manifest in manifests:
        root = _package_root(PurePosixPath(manifest))
        signals[root].add(f"manifest:{PurePosixPath(manifest).name}")

    for entry in entries:
        path = PurePosixPath(entry.path)
        dirs = path.parts[:-1]
        for index, part in enumerate(dirs):
            lowered = part.lower()
            if lowered not in RUNTIME_MARKERS:
                continue
            candidate_parts = dirs[: index + 1]
            if not candidate_parts:
                continue
            candidate = PurePosixPath(*candidate_parts).as_posix()
            # Root-level generic `src` is useful; deeply nested `src` is useful
            # only with its package parent so the boundary remains human-legible.
            if lowered == "src" and index > 0:
                candidate = PurePosixPath(*dirs[: index + 1]).as_posix()
            signals[candidate].add(f"runtime-marker:{lowered}")

    rows = [
        {"path": path, "signals": sorted(values)}
        for path, values in signals.items()
    ]
    return sorted(rows, key=lambda row: str(row["path"]))


def scan_repository(repository: str | Path, pin: UpstreamPin) -> dict[str, object]:
    repo_path = Path(repository)
    if not (repo_path / ".git").is_dir():
        raise RuntimeError(f"missing git object store: {repo_path}")
    ref = pin_ref(pin)
    actual = _git_text(repo_path, "rev-parse", ref)
    if actual != pin.pinned_commit:
        raise RuntimeError(f"{pin.id}: structural scan pin mismatch: {actual} != {pin.pinned_commit}")

    entries = read_tree(repo_path, ref)
    paths = [PurePosixPath(entry.path) for entry in entries]
    manifests = sorted(path.as_posix() for path in paths if _is_manifest(path))
    tests = sorted(path.as_posix() for path in paths if _is_test(path))
    docs = sorted(path.as_posix() for path in paths if _is_doc(path))
    ci_release = sorted(path.as_posix() for path in paths if _is_ci_release(path))
    licenses = sorted(path.as_posix() for path in paths if _is_license_notice(path))

    extensions: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    top_level: Counter[str] = Counter()
    object_types: Counter[str] = Counter()
    total_bytes_known = 0
    unknown_size_objects = 0
    for entry in entries:
        path = PurePosixPath(entry.path)
        suffix = path.suffix.lower() or "<none>"
        extensions[suffix] += 1
        language = LANGUAGE_EXTENSIONS.get(path.suffix.lower())
        if language:
            languages[language] += 1
        top_level[path.parts[0] if path.parts else "."] += 1
        object_types[entry.object_type] += 1
        if entry.size is None:
            unknown_size_objects += 1
        else:
            total_bytes_known += entry.size

    package_roots = sorted({_package_root(PurePosixPath(path)) for path in manifests})
    test_roots = sorted({
        next((PurePosixPath(*path.parts[: index + 1]).as_posix() for index, part in enumerate(path.parts[:-1]) if part.lower() in TEST_DIR_MARKERS), _package_root(path))
        for path in (PurePosixPath(value) for value in tests)
    })
    docs_roots = sorted({
        next((PurePosixPath(*path.parts[: index + 1]).as_posix() for index, part in enumerate(path.parts[:-1]) if part.lower() in DOC_DIR_MARKERS), _package_root(path))
        for path in (PurePosixPath(value) for value in docs)
    })

    semantic = {
        "source_repo": pin.id,
        "repository": pin.repository,
        "source_commit": pin.pinned_commit,
        "tree_ref": ref,
        "tree_entry_count": len(entries),
        "tree_sha256": hashlib.sha256(
            "\n".join(
                f"{entry.mode}\t{entry.object_type}\t{entry.object_id}\t{entry.size}\t{entry.path}"
                for entry in entries
            ).encode("utf-8", errors="surrogateescape")
        ).hexdigest(),
        "summary": {
            "objects_by_type": dict(sorted(object_types.items())),
            "total_bytes_known": total_bytes_known,
            "unknown_size_objects": unknown_size_objects,
            "top_level_entry_counts": dict(sorted(top_level.items())),
            "extensions": dict(sorted(extensions.items())),
            "languages": dict(sorted(languages.items())),
        },
        "package_workspace_roots": package_roots,
        "manifests": manifests,
        "runtime_service_app_boundaries": _boundary_candidates(entries, manifests),
        "test_roots": test_roots,
        "test_files": tests,
        "ci_release_files": ci_release,
        "docs_roots": docs_roots,
        "doc_files": docs,
        "license_notice_files": licenses,
        "files": [entry.to_dict() for entry in entries],
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "inventory_type": "structural_repository_inventory",
        **semantic,
    }


def main() -> int:
    import argparse

    from scripts.upstream.ledger import load_upstream_pins

    parser = argparse.ArgumentParser(description="Scan the complete Git tree of one exact pinned upstream")
    parser.add_argument("repository")
    parser.add_argument("--ledger", default="UPSTREAM_LEDGER.yaml")
    parser.add_argument("--upstream", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    pins = {pin.id: pin for pin in load_upstream_pins(args.ledger)}
    if args.upstream not in pins:
        raise SystemExit(f"unknown upstream id: {args.upstream}")
    payload = scan_repository(args.repository, pins[args.upstream])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"inventory: {args.upstream}: {payload['tree_entry_count']} tree entries / "
        f"{len(payload['manifests'])} manifests / {len(payload['test_files'])} tests -> {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
