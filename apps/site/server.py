from __future__ import annotations

from html import escape
import os
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from research_os.effort_lifecycle import is_historical_proof_effort
from research_os.effort_lifecycle import is_public_proof_effort
from research_os.effort_lifecycle import proof_version
from research_os.effort_lifecycle import split_current_and_historical_efforts
from research_os.domain.models import ClaimSummary
from research_os.domain.models import EffortView
from research_os.domain.models import FrontierMember
from research_os.domain.models import WorkspaceView

DEFAULT_API_BASE_URL = "https://openintention-api-production.up.railway.app"


def create_site_app(
    dist_dir: Path | None = None,
    *,
    api_base_url: str | None = None,
    api_fetch_base_url: str | None = None,
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
    assets_root.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="OpenIntention Site", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/assets", StaticFiles(directory=assets_root), name="site-assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(dist_root / "index.html")

    @app.get("/styles.css", include_in_schema=False)
    def styles() -> FileResponse:
        return FileResponse(dist_root / "styles.css")

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
        return _effort_index_html(
            public_api_base_url=normalized_public_api_base_url,
            efforts=efforts,
        )

    @app.get("/efforts/{effort_id}", include_in_schema=False, response_class=HTMLResponse)
    def effort_detail(effort_id: str) -> str:
        efforts = _fetch_json(normalized_fetch_api_base_url, "/api/v1/efforts")
        effort = next((item for item in efforts if item["effort_id"] == effort_id), None)
        if effort is None:
            raise HTTPException(status_code=404, detail="effort not found")

        workspaces = _fetch_json(
            normalized_fetch_api_base_url,
            "/api/v1/workspaces",
            query={"effort_id": effort_id},
        )
        claims = _fetch_json(
            normalized_fetch_api_base_url,
            "/api/v1/claims",
            query={"objective": effort["objective"], "platform": effort["platform"]},
        )
        workspace_ids = {workspace["workspace_id"] for workspace in workspaces}
        effort_claims = [claim for claim in claims if claim.get("workspace_id") in workspace_ids]
        frontier = _fetch_json(
            normalized_fetch_api_base_url,
            f"/api/v1/frontiers/{quote(effort['objective'])}/{quote(effort['platform'])}",
            query={"budget_seconds": effort["budget_seconds"]},
        )

        return _effort_detail_html(
            public_api_base_url=normalized_public_api_base_url,
            effort=effort,
            workspaces=workspaces,
            claims=effort_claims,
            frontier=frontier,
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
    with urlopen(f"{api_base_url}{path}{query_string}", timeout=30) as response:
        import json

        return json.loads(response.read().decode("utf-8"))


def _effort_index_html(*, public_api_base_url: str, efforts: list[dict[str, object]]) -> str:
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
          <h2>Historical proof runs</h2>
          <p class="footer-note">Older proof windows stay visible and inspectable, but new proof work should continue on the current successor effort.</p>
          <section class="efforts">{historical_cards}</section>
        </section>
        """
    return _page_html(
        "Live Efforts",
        """
        <section class="hero">
          <div class="eyebrow">Live explorer</div>
          <h1>Shared efforts, visible state, and clear next steps.</h1>
          <p class="lede">
            These pages are generated from the hosted control plane. They show what is active now,
            what is still proxy, and what the next participant can continue.
          </p>
          <div class="hero-actions">
            <a class="button primary" href="/">Back to OpenIntention</a>
          </div>
        </section>
        """
        + f'<section class="efforts">{cards or "<p>No efforts found.</p>"}</section>'
        + historical_section
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
        <a class="button primary" href="/efforts/{escape(str(effort_model.effort_id))}">Open live effort page</a>
        <a class="button secondary" href="{escape(public_api_base_url)}/api/v1/publications/efforts/{escape(str(effort_model.effort_id))}">Open markdown mirror</a>
      </div>
    </article>
    """


def _effort_detail_html(
    *,
    public_api_base_url: str,
    effort: dict[str, object],
    workspaces: list[dict[str, object]],
    claims: list[dict[str, object]],
    frontier: dict[str, object],
) -> str:
    effort_model = EffortView.model_validate(effort)
    workspace_models = sorted(
        (WorkspaceView.model_validate(workspace) for workspace in workspaces),
        key=lambda workspace: workspace.updated_at,
        reverse=True,
    )
    claim_models = sorted(
        (ClaimSummary.model_validate(claim) for claim in claims),
        key=lambda claim: claim.updated_at,
        reverse=True,
    )
    frontier_members = [
        FrontierMember.model_validate(member) for member in frontier.get("members", [])[:8]
    ]
    state = _effort_state_label(effort_model)
    join_command = _join_command(effort, api_base_url=public_api_base_url)
    join_brief = _join_brief(effort)
    workspace_actor_map = {workspace.workspace_id: workspace.actor_id or "unknown" for workspace in workspace_models}
    recent_handoffs = "\n".join(
        _render_recent_handoff(workspace, public_api_base_url=public_api_base_url) for workspace in workspace_models[:6]
    )
    frontier_items = "\n".join(_render_frontier_item(member, workspace_actor_map) for member in frontier_members)
    claim_items = "\n".join(_render_claim_item(claim, workspace_actor_map) for claim in claim_models[:8])
    best_result = _best_result_summary(frontier_members, workspace_actor_map)
    latest_claim = _latest_claim_summary(claim_models, workspace_actor_map)
    next_move = _next_move_summary(effort_model, claim_models, frontier_members, workspace_actor_map)
    return _page_html(
        str(effort["name"]),
        f"""
        <section class="hero">
          <div class="eyebrow">{escape(state["label"])}</div>
          <h1>{escape(str(effort_model.name))}</h1>
          <p class="lede">{escape(state["description"])}</p>
          <div class="hero-actions">
            <a class="button primary" href="/">Back to OpenIntention</a>
            <a class="button secondary" href="/efforts">See all live efforts</a>
          </div>
        </section>

        <section class="panel grid two effort-summary-grid">
          <div class="summary-stack">
            <div class="summary-card">
              <div class="effort-type">Best current result</div>
              <p class="summary-headline">{escape(best_result)}</p>
            </div>
            <div class="summary-card">
              <div class="effort-type">Latest claim signal</div>
              <p class="summary-headline">{escape(latest_claim)}</p>
            </div>
            <div class="summary-card">
              <div class="effort-type">Best next move</div>
              <p class="summary-headline">{escape(next_move)}</p>
            </div>
            <ul class="state-pills">
              <li><span>Objective</span><code>{escape(str(effort["objective"]))}</code></li>
              <li><span>Platform</span><code>{escape(str(effort_model.platform))}</code></li>
              <li><span>Budget</span><code>{escape(str(effort_model.budget_seconds))}s</code></li>
              <li><span>Workspaces</span><code>{len(workspace_models)}</code></li>
              <li><span>Claims</span><code>{len(claim_models)}</code></li>
              <li><span>Frontier</span><code>{len(frontier_members)}</code></li>
              {'<li><span>Lifecycle</span><code>historical proof run</code></li>' if is_historical_proof_effort(effort_model) else ''}
              {f'<li><span>Successor</span><code>{escape(str(effort_model.successor_effort_id))}</code></li>' if effort_model.successor_effort_id else ''}
              {f'<li><span>Proof version</span><code>{escape(str(proof_version(effort_model)))}</code></li>' if is_public_proof_effort(effort_model) else ''}
            </ul>
            <p class="footer-note">Rendered directly from live hosted control-plane state.</p>
          </div>
          <div id="join-this-effort" class="summary-card join-summary-card">
            <div class="effort-type">Join this effort</div>
            <h2>Pick up the current line of work</h2>
            <p>Pick up the current line of work, then leave behind a workspace, a claim or reproduction, and an inspectable brief for the next participant.</p>
            <p class="command">{escape(join_command)}</p>
            <ul>
              <li>Brief: <code>{escape(join_brief)}</code></li>
              <li>Optional attribution: add <code>--actor-id &lt;handle&gt;</code></li>
            </ul>
          </div>
        </section>

        <section class="panel">
          <div class="proof-result-header">
            <div>
              <div class="eyebrow">Recent handoffs</div>
              <h2>What recent contributors left behind</h2>
            </div>
            <p class="section-lede">Each successful join should leave behind work the next person can inspect and continue without asking for local context.</p>
          </div>
          <div class="handoff-grid">
            {recent_handoffs or '<p>No handoffs yet. Use the join command above to leave the first visible result.</p>'}
          </div>
        </section>

        <section class="panel machine-state-panel">
          <div class="proof-result-header">
            <div>
              <div class="eyebrow">Full live state</div>
              <h2>Machine-readable frontier and claim state</h2>
            </div>
            <p class="section-lede">This lower section keeps the raw state visible for agents and technical users without making ids the first thing a human sees.</p>
          </div>
          <section class="grid two">
          <div>
            <h2>Frontier</h2>
            <ul class="link-list">
              {frontier_items or "<li>No frontier members yet.</li>"}
            </ul>
          </div>
          <div>
            <h2>Claim signals</h2>
            <ul class="link-list">
              {claim_items or "<li>No claims recorded yet.</li>"}
            </ul>
          </div>
          </section>
        </section>
        """,
    )


def _render_recent_handoff(workspace: WorkspaceView, *, public_api_base_url: str) -> str:
    actor = workspace.actor_id or "unknown"
    discussion_url = (
        f"{public_api_base_url}/api/v1/publications/workspaces/{quote(workspace.workspace_id)}/discussion"
    )
    return f"""
    <article class="result-summary-card handoff-card">
      <div class="effort-type">Recent handoff</div>
      <h3>{escape(actor)}</h3>
      <p class="summary-headline">{escape(_workspace_handoff_summary(workspace))}</p>
      <ul class="state-pills compact">
        <li><span>Role</span><code>{escape(str(workspace.participant_role))}</code></li>
        <li><span>Runs</span><code>{len(workspace.run_ids)}</code></li>
        <li><span>Claims</span><code>{len(workspace.claim_ids)}</code></li>
        <li><span>Reproductions</span><code>{workspace.reproduction_count}</code></li>
      </ul>
      <p class="handoff-meta">
        Workspace <code>{escape(workspace.workspace_id)}</code> · updated <code>{escape(workspace.updated_at.isoformat())}</code>
      </p>
      <div class="card-links">
        <a href="{escape(discussion_url)}">View discussion</a>
        <a href="#join-this-effort">Continue from this effort</a>
      </div>
    </article>
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
        f"{best.claim_count} claim signal{'s' if best.claim_count != 1 else ''} attached."
    )


def _latest_claim_summary(
    claim_summaries: list[ClaimSummary],
    workspace_actor_map: dict[str, str],
) -> str:
    if not claim_summaries:
        return "No claims yet. The next participant can leave the first explicit claim."

    latest = claim_summaries[0]
    actor = workspace_actor_map.get(latest.workspace_id or "", "unknown")
    return (
        f"{actor} left a {latest.status} claim: "
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


def _join_command(effort: dict[str, object], *, api_base_url: str) -> str:
    tags = effort.get("tags", {})
    if explicit := tags.get("join_command"):
        return str(explicit)

    effort_type = tags.get("effort_type")
    command = "python3 -m clients.tiny_loop.run"
    if effort_type == "inference":
        command = f"{command} --profile inference-sprint"
    elif effort_type != "eval":
        command = f"{command} --profile standalone"
    return f"{command} --base-url {api_base_url}"


def _join_brief(effort: dict[str, object]) -> str:
    tags = effort.get("tags", {})
    if explicit := tags.get("join_brief_path"):
        return str(explicit)
    if tags.get("external_harness") == "autoresearch-mlx":
        return "README.md#external-harness-compounding-proof"
    return "docs/seeded-efforts.md"


def _effort_state_label(effort) -> dict[str, str]:
    tags = effort.tags if hasattr(effort, "tags") else effort.get("tags", {})
    if is_historical_proof_effort(effort):
        return {
            "label": "Historical proof run",
            "description": "This proof window remains inspectable in the immutable event log, but new proof work should continue on its successor effort.",
        }
    if tags.get("external_harness") == "autoresearch-mlx":
        return {
            "label": "Live external-harness proof",
            "description": "Real kept-history from autoresearch-mlx is compounding through adoption in the hosted shared control plane.",
        }
    if tags.get("effort_type") == "inference":
        return {
            "label": "Hosted shared state, proxy contribution loop",
            "description": "The shared effort state is live, while the current contribution path is still a narrow proxy loop for the larger inference objective.",
        }
    if tags.get("effort_type") == "eval":
        return {
            "label": "Hosted shared state, proxy contribution loop",
            "description": "The shared effort state is live, while the current contribution path is still a narrow proxy loop for the larger eval objective.",
        }
    return {
        "label": "Live shared effort",
        "description": "This effort page is generated from hosted control-plane state.",
    }


def _page_html(title: str, body: str) -> str:
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
    <link rel="stylesheet" href="/styles.css">
  </head>
  <body>
    <main class="page">
      {body}
    </main>
  </body>
</html>
"""
