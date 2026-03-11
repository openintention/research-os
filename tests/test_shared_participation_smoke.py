from __future__ import annotations

from clients.tiny_loop.experiment import ExperimentResult
from research_os.domain.models import ParticipantRole
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
            contributor=ExperimentResult(
                actor_id="participant-contributor",
                participant_role=ParticipantRole.CONTRIBUTOR,
                workspace_id="workspace-contributor",
                effort_id="effort-eval",
                effort_name="Eval Sprint: improve validation loss under fixed budget",
                baseline_snapshot_id="contributor-snap-linear",
                candidate_snapshot_id="contributor-snap-quadratic",
                planner_action="reproduce_claim",
                claim_id="contributor-claim",
                reproduction_run_id=None,
                discussion_markdown="# contributor",
                pull_request_markdown="# contributor pr",
            ),
            verifier=ExperimentResult(
                actor_id="participant-verifier",
                participant_role=ParticipantRole.VERIFIER,
                workspace_id="workspace-verifier",
                effort_id="effort-eval",
                effort_name="Eval Sprint: improve validation loss under fixed budget",
                baseline_snapshot_id="verifier-snap-linear",
                candidate_snapshot_id="verifier-snap-quadratic",
                planner_action="reproduce_claim",
                claim_id="contributor-claim",
                reproduction_run_id="verifier-run-repro",
                discussion_markdown="# verifier",
                pull_request_markdown="# verifier pr",
            ),
            workspaces=[
                {
                    "workspace_id": "workspace-contributor",
                    "actor_id": "participant-contributor",
                    "participant_role": "contributor",
                    "run_ids": ["run-1", "run-2"],
                    "claim_ids": ["contributor-claim"],
                    "reproduction_count": 0,
                },
                {
                    "workspace_id": "workspace-verifier",
                    "actor_id": "participant-verifier",
                    "participant_role": "verifier",
                    "run_ids": ["run-3"],
                    "claim_ids": [],
                    "reproduction_count": 1,
                },
            ],
            claims=[
                {
                    "claim_id": "contributor-claim",
                    "status": "supported",
                    "support_count": 1,
                    "contradiction_count": 0,
                }
            ],
            frontier_member_count=2,
            effort_overview_excerpt="# Effort",
        )
    )

    assert "Shared Participation Smoke Report" in report
    assert "participant-contributor" in report
    assert "participant-verifier" in report
    assert "workspace-contributor" in report
    assert "role=`verifier`" in report
    assert "support=1" in report
    assert "Frontier members: 2" in report
