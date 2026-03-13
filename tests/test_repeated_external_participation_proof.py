from __future__ import annotations

from scripts.run_repeated_external_participation_proof import (
    EffortVisibilitySummary,
    ParticipationRecord,
    RepeatedExternalParticipationResult,
    build_repeated_external_participation_report,
)


def test_build_repeated_external_participation_report_includes_visibility_and_breakpoints() -> None:
    report = build_repeated_external_participation_report(
        RepeatedExternalParticipationResult(
            base_url="https://api.openintention.io",
            site_url="https://openintention.io",
            batch_id="20260313180000",
            records=[
                ParticipationRecord(
                    actor_id="external-eval-alpha",
                    profile_name="eval-sprint",
                    participant_role="contributor",
                    effort_id="effort-eval",
                    effort_name="Eval Sprint: improve validation loss under fixed budget",
                    workspace_id="workspace-alpha",
                    claim_id="claim-alpha",
                    reproduction_run_id=None,
                    planner_action="reproduce_claim",
                    discussion_url="https://api.openintention.io/api/v1/publications/workspaces/workspace-alpha/discussion",
                    effort_page_url="https://openintention.io/efforts/effort-eval",
                ),
                ParticipationRecord(
                    actor_id="external-eval-verifier",
                    profile_name="eval-sprint",
                    participant_role="verifier",
                    effort_id="effort-eval",
                    effort_name="Eval Sprint: improve validation loss under fixed budget",
                    workspace_id="workspace-verifier",
                    claim_id="claim-alpha",
                    reproduction_run_id="run-repro-001",
                    planner_action="reproduce_claim",
                    discussion_url="https://api.openintention.io/api/v1/publications/workspaces/workspace-verifier/discussion",
                    effort_page_url="https://openintention.io/efforts/effort-eval",
                ),
            ],
            effort_summaries=[
                EffortVisibilitySummary(
                    effort_id="effort-eval",
                    effort_name="Eval Sprint: improve validation loss under fixed budget",
                    effort_page_url="https://openintention.io/efforts/effort-eval",
                    visible_actor_ids=["external-eval-alpha", "external-eval-verifier"],
                    visible_workspace_count=7,
                    claim_count=2,
                    frontier_member_count=3,
                )
            ],
            breakpoints=[
                "Onboarding: edge checkout must stay clean.",
                "Contribution: explicit agent user-agent required.",
            ],
        )
    )

    assert "Repeated External Participation Proof" in report
    assert "external-eval-alpha" in report
    assert "external-eval-verifier" in report
    assert "https://openintention.io/efforts/effort-eval" in report
    assert "visible actors on live page" in report
    assert "Onboarding: edge checkout must stay clean." in report
