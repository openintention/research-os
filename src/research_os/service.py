from __future__ import annotations

from uuid import uuid4

from research_os.domain.models import (
    ClaimSummary,
    CreateEffortRequest,
    CreateWorkspaceRequest,
    EffortCreated,
    EffortView,
    EventEnvelope,
    EventKind,
    FrontierView,
    PublicationView,
    RecommendNextRequest,
    RecommendNextResponse,
    WorkspaceCreated,
    WorkspaceView,
)
from research_os.ledger.protocol import EventStore
from research_os.planner.heuristics import recommend_next
from research_os.projections.efforts import build_effort_views
from research_os.projections.workspaces import build_workspace_view, build_workspace_views
from research_os.publications.github import render_effort_overview, render_snapshot_pull_request, render_workspace_discussion


class ResearchOSService:
    def __init__(
        self,
        store: EventStore,
        *,
        default_frontier_size: int = 10,
        public_base_url: str | None = None,
    ) -> None:
        self.store = store
        self.default_frontier_size = default_frontier_size
        self.public_base_url = public_base_url
        self.store.init_schema()

    def create_workspace(self, request: CreateWorkspaceRequest) -> WorkspaceCreated:
        workspace_id = str(uuid4())
        workspace_tags = request.tags | {"participant_role": request.participant_role.value}
        event = EventEnvelope(
            kind=EventKind.WORKSPACE_STARTED,
            workspace_id=workspace_id,
            aggregate_id=workspace_id,
            aggregate_kind="workspace",
            actor_id=request.actor_id,
            payload={
                "name": request.name,
                "objective": request.objective,
                "platform": request.platform,
                "budget_seconds": request.budget_seconds,
                "effort_id": request.effort_id,
                "description": request.description,
                "tags": request.tags,
                "participant_role": request.participant_role.value,
            },
            tags=workspace_tags,
        )
        self.store.append(event)
        return WorkspaceCreated(workspace_id=workspace_id, bootstrap_event_id=event.event_id)

    def create_effort(self, request: CreateEffortRequest) -> EffortCreated:
        effort_id = str(uuid4())
        event = EventEnvelope(
            kind=EventKind.EFFORT_REGISTERED,
            aggregate_id=effort_id,
            aggregate_kind="effort",
            actor_id=request.actor_id,
            payload={
                "effort_id": effort_id,
                "name": request.name,
                "objective": request.objective,
                "platform": request.platform,
                "budget_seconds": request.budget_seconds,
                "summary": request.summary,
                "tags": request.tags,
            },
            tags=request.tags,
        )
        self.store.append(event)
        return EffortCreated(effort_id=effort_id, bootstrap_event_id=event.event_id)

    def append_event(self, event: EventEnvelope) -> EventEnvelope:
        self.store.append(event)
        return event

    def list_events(
        self,
        *,
        workspace_id: str | None = None,
        kind: EventKind | None = None,
        limit: int = 200,
    ) -> list[EventEnvelope]:
        return self.store.list(workspace_id=workspace_id, kind=kind, limit=limit)

    def list_workspaces(self, *, effort_id: str | None = None) -> list[WorkspaceView]:
        workspaces = build_workspace_views(self.store.list(limit=10_000))
        if effort_id is None:
            return workspaces
        return [workspace for workspace in workspaces if workspace.effort_id == effort_id]

    def list_efforts(self) -> list[EffortView]:
        return build_effort_views(self.store.list(limit=10_000))

    def get_effort(self, effort_id: str) -> EffortView | None:
        return next((effort for effort in self.list_efforts() if effort.effort_id == effort_id), None)

    def get_effort_by_name(self, name: str) -> EffortView | None:
        return next((effort for effort in self.list_efforts() if effort.name == name), None)

    def get_workspace(self, workspace_id: str) -> WorkspaceView | None:
        events = self.store.list(workspace_id=workspace_id, limit=10_000)
        return build_workspace_view(events, workspace_id)

    def get_frontier(
        self,
        *,
        objective: str,
        platform: str,
        budget_seconds: int | None = None,
        limit: int | None = None,
    ) -> FrontierView:
        return self.store.get_frontier(
            objective=objective,
            platform=platform,
            budget_seconds=budget_seconds,
            limit=limit or self.default_frontier_size,
        )

    def rebuild_frontier_projection(self) -> None:
        self.store.rebuild_frontier_projection()

    def list_claims(
        self,
        *,
        objective: str | None = None,
        platform: str | None = None,
    ) -> list[ClaimSummary]:
        return self.store.list_claims(objective=objective, platform=platform)

    def rebuild_claim_projection(self) -> None:
        self.store.rebuild_claim_projection()

    def recommend_next(self, request: RecommendNextRequest) -> RecommendNextResponse:
        return recommend_next(self.store.list(limit=10_000), request)

    def render_workspace_discussion(self, workspace_id: str) -> PublicationView | None:
        workspace = self.get_workspace(workspace_id)
        if workspace is None:
            return None

        events = self.store.list(workspace_id=workspace_id, limit=10_000)
        claims = [
            claim
            for claim in self.store.list_claims(objective=workspace.objective, platform=workspace.platform)
            if claim.workspace_id == workspace_id
        ]
        return render_workspace_discussion(workspace, events=events, claims=claims)

    def render_effort_overview(self, effort_id: str) -> PublicationView | None:
        effort = self.get_effort(effort_id)
        if effort is None:
            return None

        workspaces = self.list_workspaces(effort_id=effort_id)
        workspace_ids = {workspace.workspace_id for workspace in workspaces}
        claims = [
            claim
            for claim in self.store.list_claims(objective=effort.objective, platform=effort.platform)
            if claim.workspace_id in workspace_ids
        ]
        frontier = self.store.get_frontier(
            objective=effort.objective,
            platform=effort.platform,
            budget_seconds=effort.budget_seconds,
            limit=self.default_frontier_size,
        )
        return render_effort_overview(
            effort,
            workspaces=workspaces,
            claims=claims,
            frontier=frontier,
            public_base_url=self.public_base_url,
        )

    def render_snapshot_pull_request(self, workspace_id: str, snapshot_id: str) -> PublicationView | None:
        workspace = self.get_workspace(workspace_id)
        if workspace is None:
            return None

        events = self.store.list(workspace_id=workspace_id, limit=10_000)
        snapshot_event = next(
            (
                event
                for event in events
                if event.kind == EventKind.SNAPSHOT_PUBLISHED
                and event.payload.get("snapshot_id") == snapshot_id
            ),
            None,
        )
        if snapshot_event is None:
            return None

        run_events = [
            event
            for event in events
            if event.kind == EventKind.RUN_COMPLETED and event.payload.get("snapshot_id") == snapshot_id
        ]
        claims = [
            claim
            for claim in self.store.list_claims(objective=workspace.objective, platform=workspace.platform)
            if claim.candidate_snapshot_id == snapshot_id
        ]
        return render_snapshot_pull_request(
            workspace,
            snapshot_event=snapshot_event,
            run_events=run_events,
            claims=claims,
        )
