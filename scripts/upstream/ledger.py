from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_REQUIRED = {
    "id",
    "repository",
    "url",
    "branch",
    "pinned_commit",
    "license",
    "role",
    "integration",
}


@dataclass(frozen=True, slots=True)
class UpstreamPin:
    id: str
    repository: str
    url: str
    branch: str
    pinned_commit: str
    license: str
    role: str
    integration: str


def _scalar(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value[0:1] in {"'", '"'} and value[-1:] == value[0]:
        return value[1:-1]
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return value


def _validate(record: dict[str, str], *, path: Path) -> UpstreamPin:
    missing = sorted(_REQUIRED - record.keys())
    if missing:
        raise ValueError(f"{path}: upstream entry missing keys: {', '.join(missing)}")
    if not _ID_RE.fullmatch(record["id"]):
        raise ValueError(f"{path}: invalid upstream id {record['id']!r}")
    if not _REPO_RE.fullmatch(record["repository"]):
        raise ValueError(f"{path}: invalid repository {record['repository']!r}")
    if not record["url"].startswith("https://github.com/"):
        raise ValueError(f"{path}: only github.com HTTPS upstreams are accepted")
    if not _SHA_RE.fullmatch(record["pinned_commit"]):
        raise ValueError(f"{path}: pinned_commit must be an exact 40-char lowercase SHA")
    return UpstreamPin(**{key: record[key] for key in UpstreamPin.__dataclass_fields__})


def load_upstream_pins(path: str | Path) -> tuple[UpstreamPin, ...]:
    """Parse only the simple `sources:` sequence used by UPSTREAM_LEDGER.yaml.

    This intentionally is not a general YAML loader: acquisition metadata is treated
    as untrusted configuration and no YAML object construction is performed.
    """
    ledger = Path(path)
    lines = ledger.read_text(encoding="utf-8").splitlines()
    in_sources = False
    current: dict[str, str] | None = None
    records: list[UpstreamPin] = []

    for line_number, raw in enumerate(lines, 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        text = raw.strip()
        if indent == 0 and text == "sources:":
            in_sources = True
            continue
        if in_sources and indent == 0:
            break
        if not in_sources:
            continue
        if indent == 2 and text.startswith("- "):
            if current is not None:
                records.append(_validate(current, path=ledger))
            current = {}
            text = text[2:].strip()
            if text:
                if ":" not in text:
                    raise ValueError(f"{ledger}:{line_number}: malformed source item")
                key, value = text.split(":", 1)
                current[key.strip()] = _scalar(value)
            continue
        if current is None or indent < 4 or ":" not in text:
            raise ValueError(f"{ledger}:{line_number}: malformed sources block")
        key, value = text.split(":", 1)
        key = key.strip()
        if key in current:
            raise ValueError(f"{ledger}:{line_number}: duplicate key {key!r}")
        current[key] = _scalar(value)

    if current is not None:
        records.append(_validate(current, path=ledger))
    if not records:
        raise ValueError(f"{ledger}: no upstream sources found")
    ids = [record.id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{ledger}: duplicate upstream ids")
    return tuple(records)


def normalize_github_remote(value: str) -> str:
    value = value.strip().rstrip("/")
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value.removeprefix("git@github.com:")
    if value.startswith("ssh://git@github.com/"):
        value = "https://github.com/" + value.removeprefix("ssh://git@github.com/")
    if value.endswith(".git"):
        value = value[:-4]
    return value.lower()
