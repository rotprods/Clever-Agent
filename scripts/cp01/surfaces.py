from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable

from scripts.upstream.ledger import UpstreamPin

SCHEMA_VERSION = 1
SOURCE_EXTENSIONS = {
    ".py", ".pyi", ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs",
    ".swift", ".dart", ".rs", ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".m", ".mm",
    ".kt", ".kts", ".java", ".go",
}
TEST_MARKERS = {"test", "tests", "__tests__", "spec", "specs", "e2e", "integration", "bench", "benches"}

FAMILY_TOKENS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("security_policy", ("security", "permission", "policy", "auth", "trusted", "sandbox", "secret", "credential")),
    ("scheduler_automation", ("scheduler", "schedule", "cron", "automation", "job", "background")),
    ("session_identity", ("session", "identity", "pairing", "user", "account")),
    ("memory_persistence", ("memory", "memories", "store", "database", "repository", "persistence", "conversation", "history", "cache")),
    ("device_wearable", ("device", "wearable", "firmware", "bluetooth", "ble", "characteristic", "pairing", "zephyr", "esp32")),
    ("capture_perception", ("capture", "screen", "vision", "camera", "screenshot", "perception", "sensor")),
    ("speech_audio", ("audio", "speech", "voice", "microphone", "transcri", "diar", "speaker", "tts", "stt")),
    ("embodiment", ("overlay", "cursor", "point", "window", "menubar", "desktop", "companion", "ui")),
    ("channel_gateway", ("channel", "gateway", "websocket", "socket", "transport", "message", "node")),
    ("plugin_extension", ("plugin", "extension", "hook", "contribution")),
    ("tool", ("tool", "skill", "action", "command")),
    ("agent", ("agent", "planner", "orchestrator")),
    ("inference", ("provider", "engine", "model", "inference", "llm", "router")),
    ("learning_evaluation", ("learning", "benchmark", "eval", "trace", "feedback", "mining")),
    ("api_protocol", ("api", "route", "router", "http", "mcp", "protocol", "rpc")),
    ("worker_service", ("worker", "service", "daemon", "server", "backend")),
)

HIGH_VALUE = re.compile(
    r"agent|tool|skill|memory|store|provider|engine|model|channel|gateway|plugin|extension|"
    r"session|scheduler|security|permission|policy|device|ble|wearable|capture|screen|audio|"
    r"speech|transcri|diar|speaker|tts|stt|overlay|cursor|point|router|route|mcp|worker|service|"
    r"conversation|reconcil|listen|pair|hook|command|action|trace|benchmark|eval",
    re.IGNORECASE,
)

ROUTE_RE = re.compile(r"\b(?:app|router|server)\.(get|post|put|patch|delete|options|head|websocket)\s*\(\s*['\"]([^'\"]+)")
COMMAND_RE = re.compile(r"(?:\.command|\bcommand|\bsubcommand)\s*\(\s*['\"]([^'\"]+)")
REGISTER_RE = re.compile(r"\b(register(?:Tool|Skill|Channel|Provider|GatewayMethod|Gateway|Service|Command|Session\w*|Scheduler\w*|Hook|Node\w*|Plugin|Extension|Agent|Engine|Memory|Store|Router|Action)?|addTool|addChannel|addProvider)\s*\(")
EVENT_RE = re.compile(r"\.(?:on|once)\s*\(\s*['\"]([^'\"]+)")
PROTOCOL_RE = re.compile(r"\b(?:protocol|interface|trait)\s+([A-Za-z_][\w]*)")
DECL_RE = re.compile(r"\b(?:export\s+)?(?:default\s+)?(?:public\s+)?(?:final\s+)?(?:async\s+)?(?:class|struct|actor|enum|function|func|fn)\s+([A-Za-z_][\w]*)")


def _is_test_path(path: Path) -> bool:
    lowered = {part.lower() for part in path.parts}
    name = path.name.lower()
    return bool(lowered & TEST_MARKERS) or name.startswith("test_") or any(token in name for token in (".test.", ".spec.", "_test."))


def _family(path: str, name: str, kind: str) -> str:
    haystack = f"{path} {name} {kind}".lower()
    for family, tokens in FAMILY_TOKENS:
        if any(token in haystack for token in tokens):
            return family
    return "api_protocol" if kind.endswith("route") else "worker_service"


def _owner(repo_id: str, path: str) -> str:
    parts = PurePosixPath(path).parts
    if repo_id == "openclaw":
        if len(parts) > 1 and parts[0] in {"extensions", "packages"}:
            return f"openclaw:{parts[0]}:{parts[1]}"
        if len(parts) > 1 and parts[0] == "src":
            return f"openclaw:src:{parts[1]}"
        return "openclaw:root"
    if repo_id == "omi":
        if parts:
            root = parts[0]
            if root in {"backend", "app", "desktop", "firmware", "device", "wearable", "omi"}:
                return f"omi:{root}"
        return "omi:root"
    if repo_id == "openjarvis":
        if len(parts) >= 3 and parts[:2] == ("src", "openjarvis"):
            return f"openjarvis:{parts[2]}"
        if parts and parts[0] == "rust":
            return "openjarvis:rust"
        return "openjarvis:root"
    if repo_id == "clicky":
        if parts and parts[0] == "worker":
            return "clicky:worker"
        return "clicky:macos"
    return f"{repo_id}:unknown"


def _platforms(repo_id: str, path: str) -> list[str]:
    lowered = path.lower()
    out: set[str] = set()
    if repo_id == "clicky" or path.endswith(".swift"):
        out.add("apple")
    if path.endswith(".dart") or "/app/" in f"/{lowered}/":
        out.add("mobile")
    if any(token in lowered for token in ("firmware", "zephyr", "esp32", "ble", "bluetooth", "wearable")):
        out.add("hardware_device")
    if repo_id in {"openjarvis", "openclaw"}:
        out.add("desktop_server")
    return sorted(out)


def _semantic_facets(path: str, name: str, matched: str) -> tuple[list[str], list[str], list[str], list[str]]:
    value = f"{path} {name} {matched}".lower()
    permissions = sorted({token for token in ("permission", "auth", "scope", "policy", "secret", "credential") if token in value})
    state = sorted({token for token in ("memory", "store", "database", "repository", "cache", "session", "conversation", "history", "state") if token in value})
    lifecycle = sorted({token for token in ("start", "stop", "open", "close", "connect", "disconnect", "shutdown", "startup", "register", "unregister", "rollback") if token in value})
    failure = sorted({token for token in ("retry", "timeout", "rollback", "fallback", "error", "exception", "catch", "except") if token in value})
    return permissions, state, lifecycle, failure


def _stable_surface(
    pin: UpstreamPin,
    path: str,
    line: int,
    kind: str,
    name: str,
    interface: dict[str, Any],
    strength: str,
    text_hash: str,
    matched: str,
    extractor: str,
) -> dict[str, Any]:
    identity = json.dumps(
        [pin.id, pin.pinned_commit, path, line, kind, name, interface],
        sort_keys=True,
        separators=(",", ":"),
    )
    surface_id = f"surf_{hashlib.sha256(identity.encode()).hexdigest()[:24]}"
    permissions, state, lifecycle, failure = _semantic_facets(path, name, matched)
    return {
        "schema_version": SCHEMA_VERSION,
        "surface_id": surface_id,
        "source_repo": pin.id,
        "source_commit": pin.pinned_commit,
        "family": _family(path, name, kind),
        "surface_kind": kind,
        "name": name,
        "runtime_owner": _owner(pin.id, path),
        "source_path": path,
        "line": line,
        "interface": interface,
        "registration_evidence": [matched[:240]] if strength in {"REGISTRATION", "ROUTE_OR_PROTOCOL"} else [],
        "permissions": permissions,
        "state_effects": state,
        "lifecycle": lifecycle,
        "failure_semantics": failure,
        "platform_constraints": _platforms(pin.id, path),
        "evidence_strength": strength,
        "promotion_status": "BEHAVIOR_MAPPED" if strength in {"REGISTRATION", "ROUTE_OR_PROTOCOL", "BEHAVIOR_TEST"} else "DISCOVERED_CANDIDATE",
        "provenance": {"extractor": extractor, "source_sha256": text_hash, "matched_text": matched[:240]},
    }


def _literal_string(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _decorator_call_name(node: ast.AST) -> str:
    return _call_name(node.func if isinstance(node, ast.Call) else node)


def _extract_python(pin: UpstreamPin, path: str, text: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    text_hash = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    out: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                name = _decorator_call_name(decorator)
                leaf = name.rsplit(".", 1)[-1].lower()
                if leaf in {"get", "post", "put", "patch", "delete", "options", "head", "websocket", "route"}:
                    route = _literal_string(decorator.args[0]) if isinstance(decorator, ast.Call) and decorator.args else None
                    method = leaf.upper()
                    kind = "websocket_route" if leaf == "websocket" else "http_route"
                    matched = f"@{name}({route!r})"
                    out.append(_stable_surface(pin, path, node.lineno, kind, f"{method} {route or node.name}", {"method": method, "path": route}, "ROUTE_OR_PROTOCOL", text_hash, matched, "python-ast"))
                elif leaf in {"command", "group", "tool", "skill"}:
                    command = _literal_string(decorator.args[0]) if isinstance(decorator, ast.Call) and decorator.args else None
                    out.append(_stable_surface(pin, path, node.lineno, "cli_command" if leaf in {"command", "group"} else "registry_registration", command or node.name, {"decorator": name}, "ROUTE_OR_PROTOCOL" if leaf in {"command", "group"} else "REGISTRATION", text_hash, f"@{name}", "python-ast"))
            if HIGH_VALUE.search(f"{path} {node.name}"):
                out.append(_stable_surface(pin, path, node.lineno, "native_action", node.name, {"callable": node.name}, "DEFINITION", text_hash, f"def {node.name}", "python-ast"))
        elif isinstance(node, ast.ClassDef) and HIGH_VALUE.search(f"{path} {node.name}"):
            out.append(_stable_surface(pin, path, node.lineno, "protocol_contract" if any("Protocol" in _call_name(base) for base in node.bases) else "definition", node.name, {"class": node.name}, "DEFINITION", text_hash, f"class {node.name}", "python-ast"))
        elif isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            leaf = call_name.rsplit(".", 1)[-1]
            lowered = leaf.lower()
            first = _literal_string(node.args[0]) if node.args else None
            keyword_values = {kw.arg: _literal_string(kw.value) for kw in node.keywords if kw.arg}
            explicit_name = first or keyword_values.get("name") or keyword_values.get("id") or keyword_values.get("key") or keyword_values.get("command")
            if lowered == "include_router":
                prefix = keyword_values.get("prefix")
                out.append(_stable_surface(pin, path, getattr(node, "lineno", 1), "route_mount", prefix or explicit_name or call_name, {"mount": call_name, "prefix": prefix}, "REGISTRATION", text_hash, call_name, "python-ast"))
            elif lowered in {"add_parser", "add_command"} and explicit_name:
                out.append(_stable_surface(pin, path, getattr(node, "lineno", 1), "cli_command", explicit_name, {"registrar": call_name}, "ROUTE_OR_PROTOCOL", text_hash, call_name, "python-ast"))
            elif lowered.startswith("register") or lowered in {"add_tool", "add_channel", "add_provider", "add_api_route", "add_event_handler"}:
                kind = "lifecycle_hook" if "event" in lowered or "hook" in lowered else "registry_registration"
                if "route" in lowered:
                    kind = "http_route"
                out.append(_stable_surface(pin, path, getattr(node, "lineno", 1), kind, explicit_name or leaf, {"registrar": call_name}, "REGISTRATION" if kind != "http_route" else "ROUTE_OR_PROTOCOL", text_hash, call_name, "python-ast"))
    return out


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _first_string_after(text: str, start: int, limit: int = 280) -> str | None:
    snippet = text[start:start + limit]
    match = re.search(r"['\"]([^'\"\n]{1,160})['\"]", snippet)
    return match.group(1) if match else None


def _extract_regex(pin: UpstreamPin, path: str, text: str) -> list[dict[str, Any]]:
    text_hash = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    out: list[dict[str, Any]] = []
    for match in ROUTE_RE.finditer(text):
        method, route = match.groups()
        kind = "websocket_route" if method.lower() == "websocket" else "http_route"
        out.append(_stable_surface(pin, path, _line_number(text, match.start()), kind, f"{method.upper()} {route}", {"method": method.upper(), "path": route}, "ROUTE_OR_PROTOCOL", text_hash, match.group(0), "regex-route"))
    for match in COMMAND_RE.finditer(text):
        command = match.group(1)
        out.append(_stable_surface(pin, path, _line_number(text, match.start()), "cli_command", command, {"command": command}, "ROUTE_OR_PROTOCOL", text_hash, match.group(0), "regex-command"))
    for match in REGISTER_RE.finditer(text):
        registrar = match.group(1)
        explicit = _first_string_after(text, match.end())
        kind = "plugin_contribution" if any(token in registrar.lower() for token in ("tool", "skill", "channel", "provider", "gateway", "service", "session", "scheduler", "hook", "node", "plugin", "extension")) else "registry_registration"
        out.append(_stable_surface(pin, path, _line_number(text, match.start()), kind, explicit or f"{PurePosixPath(path).stem}:{registrar}", {"registrar": registrar}, "REGISTRATION", text_hash, match.group(0), "regex-registration"))
    if any(token in path.lower() for token in ("hook", "lifecycle", "gateway", "session", "events")):
        for match in EVENT_RE.finditer(text):
            event = match.group(1)
            out.append(_stable_surface(pin, path, _line_number(text, match.start()), "lifecycle_hook", event, {"event": event}, "REGISTRATION", text_hash, match.group(0), "regex-event"))
    for match in PROTOCOL_RE.finditer(text):
        name = match.group(1)
        if HIGH_VALUE.search(f"{path} {name}"):
            out.append(_stable_surface(pin, path, _line_number(text, match.start()), "protocol_contract", name, {"protocol": name}, "ROUTE_OR_PROTOCOL", text_hash, match.group(0), "regex-protocol"))
    for match in DECL_RE.finditer(text):
        name = match.group(1)
        if HIGH_VALUE.search(f"{path} {name}"):
            kind = "native_action" if any(token in name.lower() for token in ("start", "stop", "capture", "listen", "speak", "transcri", "connect", "disconnect", "overlay", "point", "send", "receive", "pair", "sync", "reconcil")) else "definition"
            out.append(_stable_surface(pin, path, _line_number(text, match.start()), kind, name, {"symbol": name}, "DEFINITION", text_hash, match.group(0), "regex-definition"))
    return out


def _dedupe(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    rank = {"DEFINITION": 1, "REGISTRATION": 2, "ROUTE_OR_PROTOCOL": 3, "BEHAVIOR_TEST": 4}
    for row in rows:
        key = row["surface_id"]
        previous = unique.get(key)
        if previous is None or rank[row["evidence_strength"]] > rank[previous["evidence_strength"]]:
            unique[key] = row
    return [unique[key] for key in sorted(unique)]


def extract_repository_surfaces(repository: str | Path, pin: UpstreamPin, max_file_bytes: int = 2_000_000) -> list[dict[str, Any]]:
    root = Path(repository)
    if not root.is_dir():
        raise RuntimeError(f"missing source projection for {pin.id}: {root}")
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SOURCE_EXTENSIONS or _is_test_path(path.relative_to(root)):
            continue
        try:
            if path.stat().st_size > max_file_bytes:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() in {".py", ".pyi"}:
            rows.extend(_extract_python(pin, relative, text))
        else:
            rows.extend(_extract_regex(pin, relative, text))
    return _dedupe(rows)


def surface_summary(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    data = list(rows)
    by_repo: dict[str, int] = {}
    by_family: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    by_strength: dict[str, int] = {}
    for row in data:
        by_repo[row["source_repo"]] = by_repo.get(row["source_repo"], 0) + 1
        by_family[row["family"]] = by_family.get(row["family"], 0) + 1
        by_kind[row["surface_kind"]] = by_kind.get(row["surface_kind"], 0) + 1
        by_strength[row["evidence_strength"]] = by_strength.get(row["evidence_strength"], 0) + 1
    return {
        "surface_count": len(data),
        "by_repo": dict(sorted(by_repo.items())),
        "by_family": dict(sorted(by_family.items())),
        "by_kind": dict(sorted(by_kind.items())),
        "by_evidence_strength": dict(sorted(by_strength.items())),
    }
