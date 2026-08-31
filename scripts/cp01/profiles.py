from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import re
from typing import Any

from scripts.cp01.surfaces import _stable_surface
from scripts.upstream.ledger import UpstreamPin

SWIFT_FUNC_RE = re.compile(r"\bfunc\s+([A-Za-z_][\w]*)\s*\(")
SWIFT_TYPE_RE = re.compile(r"\b(?:final\s+)?(?:class|struct|actor|protocol)\s+([A-Za-z_][\w]*)")

CLICKY_BOUNDARY_FILES = {
    "companionmanager.swift",
    "audiomanager.swift",
    "screenmanager.swift",
    "screenrecordingmanager.swift",
    "speechmanager.swift",
    "ttsmanager.swift",
    "overlaymanager.swift",
    "pointingmanager.swift",
    "appdelegate.swift",
}
CLICKY_ACTION_TOKENS = (
    "listen", "record", "audio", "speak", "speech", "transcri", "capture", "screen",
    "overlay", "point", "cursor", "send", "stream", "start", "stop", "show", "hide",
    "request", "permission", "connect", "disconnect",
)


def _clicky_surfaces(repository: Path, pin: UpstreamPin) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(repository.rglob("*.swift")):
        relative = path.relative_to(repository).as_posix()
        lowered_path = relative.lower()
        boundary = path.name.lower() in CLICKY_BOUNDARY_FILES or any(
            token in lowered_path for token in ("companion", "audio", "speech", "screen", "overlay", "cursor", "point")
        )
        if not boundary:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        text_hash = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
        for match in SWIFT_FUNC_RE.finditer(text):
            name = match.group(1)
            if not any(token in name.lower() for token in CLICKY_ACTION_TOKENS):
                continue
            line = text.count("\n", 0, match.start()) + 1
            rows.append(_stable_surface(pin, relative, line, "native_action", name, {"callable": name, "profile": "clicky-native"}, "DEFINITION", text_hash, match.group(0), "profile-clicky-swift"))
        for match in SWIFT_TYPE_RE.finditer(text):
            name = match.group(1)
            line = text.count("\n", 0, match.start()) + 1
            rows.append(_stable_surface(pin, relative, line, "protocol_contract" if "protocol" in match.group(0) else "definition", name, {"symbol": name, "profile": "clicky-native"}, "DEFINITION", text_hash, match.group(0), "profile-clicky-swift"))
    return rows


def supplement_repository_surfaces(repository: str | Path, pin: UpstreamPin) -> list[dict[str, Any]]:
    root = Path(repository)
    if pin.id == "clicky":
        return _clicky_surfaces(root, pin)
    return []
