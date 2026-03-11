from __future__ import annotations

import shlex

from research_os.domain.models import ClaimSummary, EffortView, EventEnvelope, FrontierView, PublicationView, WorkspaceView


def render_workspace_discussion(
    workspace: WorkspaceView,
    *,
    events: list[EventEnvelope],
    claims: list[ClaimSummary],
) -> PublicationView:
    recent_events = sorted(events, key=lambda event: event.occurred_at, reverse=True)[:5]
    claim_lines = _render_claim_lines(claims)
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
            f"- Adoptions: {workspace.adoption_count}",
            f"- Summaries: {workspace.summary_count}",
            f"- Events: {workspace.event_count}",
            "",
            "## Claim Signals",
            *claim_lines,
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
) -> PublicationView:
    payload = snapshot_event.payload
    best_run = _select_best_run(run_events)
    claim_lines = _render_claim_lines(claims)
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
            f"runs={len(workspace.run_ids)}, claims={len(workspace.claim_ids)}, "
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
    body = "\n".join(
        [
            f"# Effort: {effort.name}",
            "",
            "## Objective",
            f"- Objective: `{effort.objective}`",
            f"- Platform: `{effort.platform}`",
            f"- Budget seconds: `{effort.budget_seconds}`",
            *(["- Summary: " + effort.summary] if effort.summary else []),
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
            "- Read the effort brief in `docs/seeded-efforts.md`.",
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

    ordered_claims = sorted(claims, key=lambda claim: (claim.updated_at, claim.claim_id), reverse=True)
    return [
        (
            f"- `{claim.claim_id}` [{claim.status}] {claim.statement} "
            f"(support={claim.support_count}, contradictions={claim.contradiction_count})"
        )
        for claim in ordered_claims
    ]


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


def _render_effort_join_command(effort: EffortView, *, public_base_url: str | None = None) -> str:
    effort_type = effort.tags.get("effort_type")
    command = "python3 -m clients.tiny_loop.run"
    if effort_type == "inference":
        command = f"{command} --profile inference-sprint"
    elif effort_type != "eval":
        command = f"{command} --profile standalone"
    if public_base_url:
        command = f"{command} --base-url {shlex.quote(public_base_url)}"
    return command


def _render_artifact_reference(payload: dict[str, object]) -> str:
    artifact_uri = str(payload.get("artifact_uri") or "n/a")
    if artifact_uri.startswith("file://"):
        digest = payload.get("source_bundle_digest")
        if digest:
            return f"local artifact plane path hidden (digest={digest})"
        return "local artifact plane path hidden"
    return artifact_uri
