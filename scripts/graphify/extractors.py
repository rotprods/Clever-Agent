from __future__ import annotations

import ast
from dataclasses import dataclass, field
import re
from typing import Any


@dataclass(frozen=True, slots=True)
class Candidate:
    kind: str
    name: str
    line: int
    metadata: dict[str, Any] = field(default_factory=dict)


def _python_decorator_text(node: ast.AST) -> str:
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute):
        parts: list[str] = []
        current: ast.AST | None = target
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    if isinstance(target, ast.Name):
        return target.id
    return ""


def _route_literal(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call) or not node.args:
        return None
    first = node.args[0]
    return first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None


def _semantic_kind(name: str, default: str = "symbol") -> str:
    lowered = name.lower()
    if lowered.endswith("agent") or "agent" in lowered:
        return "agent"
    if any(token in lowered for token in ("provider", "inference", "engine", "modelclient")):
        return "provider"
    if "plugin" in lowered or "extension" in lowered:
        return "plugin"
    if "channel" in lowered or "gateway" in lowered:
        return "channel"
    if any(token in lowered for token in ("memory", "store", "repository", "database", "persistence")):
        return "persistence"
    if any(token in lowered for token in ("device", "firmware", "ble", "bluetooth", "wearable")):
        return "device"
    if any(token in lowered for token in ("capture", "audio", "speech", "transcri", "tts", "microphone")):
        return "media"
    if any(token in lowered for token in ("policy", "permission", "auth", "sandbox", "security")):
        return "security"
    if "tool" in lowered or "skill" in lowered:
        return "tool"
    return default


def extract_python(text: str) -> list[Candidate]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    out: list[Candidate] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = [_python_decorator_text(item) for item in node.decorator_list]
            route_decorator = next((d for d in decorators if d.rsplit(".", 1)[-1] in {"get", "post", "put", "patch", "delete", "websocket", "route"}), None)
            command_decorator = next((d for d in decorators if d.rsplit(".", 1)[-1] in {"command", "group"}), None)
            kind = "route" if route_decorator else "command" if command_decorator else _semantic_kind(node.name, "function")
            metadata: dict[str, Any] = {"decorators": [value for value in decorators if value]}
            if route_decorator:
                decorator_node = node.decorator_list[decorators.index(route_decorator)]
                metadata["route"] = _route_literal(decorator_node)
                metadata["method"] = route_decorator.rsplit(".", 1)[-1].upper()
            out.append(Candidate(kind, node.name, node.lineno, metadata))
        elif isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases:
                try:
                    bases.append(ast.unparse(base))
                except Exception:
                    pass
            out.append(Candidate(_semantic_kind(node.name, "class"), node.name, node.lineno, {"bases": bases}))
    return _dedupe(out)


_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "typescript": (
        re.compile(r"\b(?:export\s+)?(?:default\s+)?(?:async\s+)?(class|function|interface|type|enum|const)\s+([A-Za-z_$][\w$]*)"),
    ),
    "javascript": (
        re.compile(r"\b(?:export\s+)?(?:default\s+)?(?:async\s+)?(class|function|const)\s+([A-Za-z_$][\w$]*)"),
    ),
    "swift": (
        re.compile(r"\b(?:final\s+)?(class|struct|enum|protocol|actor)\s+([A-Za-z_][\w]*)"),
        re.compile(r"\b(func)\s+([A-Za-z_][\w]*)\s*\("),
    ),
    "dart": (
        re.compile(r"\b(class|mixin|enum|extension)\s+([A-Za-z_][\w]*)"),
    ),
    "rust": (
        re.compile(r"\b(?:pub(?:\([^)]*\))?\s+)?(fn|struct|enum|trait|mod)\s+([A-Za-z_][\w]*)"),
    ),
    "c": (
        re.compile(r"^[\w\s\*]+\b([A-Za-z_][\w]*)\s*\([^;]*\)\s*\{", re.MULTILINE),
    ),
    "cpp": (
        re.compile(r"\b(class|struct|enum)\s+([A-Za-z_][\w]*)"),
        re.compile(r"^[\w:<>,\s\*&~]+\b([A-Za-z_][\w:]*)\s*\([^;]*\)\s*\{", re.MULTILINE),
    ),
}

_SURFACE_PATTERNS = (
    ("route", re.compile(r"\b(?:app|router)\.(get|post|put|patch|delete|websocket)\s*\(\s*['\"]([^'\"]+)")),
    ("registry", re.compile(r"\b(register[A-Z_a-z][\w]*)\s*\(")),
    ("command", re.compile(r"\b(?:command|subcommand)\s*\(\s*['\"]([^'\"]+)")),
)


def extract_regex(text: str, language: str) -> list[Candidate]:
    out: list[Candidate] = []
    for pattern in _PATTERNS.get(language, ()):
        for match in pattern.finditer(text):
            groups = match.groups()
            if len(groups) >= 2:
                declared, name = groups[-2], groups[-1]
            else:
                declared, name = "symbol", groups[-1]
            line = text.count("\n", 0, match.start()) + 1
            out.append(Candidate(_semantic_kind(name, declared), name, line, {"declaration": declared}))
    for surface_kind, pattern in _SURFACE_PATTERNS:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            groups = match.groups()
            if surface_kind == "route":
                method, route = groups
                out.append(Candidate("route", f"{method.upper()} {route}", line, {"method": method.upper(), "route": route}))
            else:
                out.append(Candidate(surface_kind, groups[-1], line, {}))
    return _dedupe(out)


def extract_candidates(text: str, language: str) -> list[Candidate]:
    if language == "python":
        return extract_python(text)
    return extract_regex(text, language)


def _dedupe(candidates: list[Candidate]) -> list[Candidate]:
    unique: dict[tuple[str, str, int], Candidate] = {}
    for candidate in candidates:
        unique[(candidate.kind, candidate.name, candidate.line)] = candidate
    return [unique[key] for key in sorted(unique)]
