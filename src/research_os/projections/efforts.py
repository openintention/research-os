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
                metric_name=payload.get("metric_name"),
                direction=payload.get("direction"),
                constraints=list(payload.get("constraints", [])),
                evidence_requirement=payload.get("evidence_requirement"),
                stop_condition=payload.get("stop_condition"),
                author_id=payload.get("author_id"),
                tags=payload.get("tags", {}) or event.tags,
                successor_effort_id=None,
                updated_at=event.occurred_at,
            )
            continue

        if event.kind == EventKind.EFFORT_ROLLED_OVER:
            effort_id = event.aggregate_id or event.payload.get("effort_id")
            if not effort_id:
                continue
            effort = efforts.get(effort_id)
            if effort is None:
                continue
            effort.successor_effort_id = event.payload.get("successor_effort_id")
            effort.tags = {
                **effort.tags,
                **{str(key): str(value) for key, value in event.tags.items()},
            }
            effort.updated_at = event.occurred_at
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
