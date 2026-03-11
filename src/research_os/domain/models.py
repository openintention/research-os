from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventKind(StrEnum):
    EFFORT_REGISTERED = "effort.registered"
    EFFORT_ROLLED_OVER = "effort.rolled_over"
    WORKSPACE_STARTED = "workspace.started"
    SNAPSHOT_PUBLISHED = "snapshot.published"
    RUN_COMPLETED = "run.completed"
    CLAIM_ASSERTED = "claim.asserted"
    CLAIM_REPRODUCED = "claim.reproduced"
    CLAIM_CONTRADICTED = "claim.contradicted"
    ADOPTION_RECORDED = "adoption.recorded"
    SUMMARY_PUBLISHED = "summary.published"


class ParticipantRole(StrEnum):
    CONTRIBUTOR = "contributor"
    VERIFIER = "verifier"


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    kind: EventKind
    occurred_at: datetime = Field(default_factory=utcnow)
    workspace_id: str | None = None
    aggregate_id: str | None = None
    aggregate_kind: str | None = None
    actor_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    tags: dict[str, str] = Field(default_factory=dict)


class CreateWorkspaceRequest(BaseModel):
    name: str
    objective: str
    platform: str
    budget_seconds: int = Field(default=300, ge=1)
    effort_id: str | None = None
    description: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    actor_id: str | None = None
    participant_role: ParticipantRole = ParticipantRole.CONTRIBUTOR


class WorkspaceCreated(BaseModel):
    workspace_id: str
    bootstrap_event_id: str


class CreateEffortRequest(BaseModel):
    name: str
    objective: str
    platform: str
    budget_seconds: int = Field(default=300, ge=1)
    summary: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    actor_id: str | None = None


class EffortCreated(BaseModel):
    effort_id: str
    bootstrap_event_id: str


class EffortView(BaseModel):
    effort_id: str
    name: str
    objective: str
    platform: str
    budget_seconds: int
    summary: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    workspace_ids: list[str] = Field(default_factory=list)
    successor_effort_id: str | None = None
    updated_at: datetime


class CapabilityDescriptor(BaseModel):
    platforms: list[str] = Field(default_factory=list)
    max_budget_seconds: int | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class RecommendNextRequest(BaseModel):
    objective: str
    platform: str
    budget_seconds: int = Field(default=300, ge=1)
    workspace_id: str | None = None
    target_claim_id: str | None = None
    limit: int = Field(default=3, ge=1, le=20)
    worker_capabilities: CapabilityDescriptor = Field(default_factory=CapabilityDescriptor)


class Recommendation(BaseModel):
    action: str
    priority: int
    reason: str
    inputs: dict[str, Any] = Field(default_factory=dict)


class RecommendNextResponse(BaseModel):
    recommendations: list[Recommendation]


class PublicationView(BaseModel):
    kind: str
    format: str = "markdown"
    title: str
    body: str


class FrontierMember(BaseModel):
    snapshot_id: str
    workspace_id: str | None = None
    run_id: str
    objective: str
    platform: str
    budget_seconds: int
    metric_name: str
    metric_value: float
    direction: str
    claim_count: int = 0
    support_count: int = 0
    contradiction_count: int = 0
    tags: dict[str, str] = Field(default_factory=dict)
    last_updated_at: datetime


class FrontierView(BaseModel):
    objective: str
    platform: str
    budget_seconds: int | None = None
    members: list[FrontierMember]


class ClaimStatus(StrEnum):
    PENDING = "pending"
    SUPPORTED = "supported"
    CONTESTED = "contested"


class ClaimSummary(BaseModel):
    claim_id: str
    workspace_id: str | None = None
    statement: str
    claim_type: str
    candidate_snapshot_id: str
    baseline_snapshot_id: str | None = None
    objective: str
    platform: str
    metric_name: str | None = None
    delta: float | None = None
    confidence: float | None = None
    evidence_run_ids: list[str] = Field(default_factory=list)
    support_count: int = 0
    contradiction_count: int = 0
    status: ClaimStatus = ClaimStatus.PENDING
    tags: dict[str, str] = Field(default_factory=dict)
    updated_at: datetime


class WorkspaceView(BaseModel):
    workspace_id: str
    name: str
    actor_id: str | None = None
    participant_role: ParticipantRole = ParticipantRole.CONTRIBUTOR
    objective: str
    platform: str
    budget_seconds: int
    effort_id: str | None = None
    description: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    snapshot_ids: list[str] = Field(default_factory=list)
    run_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    reproduction_count: int = 0
    adoption_count: int = 0
    summary_count: int = 0
    event_count: int = 0
    updated_at: datetime
