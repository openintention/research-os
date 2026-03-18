from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from scripts.run_first_user_smoke import SmokeResult, _resolve_python_executable, _open_request, build_smoke_report
from research_os.http import build_request


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_build_smoke_report_includes_efforts_and_exported_briefs():
    report = build_smoke_report(
        SmokeResult(
            base_url="http://127.0.0.1:9999",
            efforts=[
                {
                    "name": "Eval Sprint: improve validation loss under fixed budget",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "budget_seconds": 300,
                },
                {
                    "name": "Inference Sprint: improve flash-path throughput on H100",
                    "objective": "tokens_per_second",
                    "platform": "H100",
                    "budget_seconds": 300,
                },
            ],
            eval_client_output="effort_name=Eval Sprint",
            inference_client_output="effort_name=Inference Sprint",
            eval_workspace_provenance_excerpt=["- Eval provenance snippet"],
            inference_workspace_provenance_excerpt=["- Inference provenance snippet"],
            exported_brief_paths=[
                "data/publications/efforts/eval-sprint-improve-validation-loss-under-fixed-budget.md",
                "data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md",
            ],
        )
    )

    assert "First User Smoke Report" in report
    assert "Eval Sprint: improve validation loss under fixed budget" in report
    assert "Inference Sprint: improve flash-path throughput on H100" in report
    assert "Participation Outcome" in report
    assert "Joined (Eval)" in report
    assert "Participated (Eval)" in report
    assert "Verifier-Ready Provenance" in report
    assert "- Eval provenance snippet" in report
    assert "- Inference provenance snippet" in report
    assert "effort_name=Eval Sprint" in report
    assert "data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md" in report


def test_run_first_user_smoke_script_bootstraps_from_plain_checkout() -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, "-S", "scripts/run_first_user_smoke.py", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Run the first-user launch smoke flow." in result.stdout


def test_resolve_python_executable_prefers_repo_venv_when_not_explicit(monkeypatch, tmp_path: Path) -> None:
    fake_repo_root = tmp_path / "repo"
    fake_python = fake_repo_root / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("", encoding="utf-8")

    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setattr("scripts.run_first_user_smoke.REPO_ROOT", fake_repo_root)

    assert _resolve_python_executable(None) == str(fake_python)


def test_open_request_bypasses_proxy_for_loopback(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeOpener:
        def open(self, request, *, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return "opened"

    monkeypatch.setattr("scripts.run_first_user_smoke.build_opener", lambda handler: FakeOpener())

    result = _open_request(build_request("http://127.0.0.1:9999/healthz"), timeout=1.5)

    assert result == "opened"
    assert captured == {
        "url": "http://127.0.0.1:9999/healthz",
        "timeout": 1.5,
    }
