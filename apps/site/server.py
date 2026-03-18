from __future__ import annotations

from collections import Counter
import hashlib
from dataclasses import dataclass
from html import escape
import json
import os
from pathlib import Path
from urllib import error
from urllib.parse import quote, urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from apps.site import site_templates
from research_os.effort_lifecycle import is_historical_proof_effort
from research_os.effort_lifecycle import is_public_proof_effort
from research_os.effort_lifecycle import proof_series
from research_os.effort_lifecycle import proof_version
from research_os.effort_lifecycle import split_current_and_historical_efforts
from research_os.domain.models import ClaimSummary
from research_os.domain.models import EffortView
from research_os.domain.models import EventEnvelope
from research_os.domain.models import EventKind
from research_os.domain.models import FrontierMember
from research_os.domain.models import LeaseLivenessStatus
from research_os.domain.models import LeaseObservation
from research_os.domain.models import LeaseState
from research_os.domain.models import WorkspaceView
from research_os.edge_bootstrap import render_edge_bootstrap_script
from research_os.http import build_request
from research_os.http import open_url

DEFAULT_API_BASE_URL = "https://api.openintention.io"
DEFAULT_PUBLIC_REPO_URL = "https://github.com/openintention/research-os"


@dataclass(frozen=True, slots=True)
class ProgressMilestone:
    label: str
    actor: str
    metric_name: str
    metric_value: float
    direction: str
    run_id: str
    occurred_at: str


@dataclass(frozen=True, slots=True)
class ParticipantSpotlight:
    actor: str
    latest_workspace: WorkspaceView
    workspace_count: int
    current_window_workspace_count: int
    run_count: int
    claim_count: int
    reproduction_count: int
    adoption_count: int
    has_worker_handoff: bool
    has_verifier_handoff: bool


@dataclass(frozen=True, slots=True)
class EffortWorkerCoordination:
    observations: list[LeaseObservation]
    active_count: int
    healthy_count: int
    stale_count: int
    missing_count: int
    released_count: int
    completed_count: int
    failed_count: int
    expired_count: int
    latest_observation: LeaseObservation | None
    summary_line: str


@dataclass(frozen=True, slots=True)
class EffortProof:
    contributor_count: int
    current_window_participant_count: int
    new_arrival_count: int
    repeat_contributor_count: int
    worker_contributor_count: int
    verifier_contributor_count: int
    visible_handoff_count: int
    successful_run_count: int
    claim_count: int
    reproduction_count: int
    adoption_count: int
    record_setter_count: int
    latest_workspace: WorkspaceView | None
    progress_milestones: list[ProgressMilestone]
    summary_line: str
    latest_handoff_line: str
    actor_workspace_counts: dict[str, int]
    participant_spotlights: list[ParticipantSpotlight]


@dataclass(frozen=True, slots=True)
class EffortProofSurfaceContext:
    current_workspaces: list[WorkspaceView]
    current_claims: list[ClaimSummary]
    display_workspaces: list[WorkspaceView]
    display_claims: list[ClaimSummary]
    display_workspace_events: dict[str, list[EventEnvelope]]
    carries_forward: bool


def _asset_version(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


def create_site_app(
    dist_dir: Path | None = None,
    *,
    api_base_url: str | None = None,
    api_fetch_base_url: str | None = None,
    site_base_url: str | None = None,
) -> FastAPI:
    dist_root = dist_dir or Path(__file__).resolve().parent / "dist"
    assets_root = dist_root / "assets"
    evidence_root = dist_root / "evidence"
    normalized_public_api_base_url = (
        api_base_url
        or os.getenv("OPENINTENTION_API_BASE_URL")
        or os.getenv("RESEARCH_OS_PUBLIC_BASE_URL")
        or DEFAULT_API_BASE_URL
    ).rstrip("/")
    normalized_fetch_api_base_url = (
        api_fetch_base_url
        or os.getenv("OPENINTENTION_API_FETCH_BASE_URL")
        or normalized_public_api_base_url
    ).rstrip("/")
    normalized_site_base_url = (
        site_base_url
        or os.getenv("OPENINTENTION_SITE_BASE_URL")
        or None
    )
    if normalized_site_base_url is not None:
        normalized_site_base_url = normalized_site_base_url.rstrip("/")
    assets_root.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)
    site_css_url = "/styles.css"
    site_css_hash = _asset_version(dist_root / "styles.css")
    if site_css_hash:
        site_css_url = f"/styles.css?v={site_css_hash}"
    site_js_url = None
    site_js_hash = _asset_version(dist_root / "site.js")
    if site_js_hash:
        site_js_url = f"/site.js?v={site_js_hash}"
    template_asset_kwargs = {
        "site_css_url": site_css_url,
        "site_js_url": site_js_url,
    }
    app = FastAPI(title="OpenIntention Site", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/assets", StaticFiles(directory=assets_root), name="site-assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(dist_root / "index.html")

    @app.get("/styles.css", include_in_schema=False)
    def styles() -> FileResponse:
        return FileResponse(dist_root / "styles.css")

    @app.get("/site.js", include_in_schema=False)
    def site_script() -> FileResponse:
        site_script_file = dist_root / "site.js"
        if not site_script_file.is_file():
            raise HTTPException(status_code=404, detail="site.js not found")
        return FileResponse(site_script_file)

    @app.get("/join", include_in_schema=False, response_class=PlainTextResponse)
    @app.get("/join.sh", include_in_schema=False, response_class=PlainTextResponse)
    def join_script() -> PlainTextResponse:
        return PlainTextResponse(
            render_edge_bootstrap_script(site_url="https://openintention.io"),
            media_type="text/plain; charset=utf-8",
        )

    @app.get("/publish", include_in_schema=False, response_class=HTMLResponse)
    def publish_goal_page() -> str:
        return site_templates.render_publish_goal_page(
            site_templates.build_publish_goal_context(**template_asset_kwargs)
        )

    @app.post("/publish", include_in_schema=False)
    async def publish_goal(request: Request) -> dict[str, object]:
        try:
            payload = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="request body must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="request body must be a JSON object")
        created = _post_json(
            normalized_fetch_api_base_url,
            "/api/v1/goals/publish",
            payload,
        )
        effort_id = str(created["effort_id"])
        actor_id = str(payload.get("actor_id") or "unknown")
        site_base_url = _resolve_site_base_url(request, configured_base_url=normalized_site_base_url)
        return {
            **created,
            "goal_page_url": f"{site_base_url}/efforts/{effort_id}",
            "join_command": (
                f"curl -fsSL {site_base_url}/join | bash -s -- "
                f"--effort-id {effort_id} --actor-id <handle>"
            ),
            "author_id": actor_id,
        }

    @app.get("/evidence/{path:path}", include_in_schema=False)
    def evidence(path: str) -> FileResponse:
        target = (evidence_root / path).resolve()
        if evidence_root.resolve() not in target.parents or not target.is_file():
            raise HTTPException(status_code=404)
        media_type = "text/markdown; charset=utf-8" if target.suffix == ".md" else None
        return FileResponse(target, media_type=media_type)

    @app.get("/efforts", include_in_schema=False, response_class=HTMLResponse)
    def effort_index() -> str:
        efforts = _fetch_json(normalized_fetch_api_base_url, "/api/v1/efforts")
        return site_templates.render_effort_index_page(
            site_templates.build_effort_index_context(
                public_api_base_url=normalized_public_api_base_url,
                efforts=efforts,
                **template_asset_kwargs,
            ),
        )

    @app.get("/efforts/{effort_id}", include_in_schema=False, response_class=HTMLResponse)
    def effort_detail(
        effort_id: str,
        workspace: str | None = None,
        actor: str | None = None,
        claim: str | None = None,
        reproduction: str | None = None,
        joined: int | None = None,
    ) -> str:
        efforts = _fetch_json(normalized_fetch_api_base_url, "/api/v1/efforts")
        effort_payload = next((item for item in efforts if item["effort_id"] == effort_id), None)
        if effort_payload is None:
            raise HTTPException(status_code=404, detail="effort not found")
        effort = EffortView.model_validate(effort_payload)

        workspaces = _fetch_json(
            normalized_fetch_api_base_url,
            "/api/v1/workspaces",
            query={"effort_id": effort_id},
        )
        workspace_events = {
            workspace["workspace_id"]: [
                EventEnvelope.model_validate(event)
                for event in _fetch_json(
                    normalized_fetch_api_base_url,
                    "/api/v1/events",
                    query={"workspace_id": workspace["workspace_id"], "limit": 10_000},
                )
            ]
            for workspace in workspaces
        }
        claims = _fetch_json(
            normalized_fetch_api_base_url,
            "/api/v1/claims",
            query={"objective": effort.objective, "platform": effort.platform},
        )
        frontier = _fetch_json(
            normalized_fetch_api_base_url,
            f"/api/v1/frontiers/{quote(effort.objective)}/{quote(effort.platform)}",
            query={"budget_seconds": effort.budget_seconds},
        )
        lease_observations = [
            LeaseObservation.model_validate(item)
            for item in _fetch_json(
                normalized_fetch_api_base_url,
                "/api/v1/leases",
                query={"effort_id": effort_id},
            )
        ]
        proof_surface = _build_effort_proof_surface_context(
            api_base_url=normalized_fetch_api_base_url,
            effort=effort,
            all_efforts=efforts,
            current_workspaces=workspaces,
            current_workspace_events=workspace_events,
            all_claims=claims,
        )

        return site_templates.render_effort_detail_page(
            site_templates.build_effort_detail_context(
                public_api_base_url=normalized_public_api_base_url,
                effort=effort,
                proof_surface=proof_surface,
                frontier=frontier,
                lease_observations=lease_observations,
                highlighted_workspace_id=workspace,
                highlighted_actor_id=actor,
                highlighted_claim_id=claim,
                highlighted_reproduction_run_id=reproduction,
                joined=bool(joined),
                **template_asset_kwargs,
            )
        )

    return app


app = create_site_app()


def _fetch_json(
    api_base_url: str,
    path: str,
    *,
    query: dict[str, object] | None = None,
) -> list[dict[str, object]] | dict[str, object]:
    query_string = f"?{urlencode(query)}" if query else ""
    request = build_request(f"{api_base_url}{path}{query_string}")
    with open_url(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(
    api_base_url: str,
    path: str,
    payload: dict[str, object],
) -> dict[str, object]:
    request = build_request(
        f"{api_base_url}{path}",
        method="POST",
        headers={"content-type": "application/json", "accept": "application/json"},
        data=json.dumps(payload).encode("utf-8"),
    )
    try:
        with open_url(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail_text = exc.read().decode("utf-8")
        detail: object = detail_text
        try:
            parsed = json.loads(detail_text)
            if isinstance(parsed, dict) and "detail" in parsed:
                detail = parsed["detail"]
            else:
                detail = parsed
        except json.JSONDecodeError:
            detail = detail_text
        raise HTTPException(status_code=exc.code, detail=detail) from exc


def _resolve_site_base_url(request: Request, *, configured_base_url: str | None) -> str:
    if configured_base_url:
        return configured_base_url
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}".rstrip("/")
    return str(request.base_url).rstrip("/")


def _effort_index_html(
    *,
    public_api_base_url: str,
    efforts: list[dict[str, object]],
    site_css_url: str = "/styles.css",
    site_js_url: str | None = None,
) -> str:
    effort_models = [EffortView.model_validate(effort) for effort in efforts]
    current_efforts, historical_efforts = split_current_and_historical_efforts(effort_models)
    cards = "\n".join(
        _render_effort_index_card(public_api_base_url=public_api_base_url, effort=effort.model_dump(mode="json"))
        for effort in current_efforts
    )
    historical_cards = "\n".join(
        _render_effort_index_card(public_api_base_url=public_api_base_url, effort=effort.model_dump(mode="json"))
        for effort in historical_efforts
    )
    historical_section = ""
    if historical_cards:
        historical_section = f"""
        <section class="panel">
          <h2>Historical goal windows</h2>
          <p class="footer-note">Older proof windows stay visible and inspectable, but new proof work should continue on the current successor goal window.</p>
          <section class="efforts">{historical_cards}</section>
        </section>
        """
    return _page_html(
        "Live Goals",
        """
        <section class="hero">
          <div class="eyebrow">Live explorer</div>
          <h1>Shared ML goals, visible progress, and clear next steps.</h1>
          <p class="lede">
            These pages are generated from the hosted control plane. Today the public surface starts
            with seeded goals, and each page shows what people and agents have tried, what moved
            the frontier, and what the next contributor can continue.
          </p>
          <div class="hero-actions">
            <a class="button primary" href="/">Back to OpenIntention</a>
            <a class="button secondary" href="/publish">Publish a goal</a>
          </div>
        </section>
        """
        + f'<section class="efforts">{cards or "<p>No efforts found.</p>"}</section>'
        + historical_section
        ,
        site_css_url=site_css_url,
        site_js_url=site_js_url,
    )


def _render_effort_index_card(*, public_api_base_url: str, effort: dict[str, object]) -> str:
    effort_model = EffortView.model_validate(effort)
    state = _effort_state_label(effort_model)
    return f"""
    <article class="effort-card">
      <div class="effort-type">{escape(state["label"])}</div>
      <h2>{escape(str(effort_model.name))}</h2>
      <p>{escape(state["description"])}</p>
      <ul class="link-list">
        <li>Objective: <code>{escape(str(effort_model.objective))}</code></li>
        <li>Platform: <code>{escape(str(effort_model.platform))}</code></li>
        <li>Budget seconds: <code>{escape(str(effort_model.budget_seconds))}</code></li>
        <li>Attached workspaces: <code>{len(effort_model.workspace_ids)}</code></li>
        {f'<li>Current successor: <code>{escape(str(effort_model.successor_effort_id))}</code></li>' if effort_model.successor_effort_id else ''}
      </ul>
      <div class="hero-actions">
        <a class="button primary" href="/efforts/{escape(str(effort_model.effort_id))}">Open live goal page</a>
        <a class="button secondary" href="{escape(public_api_base_url)}/api/v1/publications/efforts/{escape(str(effort_model.effort_id))}">Open markdown mirror</a>
      </div>
    </article>
    """


def _build_effort_proof_surface_context(
    *,
    api_base_url: str,
    effort: EffortView,
    all_efforts: list[dict[str, object]],
    current_workspaces: list[dict[str, object]],
    current_workspace_events: dict[str, list[EventEnvelope]],
    all_claims: list[dict[str, object]],
) -> EffortProofSurfaceContext:
    current_workspace_models = sorted(
        (WorkspaceView.model_validate(workspace) for workspace in current_workspaces),
        key=lambda workspace: workspace.updated_at,
        reverse=True,
    )
    current_workspace_ids = {workspace.workspace_id for workspace in current_workspace_models}
    current_claim_models = sorted(
        (
            ClaimSummary.model_validate(claim)
            for claim in all_claims
            if claim.get("workspace_id") in current_workspace_ids
        ),
        key=lambda claim: claim.updated_at,
        reverse=True,
    )
    display_workspaces = list(current_workspace_models)
    display_workspace_events = dict(current_workspace_events)
    carries_forward = False

    series = proof_series(effort)
    if is_public_proof_effort(effort) and not is_historical_proof_effort(effort) and series:
        related_efforts = [
            EffortView.model_validate(item)
            for item in all_efforts
            if item.get("effort_id") != effort.effort_id
            and proof_series(EffortView.model_validate(item)) == series
        ]
        for related_effort in related_efforts:
            related_workspaces = _fetch_json(
                api_base_url,
                "/api/v1/workspaces",
                query={"effort_id": related_effort.effort_id},
            )
            for workspace in related_workspaces:
                workspace_model = WorkspaceView.model_validate(workspace)
                if workspace_model.workspace_id in current_workspace_ids:
                    continue
                display_workspaces.append(workspace_model)
                display_workspace_events[workspace_model.workspace_id] = [
                    EventEnvelope.model_validate(event)
                    for event in _fetch_json(
                        api_base_url,
                        "/api/v1/events",
                        query={"workspace_id": workspace_model.workspace_id, "limit": 10_000},
                    )
                ]
                carries_forward = True

        display_workspaces = sorted(
            display_workspaces,
            key=lambda workspace: workspace.updated_at,
            reverse=True,
        )

    display_workspace_ids = {workspace.workspace_id for workspace in display_workspaces}
    display_claim_models = sorted(
        (
            ClaimSummary.model_validate(claim)
            for claim in all_claims
            if claim.get("workspace_id") in display_workspace_ids
        ),
        key=lambda claim: claim.updated_at,
        reverse=True,
    )
    return EffortProofSurfaceContext(
        current_workspaces=current_workspace_models,
        current_claims=current_claim_models,
        display_workspaces=display_workspaces,
        display_claims=display_claim_models,
        display_workspace_events=display_workspace_events,
        carries_forward=carries_forward,
    )


def _effort_detail_html(
    *,
    public_api_base_url: str,
    effort: EffortView,
    proof_surface: EffortProofSurfaceContext,
    frontier: dict[str, object],
    lease_observations: list[LeaseObservation],
    highlighted_workspace_id: str | None = None,
    highlighted_actor_id: str | None = None,
    highlighted_claim_id: str | None = None,
    highlighted_reproduction_run_id: str | None = None,
    joined: bool = False,
    site_css_url: str = "/styles.css",
    site_js_url: str | None = None,
) -> str:
    current_workspace_models = proof_surface.current_workspaces
    current_claim_models = proof_surface.current_claims
    display_workspace_models = proof_surface.display_workspaces
    display_claim_models = proof_surface.display_claims
    frontier_members = [
        FrontierMember.model_validate(member) for member in frontier.get("members", [])[:8]
    ]
    state = _effort_state_label(effort)
    join_command = _join_command(effort.model_dump(mode="json"), api_base_url=public_api_base_url)
    join_brief = _join_brief(effort.model_dump(mode="json"))
    workspace_actor_map = {
        workspace.workspace_id: workspace.actor_id or "unknown" for workspace in display_workspace_models
    }
    current_workspace_ids = {workspace.workspace_id for workspace in current_workspace_models}
    highlighted_workspace = next(
        (workspace for workspace in display_workspace_models if workspace.workspace_id == highlighted_workspace_id),
        None,
    )
    featured_workspace = (
        highlighted_workspace or proof_surface.display_workspaces[0]
        if proof_surface.display_workspaces
        else None
    )
    proof = _build_effort_proof(
        display_workspace_models,
        proof_surface.display_workspace_events,
        current_workspace_ids=current_workspace_ids,
        scope_label="goal series" if proof_surface.carries_forward else "goal",
    )
    worker_coordination = _build_effort_worker_coordination(lease_observations)
    show_worker_coordination = bool(worker_coordination.observations) or any(
        _workspace_is_worker_origin(workspace) for workspace in display_workspace_models
    )
    worker_cards = "\n".join(
        _render_worker_coordination_card(
            observation,
            public_api_base_url=public_api_base_url,
        )
        for observation in worker_coordination.observations[:4]
    )
    spotlight_models = _prioritize_spotlights(
        proof.participant_spotlights,
        highlighted_actor_id=highlighted_actor_id,
        highlighted_workspace_id=highlighted_workspace_id,
    )
    recent_handoffs = "\n".join(
        _render_recent_handoff(
            workspace,
            public_api_base_url=public_api_base_url,
            is_current_window=workspace.workspace_id in current_workspace_ids,
            is_repeat_contributor=proof.actor_workspace_counts.get(workspace.actor_id or "unknown", 0) > 1,
            highlighted_workspace_id=highlighted_workspace_id,
        )
        for workspace in _prioritize_workspaces(display_workspace_models, highlighted_workspace_id)[:6]
    )
    participant_cards = "\n".join(
        _render_participant_spotlight(
            spotlight,
            public_api_base_url=public_api_base_url,
            highlighted_actor_id=highlighted_actor_id,
            highlighted_workspace_id=highlighted_workspace_id,
        )
        for spotlight in spotlight_models[:6]
    )
    frontier_items = "\n".join(_render_frontier_item(member, workspace_actor_map) for member in frontier_members)
    claim_items = "\n".join(_render_claim_item(claim, workspace_actor_map) for claim in display_claim_models[:8])
    best_result = _best_result_summary(frontier_members, workspace_actor_map)
    latest_claim = _latest_claim_summary(display_claim_models, workspace_actor_map)
    next_move = _next_move_summary(effort, display_claim_models, frontier_members, workspace_actor_map)
    goal_contract_card = _render_goal_contract_card(effort)
    progress_items = "\n".join(_render_progress_milestone(step) for step in proof.progress_milestones)
    latest_workspace = featured_workspace or proof.latest_workspace
    carried_workspace_count = len(display_workspace_models) - len(current_workspace_models)
    proof_summary_line = proof.summary_line
    if proof_surface.carries_forward and not current_workspace_models:
        proof_summary_line += " The current proof window is fresh, so this context is carried forward from earlier proof windows in the same series."
    elif proof_surface.carries_forward:
        proof_summary_line += " Earlier proof windows in the same series are carried forward here so the line of work stays visible."
    latest_discussion_url = (
        f"{public_api_base_url}/api/v1/publications/workspaces/{quote(latest_workspace.workspace_id)}/discussion"
        if latest_workspace is not None
        else None
    )
    highlighted_claim = _find_highlighted_claim(
        display_claim_models,
        highlighted_claim_id=highlighted_claim_id,
        highlighted_workspace_id=highlighted_workspace_id,
    )
    join_success_section = _render_join_success_section(
        highlighted_workspace=highlighted_workspace,
        highlighted_claim=highlighted_claim,
        highlighted_actor_id=highlighted_actor_id,
        highlighted_reproduction_run_id=highlighted_reproduction_run_id,
        current_workspace_ids=current_workspace_ids,
        joined=joined,
        next_move=next_move,
        public_api_base_url=public_api_base_url,
    )
    carry_forward_note = ""
    if proof_surface.carries_forward:
        carry_forward_note = (
            f'<p class="footer-note">Current window workspaces: <code>{len(current_workspace_models)}</code>. '
            f'The proof cards below carry forward <code>{carried_workspace_count}</code> earlier handoff'
            f'{"s" if carried_workspace_count != 1 else ""} from this proof series.</p>'
        )
    machine_state_lede = (
        "This lower section keeps raw state visible for agents and technical users while carrying forward earlier proof-window context in the same proof series."
        if proof_surface.carries_forward
        else "This lower section keeps the raw state visible for agents and technical users without making ids the first thing a human sees."
    )
    worker_coordination_section = ""
    if show_worker_coordination:
        worker_coordination_section = f"""
        <section class="panel">
          <div class="eyebrow">Worker activity</div>
          <h2>What background workers are doing on this goal</h2>
          <p class="section-lede">{escape(worker_coordination.summary_line)}</p>
          <ul class="state-pills proof-stat-pills">
            <li><span>Observed leases</span><code>{len(worker_coordination.observations)}</code></li>
            <li><span>Active</span><code>{worker_coordination.active_count}</code></li>
            <li><span>Healthy</span><code>{worker_coordination.healthy_count}</code></li>
            <li><span>Stale</span><code>{worker_coordination.stale_count}</code></li>
            <li><span>Missing</span><code>{worker_coordination.missing_count}</code></li>
            {'<li><span>Released</span><code>%s</code></li>' % worker_coordination.released_count if worker_coordination.released_count else ''}
            {'<li><span>Completed</span><code>%s</code></li>' % worker_coordination.completed_count if worker_coordination.completed_count else ''}
            {'<li><span>Failed</span><code>%s</code></li>' % worker_coordination.failed_count if worker_coordination.failed_count else ''}
            {'<li><span>Expired</span><code>%s</code></li>' % worker_coordination.expired_count if worker_coordination.expired_count else ''}
          </ul>
          <div class="handoff-grid">
            {worker_cards or '<p>No worker lease observations are visible on this goal yet.</p>'}
          </div>
          <p class="footer-note">This panel is derived from lease observations and signed node heartbeats on the hosted control plane.</p>
        </section>
        """
    return _page_html(
        str(effort.name),
        f"""
        <section class="hero">
          <div class="eyebrow">{escape(state["label"])}</div>
          <h1>{escape(str(effort.name))}</h1>
          <p class="lede">{escape(state["description"])}</p>
          <div class="hero-actions">
            <a class="button primary" href="/">Back to OpenIntention</a>
            <a class="button secondary" href="/efforts">See all live goals</a>
          </div>
        </section>

        {join_success_section}

        <section class="panel grid two effort-summary-grid">
          <div class="summary-stack">
            <div class="summary-card">
              <div class="effort-type">What's working best right now</div>
              <p class="summary-headline">{escape(best_result)}</p>
            </div>
            <div class="summary-card">
              <div class="effort-type">Latest finding</div>
              <p class="summary-headline">{escape(latest_claim)}</p>
            </div>
            <div class="summary-card">
              <div class="effort-type">What to try next</div>
              <p class="summary-headline">{escape(next_move)}</p>
            </div>
            {goal_contract_card}
            <ul class="state-pills">
              <li><span>Objective</span><code>{escape(str(effort.objective))}</code></li>
              <li><span>Platform</span><code>{escape(str(effort.platform))}</code></li>
              <li><span>Budget</span><code>{escape(str(effort.budget_seconds))}s</code></li>
              <li><span>{'Current contributions' if proof_surface.carries_forward else 'Contributions'}</span><code>{len(current_workspace_models)}</code></li>
              <li><span>{'Current findings' if proof_surface.carries_forward else 'Findings'}</span><code>{len(current_claim_models)}</code></li>
              <li><span>Frontier</span><code>{len(frontier_members)}</code></li>
              {f'<li><span>Series history</span><code>{len(display_workspace_models)}</code></li>' if proof_surface.carries_forward else ''}
              {'<li><span>Lifecycle</span><code>historical proof run</code></li>' if is_historical_proof_effort(effort) else ''}
              {f'<li><span>Successor</span><code>{escape(str(effort.successor_effort_id))}</code></li>' if effort.successor_effort_id else ''}
              {f'<li><span>Window version</span><code>{escape(str(proof_version(effort)))}</code></li>' if is_public_proof_effort(effort) else ''}
            </ul>
            {carry_forward_note}
            <p class="footer-note">This page is reading the live hosted goal state right now.</p>
          </div>
          <div id="join-this-effort" class="summary-card join-summary-card">
            <div class="effort-type">Join this goal</div>
            <h2>Pick up the current line of work</h2>
            <p>Pick up the current line of work on this goal, then leave behind a workspace, a claim or reproduction, and an inspectable brief for the next participant.</p>
            <p class="command">{escape(join_command)}</p>
            <ul>
              <li>Brief: <code>{escape(join_brief)}</code></li>
              <li>Optional attribution: add <code>--actor-id &lt;handle&gt;</code></li>
            </ul>
          </div>
        </section>

        <section class="panel">
          <div class="eyebrow">How this goal is moving</div>
          <h2>How people are moving this goal forward</h2>
          <p class="section-lede">{escape(proof_summary_line)}</p>
          <ul class="state-pills proof-stat-pills">
            <li><span>Contributors</span><code>{proof.contributor_count}</code></li>
            <li><span>Visible handoffs</span><code>{proof.visible_handoff_count}</code></li>
            <li><span>Runs</span><code>{proof.successful_run_count}</code></li>
            <li><span>Claims</span><code>{proof.claim_count}</code></li>
            <li><span>Reproductions</span><code>{proof.reproduction_count}</code></li>
            <li><span>Record setters</span><code>{proof.record_setter_count}</code></li>
            {'<li><span>Adoptions</span><code>%s</code></li>' % proof.adoption_count if proof.adoption_count else ''}
            {'<li><span>Repeat contributors</span><code>%s</code></li>' % proof.repeat_contributor_count if proof.repeat_contributor_count else ''}
          </ul>
          <div class="proof-surface-grid">
            <article class="result-card shell-card">
              <div class="shell-bar">
                <div class="shell-dots"><span></span><span></span><span></span></div>
                <div class="shell-title">Compounding history · record setters</div>
              </div>
              <div class="effort-type">Best-so-far progression</div>
              <ol class="progress-ladder">
                {progress_items or '<li class="progress-step-empty">No record-setting run yet. The next participant can leave the first best-so-far marker.</li>'}
              </ol>
            </article>
            <article class="result-summary-card">
              <div class="effort-type">Latest handoff</div>
              <h3>{escape(latest_workspace.actor_id or "unknown") if latest_workspace else "No public handoff yet"}</h3>
              <p class="summary-headline">{escape(_workspace_handoff_summary(latest_workspace) if latest_workspace is not None else proof.latest_handoff_line)}</p>
              {
                  _render_workspace_proof_meta(
                      latest_workspace,
                      is_current_window=latest_workspace.workspace_id in current_workspace_ids,
                  )
                  if latest_workspace is not None
                  else '<p class="footer-note">Use the join command above to leave the first hosted handoff on this goal.</p>'
              }
              {
                  f'''
                  <div class="card-links">
                    <a href="{escape(latest_discussion_url)}">View discussion</a>
                    <a href="#join-this-effort">Continue from this goal</a>
                  </div>
                  '''
                  if latest_workspace is not None and latest_discussion_url is not None
                  else ""
              }
            </article>
          </div>
        </section>

        <section class="panel">
          <div class="eyebrow">Who is involved</div>
          <h2>People and agents visible on this goal</h2>
          <p class="section-lede">{escape(_participant_visibility_summary(proof, scope_label="goal series" if proof_surface.carries_forward else "goal"))}</p>
          <div class="handoff-grid">
            {participant_cards or '<p>No participants are visible yet. Use the join command above to leave the first hosted handoff.</p>'}
          </div>
        </section>

        {worker_coordination_section}

        <section class="panel">
          <div class="eyebrow">Recent handoffs</div>
          <h2>Work the next person can continue on this goal</h2>
          <p class="section-lede">These are the most recent hosted contributions. Each one links back to a discussion mirror and leaves behind enough evidence for the next participant to inspect or extend.</p>
          <div class="handoff-grid">
            {recent_handoffs or '<p>No handoffs yet. Use the join command above to leave the first visible result.</p>'}
          </div>
        </section>

        <section class="panel machine-state-panel">
          <div class="eyebrow">Full live goal state</div>
          <h2>Machine-readable goal state</h2>
          <p class="section-lede">{escape(machine_state_lede)}</p>
          <section class="grid two">
          <div>
            <h2>{'Frontier context' if proof_surface.carries_forward else 'Frontier'}</h2>
            <ul class="link-list">
              {frontier_items or "<li>No frontier members yet.</li>"}
            </ul>
          </div>
          <div>
            <h2>{'Goal-series findings' if proof_surface.carries_forward else 'Recorded findings'}</h2>
            <ul class="link-list">
              {claim_items or "<li>No findings recorded yet.</li>"}
            </ul>
          </div>
          </section>
        </section>
        """,
        site_css_url=site_css_url,
        site_js_url=site_js_url,
    )


def _render_recent_handoff(
    workspace: WorkspaceView,
    *,
    public_api_base_url: str,
    is_current_window: bool,
    is_repeat_contributor: bool,
    highlighted_workspace_id: str | None = None,
) -> str:
    actor = workspace.actor_id or "unknown"
    discussion_url = (
        f"{public_api_base_url}/api/v1/publications/workspaces/{quote(workspace.workspace_id)}/discussion"
    )
    highlight_class = " highlight-card" if workspace.workspace_id == highlighted_workspace_id else ""
    return f"""
    <article id="workspace-{escape(workspace.workspace_id)}" class="result-summary-card handoff-card{highlight_class}">
      <div class="effort-type">Recent handoff</div>
      <h3>{escape(actor)}</h3>
      <p class="summary-headline">{escape(_workspace_handoff_summary(workspace))}</p>
      <ul class="state-pills compact">
        <li><span>Window</span><code>{'current' if is_current_window else 'carried'}</code></li>
        <li><span>Role</span><code>{escape(str(workspace.participant_role))}</code></li>
        <li><span>Origin</span><code>{escape(_workspace_origin_label(workspace))}</code></li>
        <li><span>Pattern</span><code>{'repeat' if is_repeat_contributor else 'first visible'}</code></li>
        <li><span>Runs</span><code>{len(workspace.run_ids)}</code></li>
        <li><span>Claims</span><code>{len(workspace.claim_ids)}</code></li>
        <li><span>Reproductions</span><code>{workspace.reproduction_count}</code></li>
      </ul>
      <p class="handoff-meta">
        Workspace <code>{escape(_short_id(workspace.workspace_id))}</code> · updated <code>{escape(_format_timestamp(workspace.updated_at))}</code>
      </p>
      <div class="card-links">
        <a href="{escape(discussion_url)}">View discussion</a>
        <a href="#join-this-effort">Continue from this goal</a>
      </div>
    </article>
    """


def _build_effort_proof(
    workspaces: list[WorkspaceView],
    workspace_events: dict[str, list[EventEnvelope]],
    *,
    current_workspace_ids: set[str],
    scope_label: str = "effort",
) -> EffortProof:
    actor_counts = Counter(workspace.actor_id or "unknown" for workspace in workspaces)
    current_window_actor_counts = Counter(
        workspace.actor_id or "unknown"
        for workspace in workspaces
        if workspace.workspace_id in current_workspace_ids
    )
    visible_handoffs = sum(
        1
        for workspace in workspaces
        if workspace.run_ids or workspace.claim_ids or workspace.reproduction_count or workspace.adoption_count
    )
    events = sorted(
        [event for event_list in workspace_events.values() for event in event_list],
        key=lambda event: event.occurred_at,
    )
    event_counts = Counter(event.kind.value for event in events)
    successful_runs = [
        event
        for event in events
        if event.kind == EventKind.RUN_COMPLETED and event.payload.get("status") == "success"
    ]
    progress_milestones = _build_progress_milestones(successful_runs)

    contributor_count = len(actor_counts)
    current_window_participant_count = len(current_window_actor_counts)
    new_arrival_count = sum(1 for count in actor_counts.values() if count == 1)
    repeat_contributor_count = sum(1 for count in actor_counts.values() if count > 1)
    worker_contributor_count = sum(
        1
        for actor in actor_counts
        if any(
            _workspace_is_worker_origin(workspace)
            for workspace in workspaces
            if (workspace.actor_id or "unknown") == actor
        )
    )
    verifier_contributor_count = sum(
        1
        for actor in actor_counts
        if any(
            str(workspace.participant_role) == "verifier"
            for workspace in workspaces
            if (workspace.actor_id or "unknown") == actor
        )
    )
    latest_workspace = workspaces[0] if workspaces else None
    latest_handoff_line = (
        _workspace_handoff_summary(latest_workspace) if latest_workspace is not None else "No public handoff yet."
    )
    participant_spotlights = _build_participant_spotlights(
        workspaces,
        current_workspace_ids=current_workspace_ids,
    )
    if contributor_count == 0:
        summary_line = (
            f"No public handoffs yet on this {scope_label}. "
            "The first participant can leave the initial hosted result."
        )
    else:
        summary_bits = [
            f"{contributor_count} contributor{'s' if contributor_count != 1 else ''}",
            f"{visible_handoffs} visible handoff{'s' if visible_handoffs != 1 else ''}",
            f"{len(successful_runs)} successful run{'s' if len(successful_runs) != 1 else ''}",
        ]
        if event_counts[EventKind.CLAIM_ASSERTED.value]:
            summary_bits.append(
                f"{event_counts[EventKind.CLAIM_ASSERTED.value]} recorded finding{'s' if event_counts[EventKind.CLAIM_ASSERTED.value] != 1 else ''}"
            )
        if event_counts[EventKind.CLAIM_REPRODUCED.value]:
            summary_bits.append(
                f"{event_counts[EventKind.CLAIM_REPRODUCED.value]} reproduction{'s' if event_counts[EventKind.CLAIM_REPRODUCED.value] != 1 else ''}"
            )
        if event_counts[EventKind.ADOPTION_RECORDED.value]:
            summary_bits.append(
                f"{event_counts[EventKind.ADOPTION_RECORDED.value]} adoption{'s' if event_counts[EventKind.ADOPTION_RECORDED.value] != 1 else ''}"
            )
        if repeat_contributor_count:
            summary_bits.append(
                f"{repeat_contributor_count} repeat contributor{'s' if repeat_contributor_count != 1 else ''}"
            )
        summary_line = f"This {scope_label} already has " + ", ".join(summary_bits) + "."

    return EffortProof(
        contributor_count=contributor_count,
        current_window_participant_count=current_window_participant_count,
        new_arrival_count=new_arrival_count,
        repeat_contributor_count=repeat_contributor_count,
        worker_contributor_count=worker_contributor_count,
        verifier_contributor_count=verifier_contributor_count,
        visible_handoff_count=visible_handoffs,
        successful_run_count=len(successful_runs),
        claim_count=event_counts[EventKind.CLAIM_ASSERTED.value],
        reproduction_count=event_counts[EventKind.CLAIM_REPRODUCED.value],
        adoption_count=event_counts[EventKind.ADOPTION_RECORDED.value],
        record_setter_count=len(progress_milestones),
        latest_workspace=latest_workspace,
        progress_milestones=progress_milestones,
        summary_line=summary_line,
        latest_handoff_line=latest_handoff_line,
        actor_workspace_counts=dict(actor_counts),
        participant_spotlights=participant_spotlights,
    )


def _build_participant_spotlights(
    workspaces: list[WorkspaceView],
    *,
    current_workspace_ids: set[str],
) -> list[ParticipantSpotlight]:
    workspaces_by_actor: dict[str, list[WorkspaceView]] = {}
    for workspace in workspaces:
        actor = workspace.actor_id or "unknown"
        workspaces_by_actor.setdefault(actor, []).append(workspace)

    spotlights: list[ParticipantSpotlight] = []
    for actor, actor_workspaces in workspaces_by_actor.items():
        latest_workspace = max(actor_workspaces, key=lambda item: item.updated_at)
        spotlights.append(
            ParticipantSpotlight(
                actor=actor,
                latest_workspace=latest_workspace,
                workspace_count=len(actor_workspaces),
                current_window_workspace_count=sum(
                    1 for workspace in actor_workspaces if workspace.workspace_id in current_workspace_ids
                ),
                run_count=sum(len(workspace.run_ids) for workspace in actor_workspaces),
                claim_count=sum(len(workspace.claim_ids) for workspace in actor_workspaces),
                reproduction_count=sum(workspace.reproduction_count for workspace in actor_workspaces),
                adoption_count=sum(workspace.adoption_count for workspace in actor_workspaces),
                has_worker_handoff=any(_workspace_is_worker_origin(workspace) for workspace in actor_workspaces),
                has_verifier_handoff=any(
                    str(workspace.participant_role) == "verifier" for workspace in actor_workspaces
                ),
            )
        )

    return sorted(
        spotlights,
        key=lambda spotlight: (
            spotlight.current_window_workspace_count > 0,
            spotlight.workspace_count > 1,
            spotlight.latest_workspace.updated_at,
        ),
        reverse=True,
    )


def _build_progress_milestones(
    run_events: list[EventEnvelope],
) -> list[ProgressMilestone]:
    if not run_events:
        return []

    milestones: list[ProgressMilestone] = []
    best_run: EventEnvelope | None = None
    for event in run_events:
        if best_run is None:
            best_run = event
            milestones.append(
                _progress_milestone_from_event(
                    event,
                    label="Starting point",
                )
            )
            continue

        if _is_better_run_event(event, best_run):
            best_run = event
            milestones.append(
                _progress_milestone_from_event(
                    event,
                    label=f"New best #{len(milestones)}",
                )
            )

    if len(milestones) <= 5:
        return milestones
    return [milestones[0], *milestones[-4:]]


def _progress_milestone_from_event(event: EventEnvelope, *, label: str) -> ProgressMilestone:
    payload = event.payload
    return ProgressMilestone(
        label=label,
        actor=event.actor_id or "unknown",
        metric_name=str(payload.get("metric_name", "metric")),
        metric_value=float(payload.get("metric_value", 0.0)),
        direction=str(payload.get("direction", "min")),
        run_id=str(payload.get("run_id", event.aggregate_id or "run")),
        occurred_at=_format_timestamp(event.occurred_at),
    )


def _render_progress_milestone(step: ProgressMilestone) -> str:
    return f"""
    <li class="progress-step">
      <div class="progress-step-kicker">{escape(step.label)} · {escape(step.occurred_at)}</div>
      <strong>{escape(step.actor)} pushed <code>{escape(step.metric_name)}</code> to <code>{escape(_format_metric(step.metric_value))}</code>.</strong>
      <span>Run <code>{escape(_short_id(step.run_id))}</code> set the current {escape(step.direction == 'min' and 'lower-is-better' or 'higher-is-better')} marker.</span>
    </li>
    """


def _render_participant_spotlight(
    spotlight: ParticipantSpotlight,
    *,
    public_api_base_url: str,
    highlighted_actor_id: str | None = None,
    highlighted_workspace_id: str | None = None,
) -> str:
    latest_workspace = spotlight.latest_workspace
    discussion_url = (
        f"{public_api_base_url}/api/v1/publications/workspaces/{quote(latest_workspace.workspace_id)}/discussion"
    )
    highlight_class = (
        " highlight-card"
        if (highlighted_actor_id and spotlight.actor == highlighted_actor_id)
        or (highlighted_workspace_id and latest_workspace.workspace_id == highlighted_workspace_id)
        else ""
    )
    return f"""
    <article class="result-summary-card handoff-card{highlight_class}">
      <div class="effort-type">{'Returning contributor' if spotlight.workspace_count > 1 else 'Visible participant'}</div>
      <h3>{escape(spotlight.actor)}</h3>
      <p class="summary-headline">{escape(_participant_spotlight_summary(spotlight))}</p>
      <ul class="state-pills compact">
        <li><span>Presence</span><code>{'current window' if spotlight.current_window_workspace_count else 'carried forward'}</code></li>
        <li><span>Pattern</span><code>{'repeat' if spotlight.workspace_count > 1 else 'first visible'}</code></li>
        <li><span>Latest role</span><code>{escape(str(latest_workspace.participant_role))}</code></li>
        <li><span>Origin</span><code>{escape(_workspace_origin_label(latest_workspace))}</code></li>
        <li><span>Workspaces</span><code>{spotlight.workspace_count}</code></li>
        <li><span>Runs</span><code>{spotlight.run_count}</code></li>
        <li><span>Claims</span><code>{spotlight.claim_count}</code></li>
      </ul>
      <p class="handoff-meta">
        Latest workspace <code>{escape(_short_id(latest_workspace.workspace_id))}</code> · updated <code>{escape(_format_timestamp(latest_workspace.updated_at))}</code>
      </p>
      <div class="card-links">
        <a href="{escape(discussion_url)}">View latest discussion</a>
        <a href="#join-this-effort">Continue from this goal</a>
      </div>
    </article>
    """


def _participant_spotlight_summary(spotlight: ParticipantSpotlight) -> str:
    parts = [
        f"{spotlight.workspace_count} workspace{'s' if spotlight.workspace_count != 1 else ''}",
        f"{spotlight.run_count} run{'s' if spotlight.run_count != 1 else ''}",
    ]
    if spotlight.claim_count:
        parts.append(f"{spotlight.claim_count} claim{'s' if spotlight.claim_count != 1 else ''}")
    if spotlight.reproduction_count:
        parts.append(
            f"{spotlight.reproduction_count} reproduction{'s' if spotlight.reproduction_count != 1 else ''}"
        )
    if spotlight.adoption_count:
        parts.append(f"{spotlight.adoption_count} adoption{'s' if spotlight.adoption_count != 1 else ''}")

    summary = ", ".join(parts[:-1])
    if len(parts) > 1:
        summary = f"{summary}, and {parts[-1]}" if summary else parts[-1]
    else:
        summary = parts[0]
    return f"Visible through {summary} on this goal."


def _participant_visibility_summary(proof: EffortProof, *, scope_label: str) -> str:
    if proof.contributor_count == 0:
        return (
            f"No participants are visible on this {scope_label} yet. "
            "The first newcomer can leave the initial hosted handoff."
        )

    bits = [f"{proof.contributor_count} visible participant{'s' if proof.contributor_count != 1 else ''}"]
    if proof.current_window_participant_count == proof.contributor_count:
        bits.append("all visible in the current window")
    elif proof.current_window_participant_count:
        bits.append(
            f"{proof.current_window_participant_count} active in the current window"
        )
    if proof.worker_contributor_count:
        bits.append(
            f"{proof.worker_contributor_count} through worker import{'s' if proof.worker_contributor_count != 1 else ''}"
        )
    if proof.verifier_contributor_count:
        bits.append(
            f"{proof.verifier_contributor_count} acting as verifier{'s' if proof.verifier_contributor_count != 1 else ''}"
        )
    if proof.repeat_contributor_count:
        bits.append(
            f"{proof.repeat_contributor_count} returning contributor{'s' if proof.repeat_contributor_count != 1 else ''}"
        )
    if proof.new_arrival_count and proof.new_arrival_count != proof.contributor_count:
        bits.append(
            f"{proof.new_arrival_count} first-time visible contributor{'s' if proof.new_arrival_count != 1 else ''}"
        )

    lead = ", ".join(bits[:-1])
    if len(bits) > 1:
        lead = f"{lead}, and {bits[-1]}" if lead else bits[-1]
    else:
        lead = bits[0]
    return f"This {scope_label} currently shows {lead}."


def _prioritize_workspaces(
    workspaces: list[WorkspaceView],
    highlighted_workspace_id: str | None,
) -> list[WorkspaceView]:
    if highlighted_workspace_id is None:
        return workspaces
    return sorted(
        workspaces,
        key=lambda workspace: (workspace.workspace_id == highlighted_workspace_id, workspace.updated_at),
        reverse=True,
    )


def _prioritize_spotlights(
    spotlights: list[ParticipantSpotlight],
    *,
    highlighted_actor_id: str | None,
    highlighted_workspace_id: str | None,
) -> list[ParticipantSpotlight]:
    if highlighted_actor_id is None and highlighted_workspace_id is None:
        return spotlights
    return sorted(
        spotlights,
        key=lambda spotlight: (
            spotlight.actor == highlighted_actor_id
            or spotlight.latest_workspace.workspace_id == highlighted_workspace_id,
            spotlight.current_window_workspace_count > 0,
            spotlight.workspace_count > 1,
            spotlight.latest_workspace.updated_at,
        ),
        reverse=True,
    )


def _find_highlighted_claim(
    claim_summaries: list[ClaimSummary],
    *,
    highlighted_claim_id: str | None,
    highlighted_workspace_id: str | None,
) -> ClaimSummary | None:
    if highlighted_claim_id is not None:
        for claim in claim_summaries:
            if claim.claim_id == highlighted_claim_id:
                return claim
    if highlighted_workspace_id is not None:
        for claim in claim_summaries:
            if claim.workspace_id == highlighted_workspace_id:
                return claim
    return None


def _render_join_success_section(
    *,
    highlighted_workspace: WorkspaceView | None,
    highlighted_claim: ClaimSummary | None,
    highlighted_actor_id: str | None,
    highlighted_reproduction_run_id: str | None,
    current_workspace_ids: set[str],
    joined: bool,
    next_move: str,
    public_api_base_url: str,
) -> str:
    if highlighted_workspace is None:
        return ""
    discussion_url = (
        f"{public_api_base_url}/api/v1/publications/workspaces/{quote(highlighted_workspace.workspace_id)}/discussion"
    )
    heading = "You joined this goal" if joined else "Highlighted contribution"
    actor_label = highlighted_actor_id or highlighted_workspace.actor_id or "unknown"
    claim_line = (
        highlighted_claim.statement
        if highlighted_claim is not None
        else "No recorded finding was attached to this highlighted contribution."
    )
    reproduction_line = highlighted_reproduction_run_id or "none"
    return f"""
    <section id="your-contribution" class="panel success-panel">
      <div class="eyebrow">Your contribution</div>
      <h2>{escape(heading)}</h2>
      <p class="section-lede">
        {escape(actor_label)} now has visible hosted work on this goal. This is the page you can
        hand to the next human or agent instead of sending them back to a blank local loop.
      </p>
      <div class="grid two">
        <article class="result-summary-card highlight-card">
          <div class="effort-type">Visible now</div>
          <h3>{escape(actor_label)}</h3>
          <p class="summary-headline">{escape(_workspace_handoff_summary(highlighted_workspace))}</p>
          <ul class="state-pills compact">
            <li><span>Window</span><code>{'current' if highlighted_workspace.workspace_id in current_workspace_ids else 'carried'}</code></li>
            <li><span>Role</span><code>{escape(str(highlighted_workspace.participant_role))}</code></li>
            <li><span>Origin</span><code>{escape(_workspace_origin_label(highlighted_workspace))}</code></li>
            <li><span>Workspace</span><code>{escape(_short_id(highlighted_workspace.workspace_id))}</code></li>
            <li><span>Claim</span><code>{escape(_short_id(highlighted_claim.claim_id) if highlighted_claim is not None else 'none')}</code></li>
            <li><span>Reproduction</span><code>{escape(_short_id(reproduction_line) if reproduction_line != 'none' else 'none')}</code></li>
          </ul>
          <p class="handoff-meta">{escape(claim_line)}</p>
          <div class="card-links">
            <a href="{escape(discussion_url)}">View workspace discussion</a>
            <a href="#workspace-{escape(highlighted_workspace.workspace_id)}">Jump to this handoff</a>
          </div>
        </article>
        <article class="result-summary-card">
          <div class="effort-type">Hand this forward</div>
          <h3>What the next contributor should do</h3>
          <p class="summary-headline">{escape(next_move)}</p>
          <p class="footer-note">
            If you want to invite the next person in, hand them this goal page or the discussion
            link above. They should be able to see this workspace, inspect the evidence, and pick
            up from here.
          </p>
        </article>
      </div>
    </section>
    """


def _build_effort_worker_coordination(
    observations: list[LeaseObservation],
) -> EffortWorkerCoordination:
    sorted_observations = sorted(
        observations,
        key=_lease_sort_key,
        reverse=True,
    )
    active_count = sum(
        1
        for observation in sorted_observations
        if observation.lease.status in {LeaseState.ACQUIRED, LeaseState.RENEWED}
    )
    healthy_count = sum(
        1 for observation in sorted_observations if observation.liveness_status is LeaseLivenessStatus.HEALTHY
    )
    stale_count = sum(
        1 for observation in sorted_observations if observation.liveness_status is LeaseLivenessStatus.STALE
    )
    missing_count = sum(
        1 for observation in sorted_observations if observation.liveness_status is LeaseLivenessStatus.MISSING
    )
    released_count = sum(
        1 for observation in sorted_observations if observation.lease.status is LeaseState.RELEASED
    )
    completed_count = sum(
        1 for observation in sorted_observations if observation.lease.status is LeaseState.COMPLETED
    )
    failed_count = sum(
        1 for observation in sorted_observations if observation.lease.status is LeaseState.FAILED
    )
    expired_count = sum(
        1 for observation in sorted_observations if observation.lease.status is LeaseState.EXPIRED
    )
    latest_observation = sorted_observations[0] if sorted_observations else None

    if not sorted_observations:
        summary_line = (
            "No worker lease or heartbeat state is visible on this goal yet."
        )
    elif active_count:
        bits = [f"{active_count} active worker lease{'s' if active_count != 1 else ''}"]
        if healthy_count:
            bits.append(f"{healthy_count} healthy")
        if stale_count:
            bits.append(f"{stale_count} stale")
        if missing_count:
            bits.append(f"{missing_count} still waiting for a heartbeat")
        lead = ", ".join(bits[:-1])
        if len(bits) > 1:
            lead = f"{lead}, and {bits[-1]}" if lead else bits[-1]
        else:
            lead = bits[0]
        summary_line = f"This goal currently has {lead}."
    else:
        latest_node = latest_observation.lease.holder_node_id or "the latest worker"
        latest_status = latest_observation.lease.status.value
        renewal_note = (
            f" after {latest_observation.lease.renewal_count} renewal"
            f"{'s' if latest_observation.lease.renewal_count != 1 else ''}"
            if latest_observation.lease.renewal_count
            else ""
        )
        heartbeat_note = ""
        if latest_observation.holder_heartbeat is None:
            heartbeat_note = " No heartbeat was observed for that lease."
        else:
            heartbeat_note = (
                f" The last observed heartbeat is {latest_observation.holder_heartbeat.freshness_status.value}."
            )
        summary_line = (
            f"{len(sorted_observations)} worker lease window"
            f"{'s have' if len(sorted_observations) != 1 else ' has'} touched this goal. "
            f"No worker is active right now; {latest_node} left its latest lease in status {latest_status}{renewal_note}."
            f"{heartbeat_note}"
        )

    return EffortWorkerCoordination(
        observations=sorted_observations,
        active_count=active_count,
        healthy_count=healthy_count,
        stale_count=stale_count,
        missing_count=missing_count,
        released_count=released_count,
        completed_count=completed_count,
        failed_count=failed_count,
        expired_count=expired_count,
        latest_observation=latest_observation,
        summary_line=summary_line,
    )


def _render_worker_coordination_card(
    observation: LeaseObservation,
    *,
    public_api_base_url: str,
) -> str:
    lease = observation.lease
    raw_url = f"{public_api_base_url}/api/v1/leases/{quote(lease.lease_id)}"
    discussion_url = (
        f"{public_api_base_url}/api/v1/publications/workspaces/{quote(lease.holder_workspace_id)}/discussion"
        if lease.holder_workspace_id
        else None
    )
    latest_change = _lease_latest_timestamp(observation)
    latest_change_line = (
        f"Latest change <code>{escape(_format_timestamp(latest_change))}</code>"
        if latest_change is not None
        else "Latest change time unavailable"
    )
    heartbeat_line = (
        f"Heartbeat <code>{escape(_format_timestamp(observation.holder_heartbeat.observed_at))}</code>"
        if observation.holder_heartbeat is not None
        else "No heartbeat observed"
    )
    links = [f'<a href="{escape(raw_url)}">Open lease observation</a>']
    if discussion_url is not None:
        links.insert(0, f'<a href="{escape(discussion_url)}">View workspace discussion</a>')
    return f"""
    <article class="result-summary-card handoff-card">
      <div class="effort-type">Worker lease</div>
      <h3>{escape(lease.holder_node_id or "unknown worker")}</h3>
      <p class="summary-headline">{escape(_worker_lease_summary(observation))}</p>
      <ul class="state-pills compact">
        <li><span>Status</span><code>{escape(_display_token(lease.status.value))}</code></li>
        <li><span>Liveness</span><code>{escape(_display_token(observation.liveness_status.value))}</code></li>
        <li><span>Work item</span><code>{escape(_display_token(lease.work_item_type.value))}</code></li>
        <li><span>Subject</span><code>{escape(_lease_subject_label(observation))}</code></li>
        <li><span>Renewals</span><code>{lease.renewal_count}</code></li>
        <li><span>Heartbeat</span><code>{escape(_display_token(observation.holder_heartbeat.freshness_status.value if observation.holder_heartbeat is not None else 'none'))}</code></li>
      </ul>
      <p class="handoff-meta">
        Lease <code>{escape(_short_id(lease.lease_id))}</code> · {latest_change_line} · {heartbeat_line}
      </p>
      <div class="card-links">
        {' '.join(links)}
      </div>
    </article>
    """


def _worker_lease_summary(observation: LeaseObservation) -> str:
    lease = observation.lease
    subject_label = _lease_subject_label(observation)
    if lease.status in {LeaseState.ACQUIRED, LeaseState.RENEWED}:
        if observation.liveness_status is LeaseLivenessStatus.HEALTHY:
            return f"Currently holding a {lease.work_item_type.value} lease on {subject_label} with healthy heartbeats."
        if observation.liveness_status is LeaseLivenessStatus.MISSING:
            return f"Holds a {lease.work_item_type.value} lease on {subject_label}, but no heartbeat has been observed yet."
        return f"Still holds a {lease.work_item_type.value} lease on {subject_label}, but the latest heartbeat is stale."
    if lease.status is LeaseState.RELEASED:
        return f"Released a {lease.work_item_type.value} lease on {subject_label}."
    if lease.status is LeaseState.COMPLETED:
        return f"Completed a {lease.work_item_type.value} lease on {subject_label}."
    if lease.status is LeaseState.FAILED:
        return f"Failed a {lease.work_item_type.value} lease on {subject_label}: {_trim_sentence(lease.failure_reason or 'no failure reason recorded', limit=120)}"
    if lease.status is LeaseState.EXPIRED:
        return f"The {lease.work_item_type.value} lease on {subject_label} expired before a clean release."
    return f"Observed a {lease.work_item_type.value} lease on {subject_label}."


def _lease_subject_label(observation: LeaseObservation) -> str:
    lease = observation.lease
    if lease.subject_type.value == "effort" and lease.effort_id == lease.subject_id:
        return "this goal"
    return f"{lease.subject_type.value}:{_short_id(lease.subject_id)}"


def _lease_sort_key(observation: LeaseObservation):
    latest = _lease_latest_timestamp(observation)
    return (
        observation.lease.status in {LeaseState.ACQUIRED, LeaseState.RENEWED},
        latest or observation.lease.expires_at,
    )


def _lease_latest_timestamp(observation: LeaseObservation):
    timestamps = [
        observation.lease.failed_at,
        observation.lease.completed_at,
        observation.lease.released_at,
        observation.lease.renewed_at,
        observation.lease.acquired_at,
        observation.holder_heartbeat.observed_at if observation.holder_heartbeat is not None else None,
    ]
    return max((timestamp for timestamp in timestamps if timestamp is not None), default=None)


def _display_token(value: str) -> str:
    return value.replace("_", " ")


def _render_workspace_proof_meta(workspace: WorkspaceView, *, is_current_window: bool) -> str:
    return f"""
    <ul class="state-pills compact">
      <li><span>Window</span><code>{'current' if is_current_window else 'carried'}</code></li>
      <li><span>Role</span><code>{escape(str(workspace.participant_role))}</code></li>
      <li><span>Origin</span><code>{escape(_workspace_origin_label(workspace))}</code></li>
      <li><span>Path</span><code>{escape(_workspace_execution_label(workspace))}</code></li>
      <li><span>Runs</span><code>{len(workspace.run_ids)}</code></li>
      <li><span>Claims</span><code>{len(workspace.claim_ids)}</code></li>
      <li><span>Reproductions</span><code>{workspace.reproduction_count}</code></li>
      <li><span>Workspace</span><code>{escape(_short_id(workspace.workspace_id))}</code></li>
    </ul>
    <p class="handoff-meta">Updated <code>{escape(_format_timestamp(workspace.updated_at))}</code> on the hosted goal page{'' if is_current_window else '; carried forward from an earlier proof window in this series'}.</p>
    """


def _render_frontier_item(member: FrontierMember, workspace_actor_map: dict[str, str]) -> str:
    actor = workspace_actor_map.get(member.workspace_id or "", "unknown")
    return (
        "<li>"
        f"<code>{escape(member.snapshot_id)}</code> from "
        f"<code>{escape(actor)}</code>: "
        f"<code>{escape(member.metric_name)}</code> = "
        f"<code>{escape(_format_metric(member.metric_value))}</code> "
        f"({escape(member.direction)}, claims={member.claim_count})"
        "</li>"
    )


def _render_claim_item(claim: ClaimSummary, workspace_actor_map: dict[str, str]) -> str:
    actor = workspace_actor_map.get(claim.workspace_id or "", "unknown")
    return (
        "<li>"
        f"<code>{escape(claim.claim_id)}</code> from <code>{escape(actor)}</code> "
        f"[{escape(str(claim.status))}] "
        f"{escape(claim.statement)} "
        f"(reproductions={claim.support_count}, contradictions={claim.contradiction_count})"
        "</li>"
    )


def _best_result_summary(
    frontier_members: list[FrontierMember],
    workspace_actor_map: dict[str, str],
) -> str:
    if not frontier_members:
        return "No frontier result yet. The next participant can leave the first visible result."

    best = frontier_members[0]
    actor = workspace_actor_map.get(best.workspace_id or "", "unknown")
    return (
        f"{best.metric_name} {_format_metric(best.metric_value)} from {actor}. "
        f"{best.claim_count} recorded finding{'s' if best.claim_count != 1 else ''} attached."
    )


def _latest_claim_summary(
    claim_summaries: list[ClaimSummary],
    workspace_actor_map: dict[str, str],
) -> str:
    if not claim_summaries:
        return "No findings yet. The next participant can leave the first explicit finding."

    latest = claim_summaries[0]
    actor = workspace_actor_map.get(latest.workspace_id or "", "unknown")
    return (
        f"{actor} reported a {latest.status} finding: "
        f"{_trim_sentence(latest.statement, limit=120)}"
    )


def _next_move_summary(
    effort: EffortView,
    claim_summaries: list[ClaimSummary],
    frontier_members: list[FrontierMember],
    workspace_actor_map: dict[str, str],
) -> str:
    if claim_summaries:
        target = sorted(
            claim_summaries,
            key=lambda claim: (claim.support_count, claim.updated_at),
        )[0]
        actor = workspace_actor_map.get(target.workspace_id or "", "unknown")
        return f"Join {effort.name}, reproduce {actor}'s claim, then leave your own brief behind."

    if frontier_members:
        best = frontier_members[0]
        actor = workspace_actor_map.get(best.workspace_id or "", "unknown")
        return f"Join {effort.name}, inspect {actor}'s best result, and try to beat it or reproduce it."

    return f"Join {effort.name} and leave the first visible run, claim, and brief."


def _workspace_handoff_summary(workspace: WorkspaceView) -> str:
    parts: list[str] = [f"{len(workspace.run_ids)} run{'s' if len(workspace.run_ids) != 1 else ''}"]
    claim_count = len(workspace.claim_ids)
    if claim_count:
        parts.append(f"{claim_count} claim{'s' if claim_count != 1 else ''}")
    if workspace.reproduction_count:
        parts.append(
            f"{workspace.reproduction_count} reproduction{'s' if workspace.reproduction_count != 1 else ''}"
        )
    if workspace.adoption_count:
        parts.append(f"{workspace.adoption_count} adoption{'s' if workspace.adoption_count != 1 else ''}")

    summary = ", ".join(parts[:-1])
    if len(parts) > 1:
        summary = f"{summary}, and {parts[-1]}" if summary else parts[-1]
    else:
        summary = parts[0]
    return f"Left behind {summary} that the next participant can inspect and continue."


def _trim_sentence(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _format_metric(value: float) -> str:
    return f"{value:.6f}"


def _format_timestamp(value) -> str:
    return value.strftime("%Y-%m-%d %H:%M UTC")


def _short_id(value: str) -> str:
    if len(value) <= 12:
        return value
    return f"{value[:8]}…{value[-4:]}"


def _is_better_run_event(candidate: EventEnvelope, existing: EventEnvelope) -> bool:
    candidate_direction = str(candidate.payload.get("direction", "min"))
    existing_direction = str(existing.payload.get("direction", "min"))
    if candidate_direction != existing_direction:
        return candidate.occurred_at > existing.occurred_at

    candidate_metric = float(candidate.payload.get("metric_value", 0.0))
    existing_metric = float(existing.payload.get("metric_value", 0.0))
    if candidate_direction == "min":
        return candidate_metric < existing_metric
    return candidate_metric > existing_metric


def _render_goal_contract_card(effort: EffortView) -> str:
    if not any(
        (
            effort.metric_name,
            effort.direction,
            effort.constraints,
            effort.evidence_requirement,
            effort.stop_condition,
            effort.author_id,
        )
    ):
        return ""
    constraint_items = "".join(f"<li>{escape(item)}</li>" for item in effort.constraints)
    constraint_block = (
        f"<ul class=\"link-list compact-list\">{constraint_items}</ul>"
        if constraint_items
        else "<p class=\"footer-note\">No explicit constraints recorded on this goal yet.</p>"
    )
    return f"""
    <div class="summary-card">
      <div class="effort-type">Goal contract</div>
      <p class="summary-headline">{escape(effort.metric_name or effort.objective)} · {escape(str(effort.direction or 'n/a'))}</p>
      <ul class="state-pills compact">
        <li><span>Author</span><code>{escape(effort.author_id or 'unknown')}</code></li>
        <li><span>Join mode</span><code>{escape(effort.tags.get('join_mode') or 'standard')}</code></li>
      </ul>
      <p class="footer-note">{escape(effort.evidence_requirement or 'No explicit evidence requirement recorded.')}</p>
      <p class="footer-note">{escape(effort.stop_condition or 'No explicit stop condition recorded.')}</p>
      {constraint_block}
    </div>
    """


def _publish_goal_html(
    *,
    site_css_url: str = "/styles.css",
    site_js_url: str | None = None,
) -> str:
    return _page_html(
        "Publish Goal",
        """
        <section class="hero">
          <div class="eyebrow">Publish a goal</div>
          <h1>Publish a live ML goal people and agents can join.</h1>
          <p class="lede">
            This v1 publish path turns a scoped ML goal into a live goal page with a join command,
            visible contributions, and a public handoff trail.
          </p>
          <p class="footer-note">
            Honesty line: publication is public and attributed only by lightweight asserted handle in v1.
            The default join path for newly published goals still runs through the tiny-loop proxy contribution path.
          </p>
        </section>

        <section class="panel">
          <div class="eyebrow">Goal form</div>
          <h2>Define the goal contract</h2>
          <p class="section-lede">Fill in the minimum contract needed for other people or agents to contribute without guessing what counts as progress.</p>
          <form id="publish-goal-form" class="publish-goal-form">
            <label><span>Title</span><input name="title" required placeholder="Improve val_bpb on Apple Silicon"></label>
            <label><span>Summary</span><textarea name="summary" required rows="3" placeholder="What the goal is and why it matters."></textarea></label>
            <div class="grid two">
              <label><span>Objective key</span><input name="objective" required placeholder="val_bpb"></label>
              <label><span>Metric name</span><input name="metric_name" required placeholder="validation bits-per-byte"></label>
            </div>
            <div class="grid two">
              <label><span>Direction</span>
                <select name="direction">
                  <option value="min">Lower is better</option>
                  <option value="max">Higher is better</option>
                </select>
              </label>
              <label><span>Platform</span><input name="platform" required placeholder="Apple-Silicon-MLX"></label>
            </div>
            <div class="grid two">
              <label><span>Budget seconds</span><input name="budget_seconds" required type="number" min="1" value="300"></label>
              <label><span>Author handle</span><input name="actor_id" required placeholder="aliargun"></label>
            </div>
            <label><span>Constraints</span><textarea name="constraints" required rows="4" placeholder="One constraint per line"></textarea></label>
            <label><span>Evidence requirement</span><textarea name="evidence_requirement" required rows="2" placeholder="What evidence should a contribution leave behind?"></textarea></label>
            <label><span>Stop condition</span><textarea name="stop_condition" required rows="2" placeholder="When should this goal stop or be reconsidered?"></textarea></label>
            <div class="hero-actions">
              <button class="button primary" type="submit">Publish this goal</button>
              <a class="button secondary" href="/efforts">Back to live goals</a>
            </div>
          </form>
        </section>

        <section id="publish-result" class="panel" hidden>
          <div class="eyebrow">Published</div>
          <h2>Your goal is live</h2>
          <p class="section-lede" id="publish-result-summary"></p>
          <p class="command" id="publish-result-command"></p>
          <div class="hero-actions">
            <a class="button primary" id="publish-result-goal-link" href="#">Open live goal page</a>
            <a class="button secondary" id="publish-result-join-link" href="#">Copy join command</a>
          </div>
        </section>
        """,
        site_css_url=site_css_url,
        site_js_url=site_js_url,
    )


def _join_command(effort: dict[str, object], *, api_base_url: str) -> str:
    tags = effort.get("tags", {})
    if tags.get("external_harness") == "mlx-history":
        return (
            "python3 scripts/run_overnight_autoresearch_worker.py "
            "--repo-path <path_to_mlx_history> "
            "--runner-command '<external_harness_command>' "
            f"--base-url {api_base_url}"
        )
    if explicit := tags.get("join_command"):
        return str(explicit)

    if tags.get("goal_origin") == "user-published":
        return f"python3 -m clients.tiny_loop.run --base-url {api_base_url} --effort-id {effort.get('effort_id')}"

    effort_type = tags.get("effort_type")
    command = "python3 -m clients.tiny_loop.run"
    if effort_type == "inference":
        command = f"{command} --profile inference-sprint"
    elif effort_type != "eval":
        command = f"{command} --profile standalone"
    return f"{command} --base-url {api_base_url}"


def _join_brief(effort: dict[str, object]) -> str:
    tags = effort.get("tags", {})
    if tags.get("external_harness") == "mlx-history":
        return "README.md#real-overnight-autoresearch-worker"
    if explicit := tags.get("join_brief_path"):
        return str(explicit)
    if tags.get("goal_origin") == "user-published":
        return "/publish"
    return "docs/seeded-efforts.md"


def _workspace_execution_label(workspace: WorkspaceView) -> str:
    if workspace.tags.get("simulated_contribution") == "true":
        return "proxy"
    if harness := workspace.tags.get("external_harness"):
        worker_mode = workspace.tags.get("worker_mode")
        if worker_mode:
            return f"{harness}:{worker_mode}"
        return harness
    return "standard"


def _workspace_origin_label(workspace: WorkspaceView) -> str:
    if _workspace_is_worker_origin(workspace):
        return "worker import"
    if str(workspace.participant_role) == "verifier" and workspace.tags.get("simulated_contribution") == "true":
        return "proxy verifier"
    if str(workspace.participant_role) == "verifier":
        return "verifier handoff"
    if workspace.tags.get("simulated_contribution") == "true":
        return "proxy loop"
    if workspace.tags.get("external_harness"):
        return "external harness"
    return "hosted handoff"


def _workspace_is_worker_origin(workspace: WorkspaceView) -> bool:
    return bool(workspace.tags.get("worker_mode"))


def _effort_state_label(effort) -> dict[str, str]:
    tags = effort.tags if hasattr(effort, "tags") else effort.get("tags", {})
    if is_historical_proof_effort(effort):
        return {
            "label": "Historical goal window",
            "description": "This proof window remains inspectable in the immutable event log, but new proof work should continue on its successor goal window.",
        }
    if tags.get("external_harness") == "mlx-history":
        return {
            "label": "Live external-harness goal",
            "description": "Real kept-history from an external MLX line is compounding on a live hosted goal through adoption and visible handoffs.",
        }
    if tags.get("effort_type") == "inference":
        return {
            "label": "Live goal, proxy join path",
            "description": "This goal is live on the hosted control plane, while the current public join path is still a narrow proxy loop for the larger inference objective.",
        }
    if tags.get("effort_type") == "eval":
        return {
            "label": "Live goal, proxy join path",
            "description": "This goal is live on the hosted control plane, while the current public join path is still a narrow proxy loop for the larger eval objective.",
        }
    if tags.get("goal_origin") == "user-published":
        return {
            "label": "User-published goal, proxy join path",
            "description": "This goal was published through the public goal flow. The current join path is still the tiny-loop proxy contribution path in v1.",
        }
    return {
        "label": "Live goal",
        "description": "This goal page is generated from hosted control-plane state.",
    }

def _page_html(
    title: str,
    body: str,
    *,
    site_css_url: str = "/styles.css",
    site_js_url: str | None = None,
) -> str:
    script_markup = (
        f'<script src="{escape(site_js_url)}" defer></script>' if site_js_url else ""
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} · OpenIntention</title>
    <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link
      href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap"
      rel="stylesheet"
    >
    <link rel="stylesheet" href="{escape(site_css_url)}">
  </head>
  <body>
    <main class="page">
      {body}
    </main>
    <footer class="site-footer">
      <p class="site-footer-copy">OpenIntention keeps goals, evidence, and handoffs public enough to compound.</p>
      <div class="site-footer-links">
        <a href="/efforts">Live goals</a>
        <a href="/evidence/join-with-ai.html">Agent brief</a>
        <a href="{escape(DEFAULT_PUBLIC_REPO_URL)}">GitHub repo</a>
      </div>
    </footer>
    {script_markup}
  </body>
</html>
"""
