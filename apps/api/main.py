from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

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
    Lease,
    LeaseCommand,
    LeaseObservation,
    LeaseState,
    NodeHeartbeat,
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
    LeaseCommandIngressVerifier,
    NodeHeartbeatIngressVerifier,
    TrustedNodeRegistry,
)
from research_os.network.sqlite import SQLiteNetworkEnvelopeStore
from research_os.service import (
    EventConflictError,
    EventIngestionError,
    LeaseConflictError,
    LeaseIngestionError,
    LeaseNotFoundError,
    ResearchOSService,
)
from research_os.settings import Settings


_EVENT_APPEND_INPUT = TypeAdapter(EventEnvelope | SignedNetworkEnvelope)


def create_app(
    settings: Settings | None = None,
    *,
    now_fn: Callable[[], datetime] | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.ensure_directories()

    store = SQLiteEventStore(settings.db_path)
    service = ResearchOSService(
        store,
        default_frontier_size=settings.default_frontier_size,
        public_base_url=settings.public_base_url,
        now_fn=now_fn,
    )
    ingress_verifier = EventAppendIngressVerifier(
        trusted_nodes=TrustedNodeRegistry.from_sources(
            path=settings.network_trusted_nodes_path,
            inline_json=settings.network_trusted_nodes_json,
        ),
        receipt_store=SQLiteNetworkEnvelopeStore(settings.db_path),
    )
    lease_ingress_verifier = LeaseCommandIngressVerifier(
        trusted_nodes=TrustedNodeRegistry.from_sources(
            path=settings.network_trusted_nodes_path,
            inline_json=settings.network_trusted_nodes_json,
        ),
        receipt_store=SQLiteNetworkEnvelopeStore(settings.db_path),
        now_fn=now_fn,
    )
    heartbeat_ingress_verifier = NodeHeartbeatIngressVerifier(
        trusted_nodes=TrustedNodeRegistry.from_sources(
            path=settings.network_trusted_nodes_path,
            inline_json=settings.network_trusted_nodes_json,
        ),
        receipt_store=SQLiteNetworkEnvelopeStore(settings.db_path),
        now_fn=now_fn,
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
    app.state.lease_ingress_verifier = lease_ingress_verifier
    app.state.heartbeat_ingress_verifier = heartbeat_ingress_verifier

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

    @app.get("/api/v1/leases", response_model=list[LeaseObservation])
    def list_leases(
        status: LeaseState | None = Query(default=None),
        effort_id: str | None = Query(default=None),
    ) -> list[LeaseObservation]:
        return service.list_lease_observations(status=status, effort_id=effort_id)

    @app.get("/api/v1/leases/{lease_id}", response_model=LeaseObservation)
    def get_lease(lease_id: str) -> LeaseObservation:
        lease = service.get_lease_observation(lease_id)
        if lease is None:
            raise HTTPException(status_code=404, detail="lease not found")
        return lease

    @app.post("/api/v1/leases/acquire", response_model=Lease)
    async def acquire_lease(request: Request) -> Lease:
        body = await _decode_json_body(request)
        return _run_lease_command(
            handler=lambda lease_id, command: service.acquire_lease(command),
            lease_ingress_verifier=lease_ingress_verifier,
            action="acquire",
            payload=body,
        )

    @app.post("/api/v1/leases/{lease_id}/renew", response_model=Lease)
    async def renew_lease(lease_id: str, request: Request) -> Lease:
        body = await _decode_json_body(request)
        return _run_lease_command(
            service.renew_lease,
            lease_ingress_verifier=lease_ingress_verifier,
            lease_id=lease_id,
            action="renew",
            payload=body,
        )

    @app.post("/api/v1/leases/{lease_id}/release", response_model=Lease)
    async def release_lease(lease_id: str, request: Request) -> Lease:
        body = await _decode_json_body(request)
        return _run_lease_command(
            service.release_lease,
            lease_ingress_verifier=lease_ingress_verifier,
            lease_id=lease_id,
            action="release",
            payload=body,
        )

    @app.post("/api/v1/leases/{lease_id}/fail", response_model=Lease)
    async def fail_lease(lease_id: str, request: Request) -> Lease:
        body = await _decode_json_body(request)
        return _run_lease_command(
            service.fail_lease,
            lease_ingress_verifier=lease_ingress_verifier,
            lease_id=lease_id,
            action="fail",
            payload=body,
        )

    @app.post("/api/v1/leases/{lease_id}/complete", response_model=Lease)
    async def complete_lease(lease_id: str, request: Request) -> Lease:
        body = await _decode_json_body(request)
        return _run_lease_command(
            service.complete_lease,
            lease_ingress_verifier=lease_ingress_verifier,
            lease_id=lease_id,
            action="complete",
            payload=body,
        )

    @app.post("/api/v1/network/heartbeats", response_model=NodeHeartbeat, status_code=201)
    async def record_network_heartbeat(request: Request) -> NodeHeartbeat:
        body = await _decode_json_body(request)
        try:
            envelope = SignedNetworkEnvelope.model_validate(body)
            return heartbeat_ingress_verifier.verify_and_record(
                envelope,
                raw_envelope=body,
                record_heartbeat=service.record_node_heartbeat,
            )
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        except EnvelopeVerificationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except EnvelopeReplayError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/v1/network/heartbeats/{node_id}", response_model=NodeHeartbeat)
    def get_network_heartbeat(node_id: str) -> NodeHeartbeat:
        heartbeat = service.get_node_heartbeat(node_id)
        if heartbeat is None:
            raise HTTPException(status_code=404, detail="node heartbeat not found")
        return heartbeat

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


def _run_lease_command(
    handler: Callable[[str | None, LeaseCommand], Lease],
    *,
    lease_ingress_verifier: LeaseCommandIngressVerifier,
    lease_id: str | None = None,
    action: str,
    payload: dict[str, object],
) -> Lease:
    try:
        if _looks_like_signed_network_envelope(payload):
            envelope = SignedNetworkEnvelope.model_validate(payload)
            return lease_ingress_verifier.verify_and_record(
                envelope,
                raw_envelope=payload,
                lease_id=lease_id,
                apply_command=lambda command: handler(lease_id, command),
            )
        command = LeaseCommand.model_validate({**payload, "action": action, "lease_id": lease_id})
        return handler(lease_id, command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except LeaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EnvelopeVerificationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EnvelopeReplayError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LeaseIngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LeaseConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


async def _decode_json_body(request: Request) -> dict[str, object]:
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="request body must be valid JSON") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="request body must be a JSON object")
    return body


def _looks_like_signed_network_envelope(payload: dict[str, object]) -> bool:
    return payload.get("envelope_schema") == "openintention-network-envelope-v1"


app = create_app()
