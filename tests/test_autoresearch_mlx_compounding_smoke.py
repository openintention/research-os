from __future__ import annotations

import pytest

from scripts.run_autoresearch_mlx_compounding_smoke import _build_imported_contribution_from_workspace
from scripts.run_autoresearch_mlx_compounding_smoke import _find_existing_workspace
from scripts.run_autoresearch_mlx_compounding_smoke import _record_adoption
from research_os.domain.models import EventKind
from scripts.run_autoresearch_mlx_compounding_smoke import (
    CompoundingAutoresearchResult,
    ImportedContribution,
    build_compounding_report,
)
from research_os.integrations.autoresearch_mlx import AutoresearchResult


def test_build_compounding_report_highlights_adoption_and_next_step() -> None:
    report = build_compounding_report(
        CompoundingAutoresearchResult(
            base_url="https://openintention-api-production.up.railway.app",
            effort_id="effort-mlx",
            effort_name="Autoresearch MLX Sprint: improve val_bpb on Apple Silicon",
            alpha=ImportedContribution(
                actor_id="mlx-alpha",
                workspace_id="ws-alpha",
                workspace_name="autoresearch-mlx-alpha",
                baseline_commit="383abb4",
                candidate_commit="4161af3",
                claim_id="claim-alpha",
                run_id="run-alpha",
                metric_value=2.533728,
                delta=-0.133272,
            ),
            beta=ImportedContribution(
                actor_id="mlx-beta",
                workspace_id="ws-beta",
                workspace_name="autoresearch-mlx-beta",
                baseline_commit="4161af3",
                candidate_commit="5efc7aa",
                claim_id="claim-beta",
                run_id="run-beta",
                metric_value=1.807902,
                delta=-0.725826,
            ),
            adoption_event_id="adopt-beta",
            workspace_ids=["ws-alpha", "ws-beta"],
            claim_ids=["claim-alpha", "claim-beta"],
            frontier_member_count=2,
            planner_action="reproduce_claim",
            planner_reason="The latest external-harness claim still needs independent reproduction.",
            planner_inputs={"claim_id": "claim-beta"},
            effort_overview_excerpt="# Effort",
        )
    )

    assert "Autoresearch MLX Compounding Smoke Report" in report
    assert "mlx-beta` adopted `claim-alpha`" in report
    assert "Action: `reproduce_claim`" in report
    assert "claim-beta" in report
    assert "The next participant can continue" in report


def test_find_existing_workspace_matches_by_name_and_actor() -> None:
    workspaces = [
        {"workspace_id": "ws-1", "name": "autoresearch-mlx-alpha-4161af3", "actor_id": "mlx-alpha"},
        {"workspace_id": "ws-2", "name": "autoresearch-mlx-alpha-4161af3", "actor_id": "mlx-other"},
    ]

    workspace = _find_existing_workspace(
        workspaces,
        name="autoresearch-mlx-alpha-4161af3",
        actor_id="mlx-alpha",
    )

    assert workspace == workspaces[0]


def test_build_imported_contribution_from_workspace_reuses_existing_scope() -> None:
    contribution = _build_imported_contribution_from_workspace(
        {"workspace_id": "2785c9d9-7b37-4c06-9c8b-1759d9013a2b"},
        actor_id="mlx-alpha",
        workspace_name="autoresearch-mlx-alpha",
        baseline=AutoresearchResult(
            commit="383abb4",
            val_bpb=2.667,
            memory_gb=26.9,
            status="keep",
            description="baseline",
        ),
        candidate=AutoresearchResult(
            commit="4161af3",
            val_bpb=2.533728,
            memory_gb=26.9,
            status="keep",
            description="increase matrix LR to 0.04",
        ),
    )

    assert contribution.workspace_id == "2785c9d9-7b37-4c06-9c8b-1759d9013a2b"
    assert contribution.claim_id == "2785c9d9-claim-4161af3"
    assert contribution.run_id == "2785c9d9-run-4161af3"
    assert contribution.delta == pytest.approx(-0.133272)


def test_record_adoption_is_idempotent(monkeypatch) -> None:
    class FakeApi:
        base_url = "https://example.invalid"

        def __init__(self) -> None:
            self.appended_payloads: list[dict[str, object]] = []

        def append_event(self, payload: dict[str, object]) -> dict[str, object]:
            self.appended_payloads.append(payload)
            return payload

    def fake_get_json(url: str) -> list[dict[str, object]]:
        assert f"kind={EventKind.ADOPTION_RECORDED.value}" in url
        return [
            {
                "event_id": "existing-adoption",
                "payload": {"subject_id": "claim-alpha"},
            }
        ]

    monkeypatch.setattr(
        "scripts.run_autoresearch_mlx_compounding_smoke._get_json",
        fake_get_json,
    )
    api = FakeApi()
    event_id = _record_adoption(
        api,
        from_contribution=ImportedContribution(
            actor_id="mlx-alpha",
            workspace_id="ws-alpha",
            workspace_name="autoresearch-mlx-alpha",
            baseline_commit="383abb4",
            candidate_commit="4161af3",
            claim_id="claim-alpha",
            run_id="run-alpha",
            metric_value=2.533728,
            delta=-0.133272,
        ),
        to_contribution=ImportedContribution(
            actor_id="mlx-beta",
            workspace_id="ws-beta",
            workspace_name="autoresearch-mlx-beta",
            baseline_commit="4161af3",
            candidate_commit="5efc7aa",
            claim_id="claim-beta",
            run_id="run-beta",
            metric_value=1.807902,
            delta=-0.725826,
        ),
    )

    assert event_id == "existing-adoption"
    assert api.appended_payloads == []
