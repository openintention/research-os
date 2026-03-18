from __future__ import annotations

from scripts.run_publish_goal_smoke import PublishGoalSmokeResult
from scripts.run_publish_goal_smoke import build_publish_goal_smoke_report


def test_build_publish_goal_smoke_report_includes_publish_and_join_outcome() -> None:
    report = build_publish_goal_smoke_report(
        PublishGoalSmokeResult(
            site_url="https://openintention.io",
            api_base_url="https://api.openintention.io",
            effort_id="effort-published",
            title="OpenIntention publish-goal smoke abc12345",
            author_id="goal-author-abc12345",
            goal_page_url="https://openintention.io/efforts/effort-published",
            join_report_path="data/publications/launch/publish-goal-smoke/hosted-join/hosted-join.md",
            workspace_id="workspace-1",
            claim_id="claim-1",
            join_mode="tiny-loop-proxy",
            goal_page_excerpt="Goal contract\nvalidation loss",
        )
    )

    assert "Publish Goal Smoke Report" in report
    assert "goal-author-abc12345" in report
    assert "workspace-1" in report
    assert "claim-1" in report
    assert "tiny-loop-proxy" in report
    assert "A second participant joined the published goal" in report
