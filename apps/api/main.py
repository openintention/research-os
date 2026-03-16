from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import TypeAdapter, ValidationError

from research_os.artifacts.local import LocalArtifactRegistry
from research_os.bootstrap import ensure_seeded_efforts
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
    SignedNetworkEnvelope,
    WorkspaceCreated,
    WorkspaceView,
)
from research_os.ledger.sqlite import SQLiteEventStore
from research_os.network.ingress import (
    EnvelopeReplayError,
    EnvelopeVerificationError,
    EventAppendIngressVerifier,
    TrustedNodeRegistry,
)
from research_os.network.sqlite import SQLiteNetworkEnvelopeStore
from research_os.service import EventConflictError, EventIngestionError, ResearchOSService
from research_os.settings import Settings


_EVENT_APPEND_INPUT = TypeAdapter(EventEnvelope | SignedNetworkEnvelope)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.ensure_directories()

    store = SQLiteEventStore(settings.db_path)
    service = ResearchOSService(
        store,
        default_frontier_size=settings.default_frontier_size,
        public_base_url=settings.public_base_url,
    )
    ingress_verifier = EventAppendIngressVerifier(
        trusted_nodes=TrustedNodeRegistry.from_file(settings.network_trusted_nodes_path),
        receipt_store=SQLiteNetworkEnvelopeStore(settings.db_path),
    )
    if settings.bootstrap_seeded_efforts:
        ensure_seeded_efforts(service, actor_id=settings.bootstrap_actor_id)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Machine-native research operating system starter API.",
    )
    app.state.service = service
    app.state.artifact_registry = LocalArtifactRegistry(settings.artifact_root)
    app.state.ingress_verifier = ingress_verifier

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/workspaces", response_model=WorkspaceCreated, status_code=201)
    def create_workspace(request: CreateWorkspaceRequest) -> WorkspaceCreated:
        try:
            return service.create_workspace(request)
        except EventIngestionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EventConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/v1/efforts", response_model=EffortCreated, status_code=201)
    def create_effort(request: CreateEffortRequest) -> EffortCreated:
        return service.create_effort(request)

    @app.get("/api/v1/efforts", response_model=list[EffortView])
    def list_efforts() -> list[EffortView]:
        return service.list_efforts()

    @app.get("/api/v1/workspaces", response_model=list[WorkspaceView])
    def list_workspaces(effort_id: str | None = Query(default=None)) -> list[WorkspaceView]:
        return service.list_workspaces(effort_id=effort_id)

    @app.get("/api/v1/workspaces/{workspace_id}", response_model=WorkspaceView)
    def get_workspace(workspace_id: str) -> WorkspaceView:
        workspace = service.get_workspace(workspace_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="workspace not found")
        return workspace

    @app.post("/api/v1/events", response_model=EventEnvelope, status_code=201)
    async def append_event(request: Request) -> EventEnvelope:
        try:
            body = await request.json()
            ingress_payload = _EVENT_APPEND_INPUT.validate_python(body)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="request body must be valid JSON") from exc

        try:
            if isinstance(ingress_payload, SignedNetworkEnvelope):
                return ingress_verifier.verify_and_record(
                    ingress_payload,
                    raw_envelope=body,
                    append_event=service.append_event,
                )
            return service.append_event(ingress_payload)
        except EnvelopeVerificationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EnvelopeReplayError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except EventIngestionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EventConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

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
