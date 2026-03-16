from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


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


class NodeCapability(StrEnum):
    EVENT_APPEND = "event_append"
    LEASE_ACQUIRE = "lease_acquire"
    LEASE_RENEW = "lease_renew"
    LEASE_RELEASE = "lease_release"
    VERIFY_CLAIM = "verify_claim"
    EXPLORE_EFFORT = "explore_effort"
    PUBLISH_SUMMARY = "publish_summary"


class SigningKeyStatus(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"


class SignatureScheme(StrEnum):
    ED25519 = "ed25519"


class NetworkMessageType(StrEnum):
    EVENT_APPEND = "event.append"
    LEASE_ACQUIRE = "lease.acquire"
    LEASE_RENEW = "lease.renew"
    LEASE_RELEASE = "lease.release"
    LEASE_FAIL = "lease.fail"
    LEASE_COMPLETE = "lease.complete"
    NODE_HEARTBEAT = "node.heartbeat"


class LeaseState(StrEnum):
    AVAILABLE = "available"
    ACQUIRED = "acquired"
    RENEWED = "renewed"
    RELEASED = "released"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class LeaseWorkItemType(StrEnum):
    REPRODUCE_CLAIM = "reproduce_claim"
    CONTRADICT_CLAIM = "contradict_claim"
    ADOPT_SNAPSHOT = "adopt_snapshot"
    COMPOSE_FRONTIER = "compose_frontier"
    EXPLORE_EFFORT = "explore_effort"
    PUBLISH_SUMMARY = "publish_summary"


class LeaseSubjectType(StrEnum):
    CLAIM = "claim"
    SNAPSHOT = "snapshot"
    EFFORT = "effort"
    FRONTIER = "frontier"
    SUMMARY = "summary"


class LeaseCommandAction(StrEnum):
    ACQUIRE = "acquire"
    RENEW = "renew"
    RELEASE = "release"
    FAIL = "fail"
    COMPLETE = "complete"
    HEARTBEAT = "heartbeat"


class NodeSigningKey(BaseModel):
    key_id: str
    public_key: str
    signature_scheme: SignatureScheme
    status: SigningKeyStatus


class NodeIdentity(BaseModel):
    node_id: str
    identity_schema: str = "openintention-node-identity-v1"
    identity_version: int = 1
    display_name: str
    description: str | None = None
    signing_keys: list[NodeSigningKey]
    capabilities: list[NodeCapability]
    transport_hints: list[str] = Field(default_factory=list)
    operator_hint: str | None = None
    created_at: datetime
    expires_at: datetime | None = None


class SignedNetworkEnvelope(BaseModel):
    envelope_id: str
    envelope_schema: str = "openintention-network-envelope-v1"
    envelope_version: int = 1
    message_type: NetworkMessageType
    sender_node_id: str
    sender_key_id: str
    sent_at: datetime
    expires_at: datetime | None = None
    payload_schema: str
    payload_digest: str
    payload: dict[str, Any]
    signature: str
    signature_scheme: SignatureScheme
    request_id: str | None = None
    trace_id: str | None = None
    replay_window_seconds: int | None = Field(default=None, ge=1)


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
    planner_fingerprint: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    work_item_type: LeaseWorkItemType | None = None
    subject_type: LeaseSubjectType | None = None
    subject_id: str | None = Field(default=None, min_length=1)


class RecommendNextResponse(BaseModel):
    recommendations: list[Recommendation]


class Lease(BaseModel):
    lease_id: str = Field(min_length=1)
    lease_schema: str = "openintention-lease-v1"
    lease_version: int = 1
    work_item_type: LeaseWorkItemType
    participant_role: ParticipantRole
    subject_type: LeaseSubjectType
    subject_id: str = Field(min_length=1)
    effort_id: str | None = None
    objective: str | None = None
    platform: str | None = None
    budget_seconds: int | None = Field(default=None, ge=1)
    planner_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    holder_node_id: str | None = Field(default=None, pattern=r"^node_[a-z0-9]{16,64}$")
    holder_workspace_id: str | None = None
    status: LeaseState
    max_duration_seconds: int = Field(ge=1)
    renewal_count: int = Field(default=0, ge=0)
    acquired_at: datetime | None = None
    renewed_at: datetime | None = None
    released_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None
    observed_run_id: str | None = None
    observed_claim_id: str | None = None
    stale_completion: bool = False
    expires_at: datetime


class LeaseCommand(BaseModel):
    command_schema: str = "openintention-lease-command-v1"
    command_version: int = 1
    action: LeaseCommandAction
    request_id: str = Field(min_length=1)
    node_id: str = Field(pattern=r"^node_[a-z0-9]{16,64}$")
    lease_id: str | None = None
    planner_fingerprint: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    ttl_seconds: int | None = Field(default=None, ge=1)
    participant_role: ParticipantRole | None = None
    work_item_type: LeaseWorkItemType | None = None
    subject_type: LeaseSubjectType | None = None
    subject_id: str | None = Field(default=None, min_length=1)
    effort_id: str | None = None
    objective: str | None = None
    platform: str | None = None
    budget_seconds: int | None = Field(default=None, ge=1)
    workspace_id: str | None = None
    observed_run_id: str | None = None
    observed_claim_id: str | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def validate_for_action(self) -> "LeaseCommand":
        if self.action is LeaseCommandAction.ACQUIRE:
            missing = [
                field
                for field in (
                    "planner_fingerprint",
                    "ttl_seconds",
                    "participant_role",
                    "work_item_type",
                    "subject_type",
                    "subject_id",
                )
                if getattr(self, field) is None
            ]
            if missing:
                raise ValueError(f"acquire requires {', '.join(missing)}")
            return self

        if self.action in {
            LeaseCommandAction.RENEW,
            LeaseCommandAction.RELEASE,
            LeaseCommandAction.FAIL,
            LeaseCommandAction.COMPLETE,
            LeaseCommandAction.HEARTBEAT,
        } and self.lease_id is None:
            raise ValueError(f"{self.action.value} requires lease_id")

        if self.action is LeaseCommandAction.RENEW and self.ttl_seconds is None:
            raise ValueError("renew requires ttl_seconds")
        if self.action is LeaseCommandAction.FAIL and not self.failure_reason:
            raise ValueError("fail requires failure_reason")
        return self


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
