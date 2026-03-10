from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from research_os.artifacts.local import LocalArtifactRegistry
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
from research_os.ledger.sqlite import SQLiteEventStore
from research_os.service import ResearchOSService
from research_os.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.ensure_directories()

    store = SQLiteEventStore(settings.db_path)
    service = ResearchOSService(store, default_frontier_size=settings.default_frontier_size)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Machine-native research operating system starter API.",
    )
    app.state.service = service
    app.state.artifact_registry = LocalArtifactRegistry(settings.artifact_root)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/workspaces", response_model=WorkspaceCreated, status_code=201)
    def create_workspace(request: CreateWorkspaceRequest) -> WorkspaceCreated:
        return service.create_workspace(request)

    @app.post("/api/v1/efforts", response_model=EffortCreated, status_code=201)
    def create_effort(request: CreateEffortRequest) -> EffortCreated:
        return service.create_effort(request)

    @app.get("/api/v1/efforts", response_model=list[EffortView])
    def list_efforts() -> list[EffortView]:
        return service.list_efforts()

    @app.get("/api/v1/workspaces", response_model=list[WorkspaceView])
    def list_workspaces() -> list[WorkspaceView]:
        return service.list_workspaces()

    @app.get("/api/v1/workspaces/{workspace_id}", response_model=WorkspaceView)
    def get_workspace(workspace_id: str) -> WorkspaceView:
        workspace = service.get_workspace(workspace_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="workspace not found")
        return workspace

    @app.post("/api/v1/events", response_model=EventEnvelope, status_code=201)
    def append_event(event: EventEnvelope) -> EventEnvelope:
        return service.append_event(event)

    @app.get("/api/v1/events", response_model=list[EventEnvelope])
    def list_events(
        workspace_id: str | None = None,
        kind: EventKind | None = Query(default=None),
        limit: int = Query(default=200, ge=1, le=10_000),
    ) -> list[EventEnvelope]:
        return service.list_events(workspace_id=workspace_id, kind=kind, limit=limit)

    @app.get("/api/v1/frontiers/{objective}/{platform}", response_model=FrontierView)
    def get_frontier(
        objective: str,
        platform: str,
        budget_seconds: int | None = Query(default=None, ge=1),
        limit: int = Query(default=10, ge=1, le=100),
    ) -> FrontierView:
        return service.get_frontier(
            objective=objective,
            platform=platform,
            budget_seconds=budget_seconds,
            limit=limit,
        )

    @app.get("/api/v1/claims", response_model=list[ClaimSummary])
    def list_claims(
        objective: str | None = None,
        platform: str | None = None,
    ) -> list[ClaimSummary]:
        return service.list_claims(objective=objective, platform=platform)

    @app.post("/api/v1/planner/recommend", response_model=RecommendNextResponse)
    def planner_recommend(request: RecommendNextRequest) -> RecommendNextResponse:
        return service.recommend_next(request)

    @app.get("/api/v1/publications/workspaces/{workspace_id}/discussion", response_model=PublicationView)
    def get_workspace_discussion(workspace_id: str) -> PublicationView:
        publication = service.render_workspace_discussion(workspace_id)
        if publication is None:
            raise HTTPException(status_code=404, detail="workspace not found")
        return publication

    @app.get("/api/v1/publications/efforts/{effort_id}", response_model=PublicationView)
    def get_effort_overview(effort_id: str) -> PublicationView:
        publication = service.render_effort_overview(effort_id)
        if publication is None:
            raise HTTPException(status_code=404, detail="effort not found")
        return publication

    @app.get(
        "/api/v1/publications/workspaces/{workspace_id}/pull-requests/{snapshot_id}",
        response_model=PublicationView,
    )
    def get_snapshot_pull_request(workspace_id: str, snapshot_id: str) -> PublicationView:
        publication = service.render_snapshot_pull_request(workspace_id, snapshot_id)
        if publication is None:
            raise HTTPException(status_code=404, detail="snapshot not found")
        return publication

    return app


app = create_app()
