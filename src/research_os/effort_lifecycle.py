from __future__ import annotations

import re
from typing import Iterable

from research_os.domain.models import EffortView

PROOF_VERSION_PATTERN = re.compile(r"^(?P<base>.+?) \(proof v(?P<version>\d+)\)$")


def is_public_proof_effort(effort: EffortView) -> bool:
    tags = effort.tags
    return tags.get("public_proof") == "true" or tags.get("external_harness") == "autoresearch-mlx"


def is_historical_proof_effort(effort: EffortView) -> bool:
    if not is_public_proof_effort(effort):
        return False
    return bool(effort.successor_effort_id) or effort.tags.get("proof_status") == "historical"


def proof_series(effort: EffortView) -> str | None:
    return effort.tags.get("proof_series")


def proof_version(effort: EffortView) -> int:
    raw = effort.tags.get("proof_version")
    if raw is None:
        return 1
    try:
        return max(1, int(raw))
    except ValueError:
        return 1


def base_effort_name(name: str) -> str:
    if match := PROOF_VERSION_PATTERN.match(name):
        return match.group("base")
    return name


def next_proof_effort_name(name: str, next_version: int) -> str:
    return f"{base_effort_name(name)} (proof v{next_version})"


def split_current_and_historical_efforts(
    efforts: Iterable[EffortView],
) -> tuple[list[EffortView], list[EffortView]]:
    current: list[EffortView] = []
    historical: list[EffortView] = []
    for effort in efforts:
        if is_historical_proof_effort(effort):
            historical.append(effort)
        else:
            current.append(effort)
    return current, historical
