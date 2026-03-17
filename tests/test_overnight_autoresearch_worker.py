from __future__ import annotations

import base64
from pathlib import Path
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.run_overnight_autoresearch_worker import (
    OvernightWorkerIteration,
    OvernightWorkerResult,
    RunnerCommandResult,
    _resolve_worker_network_config,
    _run_runner_command,
    build_overnight_worker_report,
    execute_overnight_autoresearch_worker,
)
from scripts.run_mlx_history_compounding_smoke import ImportedContribution


def test_build_overnight_worker_report_mentions_handoff_and_honesty_line() -> None:
    report = build_overnight_worker_report(
        OvernightWorkerResult(
            actor_id="aliargun",
            base_url="https://api.openintention.io",
            site_url="https://openintention.io",
            repo_path="/tmp/mlx-history",
            repo_url="https://github.com/example/mlx-history",
            runner_command="python3 agent.py",
            effort_id="effort-mlx",
            effort_name="MLX History Sprint: improve val_bpb on Apple Silicon",
            window_seconds=28800,
            interval_seconds=900,
            max_loops=2,
            command_timeout_seconds=300,
            budget_cap_seconds=2400,
            loops_completed=2,
            imported_iterations=2,
            total_runner_seconds=600.0,
            stop_reason="max_loops_reached",
            iterations=[
                OvernightWorkerIteration(
                    index=1,
                    runner_status="success",
                    duration_seconds=300.0,
                    exit_code=0,
                    imported_candidate_commit="4161af3",
                    imported_baseline_commit="383abb4",
                    workspace_id="workspace-1",
                    claim_id="claim-1",
                    discussion_url="https://api.openintention.io/api/v1/publications/workspaces/workspace-1/discussion",
                    adoption_event_id=None,
                    note="Imported a kept result.",
                    log_path="/tmp/loop-001.log",
                )
            ],
            effort_workspace_count=2,
            effort_claim_count=2,
            frontier_member_count=1,
        )
    )

    assert "Overnight Autoresearch Worker" in report
    assert "Latest discussion" in report
    assert "runner `success`" in report
    assert "real external command" in report
    assert "not a mesh worker network" in report


def test_execute_overnight_worker_imports_new_kept_results_and_records_adoption(monkeypatch, tmp_path: Path) -> None:
    effort = {
        "effort_id": "effort-mlx",
        "name": "MLX History Sprint: improve val_bpb on Apple Silicon",
    }
    results_path = tmp_path / "results.tsv"
    run_count = {"value": 0}
    adoption_calls: list[tuple[str, str]] = []

    class FakeApi:
        def __init__(self) -> None:
            self.workspaces: list[dict[str, object]] = []

        def list_workspaces(self, effort_id: str | None = None) -> list[dict[str, object]]:
            return list(self.workspaces)

    fake_api = FakeApi()

    def fake_run_command(command: str, cwd: Path, timeout_seconds: int, log_path: Path) -> RunnerCommandResult:
        run_count["value"] += 1
        assert cwd == tmp_path
        if run_count["value"] == 1:
            results_path.write_text(
                "\n".join(
                    [
                        "commit\tval_bpb\tmemory_gb\tstatus\tdescription",
                        "383abb4\t2.667000\t26.9\tkeep\tbaseline",
                        "4161af3\t2.533728\t26.9\tkeep\tincrease matrix LR to 0.04",
                    ]
                ),
                encoding="utf-8",
            )
        else:
            results_path.write_text(
                "\n".join(
                    [
                        "commit\tval_bpb\tmemory_gb\tstatus\tdescription",
                        "383abb4\t2.667000\t26.9\tkeep\tbaseline",
                        "4161af3\t2.533728\t26.9\tkeep\tincrease matrix LR to 0.04",
                        "5efc7aa\t1.807902\t26.9\tkeep\treduce depth from 8 to 4",
                    ]
                ),
                encoding="utf-8",
            )
        log_path.write_text(f"loop {run_count['value']}", encoding="utf-8")
        return RunnerCommandResult(
            status="success",
            duration_seconds=4.0,
            exit_code=0,
            output=f"loop {run_count['value']}",
            log_path=str(log_path),
        )

    def fake_import_contribution(
        api,
        *,
        effort_id: str,
        actor_id: str,
        workspace_name: str,
        baseline,
        candidate,
        repo_url: str,
        artifact_root,
        workspace_tags=None,
        event_tags=None,
    ) -> ImportedContribution:
        workspace_id = f"workspace-{candidate.commit}"
        api.workspaces.append(
            {
                "workspace_id": workspace_id,
                "name": f"{workspace_name}-{candidate.commit}",
                "actor_id": actor_id,
                "claim_ids": [f"claim-{candidate.commit}"],
                "run_ids": [f"run-{candidate.commit}"],
                "tags": {
                    "external_harness": "mlx-history",
                    "candidate_commit": candidate.commit,
                    "baseline_commit": baseline.commit,
                    **(workspace_tags or {}),
                },
            }
        )
        return ImportedContribution(
            actor_id=actor_id,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            baseline_commit=baseline.commit,
            candidate_commit=candidate.commit,
            claim_id=f"claim-{candidate.commit}",
            run_id=f"run-{candidate.commit}",
            metric_value=candidate.val_bpb,
            delta=candidate.val_bpb - baseline.val_bpb,
        )

    def fake_record_adoption(api, *, from_contribution, to_contribution) -> str:
        adoption_calls.append((from_contribution.candidate_commit, to_contribution.candidate_commit))
        return f"adopt-{from_contribution.candidate_commit}-to-{to_contribution.candidate_commit}"

    def fake_get_json(url: str):
        if "frontiers" in url:
            return {"members": [{"snapshot_id": "snap-5efc7aa"}]}
        return [
            {"workspace_id": workspace["workspace_id"], "claim_id": workspace["claim_ids"][0]}
            for workspace in fake_api.workspaces
        ]

    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker.HttpResearchOSApi", lambda base_url: fake_api)
    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker._ensure_effort", lambda api, base_url: effort)
    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker._import_contribution", fake_import_contribution)
    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker._record_adoption", fake_record_adoption)
    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker._get_json", fake_get_json)

    result = execute_overnight_autoresearch_worker(
        base_url="https://api.openintention.io",
        site_url="https://openintention.io",
        repo_path=str(tmp_path),
        runner_command="python3 agent.py",
        actor_id="aliargun",
        window_seconds=60,
        interval_seconds=0,
        max_loops=2,
        command_timeout_seconds=300,
        budget_cap_seconds=20,
        artifact_root=str(tmp_path / "artifacts"),
        repo_url="https://github.com/example/mlx-history",
        results_path="results.tsv",
        log_root=tmp_path / "logs",
        run_command_fn=fake_run_command,
    )

    assert result.loops_completed == 2
    assert result.imported_iterations == 2
    assert result.stop_reason == "max_loops_reached"
    assert result.iterations[0].imported_candidate_commit == "4161af3"
    assert result.iterations[1].imported_candidate_commit == "5efc7aa"
    assert result.iterations[1].adoption_event_id == "adopt-4161af3-to-5efc7aa"
    assert adoption_calls == [("4161af3", "5efc7aa")]


def test_execute_overnight_worker_stops_at_budget_cap(monkeypatch, tmp_path: Path) -> None:
    results_path = tmp_path / "results.tsv"
    results_path.write_text(
        "\n".join(
            [
                "commit\tval_bpb\tmemory_gb\tstatus\tdescription",
                "383abb4\t2.667000\t26.9\tkeep\tbaseline",
                "4161af3\t2.533728\t26.9\tkeep\tincrease matrix LR to 0.04",
            ]
        ),
        encoding="utf-8",
    )

    class FakeApi:
        def list_workspaces(self, effort_id: str | None = None) -> list[dict[str, object]]:
            return []

    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker.HttpResearchOSApi", lambda base_url: FakeApi())
    monkeypatch.setattr(
        "scripts.run_overnight_autoresearch_worker._ensure_effort",
        lambda api, base_url: {"effort_id": "effort-mlx", "name": "MLX History Sprint: improve val_bpb on Apple Silicon"},
    )
    monkeypatch.setattr(
        "scripts.run_overnight_autoresearch_worker._import_contribution",
        lambda *args, **kwargs: ImportedContribution(
            actor_id="aliargun",
            workspace_id="workspace-1",
            workspace_name="mlx-history-worker",
            baseline_commit="383abb4",
            candidate_commit="4161af3",
            claim_id="claim-1",
            run_id="run-1",
            metric_value=2.533728,
            delta=-0.133272,
        ),
    )
    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker._record_adoption", lambda *args, **kwargs: "adopt-1")
    monkeypatch.setattr(
        "scripts.run_overnight_autoresearch_worker._get_json",
        lambda url: {"members": [{"snapshot_id": "snap-1"}]} if "frontiers" in url else [{"workspace_id": "workspace-1", "claim_id": "claim-1"}],
    )

    result = execute_overnight_autoresearch_worker(
        base_url="https://api.openintention.io",
        site_url="https://openintention.io",
        repo_path=str(tmp_path),
        runner_command="python3 agent.py",
        actor_id="aliargun",
        window_seconds=60,
        interval_seconds=0,
        max_loops=None,
        command_timeout_seconds=300,
        budget_cap_seconds=5,
        artifact_root=str(tmp_path / "artifacts"),
        repo_url="https://github.com/example/mlx-history",
        results_path="results.tsv",
        log_root=tmp_path / "logs",
        run_command_fn=lambda command, cwd, timeout_seconds, log_path: RunnerCommandResult(
            status="success",
            duration_seconds=6.0,
            exit_code=0,
            output="done",
            log_path=str(log_path),
        ),
    )

    assert result.loops_completed == 1
    assert result.stop_reason == "budget_cap_reached"


def test_execute_overnight_worker_stops_when_window_elapses(monkeypatch, tmp_path: Path) -> None:
    results_path = tmp_path / "results.tsv"
    results_path.write_text(
        "\n".join(
            [
                "commit\tval_bpb\tmemory_gb\tstatus\tdescription",
                "383abb4\t2.667000\t26.9\tkeep\tbaseline",
                "4161af3\t2.533728\t26.9\tkeep\tincrease matrix LR to 0.04",
            ]
        ),
        encoding="utf-8",
    )
    monotonic_values = iter([0.0, 0.0, 2.0, 2.0])

    class FakeApi:
        def list_workspaces(self, effort_id: str | None = None) -> list[dict[str, object]]:
            return []

    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker.HttpResearchOSApi", lambda base_url: FakeApi())
    monkeypatch.setattr(
        "scripts.run_overnight_autoresearch_worker._ensure_effort",
        lambda api, base_url: {"effort_id": "effort-mlx", "name": "MLX History Sprint: improve val_bpb on Apple Silicon"},
    )
    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker._import_contribution", lambda *args, **kwargs: ImportedContribution(
        actor_id="aliargun",
        workspace_id="workspace-1",
        workspace_name="mlx-history-worker",
        baseline_commit="383abb4",
        candidate_commit="4161af3",
        claim_id="claim-1",
        run_id="run-1",
        metric_value=2.533728,
        delta=-0.133272,
    ))
    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker._record_adoption", lambda *args, **kwargs: "adopt-1")
    monkeypatch.setattr(
        "scripts.run_overnight_autoresearch_worker._get_json",
        lambda url: {"members": [{"snapshot_id": "snap-1"}]} if "frontiers" in url else [{"workspace_id": "workspace-1", "claim_id": "claim-1"}],
    )

    result = execute_overnight_autoresearch_worker(
        base_url="https://api.openintention.io",
        site_url="https://openintention.io",
        repo_path=str(tmp_path),
        runner_command="python3 agent.py",
        actor_id="aliargun",
        window_seconds=1,
        interval_seconds=0,
        max_loops=None,
        command_timeout_seconds=300,
        budget_cap_seconds=30,
        artifact_root=str(tmp_path / "artifacts"),
        repo_url="https://github.com/example/mlx-history",
        results_path="results.tsv",
        log_root=tmp_path / "logs",
        monotonic_fn=lambda: next(monotonic_values),
        run_command_fn=lambda command, cwd, timeout_seconds, log_path: RunnerCommandResult(
            status="success",
            duration_seconds=0.5,
            exit_code=0,
            output="done",
            log_path=str(log_path),
        ),
    )

    assert result.loops_completed == 1
    assert result.stop_reason == "window_elapsed"


def test_run_runner_command_calls_activity_tick_while_command_runs(tmp_path: Path) -> None:
    tick_markers: list[str] = []

    result = _run_runner_command(
        f"{sys.executable} -c \"import time; time.sleep(0.25); print('done')\"",
        tmp_path,
        5,
        tmp_path / "runner.log",
        on_activity_tick=lambda: tick_markers.append("tick"),
        activity_tick_seconds=0.05,
    )

    assert result.status == "success"
    assert result.exit_code == 0
    assert "done" in result.output
    assert tick_markers


def test_resolve_worker_network_config_uses_bounded_default_lease_ttl(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    private_key_path = tmp_path / "worker-node.key"
    private_key_path.write_text(
        base64.b64encode(private_key.private_bytes_raw()).decode("ascii"),
        encoding="utf-8",
    )

    config = _resolve_worker_network_config(
        node_id="node_testworkercoord0001",
        node_key_id="key-worker-1",
        node_private_key_path=str(private_key_path),
        window_seconds=3600,
        heartbeat_ttl_seconds=None,
        heartbeat_interval_seconds=None,
        lease_ttl_seconds=None,
        release_lease_on_exit=True,
    )

    assert config is not None
    assert config.heartbeat_ttl_seconds == 30
    assert config.heartbeat_interval_seconds == 15
    assert config.lease_ttl_seconds == 180
    assert config.lease_renewal_interval_seconds == 90


def test_execute_overnight_worker_emits_signed_heartbeats_renews_lease_and_releases(
    monkeypatch,
    tmp_path: Path,
) -> None:
    effort = {
        "effort_id": "effort-mlx",
        "name": "MLX History Sprint: improve val_bpb on Apple Silicon",
        "objective": "val_bpb",
        "platform": "A100",
        "budget_seconds": 300,
    }
    results_path = tmp_path / "results.tsv"
    private_key = Ed25519PrivateKey.generate()
    private_key_path = tmp_path / "worker-node.key"
    private_key_path.write_text(
        base64.b64encode(private_key.private_bytes_raw()).decode("ascii"),
        encoding="utf-8",
    )

    acquire_calls: list[dict[str, object]] = []
    renew_calls: list[dict[str, object]] = []
    heartbeat_calls: list[dict[str, object]] = []
    release_calls: list[dict[str, object]] = []
    fail_calls: list[str] = []
    monotonic_state = {"now": 0.0}

    class FakeApi:
        def __init__(self) -> None:
            self.workspaces: list[dict[str, object]] = []

        def list_workspaces(self, effort_id: str | None = None) -> list[dict[str, object]]:
            return list(self.workspaces)

    fake_api = FakeApi()

    def fake_run_command(
        command: str,
        cwd: Path,
        timeout_seconds: int,
        log_path: Path,
        *,
        on_activity_tick=None,
        activity_tick_seconds=None,
    ) -> RunnerCommandResult:
        assert cwd == tmp_path
        assert timeout_seconds == 20
        assert activity_tick_seconds == 2
        results_path.write_text(
            "\n".join(
                [
                    "commit\tval_bpb\tmemory_gb\tstatus\tdescription",
                    "383abb4\t2.667000\t26.9\tkeep\tbaseline",
                    "4161af3\t2.533728\t26.9\tkeep\tincrease matrix LR to 0.04",
                ]
            ),
            encoding="utf-8",
        )
        if on_activity_tick is not None:
            monotonic_state["now"] = 6.0
            on_activity_tick()
            monotonic_state["now"] = 8.0
            on_activity_tick()
        log_path.write_text("worker loop", encoding="utf-8")
        return RunnerCommandResult(
            status="success",
            duration_seconds=4.0,
            exit_code=0,
            output="worker loop",
            log_path=str(log_path),
        )

    def fake_import_contribution(
        api,
        *,
        effort_id: str,
        actor_id: str,
        workspace_name: str,
        baseline,
        candidate,
        repo_url: str,
        artifact_root,
        workspace_tags=None,
        event_tags=None,
    ) -> ImportedContribution:
        workspace_id = f"workspace-{candidate.commit}"
        api.workspaces.append(
            {
                "workspace_id": workspace_id,
                "name": f"{workspace_name}-{candidate.commit}",
                "actor_id": actor_id,
                "claim_ids": [f"claim-{candidate.commit}"],
                "run_ids": [f"run-{candidate.commit}"],
                "tags": {
                    "external_harness": "mlx-history",
                    "candidate_commit": candidate.commit,
                    "baseline_commit": baseline.commit,
                    **(workspace_tags or {}),
                },
            }
        )
        return ImportedContribution(
            actor_id=actor_id,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            baseline_commit=baseline.commit,
            candidate_commit=candidate.commit,
            claim_id=f"claim-{candidate.commit}",
            run_id=f"run-{candidate.commit}",
            metric_value=candidate.val_bpb,
            delta=candidate.val_bpb - baseline.val_bpb,
        )

    def fake_get_json(url: str):
        if "frontiers" in url:
            return {"members": [{"snapshot_id": "snap-4161af3"}]}
        return [{"workspace_id": "workspace-4161af3", "claim_id": "claim-4161af3"}]

    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker.HttpResearchOSApi", lambda base_url: fake_api)
    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker._ensure_effort", lambda api, base_url: effort)
    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker._import_contribution", fake_import_contribution)
    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker._record_adoption", lambda *args, **kwargs: "adopt-1")
    monkeypatch.setattr("scripts.run_overnight_autoresearch_worker._get_json", fake_get_json)
    monkeypatch.setattr(
        "scripts.run_overnight_autoresearch_worker._acquire_worker_lease",
        lambda **kwargs: acquire_calls.append(kwargs) or {
            "lease_id": "lease-1",
            "status": "acquired",
            "renewal_count": 0,
            "expires_at": "2026-03-17T00:00:10Z",
        },
    )
    monkeypatch.setattr(
        "scripts.run_overnight_autoresearch_worker._renew_worker_lease",
        lambda **kwargs: renew_calls.append(kwargs) or {
            "lease_id": kwargs["lease_id"],
            "status": "renewed",
            "renewal_count": 1,
            "renewed_at": "2026-03-17T00:00:06Z",
            "expires_at": "2026-03-17T00:00:16Z",
        },
    )
    monkeypatch.setattr(
        "scripts.run_overnight_autoresearch_worker._emit_worker_heartbeat",
        lambda **kwargs: heartbeat_calls.append(kwargs) or {"node_id": kwargs["signer"].node_id},
    )
    monkeypatch.setattr(
        "scripts.run_overnight_autoresearch_worker._release_worker_lease",
        lambda **kwargs: release_calls.append(kwargs) or {
            "lease_id": kwargs["lease_id"],
            "status": "released",
            "renewal_count": 1,
            "renewed_at": "2026-03-17T00:00:06Z",
            "expires_at": "2026-03-17T00:00:16Z",
        },
    )
    monkeypatch.setattr(
        "scripts.run_overnight_autoresearch_worker._fail_worker_lease",
        lambda **kwargs: fail_calls.append(kwargs["failure_reason"]) or {"lease_id": kwargs["lease_id"], "status": "failed"},
    )

    result = execute_overnight_autoresearch_worker(
        base_url="https://api.openintention.io",
        site_url="https://openintention.io",
        repo_path=str(tmp_path),
        runner_command="python3 agent.py",
        actor_id="aliargun",
        window_seconds=60,
        interval_seconds=0,
        max_loops=1,
        command_timeout_seconds=300,
        budget_cap_seconds=20,
        node_id="node_testworkercoord0001",
        node_key_id="key-worker-1",
        node_private_key_path=str(private_key_path),
        lease_ttl_seconds=12,
        heartbeat_ttl_seconds=12,
        heartbeat_interval_seconds=2,
        artifact_root=str(tmp_path / "artifacts"),
        repo_url="https://github.com/example/mlx-history",
        results_path="results.tsv",
        log_root=tmp_path / "logs",
        monotonic_fn=lambda: monotonic_state["now"],
        run_command_fn=fake_run_command,
    )

    assert result.loops_completed == 1
    assert result.imported_iterations == 1
    assert result.coordination is not None
    assert result.coordination.node_id == "node_testworkercoord0001"
    assert result.coordination.lease_id == "lease-1"
    assert result.coordination.lease_status == "released"
    assert result.coordination.renewal_count == 1
    assert result.coordination.latest_renewed_at == "2026-03-17T00:00:06Z"
    assert result.coordination.latest_expires_at == "2026-03-17T00:00:16Z"
    assert result.coordination.heartbeat_count >= 4
    assert acquire_calls[0]["lease_ttl_seconds"] == 12
    assert len(renew_calls) == 1
    assert renew_calls[0]["lease_id"] == "lease-1"
    assert renew_calls[0]["lease_ttl_seconds"] == 12
    assert len(heartbeat_calls) >= 4
    assert len(release_calls) == 1
    assert release_calls[0]["lease_id"] == "lease-1"
    assert release_calls[0]["signer"].node_id == "node_testworkercoord0001"
    assert release_calls[0]["request_id"].startswith("node_testworkercoord0001-")
    assert not fail_calls

    report = build_overnight_worker_report(result)
    assert "Lease renewals" in report
    assert "Lease expires at" in report
