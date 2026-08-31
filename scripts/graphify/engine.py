from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import tomllib
from typing import Iterable

from scripts.graphify.extractors import extract_candidates
from scripts.graphify.model import Node, RepositoryGraph, stable_id


LANGUAGE_BY_SUFFIX = {
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
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".m": "objective-c",
    ".mm": "objective-cpp",
    ".kt": "kotlin",
    ".java": "java",
    ".go": "go",
    ".sh": "shell",
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
    ".toml": "config",
    ".yaml": "config",
    ".yml": "config",
    ".json": "config",
}
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
}
SKIP_DIRS = {
    ".git",
    "node_modules",
    ".dart_tool",
    ".venv",
    "venv",
    "dist",
    "build",
    "target",
    "Pods",
    "DerivedData",
    "__pycache__",
}


def _is_manifest(path: Path) -> bool:
    name = path.name
    return (
        name in MANIFEST_NAMES
        or name.startswith("requirements") and name.endswith(".txt")
        or name.startswith("Dockerfile")
        or name.startswith("docker-compose") and path.suffix in {".yml", ".yaml"}
        or path.as_posix().endswith(".xcodeproj/project.pbxproj")
    )


def _read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > 2_000_000:
            return None
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() in LANGUAGE_BY_SUFFIX or _is_manifest(path):
            yield path


def _python_dependency_name(item: str) -> str:
    return re.split(r"[<>=!~;\s\[]", item, 1)[0]


def _manifest_dependencies(path: Path, text: str) -> list[str]:
    try:
        if path.name == "package.json":
            data = json.loads(text)
            deps: set[str] = set()
            for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                deps.update((data.get(key) or {}).keys())
            return sorted(deps)
        if path.name == "pyproject.toml":
            data = tomllib.loads(text)
            project = data.get("project") or {}
            deps = {_python_dependency_name(item) for item in project.get("dependencies") or [] if item}
            for values in (project.get("optional-dependencies") or {}).values():
                deps.update(_python_dependency_name(item) for item in values if item)
            return sorted(value for value in deps if value)
        if path.name == "Cargo.toml":
            data = tomllib.loads(text)
            deps: set[str] = set()
            for key in ("dependencies", "dev-dependencies", "build-dependencies"):
                section = data.get(key) or {}
                if isinstance(section, dict):
                    deps.update(section.keys())
            return sorted(deps)
        if path.name.startswith("requirements") and path.name.endswith(".txt"):
            deps = set()
            for raw in text.splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                name = _python_dependency_name(line)
                if name:
                    deps.add(name)
            return sorted(deps)
        if path.name == "go.mod":
            deps: set[str] = set()
            in_require = False
            for raw in text.splitlines():
                line = raw.strip()
                if line == "require (":
                    in_require = True
                    continue
                if in_require and line == ")":
                    in_require = False
                    continue
                if line.startswith("require "):
                    fields = line.split()
                    if len(fields) >= 2:
                        deps.add(fields[1])
                elif in_require and line and not line.startswith("//"):
                    fields = line.split()
                    if fields:
                        deps.add(fields[0])
            return sorted(deps)
        if path.name == "pubspec.yaml":
            deps: set[str] = set()
            in_deps = False
            for raw in text.splitlines():
                if raw and not raw.startswith(" "):
                    in_deps = raw.rstrip() in {"dependencies:", "dev_dependencies:", "dependency_overrides:"}
                    continue
                if in_deps:
                    match = re.match(r"^\s{2}([A-Za-z0-9_\-.]+):", raw)
                    if match:
                        deps.add(match.group(1))
            return sorted(deps)
    except (ValueError, TypeError):
        return []
    return []


def graphify_repository(root: str | Path, repo_id: str, source_commit: str) -> RepositoryGraph:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ValueError(f"repository root does not exist: {root_path}")
    graph = RepositoryGraph(repo_id, source_commit)
    repo_node = Node(
        id=stable_id("repo", repo_id, source_commit),
        kind="repository",
        name=repo_id,
        source_repo=repo_id,
        source_commit=source_commit,
        metadata={"root_name": root_path.name},
    )
    graph.add_node(repo_node)
    language_counts: dict[str, int] = {}
    file_count = 0

    for path in _iter_files(root_path):
        rel = path.relative_to(root_path).as_posix()
        text = _read_text(path)
        if text is None:
            continue
        file_count += 1
        language = LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "manifest")
        language_counts[language] = language_counts.get(language, 0) + 1
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        file_kind = "manifest" if _is_manifest(path) else "file"
        file_node = Node(
            id=stable_id("file", repo_id, source_commit, rel),
            kind=file_kind,
            name=path.name,
            source_repo=repo_id,
            source_commit=source_commit,
            path=rel,
            language=language,
            metadata={"sha256": digest},
        )
        graph.add_node(file_node)
        graph.add_edge("contains", repo_node.id, file_node.id, path=rel)

        if file_kind == "manifest":
            for dependency in _manifest_dependencies(path, text):
                dep_node = Node(
                    id=stable_id("dependency", repo_id, source_commit, dependency),
                    kind="dependency",
                    name=dependency,
                    source_repo=repo_id,
                    source_commit=source_commit,
                )
                graph.add_node(dep_node)
                graph.add_edge("requires", file_node.id, dep_node.id, path=rel)

        if language in LANGUAGE_BY_SUFFIX.values():
            for candidate in extract_candidates(text, language):
                symbol_node = Node(
                    id=stable_id("symbol", repo_id, source_commit, rel, candidate.kind, candidate.name, candidate.line),
                    kind=candidate.kind,
                    name=candidate.name,
                    source_repo=repo_id,
                    source_commit=source_commit,
                    path=rel,
                    line=candidate.line,
                    language=language,
                    metadata=candidate.metadata,
                )
                graph.add_node(symbol_node)
                graph.add_edge("declares", file_node.id, symbol_node.id, path=rel, line=candidate.line)

    graph.metadata = {
        "file_count": file_count,
        "language_counts": dict(sorted(language_counts.items())),
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
    }
    return graph
