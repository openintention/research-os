from __future__ import annotations

from clients.tiny_loop.experiment import ExperimentResult
from scripts.run_shared_participation_smoke import (
    SharedParticipationResult,
    build_shared_participation_report,
)


def test_build_shared_participation_report_includes_two_distinct_participants():
    report = build_shared_participation_report(
        SharedParticipationResult(
            base_url="https://api.openintention.io",
            effort_id="effort-eval",
            effort_name="Eval Sprint: improve validation loss under fixed budget",
            first=ExperimentResult(
                actor_id="participant-alpha",
                workspace_id="workspace-alpha",
                effort_id="effort-eval",
                effort_name="Eval Sprint: improve validation loss under fixed budget",
                baseline_snapshot_id="alpha-snap-linear",
                candidate_snapshot_id="alpha-snap-quadratic",
                planner_action="reproduce_claim",
                claim_id="alpha-claim",
                reproduction_run_id="alpha-run-repro",
                discussion_markdown="# alpha",
                pull_request_markdown="# alpha pr",
            ),
            second=ExperimentResult(
                actor_id="participant-beta",
                workspace_id="workspace-beta",
                effort_id="effort-eval",
                effort_name="Eval Sprint: improve validation loss under fixed budget",
                baseline_snapshot_id="beta-snap-linear",
                candidate_snapshot_id="beta-snap-quadratic",
                planner_action="reproduce_claim",
                claim_id="beta-claim",
                reproduction_run_id="beta-run-repro",
                discussion_markdown="# beta",
                pull_request_markdown="# beta pr",
            ),
            workspace_ids=["workspace-alpha", "workspace-beta"],
            claim_ids=["alpha-claim", "beta-claim"],
            frontier_member_count=2,
            effort_overview_excerpt="# Effort",
        )
    )

    assert "Shared Participation Smoke Report" in report
    assert "participant-alpha" in report
    assert "participant-beta" in report
    assert "workspace-alpha" in report
    assert "beta-claim" in report
    assert "Frontier members: 2" in report
