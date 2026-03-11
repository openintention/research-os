from __future__ import annotations

from scripts.run_proof_effort_rollover_smoke import ProofEffortRolloverSmokeResult
from scripts.run_proof_effort_rollover_smoke import build_rollover_smoke_report


def test_build_rollover_smoke_report_mentions_historical_and_successor() -> None:
    report = build_rollover_smoke_report(
        ProofEffortRolloverSmokeResult(
            base_url="https://api.openintention.io",
            source_effort_id="effort-v1",
            successor_effort_id="effort-v2",
            source_name="Eval Sprint",
            successor_name="Eval Sprint (proof v2)",
            proof_series="eval-a100-300",
            source_overview_excerpt="# Effort\n- Proof state: `historical`",
            successor_overview_excerpt="# Effort\n- Proof state: `current`",
        )
    )

    assert "Proof Effort Rollover Smoke Report" in report
    assert "effort-v2" in report
    assert "historical" in report
    assert "current" in report
