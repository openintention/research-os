from __future__ import annotations

import math
import re
import sqlite3
from urllib.parse import urlparse
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


class EventIngestionError(ValueError):
    pass


class EventConflictError(RuntimeError):
    pass


_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_HANDLE_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_DIFF_DIRECTIONS = {"min", "max"}
_RUN_STATUSES = {"success", "failed", "error", "timeout", "cancelled"}
_PARTICIPANT_ROLES = {"contributor", "verifier"}
_SHA256_DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_MANIFEST_PROVENANCE_VERSION_RE = re.compile(r"^[1-9][0-9]*$")
_MANIFEST_PROVENANCE_SCHEMA_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{3,63}$")
_KNOWN_MANIFEST_PROVENANCE_SCHEMAS = {
    "openintention-artifact-manifest-v1",
}


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
        self.append_event(event)
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
        self._validate_incoming_event(event)
        try:
            self.store.append(event)
        except sqlite3.IntegrityError as exc:
            raise EventConflictError(f"event_id {event.event_id} already exists") from exc
        return event

    def _validate_incoming_event(self, event: EventEnvelope) -> None:
        if event.actor_id is not None:
            self._require_identifier_value(
                key="actor_id",
                value=event.actor_id,
                pattern=_HANDLE_RE,
                max_length=64,
            )

        match event.kind:
            case EventKind.WORKSPACE_STARTED:
                self._validate_workspace_started(event)
            case EventKind.SNAPSHOT_PUBLISHED:
                workspace = self._require_existing_workspace(event.workspace_id)
                self._validate_snapshot_published(event, workspace=workspace)
            case EventKind.RUN_COMPLETED:
                workspace = self._require_existing_workspace(event.workspace_id)
                self._validate_run_completed(event, workspace=workspace)
            case EventKind.CLAIM_ASSERTED:
                workspace = self._require_existing_workspace(event.workspace_id)
                self._validate_claim_asserted(event, workspace=workspace)
            case EventKind.CLAIM_REPRODUCED:
                workspace = self._require_existing_workspace(event.workspace_id)
                self._validate_claim_feedback(event, workspace=workspace, reproduced=True)
            case EventKind.CLAIM_CONTRADICTED:
                workspace = self._require_existing_workspace(event.workspace_id)
                self._validate_claim_feedback(event, workspace=workspace, reproduced=False)
            case EventKind.ADOPTION_RECORDED:
                workspace = self._require_existing_workspace(event.workspace_id)
                self._validate_adoption_recorded(event, workspace=workspace)
            case EventKind.SUMMARY_PUBLISHED:
                workspace = self._require_existing_workspace(event.workspace_id)
                self._validate_summary_published(event, workspace=workspace)
            case EventKind.EFFORT_ROLLED_OVER:
                self._validate_effort_rolled_over(event)
            case _:
                raise EventIngestionError(f"unsupported event kind: {event.kind}")

    def _validate_workspace_started(self, event: EventEnvelope) -> None:
        payload = event.payload
        self._require_non_empty_string(payload, "name", max_length=128)
        self._require_non_empty_string(payload, "objective", max_length=64)
        self._require_non_empty_string(payload, "platform", max_length=64)
        self._require_int(payload, "budget_seconds", minimum=1)
        effort_id = payload.get("effort_id")
        if effort_id is not None:
            self._require_identifier(
                payload,
                key="effort_id",
                pattern=_IDENTIFIER_RE,
                max_length=128,
            )
            if self.get_effort(str(effort_id)) is None:
                raise EventIngestionError("workspace.started effort_id must reference a known effort")
        participant_role = payload.get("participant_role")
        if participant_role is not None and participant_role not in _PARTICIPANT_ROLES:
            raise EventIngestionError("workspace.started participant_role must be contributor or verifier")

        if event.workspace_id is None:
            raise EventIngestionError("workspace.started requires workspace_id")

        if self.get_workspace(event.workspace_id) is not None:
            raise EventIngestionError(f"workspace {event.workspace_id} is already started")
        self._require_equal(event.aggregate_id, event.workspace_id, "workspace.started aggregate_id")
        if event.aggregate_kind is not None and event.aggregate_kind != "workspace":
            raise EventIngestionError("workspace.started aggregate_kind must be 'workspace'")

    def _validate_snapshot_published(self, event: EventEnvelope, *, workspace: WorkspaceView) -> None:
        payload = event.payload
        snapshot_id = self._require_identifier(
            payload,
            key="snapshot_id",
            pattern=_IDENTIFIER_RE,
            max_length=128,
        )
        self._require_non_empty_string(payload, "artifact_uri")
        self._validate_artifact_uri(payload["artifact_uri"])
        source_bundle_digest = payload.get("source_bundle_digest")
        self._validate_optional_digest(source_bundle_digest)
        self._validate_optional_manifest_attestation(
            manifest_uri=payload.get("source_bundle_manifest_uri"),
            manifest_digest=payload.get("source_bundle_manifest_digest"),
            manifest_signature=payload.get("source_bundle_manifest_signature"),
            field_prefix="source_bundle_manifest",
            provenance_schema=payload.get("source_bundle_manifest_provenance_schema"),
            provenance_version=payload.get("source_bundle_manifest_provenance_version"),
            signature_scheme=payload.get("source_bundle_manifest_signature_scheme"),
        )
        self._validate_digest_alignment(
            field_prefix="snapshot",
            artifact_uri=payload["artifact_uri"],
            source_bundle_digest=source_bundle_digest,
        )
        self._require_equal(event.aggregate_id, snapshot_id, "snapshot aggregate_id")
        if event.aggregate_kind is not None and event.aggregate_kind != "snapshot":
            raise EventIngestionError("snapshot.published aggregate_kind must be 'snapshot'")

    def _validate_run_completed(self, event: EventEnvelope, *, workspace: WorkspaceView) -> None:
        payload = event.payload
        run_id = self._require_identifier(
            payload,
            key="run_id",
            pattern=_IDENTIFIER_RE,
            max_length=128,
        )
        snapshot_id = self._require_identifier(
            payload,
            key="snapshot_id",
            pattern=_IDENTIFIER_RE,
            max_length=128,
        )
        objective = self._require_non_empty_string(payload, "objective", max_length=64)
        platform = self._require_non_empty_string(payload, "platform", max_length=64)
        self._require_non_empty_string(payload, "metric_name", max_length=64)
        self._require_int(payload, "budget_seconds", minimum=1, maximum=86400)
        self._require_non_empty_string(payload, "direction")
        if payload["direction"] not in _DIFF_DIRECTIONS:
            raise EventIngestionError(f"run.completed direction must be one of {_DIFF_DIRECTIONS}")
        self._require_non_empty_string(payload, "status")
        if payload["status"] not in _RUN_STATUSES:
            raise EventIngestionError(
                f"run.completed status must be one of {sorted(_RUN_STATUSES)}"
            )
        metric_value = self._require_number(payload, "metric_value")
        if not math.isfinite(metric_value):
            raise EventIngestionError("run.completed metric_value must be finite")

        if objective != workspace.objective:
            raise EventIngestionError("run.completed objective must match workspace objective")
        if platform != workspace.platform:
            raise EventIngestionError("run.completed platform must match workspace platform")
        if int(payload["budget_seconds"]) != workspace.budget_seconds:
            raise EventIngestionError("run.completed budget_seconds must match workspace budget_seconds")
        if snapshot_id not in self._snapshot_ids_for_workspace(workspace.workspace_id):
            raise EventIngestionError("run.completed snapshot_id must reference a known workspace snapshot")
        if event.aggregate_kind is not None and event.aggregate_kind != "run":
            raise EventIngestionError("run.completed aggregate_kind must be 'run'")
        self._require_equal(event.aggregate_id, run_id, "run aggregate_id")

    def _validate_claim_asserted(self, event: EventEnvelope, *, workspace: WorkspaceView) -> None:
        payload = event.payload
        claim_id = self._require_identifier(
            payload,
            key="claim_id",
            pattern=_IDENTIFIER_RE,
            max_length=128,
        )
        self._require_non_empty_string(payload, "statement", max_length=2048)
        self._require_non_empty_string(payload, "claim_type", max_length=64)
        candidate_snapshot_id = self._require_identifier(
            payload,
            key="candidate_snapshot_id",
            pattern=_IDENTIFIER_RE,
            max_length=128,
        )
        objective = self._require_non_empty_string(payload, "objective", max_length=64)
        platform = self._require_non_empty_string(payload, "platform", max_length=64)
        self._require_equal(event.aggregate_id, claim_id, "claim aggregate_id")
        if event.aggregate_kind is not None and event.aggregate_kind != "claim":
            raise EventIngestionError("claim.asserted aggregate_kind must be 'claim'")
        if objective != workspace.objective:
            raise EventIngestionError("claim.asserted objective must match workspace objective")
        if platform != workspace.platform:
            raise EventIngestionError("claim.asserted platform must match workspace platform")
        snapshot_ids = self._snapshot_ids_for_workspace(workspace.workspace_id)
        if candidate_snapshot_id not in snapshot_ids:
            raise EventIngestionError(
                "claim.asserted candidate_snapshot_id must reference a known workspace snapshot"
            )
        candidate_snapshot_manifest_uri = payload.get("candidate_snapshot_manifest_uri")
        candidate_snapshot_manifest_digest = payload.get("candidate_snapshot_manifest_digest")
        self._validate_optional_manifest_attestation(
            manifest_uri=candidate_snapshot_manifest_uri,
            manifest_digest=candidate_snapshot_manifest_digest,
            manifest_signature=payload.get("candidate_snapshot_manifest_signature"),
            field_prefix="candidate_snapshot_manifest",
            provenance_schema=payload.get("candidate_snapshot_manifest_provenance_schema"),
            provenance_version=payload.get("candidate_snapshot_manifest_provenance_version"),
            signature_scheme=payload.get("candidate_snapshot_manifest_signature_scheme"),
        )
        self._validate_candidate_snapshot_provenance_alignment(
            workspace_id=workspace.workspace_id,
            candidate_snapshot_id=payload["candidate_snapshot_id"],
            candidate_manifest_uri=candidate_snapshot_manifest_uri,
            candidate_manifest_digest=candidate_snapshot_manifest_digest,
        )
        evidence_run_ids = payload.get("evidence_run_ids")
        normalized_evidence_run_ids = self._require_string_list(evidence_run_ids, optional=True)
        workspace_run_ids = self._run_ids_for_workspace(workspace.workspace_id)
        for run_id in normalized_evidence_run_ids:
            if run_id not in workspace_run_ids:
                raise EventIngestionError(
                    "claim.asserted evidence_run_ids must reference known workspace runs"
                )
        baseline_snapshot_id = payload.get("baseline_snapshot_id")
        if baseline_snapshot_id is not None:
            if not isinstance(baseline_snapshot_id, str):
                raise EventIngestionError("claim.asserted baseline_snapshot_id must be a string")
            if not _IDENTIFIER_RE.match(baseline_snapshot_id):
                raise EventIngestionError("claim.asserted baseline_snapshot_id has invalid characters")
            if baseline_snapshot_id not in snapshot_ids:
                raise EventIngestionError(
                    "claim.asserted baseline_snapshot_id must reference a known workspace snapshot"
                )
        metric_name = payload.get("metric_name")
        if metric_name is not None:
            self._require_non_empty_string(payload, "metric_name", max_length=64)

    def _validate_claim_feedback(self, event: EventEnvelope, *, workspace: WorkspaceView, reproduced: bool) -> None:
        payload = event.payload
        claim_id = self._require_identifier(
            payload,
            key="claim_id",
            pattern=_IDENTIFIER_RE,
            max_length=128,
        )
        if not any(claim.claim_id == claim_id for claim in self.store.list_claims()):
            raise EventIngestionError("claim id does not exist")
        self._require_identifier(
            payload,
            key="evidence_run_id",
            pattern=_IDENTIFIER_RE,
            max_length=128,
        )
        event_kind = "claim.reproduced" if reproduced else "claim.contradicted"
        if payload["evidence_run_id"] not in self._run_ids_for_workspace(workspace.workspace_id):
            raise EventIngestionError(
                f"{event_kind} evidence_run_id must reference a known workspace run"
            )
        if event.aggregate_kind is not None and event.aggregate_kind != "claim":
            raise EventIngestionError(f"{event_kind} aggregate_kind must be 'claim'")
        self._require_equal(event.aggregate_id, claim_id, f"{event_kind} aggregate_id")

    def _validate_adoption_recorded(self, event: EventEnvelope, *, workspace: WorkspaceView) -> None:
        payload = event.payload
        if payload.get("subject_type") != "claim":
            raise EventIngestionError("adoption.recorded subject_type must be 'claim'")
        if "subject_id" not in payload or not isinstance(payload["subject_id"], str):
            raise EventIngestionError("adoption.recorded subject_id is required and must be a string")
        if not _IDENTIFIER_RE.match(payload["subject_id"]):
            raise EventIngestionError("adoption.recorded subject_id has invalid characters")
        if not any(claim.claim_id == payload["subject_id"] for claim in self.store.list_claims()):
            raise EventIngestionError("adoption.recorded subject_id does not exist")
        self._require_identifier(payload, "from_workspace_id", _IDENTIFIER_RE, max_length=128)
        if self.get_workspace(payload["from_workspace_id"]) is None:
            raise EventIngestionError("adoption.recorded from_workspace_id must reference a known workspace")
        if event.aggregate_kind is not None and event.aggregate_kind != "adoption":
            raise EventIngestionError("adoption.recorded aggregate_kind must be 'adoption'")

    def _validate_summary_published(self, event: EventEnvelope, *, workspace: WorkspaceView) -> None:
        payload = event.payload
        self._require_non_empty_string(payload, "summary_id", max_length=128)
        self._require_non_empty_string(payload, "title", max_length=128)
        self._require_non_empty_string(payload, "format", max_length=32)
        artifact_uri = payload.get("artifact_uri")
        if artifact_uri is not None:
            self._validate_artifact_uri(artifact_uri)
        if event.aggregate_kind is not None and event.aggregate_kind != "summary":
            raise EventIngestionError("summary.published aggregate_kind must be 'summary'")

    def _validate_effort_rolled_over(self, event: EventEnvelope) -> None:
        payload = event.payload
        source_id = self._require_identifier(
            payload,
            key="effort_id",
            pattern=_IDENTIFIER_RE,
            max_length=128,
        )
        self._require_identifier(
            payload,
            key="successor_effort_id",
            pattern=_IDENTIFIER_RE,
            max_length=128,
        )
        self._require_equal(event.aggregate_id, source_id, "effort.rolled_over aggregate_id")
        if event.aggregate_kind is not None and event.aggregate_kind != "effort":
            raise EventIngestionError("effort.rolled_over aggregate_kind must be 'effort'")

    def _require_existing_workspace(self, workspace_id: str | None) -> WorkspaceView:
        if workspace_id is None:
            raise EventIngestionError("event requires workspace_id")
        workspace = self.get_workspace(workspace_id)
        if workspace is None:
            raise EventIngestionError(f"unknown workspace_id: {workspace_id}")
        return workspace

    def _require_identifier(
        self,
        payload: dict[str, object],
        key: str,
        pattern: re.Pattern[str],
        *,
        max_length: int,
        optional: bool = False,
    ) -> str:
        value = payload.get(key)
        if value is None:
            if optional:
                return ""
            raise EventIngestionError(f"{key} is required")
        if not isinstance(value, str):
            raise EventIngestionError(f"{key} must be a string")
        if not value:
            raise EventIngestionError(f"{key} must be a non-empty string")
        if len(value) > max_length:
            raise EventIngestionError(f"{key} exceeds max length of {max_length}")
        if not pattern.match(value):
            raise EventIngestionError(f"{key} has invalid characters")
        return value

    def _require_non_empty_string(
        self,
        payload: dict[str, object],
        key: str,
        *,
        max_length: int = 2048,
        optional: bool = False,
    ) -> str:
        value = payload.get(key)
        if value is None:
            if optional:
                return ""
            raise EventIngestionError(f"{key} is required")
        if not isinstance(value, str) or not value.strip():
            raise EventIngestionError(f"{key} must be a non-empty string")
        normalized = value.strip()
        if len(normalized) > max_length:
            raise EventIngestionError(f"{key} exceeds max length of {max_length}")
        return normalized

    def _require_int(
        self,
        payload: dict[str, object],
        key: str,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
        optional: bool = False,
    ) -> int:
        value = payload.get(key)
        if value is None:
            if optional:
                return 0
            raise EventIngestionError(f"{key} is required")
        if not isinstance(value, int) or isinstance(value, bool):
            raise EventIngestionError(f"{key} must be an integer")
        if minimum is not None and value < minimum:
            raise EventIngestionError(f"{key} must be >= {minimum}")
        if maximum is not None and value > maximum:
            raise EventIngestionError(f"{key} must be <= {maximum}")
        return int(value)

    def _require_number(self, payload: dict[str, object], key: str) -> float:
        value = payload.get(key)
        if value is None:
            raise EventIngestionError(f"{key} is required")
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise EventIngestionError(f"{key} must be a number")
        return float(value)

    def _require_equal(self, actual: str | None, expected: str, field: str) -> None:
        if actual != expected:
            raise EventIngestionError(f"{field} must be {expected}")

    def _require_identifier_value(self, key: str, value: str, pattern: re.Pattern[str], max_length: int) -> str:
        if not isinstance(value, str):
            raise EventIngestionError(f"{key} must be a string")
        if not value:
            raise EventIngestionError(f"{key} must be a non-empty string")
        if len(value) > max_length:
            raise EventIngestionError(f"{key} exceeds max length of {max_length}")
        if not pattern.match(value):
            raise EventIngestionError(f"{key} has invalid characters")
        return value

    def _require_string_list(self, value: object, optional: bool = False) -> list[str]:
        if value is None:
            if optional:
                return []
            return []
        if not isinstance(value, list):
            raise EventIngestionError("evidence_run_ids must be a list")
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item:
                raise EventIngestionError("evidence_run_ids must contain non-empty strings")
            if not _IDENTIFIER_RE.match(item):
                raise EventIngestionError("evidence_run_ids contains invalid identifier")
            normalized.append(item)
        return normalized

    def _validate_artifact_uri(self, value: object) -> None:
        if not isinstance(value, str):
            raise EventIngestionError("artifact_uri must be a string")
        if len(value) == 0 or len(value) > 2048:
            raise EventIngestionError("artifact_uri has invalid length")
        parsed = urlparse(value)
        if parsed.scheme == "":
            raise EventIngestionError("artifact_uri must be an absolute URI")
        if parsed.scheme not in {"artifact", "http", "https", "file"}:
            raise EventIngestionError("artifact_uri must use artifact, http, https, or file scheme")
        if parsed.scheme == "artifact":
            artifact_path = parsed.netloc
            if parsed.path:
                artifact_path = f"{artifact_path}/{parsed.path.lstrip('/')}"
            artifact_path = artifact_path.lstrip("/")
            if not re.match(r"^sha256/[a-f0-9]{64}$", artifact_path):
                raise EventIngestionError("artifact_uri must reference a digest")
            return
        if parsed.scheme in {"http", "https", "file"} and not parsed.netloc and parsed.scheme != "file":
            raise EventIngestionError("artifact_uri is missing host")

    def _validate_optional_digest(self, digest: object) -> None:
        if digest is None:
            return
        if not isinstance(digest, str):
            raise EventIngestionError("source_bundle_digest must be a string")
        if not digest.startswith("sha256:"):
            raise EventIngestionError("source_bundle_digest must be a sha256 digest")

    def _validate_optional_strict_digest(self, digest: object, field_name: str) -> None:
        if digest is None:
            return
        if not isinstance(digest, str):
            raise EventIngestionError(f"{field_name} must be a string")
        if not _SHA256_DIGEST_RE.match(digest):
            raise EventIngestionError(f"{field_name} must be a sha256 digest")

    def _validate_optional_manifest_attestation(
        self,
        *,
        manifest_uri: object,
        manifest_digest: object,
        manifest_signature: object,
        field_prefix: str,
        provenance_schema: object,
        provenance_version: object,
        signature_scheme: object,
    ) -> None:
        if manifest_uri is None and manifest_digest is None and manifest_signature is None:
            if provenance_schema is None and provenance_version is None and signature_scheme is None:
                return
            raise EventIngestionError(f"{field_prefix}_uri is required when manifest provenance is provided")

        if manifest_uri is None:
            raise EventIngestionError(f"{field_prefix}_uri is required when manifest provenance is provided")

        if not isinstance(manifest_uri, str) or not manifest_uri.strip():
            raise EventIngestionError(f"{field_prefix}_uri must be a non-empty string")
        self._validate_artifact_uri(manifest_uri)

        if manifest_digest is not None and not isinstance(manifest_digest, str):
            raise EventIngestionError(f"{field_prefix}_digest must be a string")
        self._validate_optional_strict_digest(manifest_digest, f"{field_prefix}_digest")

        if manifest_signature is not None and not isinstance(manifest_signature, str):
            raise EventIngestionError(f"{field_prefix}_signature must be a string")
        if manifest_signature is not None and not manifest_signature.strip():
            raise EventIngestionError(f"{field_prefix}_signature must be a non-empty string")
        if manifest_signature is not None and manifest_digest is None:
            raise EventIngestionError(
                f"{field_prefix}_signature requires {field_prefix}_digest for validation context"
            )

        if manifest_digest is not None:
            manifest_digest_from_uri = self._extract_artifact_digest(manifest_uri)
            if manifest_digest_from_uri is not None:
                if manifest_digest != f"sha256:{manifest_digest_from_uri}":
                    raise EventIngestionError(
                        f"{field_prefix}_digest must match digest in {field_prefix}_uri"
                    )

        if provenance_schema is None and provenance_version is None and signature_scheme is None:
            return

        if provenance_schema is None and provenance_version is not None:
            raise EventIngestionError(
                f"{field_prefix}_provenance_schema is required when "
                f"{field_prefix}_provenance_version is provided"
            )
        if provenance_version is None and provenance_schema is not None:
            raise EventIngestionError(
                f"{field_prefix}_provenance_version is required when "
                f"{field_prefix}_provenance_schema is provided"
            )

        if not isinstance(provenance_schema, str):
            raise EventIngestionError(f"{field_prefix}_provenance_schema must be a string")
        if not _MANIFEST_PROVENANCE_SCHEMA_RE.match(provenance_schema):
            raise EventIngestionError(
                f"{field_prefix}_provenance_schema must match {_MANIFEST_PROVENANCE_SCHEMA_RE.pattern}"
            )
        if provenance_schema not in _KNOWN_MANIFEST_PROVENANCE_SCHEMAS:
            raise EventIngestionError(
                f"{field_prefix}_provenance_schema is unsupported: {provenance_schema}"
            )

        if not isinstance(provenance_version, str):
            raise EventIngestionError(f"{field_prefix}_provenance_version must be a string")
        if not provenance_version.strip():
            raise EventIngestionError(f"{field_prefix}_provenance_version must be a non-empty string")
        if not _MANIFEST_PROVENANCE_VERSION_RE.match(provenance_version):
            raise EventIngestionError(f"{field_prefix}_provenance_version must be an integer version string")

        if manifest_signature is not None and signature_scheme is None:
            raise EventIngestionError(
                f"{field_prefix}_signature_scheme is required when {field_prefix}_signature is provided"
            )
        if signature_scheme is not None:
            if not isinstance(signature_scheme, str):
                raise EventIngestionError(f"{field_prefix}_signature_scheme must be a string")
            if not signature_scheme.strip():
                raise EventIngestionError(f"{field_prefix}_signature_scheme must be a non-empty string")

    def _extract_artifact_digest(self, artifact_uri: str) -> str | None:
        parsed = urlparse(artifact_uri)
        if parsed.scheme != "artifact":
            return None
        artifact_path = parsed.netloc
        if parsed.path:
            artifact_path = f"{artifact_path}/{parsed.path.lstrip('/')}"
        artifact_path = artifact_path.lstrip("/")
        match = re.match(r"^sha256/([a-f0-9]{64})$", artifact_path)
        if not match:
            return None
        return match.group(1)

    def _validate_digest_alignment(
        self,
        *,
        field_prefix: str,
        artifact_uri: str,
        source_bundle_digest: object | None,
    ) -> None:
        if source_bundle_digest is None:
            return
        if not isinstance(source_bundle_digest, str):
            raise EventIngestionError(f"{field_prefix}_source_bundle_digest must be a string")
        if not source_bundle_digest.startswith("sha256:"):
            raise EventIngestionError(f"{field_prefix}_source_bundle_digest must be a sha256 digest")
        artifact_digest = self._extract_artifact_digest(artifact_uri)
        if artifact_digest is None:
            return
        if source_bundle_digest != f"sha256:{artifact_digest}":
            raise EventIngestionError(
                f"{field_prefix}_source_bundle_digest must match digest in artifact_uri"
            )

    def _validate_candidate_snapshot_provenance_alignment(
        self,
        *,
        workspace_id: str,
        candidate_snapshot_id: str,
        candidate_manifest_uri: object,
        candidate_manifest_digest: object,
    ) -> None:
        if candidate_manifest_uri is None and candidate_manifest_digest is None:
            return

        snapshot_event = self._get_snapshot_by_id(workspace_id, candidate_snapshot_id)
        if snapshot_event is None:
            return
        snapshot_payload = snapshot_event.payload
        source_snapshot_manifest_uri = snapshot_payload.get("source_bundle_manifest_uri")
        source_snapshot_manifest_digest = snapshot_payload.get("source_bundle_manifest_digest")
        if (
            source_snapshot_manifest_uri is not None
            and candidate_manifest_uri is not None
            and source_snapshot_manifest_uri != candidate_manifest_uri
        ):
            raise EventIngestionError(
                "claim.asserted candidate snapshot manifest uri does not match source snapshot provenance"
            )
        if (
            source_snapshot_manifest_digest is not None
            and candidate_manifest_digest is not None
            and source_snapshot_manifest_digest != candidate_manifest_digest
        ):
            raise EventIngestionError(
                "claim.asserted candidate snapshot manifest digest does not match source snapshot provenance"
            )

    def _get_snapshot_by_id(self, workspace_id: str, snapshot_id: str) -> EventEnvelope | None:
        for event in self.store.list(
            workspace_id=workspace_id,
            kind=EventKind.SNAPSHOT_PUBLISHED,
            limit=10_000,
        ):
            snapshot_id_from_event = event.payload.get("snapshot_id")
            if snapshot_id_from_event == snapshot_id:
                return event
        return None

    def _snapshot_ids_for_workspace(self, workspace_id: str) -> set[str]:
        return {
            str(event.payload.get("snapshot_id"))
            for event in self.store.list(workspace_id=workspace_id, kind=EventKind.SNAPSHOT_PUBLISHED, limit=10_000)
            if isinstance(event.payload.get("snapshot_id"), str)
        }

    def _run_ids_for_workspace(self, workspace_id: str) -> set[str]:
        return {
            str(event.payload.get("run_id"))
            for event in self.store.list(workspace_id=workspace_id, kind=EventKind.RUN_COMPLETED, limit=10_000)
            if isinstance(event.payload.get("run_id"), str)
        }

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
        claim_events = [
            event
            for event in events
            if event.kind == EventKind.CLAIM_ASSERTED and event.payload.get("candidate_snapshot_id") == snapshot_id
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
            claim_events=claim_events,
        )
