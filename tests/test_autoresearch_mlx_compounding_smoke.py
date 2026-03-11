from __future__ import annotations

from scripts.run_autoresearch_mlx_compounding_smoke import (
    CompoundingAutoresearchResult,
    ImportedContribution,
    build_compounding_report,
)


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
