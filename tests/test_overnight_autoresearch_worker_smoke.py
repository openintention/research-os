from __future__ import annotations

from scripts.run_overnight_autoresearch_worker_smoke import (
    OvernightWorkerSmokeResult,
    build_worker_smoke_report,
)


def test_build_worker_smoke_report_mentions_disposable_sandbox() -> None:
    report = build_worker_smoke_report(
        OvernightWorkerSmokeResult(
            base_url="http://127.0.0.1:8000",
            worker_report_path="data/publications/launch/overnight-autoresearch-worker/overnight-autoresearch-worker.md",
            repo_path="/tmp/mlx-history-fixture",
            effort_page_hint="https://openintention.io/efforts/effort-mlx",
            worker_report_excerpt="# Overnight Autoresearch Worker",
        )
    )

    assert "Disposable Sandbox" in report
    assert "overnight-autoresearch-worker.md" in report
    assert "Two kept results were appended" in report
