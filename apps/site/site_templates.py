from __future__ import annotations

from typing import Any

from apps.site.context_contracts import (
    EffortDetailContext,
    EffortIndexContext,
    PublishGoalContext,
)


def build_effort_index_context(
    *,
    public_api_base_url: str,
    efforts: list[dict[str, object]],
    site_css_url: str = "/styles.css",
    site_js_url: str | None = None,
) -> EffortIndexContext:
    return EffortIndexContext(
        public_api_base_url=public_api_base_url,
        efforts=efforts,
        site_css_url=site_css_url,
        site_js_url=site_js_url,
    )


def render_effort_index_page(context: EffortIndexContext) -> str:
    from apps.site import server

    return server._effort_index_html(
        public_api_base_url=context.public_api_base_url,
        efforts=context.efforts,
        site_css_url=context.site_css_url,
        site_js_url=context.site_js_url,
    )


def build_publish_goal_context(
    *,
    site_css_url: str = "/styles.css",
    site_js_url: str | None = None,
) -> PublishGoalContext:
    return PublishGoalContext(
        site_css_url=site_css_url,
        site_js_url=site_js_url,
    )


def render_publish_goal_page(context: PublishGoalContext) -> str:
    from apps.site import server

    return server._publish_goal_html(
        site_css_url=context.site_css_url,
        site_js_url=context.site_js_url,
    )


def build_effort_detail_context(
    *,
    public_api_base_url: str,
    effort: Any,
    proof_surface: Any,
    frontier: dict[str, object],
    lease_observations: list[Any],
    highlighted_workspace_id: str | None = None,
    highlighted_actor_id: str | None = None,
    highlighted_claim_id: str | None = None,
    highlighted_reproduction_run_id: str | None = None,
    joined: bool = False,
    site_css_url: str = "/styles.css",
    site_js_url: str | None = None,
) -> EffortDetailContext:
    return EffortDetailContext(
        public_api_base_url=public_api_base_url,
        effort=effort,
        proof_surface=proof_surface,
        frontier=frontier,
        lease_observations=lease_observations,
        highlighted_workspace_id=highlighted_workspace_id,
        highlighted_actor_id=highlighted_actor_id,
        highlighted_claim_id=highlighted_claim_id,
        highlighted_reproduction_run_id=highlighted_reproduction_run_id,
        joined=joined,
        site_css_url=site_css_url,
        site_js_url=site_js_url,
    )


def render_effort_detail_page(context: EffortDetailContext) -> str:
    from apps.site import server

    return server._effort_detail_html(
        public_api_base_url=context.public_api_base_url,
        effort=context.effort,
        proof_surface=context.proof_surface,
        frontier=context.frontier,
        lease_observations=context.lease_observations,
        highlighted_workspace_id=context.highlighted_workspace_id,
        highlighted_actor_id=context.highlighted_actor_id,
        highlighted_claim_id=context.highlighted_claim_id,
        highlighted_reproduction_run_id=context.highlighted_reproduction_run_id,
        joined=context.joined,
        site_css_url=context.site_css_url,
        site_js_url=context.site_js_url,
    )
