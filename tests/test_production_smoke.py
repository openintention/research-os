from __future__ import annotations

from scripts.run_production_smoke import ProductionSmokeResult
from scripts.run_production_smoke import build_production_smoke_report


def test_build_production_smoke_report_includes_public_and_shared_checks() -> None:
    report = build_production_smoke_report(
        ProductionSmokeResult(
            site_url="https://openintention.io",
            api_base_url="https://api.openintention.io",
            public_ingress_report="data/publications/launch/production-smoke/public-ingress/public-ingress-smoke.md",
            shared_participation_report="data/publications/launch/production-smoke/shared-participation/shared-participation-smoke.md",
            effort_names=[
                "Eval Sprint: improve validation loss under fixed budget",
                "MLX History Sprint: compound kept improvements on Apple Silicon",
            ],
            homepage_url="https://openintention.io/",
            effort_page_urls=[
                "https://openintention.io/efforts/effort-eval",
                "https://openintention.io/efforts/effort-mlx",
            ],
        )
    )

    assert "Production Smoke Report" in report
    assert "Hosted Surface" in report
    assert "Homepage freshness copy" in report
    assert "public-ingress-smoke.md" in report
    assert "shared-participation-smoke.md" in report
    assert "MLX History Sprint" in report
    assert "https://openintention.io/efforts/effort-mlx" in report
