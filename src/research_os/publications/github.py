from __future__ import annotations

import shlex

from research_os.effort_lifecycle import is_historical_proof_effort
from research_os.effort_lifecycle import is_public_proof_effort
from research_os.effort_lifecycle import proof_version
from research_os.domain.models import (
    ClaimSummary,
    EffortView,
    EventEnvelope,
    EventKind,
    FrontierView,
    PublicationView,
    WorkspaceView,
)


def render_workspace_discussion(
    workspace: WorkspaceView,
    *,
    events: list[EventEnvelope],
    claims: list[ClaimSummary],
) -> PublicationView:
    recent_events = sorted(events, key=lambda event: event.occurred_at, reverse=True)[:5]
    claim_lines = _render_claim_lines(claims)
    provenance_lines = _render_workspace_provenance_lines(events=events, claims=claims)
    event_lines = [
        f"- `{event.kind}` at {event.occurred_at.isoformat()} on `{event.aggregate_id or event.workspace_id}`"
        for event in recent_events
    ]
    body = "\n".join(
        [
            f"# Discussion: {workspace.name}",
            "",
            "## Workspace",
            *( [f"- Started by: `{workspace.actor_id}`"] if workspace.actor_id else [] ),
            f"- Role: `{workspace.participant_role}`",
            f"- Objective: `{workspace.objective}`",
            f"- Platform: `{workspace.platform}`",
            f"- Budget seconds: `{workspace.budget_seconds}`",
            f"- Updated at: `{workspace.updated_at.isoformat()}`",
            *(["- Description: " + workspace.description] if workspace.description else []),
            "",
            "## State",
            f"- Snapshots: {len(workspace.snapshot_ids)}",
            f"- Runs: {len(workspace.run_ids)}",
            f"- Claims: {len(workspace.claim_ids)}",
            f"- Reproductions: {workspace.reproduction_count}",
            f"- Adoptions: {workspace.adoption_count}",
            f"- Summaries: {workspace.summary_count}",
            f"- Events: {workspace.event_count}",
            "",
            "## Claim Signals",
            *claim_lines,
            *(["", "## Provenance"] if provenance_lines else []),
            *provenance_lines,
            "",
            "## Recent Events",
            *event_lines,
        ]
    )
    return PublicationView(
        kind="github.discussion",
        format="markdown",
        title=f"Discussion mirror for {workspace.name}",
        body=body,
    )


def render_snapshot_pull_request(
    workspace: WorkspaceView,
    *,
    snapshot_event: EventEnvelope,
    run_events: list[EventEnvelope],
    claims: list[ClaimSummary],
    claim_events: list[EventEnvelope] | None = None,
) -> PublicationView:
    payload = snapshot_event.payload
    best_run = _select_best_run(run_events)
    snapshot_provenance_lines = _render_manifest_metadata_lines(
        payload=payload,
        manifest_prefix="source_bundle_manifest",
        title=f"snapshot `{payload['snapshot_id']}`",
    )
    claim_lines = _render_claim_lines(claims)
    candidate_claim_provenance_lines = _render_candidate_snapshot_provenance_lines(
        snapshot_id=payload["snapshot_id"],
        claim_events=claim_events or [],
    )
    body_lines = [
        f"# PR: {payload['snapshot_id']}",
        "",
        "## Context",
        f"- Workspace: `{workspace.name}`",
        f"- Objective: `{workspace.objective}`",
        f"- Platform: `{workspace.platform}`",
        f"- Budget seconds: `{workspace.budget_seconds}`",
        "",
        "## Snapshot",
        f"- Snapshot ID: `{payload['snapshot_id']}`",
        f"- Parent snapshots: {', '.join(payload.get('parent_snapshot_ids', [])) or 'none'}",
        f"- Git ref: `{payload.get('git_ref') or 'n/a'}`",
        f"- Source bundle digest: `{payload.get('source_bundle_digest') or 'n/a'}`",
        f"- Artifact reference: `{_render_artifact_reference(payload)}`",
    ]

    if payload.get("notes"):
        body_lines.append(f"- Notes: {payload['notes']}")

    body_lines.extend(["", "## Run Summary"])
    if best_run is None:
        body_lines.append("- No completed runs recorded for this snapshot.")
    else:
        run_payload = best_run.payload
        body_lines.extend(
            [
                f"- Best run: `{run_payload['run_id']}`",
                f"- Metric: `{run_payload['metric_name']}` = `{run_payload['metric_value']}`",
                f"- Direction: `{run_payload['direction']}`",
                f"- Status: `{run_payload['status']}`",
            ]
        )
        body_lines.extend(["", "## Recorded Runs", *_render_run_lines(run_events)])

    if snapshot_provenance_lines:
        body_lines.extend(["", "## Snapshot Provenance", *snapshot_provenance_lines])
    if candidate_claim_provenance_lines:
        body_lines.extend(["", "## Candidate Claim Provenance", *candidate_claim_provenance_lines])
    body_lines.extend(["", "## Claim Signals", *claim_lines])
    return PublicationView(
        kind="github.pull_request",
        format="markdown",
        title=f"PR mirror for {payload['snapshot_id']}",
        body="\n".join(body_lines),
    )


def render_effort_overview(
    effort: EffortView,
    *,
    workspaces: list[WorkspaceView],
    claims: list[ClaimSummary],
    frontier: FrontierView,
    public_base_url: str | None = None,
) -> PublicationView:
    ordered_workspaces = sorted(workspaces, key=lambda workspace: workspace.updated_at, reverse=True)
    workspace_lines = [
        (
            f"- `{workspace.name}` ({workspace.workspace_id}) "
            f"actor={workspace.actor_id or 'unknown'}, "
            f"role={workspace.participant_role}, "
            f"runs={len(workspace.run_ids)}, claims={len(workspace.claim_ids)}, "
            f"reproductions={workspace.reproduction_count}, "
            f"updated={workspace.updated_at.isoformat()}"
        )
        for workspace in ordered_workspaces[:5]
    ] or ["- No workspaces attached yet."]

    frontier_lines = [
        (
            f"- `{member.snapshot_id}` from `{member.workspace_id}`: "
            f"`{member.metric_name}` = `{member.metric_value}` "
            f"({member.direction}, claims={member.claim_count})"
        )
        for member in frontier.members[:5]
    ] or ["- No frontier members recorded yet."]

    claim_lines = _render_claim_lines(claims)
    join_command = _render_effort_join_command(effort, public_base_url=public_base_url)
    join_brief = _render_effort_join_brief(effort)
    body = "\n".join(
        [
            f"# Effort: {effort.name}",
            "",
            "## Objective",
            f"- Objective: `{effort.objective}`",
            f"- Platform: `{effort.platform}`",
            f"- Budget seconds: `{effort.budget_seconds}`",
            *(["- Summary: " + effort.summary] if effort.summary else []),
            *_render_effort_lifecycle_lines(effort),
            "",
            "## Current State",
            f"- Attached workspaces: {len(workspaces)}",
            f"- Claims in effort scope: {len(claims)}",
            f"- Frontier members: {len(frontier.members)}",
            f"- Updated at: `{effort.updated_at.isoformat()}`",
            "",
            "## Active Workspaces",
            *workspace_lines,
            "",
            "## Frontier Highlights",
            *frontier_lines,
            "",
            "## Claim Signals",
            *claim_lines,
            "",
            "## Join",
            f"- Read the effort brief in `{join_brief}`.",
            "- Optional: add `--actor-id <handle>` to make lightweight participant attribution visible.",
            f"- Run `{join_command}`",
        ]
    )
    return PublicationView(
        kind="github.issue",
        format="markdown",
        title=f"Effort overview for {effort.name}",
        body=body,
    )


def _render_claim_lines(claims: list[ClaimSummary]) -> list[str]:
    if not claims:
        return ["- No claims recorded yet."]

    ordered_claims = _sort_claims(claims)
    return [
        (
            f"- `{claim.claim_id}` [{claim.status}] {claim.statement} "
            f"(support={claim.support_count}, contradictions={claim.contradiction_count})"
        )
        for claim in ordered_claims
    ]


def _is_manifest_field_present(payload: dict[str, object], manifest_prefix: str) -> bool:
    return any(payload.get(f"{manifest_prefix}_{suffix}") is not None for suffix in _MANIFEST_FIELD_SUFFIXES)


def _render_run_lines(run_events: list[EventEnvelope]) -> list[str]:
    ordered_runs = sorted(run_events, key=lambda event: event.occurred_at, reverse=True)
    return [
        (
            f"- `{event.payload['run_id']}`: `{event.payload['metric_name']}` = "
            f"`{event.payload['metric_value']}` ({event.payload['status']})"
        )
        for event in ordered_runs
    ]


def _select_best_run(run_events: list[EventEnvelope]) -> EventEnvelope | None:
    successful_runs = [event for event in run_events if event.payload.get("status") == "success"]
    if not successful_runs:
        return None

    best = successful_runs[0]
    for candidate in successful_runs[1:]:
        if _is_better_run(candidate, best):
            best = candidate
    return best


def _is_better_run(candidate: EventEnvelope, existing: EventEnvelope) -> bool:
    candidate_payload = candidate.payload
    existing_payload = existing.payload
    if candidate_payload["direction"] != existing_payload["direction"]:
        return candidate.occurred_at > existing.occurred_at
    if candidate_payload["direction"] == "min":
        return float(candidate_payload["metric_value"]) < float(existing_payload["metric_value"])
    return float(candidate_payload["metric_value"]) > float(existing_payload["metric_value"])


_MANIFEST_FIELD_SUFFIXES = (
    "uri",
    "digest",
    "signature",
    "provenance_schema",
    "provenance_version",
    "signature_scheme",
)
_MANIFEST_FIELD_LABELS = {
    "uri": "Manifest URI",
    "digest": "Manifest digest",
    "signature": "Manifest signature",
    "provenance_schema": "Provenance schema",
    "provenance_version": "Provenance version",
    "signature_scheme": "Signature scheme",
}


def _render_workspace_provenance_lines(
    *, events: list[EventEnvelope], claims: list[ClaimSummary]
) -> list[str]:
    snapshot_lines: list[str] = []
    seen_snapshot_ids: set[str] = set()
    for event in events:
        if event.kind != EventKind.SNAPSHOT_PUBLISHED:
            continue
        payload = event.payload
        snapshot_id = payload.get("snapshot_id")
        if not isinstance(snapshot_id, str):
            continue
        if snapshot_id in seen_snapshot_ids:
            continue
        if not _is_manifest_field_present(payload, "source_bundle_manifest"):
            continue
        snapshot_lines.extend(
            _render_manifest_metadata_lines(
                payload=payload,
                manifest_prefix="source_bundle_manifest",
                title=f"snapshot `{snapshot_id}`",
            )
        )
        seen_snapshot_ids.add(snapshot_id)

    claim_events = {
        str(event.payload["claim_id"]): event
        for event in events
        if event.kind == EventKind.CLAIM_ASSERTED and isinstance(event.payload.get("claim_id"), str)
    }
    claim_lines: list[str] = []
    for claim in _sort_claims(claims):
        claim_event = claim_events.get(claim.claim_id)
        if claim_event is None:
            continue
        if not _is_manifest_field_present(claim_event.payload, "candidate_snapshot_manifest"):
            continue
        claim_lines.extend(
            _render_manifest_metadata_lines(
                payload=claim_event.payload,
                manifest_prefix="candidate_snapshot_manifest",
                title=f"claim `{claim.claim_id}`",
            )
        )
    return snapshot_lines + claim_lines


def _sort_claims(claims: list[ClaimSummary]) -> list[ClaimSummary]:
    return sorted(claims, key=lambda claim: (claim.updated_at, claim.claim_id), reverse=True)


def _render_candidate_snapshot_provenance_lines(
    *,
    snapshot_id: str,
    claim_events: list[EventEnvelope],
) -> list[str]:
    relevant_claim_lines: list[str] = []
    seen_claim_ids: set[str] = set()
    for event in claim_events:
        payload = event.payload
        if payload.get("candidate_snapshot_id") != snapshot_id:
            continue
        if not _is_manifest_field_present(payload, "candidate_snapshot_manifest"):
            continue
        claim_id = payload.get("claim_id")
        title_claim = claim_id if isinstance(claim_id, str) else snapshot_id
        if title_claim in seen_claim_ids:
            continue
        seen_claim_ids.add(title_claim)
        relevant_claim_lines.extend(
            _render_manifest_metadata_lines(
                payload=payload,
                manifest_prefix="candidate_snapshot_manifest",
                title=f"candidate claim `{title_claim}`",
            )
        )
    return relevant_claim_lines


def _render_manifest_metadata_lines(
    *,
    payload: dict[str, object],
    manifest_prefix: str,
    title: str,
) -> list[str]:
    manifest_lines = []
    for suffix in _MANIFEST_FIELD_SUFFIXES:
        key = f"{manifest_prefix}_{suffix}"
        value = payload.get(key)
        if value is None:
            continue
        label = _MANIFEST_FIELD_LABELS[suffix]
        manifest_lines.append(f"  - {label}: `{value}`")
    if not manifest_lines:
        return []
    return [f"- {title}"] + manifest_lines


def _render_effort_join_command(effort: EffortView, *, public_base_url: str | None = None) -> str:
    if explicit_command := effort.tags.get("join_command"):
        return explicit_command

    effort_type = effort.tags.get("effort_type")
    command = "python3 -m clients.tiny_loop.run"
    if effort_type == "inference":
        command = f"{command} --profile inference-sprint"
    elif effort_type != "eval":
        command = f"{command} --profile standalone"
    if public_base_url:
        command = f"{command} --base-url {shlex.quote(public_base_url)}"
    return command


def _render_effort_join_brief(effort: EffortView) -> str:
    if explicit_brief := effort.tags.get("join_brief_path"):
        return explicit_brief
    if effort.tags.get("external_harness") == "mlx-history":
        return "README.md#external-mlx-compounding-proof"
    return "docs/seeded-efforts.md"


def _render_effort_lifecycle_lines(effort: EffortView) -> list[str]:
    if not is_public_proof_effort(effort):
        return []
    if is_historical_proof_effort(effort):
        lines = [
            "",
            "## Lifecycle",
            f"- Proof version: `{proof_version(effort)}`",
            "- Proof state: `historical`",
        ]
        if effort.successor_effort_id:
            lines.append(f"- Current successor effort: `{effort.successor_effort_id}`")
        return lines
    return [
        "",
        "## Lifecycle",
        f"- Proof version: `{proof_version(effort)}`",
        "- Proof state: `current`",
    ]


def _render_artifact_reference(payload: dict[str, object]) -> str:
    artifact_uri = str(payload.get("artifact_uri") or "n/a")
    if artifact_uri.startswith("file://"):
        digest = payload.get("source_bundle_digest")
        if digest:
            return f"local artifact plane path hidden (digest={digest})"
        return "local artifact plane path hidden"
    return artifact_uri
