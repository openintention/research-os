from __future__ import annotations

from typing import Iterable

from research_os.domain.models import EffortView, EventEnvelope, EventKind


def build_effort_views(events: Iterable[EventEnvelope]) -> list[EffortView]:
    efforts: dict[str, EffortView] = {}

    for event in events:
        if event.kind == EventKind.EFFORT_REGISTERED:
            payload = event.payload
            efforts[payload["effort_id"]] = EffortView(
                effort_id=payload["effort_id"],
                name=payload["name"],
                objective=payload["objective"],
                platform=payload["platform"],
                budget_seconds=int(payload["budget_seconds"]),
                summary=payload.get("summary"),
                tags=payload.get("tags", {}) or event.tags,
                updated_at=event.occurred_at,
            )
            continue

        if event.kind != EventKind.WORKSPACE_STARTED or not event.workspace_id:
            continue

        effort_id = event.payload.get("effort_id")
        if not effort_id:
            continue

        effort = efforts.get(effort_id)
        if effort is None:
            continue

        if event.workspace_id not in effort.workspace_ids:
            effort.workspace_ids.append(event.workspace_id)
        effort.updated_at = event.occurred_at

    return sorted(efforts.values(), key=lambda item: (item.updated_at, item.effort_id), reverse=True)
