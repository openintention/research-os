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
    from research_os.domain.models import EffortView

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
    from research_os.domain.models import EffortView

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
    from research_os.domain.models import EffortView

    effort_model = EffortView.model_validate(effort)
    state = _effort_state_label(effort_model)
    join_command = _join_command(effort, api_base_url=public_api_base_url)
    join_brief = _join_brief(effort)
    recent_workspaces = "\n".join(_render_workspace_item(workspace) for workspace in workspaces[:6])
    frontier_items = "\n".join(_render_frontier_item(member) for member in frontier.get("members", [])[:8])
    claim_items = "\n".join(_render_claim_item(claim) for claim in claims[:8])
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

        <section class="panel grid two">
          <div>
            <h2>Current state</h2>
            <ul>
              <li>Objective: <code>{escape(str(effort["objective"]))}</code></li>
              <li>Platform: <code>{escape(str(effort_model.platform))}</code></li>
              <li>Budget seconds: <code>{escape(str(effort_model.budget_seconds))}</code></li>
              <li>Attached workspaces: <code>{len(workspaces)}</code></li>
              <li>Claims in effort scope: <code>{len(claims)}</code></li>
              <li>Frontier members: <code>{len(frontier.get("members", []))}</code></li>
              {'<li>Lifecycle: <code>historical proof run</code></li>' if is_historical_proof_effort(effort_model) else ''}
              {f'<li>Current successor: <code>{escape(str(effort_model.successor_effort_id))}</code></li>' if effort_model.successor_effort_id else ''}
              {f'<li>Proof version: <code>{escape(str(proof_version(effort_model)))}</code></li>' if is_public_proof_effort(effort_model) else ''}
            </ul>
            <p class="footer-note">This page is rendered from live hosted control-plane state.</p>
          </div>
          <div>
            <h2>Join this effort</h2>
            <p>Pick up the current line of work, then leave behind a workspace, a claim or reproduction, and an inspectable brief for the next participant.</p>
            <p class="command">{escape(join_command)}</p>
            <ul>
              <li>Brief: <code>{escape(join_brief)}</code></li>
              <li>Optional attribution: add <code>--actor-id &lt;handle&gt;</code></li>
            </ul>
          </div>
        </section>

        <section class="panel grid two">
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

        <section class="panel">
          <h2>Recent workspace activity</h2>
          <ul class="link-list">
            {recent_workspaces or "<li>No workspaces attached yet.</li>"}
          </ul>
        </section>
        """,
    )


def _render_workspace_item(workspace: dict[str, object]) -> str:
    actor_id = workspace.get("actor_id") or "unknown"
    participant_role = workspace.get("participant_role") or "contributor"
    return (
        "<li>"
        f"<code>{escape(str(workspace['name']))}</code> actor=<code>{escape(str(actor_id))}</code>, "
        f"role=<code>{escape(str(participant_role))}</code>, "
        f"runs=<code>{len(workspace.get('run_ids', []))}</code>, "
        f"claims=<code>{len(workspace.get('claim_ids', []))}</code>, "
        f"reproductions=<code>{escape(str(workspace.get('reproduction_count', 0)))}</code>, "
        f"adoptions=<code>{escape(str(workspace.get('adoption_count', 0)))}</code>, "
        f"updated=<code>{escape(str(workspace.get('updated_at', 'n/a')))}</code>"
        "</li>"
    )


def _render_frontier_item(member: dict[str, object]) -> str:
    return (
        "<li>"
        f"<code>{escape(str(member['snapshot_id']))}</code> from "
        f"<code>{escape(str(member['workspace_id']))}</code>: "
        f"<code>{escape(str(member['metric_name']))}</code> = "
        f"<code>{escape(str(member['metric_value']))}</code> "
        f"({escape(str(member['direction']))}, claims={escape(str(member.get('claim_count', 0)))})"
        "</li>"
    )


def _render_claim_item(claim: dict[str, object]) -> str:
    return (
        "<li>"
        f"<code>{escape(str(claim['claim_id']))}</code> "
        f"[{escape(str(claim['status']))}] "
        f"{escape(str(claim['statement']))} "
        f"(reproductions={escape(str(claim.get('support_count', 0)))}, "
        f"contradictions={escape(str(claim.get('contradiction_count', 0)))})"
        "</li>"
    )


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
