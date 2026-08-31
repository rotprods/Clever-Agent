from __future__ import annotations

import re
from pathlib import Path

_ITERATION_RE = re.compile(r"^I(?P<number>[0-9]+)$")


def iteration_number(iteration_id: str) -> int:
    match = _ITERATION_RE.fullmatch(str(iteration_id))
    if not match:
        raise ValueError(f"invalid iteration id: {iteration_id!r}")
    return int(match.group("number"))


def iteration_dir(iteration_id: str) -> Path:
    return Path("iterations") / f"{iteration_number(iteration_id):02d}"


def iteration_state_path(iteration_id: str) -> Path:
    return iteration_dir(iteration_id) / "STATE.json"


def iteration_plan_path(iteration_id: str) -> Path:
    return iteration_dir(iteration_id) / "ITERATION.md"


def iteration_metaprompt_path(iteration_id: str) -> Path:
    return iteration_dir(iteration_id) / "METAPROMPT.md"
