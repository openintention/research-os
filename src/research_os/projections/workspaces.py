from __future__ import annotations

from typing import Iterable

from research_os.domain.models import EventEnvelope, EventKind, WorkspaceView


def build_workspace_views(events: Iterable[EventEnvelope]) -> list[WorkspaceView]:
    workspaces: dict[str, WorkspaceView] = {}

    for event in events:
        if not event.workspace_id:
            continue

        if event.kind == EventKind.WORKSPACE_STARTED:
            payload = event.payload
            workspaces[event.workspace_id] = WorkspaceView(
                workspace_id=event.workspace_id,
                name=payload["name"],
                objective=payload["objective"],
                platform=payload["platform"],
                budget_seconds=int(payload["budget_seconds"]),
                effort_id=payload.get("effort_id"),
                description=payload.get("description"),
                tags=payload.get("tags", {}) or event.tags,
                updated_at=event.occurred_at,
            )

        workspace = workspaces.get(event.workspace_id)
        if workspace is None:
            continue

        workspace.event_count += 1
        workspace.updated_at = event.occurred_at

        if event.kind == EventKind.SNAPSHOT_PUBLISHED:
            snapshot_id = event.payload["snapshot_id"]
            if snapshot_id not in workspace.snapshot_ids:
                workspace.snapshot_ids.append(snapshot_id)
        elif event.kind == EventKind.RUN_COMPLETED:
            run_id = event.payload["run_id"]
            if run_id not in workspace.run_ids:
                workspace.run_ids.append(run_id)
        elif event.kind == EventKind.CLAIM_ASSERTED:
            claim_id = event.payload["claim_id"]
            if claim_id not in workspace.claim_ids:
                workspace.claim_ids.append(claim_id)
        elif event.kind == EventKind.ADOPTION_RECORDED:
            workspace.adoption_count += 1
        elif event.kind == EventKind.SUMMARY_PUBLISHED:
            workspace.summary_count += 1

    return sorted(workspaces.values(), key=lambda item: (item.updated_at, item.workspace_id), reverse=True)


def build_workspace_view(events: Iterable[EventEnvelope], workspace_id: str) -> WorkspaceView | None:
    for workspace in build_workspace_views(events):
        if workspace.workspace_id == workspace_id:
            return workspace
    return None
