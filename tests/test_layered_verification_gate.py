from __future__ import annotations

from pathlib import Path

from scripts.run_layered_verification_gate import build_layered_verification_report
from scripts.run_layered_verification_gate import GateResult
from scripts.run_layered_verification_gate import LayerResult
from scripts.run_layered_verification_gate import AutomatedCheckResult
from scripts.run_layered_verification_gate import run_layered_verification_gate


def test_build_layered_verification_report_lists_thresholds_and_tdd_loop() -> None:
    report = build_layered_verification_report(
        GateResult(
            gate="deploy",
            site_url="https://openintention.io",
            api_base_url="https://api.openintention.io",
            output_root="/tmp/layered",
            overall_status="passed",
            layers=(
                LayerResult(
                    layer_id="L0",
                    label="Fast deterministic core",
                    execution_mode="automated",
                    thresholds=("merge", "deploy", "launch-claim"),
                    automated_results=(
                        AutomatedCheckResult(
                            check_id="ruff",
                            label="Ruff check",
                            command="ruff check .",
                            status="passed",
                            return_code=0,
                            pass_criteria=("No lint violations.",),
                            evidence_paths=(),
                            output_excerpt="All checks passed!",
                        ),
                    ),
                    manual_results=(),
                ),
            ),
        )
    )

    assert "Layered Verification Gate" in report
    assert "`merge`: L0 only" in report
    assert "## TDD Loop" in report
    assert "Ruff check" in report


def test_run_layered_verification_gate_marks_launch_claim_manual_checks_pending(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(command: list[str], cwd: Path, check: bool, capture_output: bool, text: bool):
        _ = cwd, check, capture_output, text
        calls.append(tuple(command))

        class Completed:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Completed()

    monkeypatch.setattr("scripts.run_layered_verification_gate.subprocess.run", fake_run)

    try:
        run_layered_verification_gate(
            gate="launch-claim",
            site_url="https://openintention.io",
            api_base_url="https://api.openintention.io",
            output_root=str(tmp_path),
            manual_checks={},
            include_worker_layer=False,
        )
    except RuntimeError as exc:
        assert "manual-follow-up-required" in str(exc)
    else:
        raise AssertionError("launch-claim gate should require manual clean-room evidence")

    assert any(command[1:4] == ("-m", "ruff", "check") for command in calls)
    report = (tmp_path / "launch-claim" / "layered-verification-report.md").read_text(encoding="utf-8")
    assert "Claude clean-room run" in report
    assert "status=`pending-manual`" in report


def test_run_layered_verification_gate_can_pass_launch_claim_with_manual_notes(tmp_path: Path, monkeypatch) -> None:
    def fake_run(command: list[str], cwd: Path, check: bool, capture_output: bool, text: bool):
        _ = command, cwd, check, capture_output, text

        class Completed:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Completed()

    monkeypatch.setattr("scripts.run_layered_verification_gate.subprocess.run", fake_run)

    report_path = run_layered_verification_gate(
        gate="launch-claim",
        site_url="https://openintention.io",
        api_base_url="https://api.openintention.io",
        output_root=str(tmp_path),
        manual_checks={
            "claude-clean-room": "workspace=ws-1 claim=claim-1",
            "codex-clean-room": "workspace=ws-2 claim=claim-2",
        },
        include_worker_layer=True,
    )

    report = report_path.read_text(encoding="utf-8")
    assert "Overall status: `passed`" in report
    assert "Overnight worker smoke" in report
    assert "workspace=ws-1 claim=claim-1" in report
