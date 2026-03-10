from __future__ import annotations

from scripts.run_first_user_smoke import SmokeResult, build_smoke_report


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
            exported_brief_paths=[
                "data/publications/efforts/eval-sprint-improve-validation-loss-under-fixed-budget.md",
                "data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md",
            ],
        )
    )

    assert "First User Smoke Report" in report
    assert "Eval Sprint: improve validation loss under fixed budget" in report
    assert "Inference Sprint: improve flash-path throughput on H100" in report
    assert "effort_name=Eval Sprint" in report
    assert "data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md" in report
