from __future__ import annotations

from pathlib import Path

from clients.tiny_loop.experiment import ExperimentResult
from research_os.domain.models import ParticipantRole
from scripts.run_nightly_contribution_window import (
    NightlyContributionWindowResult,
    build_nightly_contribution_window_report,
    execute_nightly_contribution_window,
)


def test_build_nightly_contribution_window_report_mentions_live_evidence() -> None:
    report = build_nightly_contribution_window_report(
        NightlyContributionWindowResult(
            actor_id="aliargun",
            profile="eval-sprint",
            effort_id="effort-eval",
            effort_name="Eval Sprint: improve validation loss under fixed budget",
            base_url="https://api.openintention.io",
            site_url="https://openintention.io",
            window_seconds=120,
            interval_seconds=5,
            max_loops=2,
            loops_completed=2,
            iterations=[
                type(
                    "NightlyContributionIterationLike",
                    (),
                    {
                        "index": 1,
                        "workspace_id": "workspace-1",
                        "claim_id": "claim-1",
                        "reproduction_run_id": "run-1",
                        "discussion_url": "https://api.openintention.io/api/v1/publications/workspaces/workspace-1/discussion",
                        "planner_action": "reproduce_claim",
                    },
                )(),
                type(
                    "NightlyContributionIterationLike",
                    (),
                    {
                        "index": 2,
                        "workspace_id": "workspace-2",
                        "claim_id": "claim-2",
                        "reproduction_run_id": "run-2",
                        "discussion_url": "https://api.openintention.io/api/v1/publications/workspaces/workspace-2/discussion",
                        "planner_action": "reproduce_claim",
                    },
                )(),
            ],
            actor_workspace_count=2,
            effort_workspace_count=8,
            effort_claim_count=6,
            frontier_member_count=4,
        )
    )

    assert "Nightly Contribution Window" in report
    assert "Completed loops: `2`" in report
    assert "workspace `workspace-1`" in report
    assert "Workspaces by `aliargun` in effort: `2`" in report
    assert "Latest discussion" in report
    assert "opt-in local contribution window" in report


def test_execute_nightly_contribution_window_runs_multiple_hosted_loops(monkeypatch, tmp_path: Path) -> None:
    class FakeApi:
        def __init__(self) -> None:
            self.workspaces: list[dict[str, object]] = []

        def list_efforts(self) -> list[dict[str, object]]:
            return [
                {
                    "effort_id": "effort-eval",
                    "name": "Eval Sprint: improve validation loss under fixed budget",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "budget_seconds": 300,
                }
            ]

        def list_workspaces(self, effort_id: str | None = None) -> list[dict[str, object]]:
            return list(self.workspaces)

    fake_api = FakeApi()
    call_count = {"value": 0}
    sleep_calls: list[float] = []

    def fake_run_tiny_loop_experiment(api, *, artifact_root, profile, actor_id, workspace_suffix):
        call_count["value"] += 1
        workspace_id = f"workspace-{call_count['value']}"
        claim_id = f"claim-{call_count['value']}"
        api.workspaces.append(
            {
                "workspace_id": workspace_id,
                "actor_id": actor_id,
                "participant_role": "contributor",
                "run_ids": [f"run-{call_count['value']}-1", f"run-{call_count['value']}-2"],
                "claim_ids": [claim_id],
                "reproduction_count": 1,
            }
        )
        return ExperimentResult(
            actor_id=actor_id,
            participant_role=ParticipantRole.CONTRIBUTOR,
            workspace_id=workspace_id,
            effort_id="effort-eval",
            effort_name="Eval Sprint: improve validation loss under fixed budget",
            baseline_snapshot_id=f"{workspace_id}-baseline",
            candidate_snapshot_id=f"{workspace_id}-candidate",
            planner_action="reproduce_claim",
            claim_id=claim_id,
            reproduction_run_id=f"repro-{call_count['value']}",
            discussion_markdown="# discussion",
            pull_request_markdown="# pr",
        )

    monotonic_values = iter([0.0, 1.0, 1.0, 2.0, 2.0])

    monkeypatch.setattr("scripts.run_nightly_contribution_window.HttpResearchOSApi", lambda base_url: fake_api)
    monkeypatch.setattr("scripts.run_nightly_contribution_window.run_tiny_loop_experiment", fake_run_tiny_loop_experiment)
    monkeypatch.setattr(
        "scripts.run_nightly_contribution_window._get_json",
        lambda url: {"members": ["frontier-a", "frontier-b"]} if "frontiers" in url else [{"workspace_id": "workspace-1"}, {"workspace_id": "workspace-2"}],
    )

    result = execute_nightly_contribution_window(
        base_url="https://api.openintention.io",
        site_url="https://openintention.io",
        profile="eval-sprint",
        actor_id="aliargun",
        window_seconds=30,
        interval_seconds=5,
        max_loops=2,
        artifact_root=str(tmp_path / "artifacts"),
        monotonic_fn=lambda: next(monotonic_values),
        sleep_fn=lambda seconds: sleep_calls.append(seconds),
    )

    assert result.loops_completed == 2
    assert result.actor_workspace_count == 2
    assert result.effort_workspace_count == 2
    assert result.effort_claim_count == 2
    assert result.frontier_member_count == 2
    assert result.iterations[0].workspace_id == "workspace-1"
    assert result.iterations[1].workspace_id == "workspace-2"
    assert sleep_calls == [5]
