from __future__ import annotations

from apps.site import site_templates
from apps.site.server import _build_effort_proof_surface_context
from apps.site.server import _effort_detail_html
from apps.site.server import _effort_index_html
from apps.site.server import _publish_goal_html
from research_os.domain.models import EffortView


def test_site_templates_index_matches_existing_server_renderer():
    efforts = [
        {
            "effort_id": "effort-1",
            "name": "Eval Sprint: visible progress test",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "workspace_ids": ["workspace-1"],
            "tags": {"effort_type": "eval", "seeded": "true"},
            "successor_effort_id": None,
            "updated_at": "2026-03-11T15:00:00Z",
        },
        {
            "effort_id": "effort-2",
            "name": "Inference Sprint: inference throughput test",
            "objective": "latency",
            "platform": "H100",
            "budget_seconds": 600,
            "workspace_ids": ["workspace-2"],
            "tags": {"effort_type": "inference"},
            "successor_effort_id": None,
            "updated_at": "2026-03-11T16:00:00Z",
        },
    ]

    direct = _effort_index_html(public_api_base_url="https://api.example.com", efforts=efforts)
    rendered = site_templates.render_effort_index_page(
        site_templates.build_effort_index_context(
            public_api_base_url="https://api.example.com",
            efforts=efforts,
        )
    )
    assert rendered == direct


def test_site_templates_detail_matches_existing_server_renderer():
    effort_payload = {
        "effort_id": "effort-1",
        "name": "Eval Sprint: visible progress test",
        "objective": "val_bpb",
        "platform": "A100",
        "budget_seconds": 300,
        "workspace_ids": [],
        "tags": {"effort_type": "eval"},
        "successor_effort_id": None,
        "updated_at": "2026-03-11T15:00:00Z",
    }
    effort = EffortView.model_validate(effort_payload)
    proof_surface = _build_effort_proof_surface_context(
        api_base_url="https://api.example.com",
        effort=effort,
        all_efforts=[effort_payload],
        current_workspaces=[],
        current_workspace_events={},
        all_claims=[],
    )
    frontier: dict[str, object] = {"members": []}
    lease_observations = []

    direct = _effort_detail_html(
        public_api_base_url="https://api.example.com",
        effort=effort,
        proof_surface=proof_surface,
        frontier=frontier,
        lease_observations=lease_observations,
        joined=False,
        highlighted_workspace_id=None,
        highlighted_actor_id=None,
        highlighted_claim_id=None,
        highlighted_reproduction_run_id=None,
    )
    rendered = site_templates.render_effort_detail_page(
        site_templates.build_effort_detail_context(
            public_api_base_url="https://api.example.com",
            effort=effort,
            proof_surface=proof_surface,
            frontier=frontier,
            lease_observations=lease_observations,
            joined=False,
            highlighted_workspace_id=None,
            highlighted_actor_id=None,
            highlighted_claim_id=None,
            highlighted_reproduction_run_id=None,
        )
    )
    assert rendered == direct


def test_site_templates_publish_matches_existing_server_renderer():
    direct = _publish_goal_html()
    rendered = site_templates.render_publish_goal_page(site_templates.build_publish_goal_context())
    assert rendered == direct
