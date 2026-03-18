from __future__ import annotations

from scripts.publish_goal import PublishedGoalResult
from scripts.publish_goal import build_publish_goal_report


def test_build_publish_goal_report_includes_join_command_and_honesty_line() -> None:
    report = build_publish_goal_report(
        PublishedGoalResult(
            effort_id="effort-published",
            bootstrap_event_id="event-1",
            title="Improve validation loss on cpu",
            objective="val_loss",
            metric_name="validation loss",
            direction="min",
            platform="cpu",
            budget_seconds=300,
            author_id="goal-author",
            constraints=["Keep runtime under five minutes."],
            evidence_requirement="Leave behind one run and one finding.",
            stop_condition="Stop after the first verified improvement.",
            summary="Create a visible public goal with a clear handoff for the next contributor.",
            base_url="https://api.openintention.io",
            site_url="https://openintention.io",
        )
    )

    assert "Published Goal" in report
    assert "goal-author" in report
    assert "https://openintention.io/efforts/effort-published?published=1&author=goal-author" in report
    assert "--effort-id effort-published --actor-id <handle>" in report
    assert "lightweight asserted actor handle in v1" in report
