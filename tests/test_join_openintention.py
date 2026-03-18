from __future__ import annotations

from pathlib import Path

from scripts.join_openintention import build_join_report, run_hosted_join


def test_build_join_report_includes_live_inspection_targets() -> None:
    report = build_join_report(
        result=type(
            "HostedJoinResultLike",
            (),
            {
                "actor_id": "aliargun",
                "profile": "eval-sprint",
                "base_url": "https://api.example.com",
                "site_url": "https://openintention.io",
                "effort_id": "effort-1",
                "effort_name": "Eval Sprint",
                "workspace_id": "workspace-1",
                "claim_id": "claim-1",
                "reproduction_run_id": "run-1",
                "participant_role": "contributor",
                "provenance_snippet": ["- none found"],
                "output": "workspace_id=workspace-1\nclaim_id=claim-1\n",
            },
        )(),
    )

    assert "# Joined OpenIntention" in report
    assert (
        "https://openintention.io/efforts/effort-1?workspace=workspace-1&joined=1&actor=aliargun&claim=claim-1&reproduction=run-1#workspace-workspace-1"
        in report
    )
    assert "https://api.example.com/api/v1/publications/workspaces/workspace-1/discussion" in report
    assert "stronger external-harness compounding path exists" in report
    assert "Hand the live goal page or this report to the next human or agent." in report
    assert "The live goal URL is intended to land back on your own highlighted contribution." in report


def test_run_hosted_join_bootstraps_and_runs_hosted_path(monkeypatch, tmp_path: Path) -> None:
    fake_repo_root = tmp_path / "repo"
    fake_repo_root.mkdir()
    commands: list[list[str]] = []

    def fake_run_command(command: list[str], *, cwd: Path) -> str:
        commands.append(command)
        assert cwd == fake_repo_root
        if command[0].endswith("/bin/python") and command[1:5] == ["-m", "clients.tiny_loop.run", "--base-url", "https://api.example.com"]:
            return "\n".join(
                [
                    "actor_id=aliargun",
                    "participant_role=contributor",
                    "effort_name=Eval Sprint",
                    "effort_id=effort-1",
                    "workspace_id=workspace-1",
                    "claim_id=claim-1",
                    "reproduction_run_id=run-1",
                ]
            )
        return ""

    monkeypatch.setattr("scripts.join_openintention.REPO_ROOT", fake_repo_root)
    monkeypatch.setattr("scripts.join_openintention._run_command", fake_run_command)
    monkeypatch.setattr("scripts.join_openintention._extract_provenance", lambda workspace_id, base_url: ["- provenance: not present"])

    report_path = run_hosted_join(
        actor_id="aliargun",
        profile="eval-sprint",
        effort_id=None,
        base_url="https://api.example.com",
        site_url="https://openintention.io",
        artifact_root="data/client-artifacts/hosted-join",
        output_dir="data/publications/launch/hosted-join",
        python_executable="/usr/bin/python3",
        venv_dir=".venv-openintention-join",
    )

    assert commands[0] == ["/usr/bin/python3", "-m", "venv", str(fake_repo_root / ".venv-openintention-join")]
    assert commands[1] == [
        str(fake_repo_root / ".venv-openintention-join" / "bin" / "python"),
        "-m",
        "pip",
        "install",
        "-e",
        ".",
    ]
    assert commands[2][:4] == [
        str(fake_repo_root / ".venv-openintention-join" / "bin" / "python"),
        "-m",
        "clients.tiny_loop.run",
        "--base-url",
    ]
    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert "workspace-1" in report
    assert "claim-1" in report


def test_run_hosted_join_can_skip_nested_bootstrap(monkeypatch, tmp_path: Path) -> None:
    fake_repo_root = tmp_path / "repo"
    fake_repo_root.mkdir()
    commands: list[list[str]] = []

    def fake_run_command(command: list[str], *, cwd: Path) -> str:
        commands.append(command)
        assert cwd == fake_repo_root
        return "\n".join(
            [
                "actor_id=aliargun",
                "participant_role=contributor",
                "effort_name=Eval Sprint",
                "effort_id=effort-1",
                "workspace_id=workspace-1",
                "claim_id=claim-1",
                "reproduction_run_id=run-1",
            ]
        )

    monkeypatch.setattr("scripts.join_openintention.REPO_ROOT", fake_repo_root)
    monkeypatch.setattr("scripts.join_openintention._run_command", fake_run_command)
    monkeypatch.setattr("scripts.join_openintention._extract_provenance", lambda workspace_id, base_url: ["- provenance: not present"])

    report_path = run_hosted_join(
        actor_id="aliargun",
        profile="eval-sprint",
        effort_id=None,
        base_url="https://api.example.com",
        site_url="https://openintention.io",
        artifact_root="data/client-artifacts/hosted-join",
        output_dir="data/publications/launch/hosted-join",
        python_executable="/opt/openintention/bin/python",
        bootstrap_environment=False,
    )

    assert commands == [
        [
            "/opt/openintention/bin/python",
            "-m",
            "clients.tiny_loop.run",
            "--base-url",
            "https://api.example.com",
            "--actor-id",
            "aliargun",
            "--artifact-root",
            str(fake_repo_root / "data/client-artifacts/hosted-join"),
            "--profile",
            "eval-sprint",
        ]
    ]
    assert report_path.exists()


def test_run_hosted_join_can_target_explicit_effort_id(monkeypatch, tmp_path: Path) -> None:
    fake_repo_root = tmp_path / "repo"
    fake_repo_root.mkdir()
    commands: list[list[str]] = []

    def fake_run_command(command: list[str], *, cwd: Path) -> str:
        commands.append(command)
        assert cwd == fake_repo_root
        return "\n".join(
            [
                "actor_id=aliargun",
                "participant_role=contributor",
                "effort_name=Published Goal",
                "effort_id=effort-123",
                "workspace_id=workspace-1",
                "claim_id=claim-1",
                "reproduction_run_id=run-1",
            ]
        )

    monkeypatch.setattr("scripts.join_openintention.REPO_ROOT", fake_repo_root)
    monkeypatch.setattr("scripts.join_openintention._run_command", fake_run_command)
    monkeypatch.setattr("scripts.join_openintention._extract_provenance", lambda workspace_id, base_url: ["- provenance: not present"])

    run_hosted_join(
        actor_id="aliargun",
        profile="eval-sprint",
        effort_id="effort-123",
        base_url="https://api.example.com",
        site_url="https://openintention.io",
        artifact_root="data/client-artifacts/hosted-join",
        output_dir="data/publications/launch/hosted-join",
        python_executable="/opt/openintention/bin/python",
        bootstrap_environment=False,
    )

    assert commands == [
        [
            "/opt/openintention/bin/python",
            "-m",
            "clients.tiny_loop.run",
            "--base-url",
            "https://api.example.com",
            "--actor-id",
            "aliargun",
            "--artifact-root",
            str(fake_repo_root / "data/client-artifacts/hosted-join"),
            "--effort-id",
            "effort-123",
        ]
    ]
