from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_surface_coherence_check import build_surface_coherence_report
from scripts.run_surface_coherence_check import run_surface_coherence_check
from scripts.run_surface_coherence_check import SurfaceCoherenceResult


def test_build_surface_coherence_report_describes_freshness_model() -> None:
    report = build_surface_coherence_report(
        SurfaceCoherenceResult(
            checked_files=["README.md", "apps/site/dist/index.html"],
            required_artifacts=[
                "data/publications/launch/public-ingress/public-ingress-smoke.md",
                "data/publications/launch/repeated-external-participation/repeated-external-participation.md",
                "apps/site/dist/index.html",
            ],
        )
    )

    assert "Surface Coherence Report" in report
    assert "/efforts` is treated as live hosted state." in report
    assert "generated snapshots" in report
    assert "deterministic proofs, not live counters" in report


def test_run_surface_coherence_check_validates_required_phrases(tmp_path: Path) -> None:
    files = {
        "README.md": "\n".join(
            [
                "## Public freshness model",
                "- live hosted state:",
                "- generated snapshot evidence:",
                "- deterministic smoke reports:",
            ]
        ),
        "docs/join-with-ai.md": "\n".join(
            [
                "## Freshness model",
                "- live hosted state:",
                "- generated snapshot evidence:",
                "- deterministic smoke reports:",
                "opt-in bounded contribution window",
            ]
        ),
        "docs/canonical-ingress-flow.md": "\n".join(
            [
                "## Freshness model",
                "data/publications/launch/public-ingress/first-user-smoke.md",
                "data/publications/launch/hosted-join/hosted-join.md",
            ]
        ),
        "docs/public-launch-runbook.md": "\n".join(
            [
                "## Freshness model",
                "python3 scripts/run_surface_coherence_check.py",
                "python3 scripts/run_repeated_external_participation_proof.py --base-url https://api.openintention.io",
            ]
        ),
        "docs/launch-package/checklist.md": "\n".join(
            [
                "python3 scripts/run_surface_coherence_check.py",
                "/efforts` is live hosted state",
                "bundled evidence pages are generated snapshots",
                "smoke reports are deterministic proofs, not live counters",
            ]
        ),
        "docs/launch-package/evidence.md": "\n".join(
            [
                "data/publications/launch/public-ingress/first-user-smoke.md",
                "data/publications/launch/hosted-join/hosted-join.md",
                "data/publications/launch/repeated-external-participation/repeated-external-participation.md",
                "python3 scripts/run_surface_coherence_check.py",
            ]
        ),
        "docs/launch-package/README.md": "\n".join(
            [
                "data/publications/launch/public-ingress/public-ingress-smoke.md",
                "data/publications/launch/public-ingress/first-user-smoke.md",
                "data/publications/launch/repeated-external-participation/repeated-external-participation.md",
                "python3 scripts/run_surface_coherence_check.py",
            ]
        ),
        "apps/site/dist/index.html": "\n".join(
            [
                "Join Eval in 1 command",
                "Visible workspace + claim",
                "Freshness model:",
                "View install script",
                "Manual join path",
                "Current goal momentum",
                "Deterministic ingress proof",
            ]
        ),
        "apps/site/dist/evidence/public-ingress-smoke.html": "\n".join(
            [
                "Deterministic smoke report",
                "not a live goal counter",
            ]
        ),
        "apps/site/dist/evidence/repeated-external-participation.html": "\n".join(
            [
                "Hosted network proof",
                "multiple distinct participants landing visible work",
            ]
        ),
        "apps/site/dist/evidence/eval-effort.html": "\n".join(
            [
                "Generated snapshot",
                "Use /efforts for live goal state.",
            ]
        ),
        "apps/site/dist/evidence/join-with-ai.html": "\n".join(
            [
                "Repo brief",
                "copied from the repo at build time",
            ]
        ),
        "apps/site/dist/evidence/inference-effort.html": "\n".join(
            [
                "Generated snapshot",
                "Use /efforts for live goal state.",
            ]
        ),
        "data/publications/launch/public-ingress/public-ingress-smoke.md": "# report",
        "data/publications/launch/public-ingress/first-user-smoke.md": "# report",
        "data/publications/launch/repeated-external-participation/repeated-external-participation.md": "# report",
        "data/publications/efforts/eval-sprint-improve-validation-loss-under-fixed-budget.md": "# eval",
        "data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md": "# inference",
    }

    for relative_path, contents in files.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")

    report_path = run_surface_coherence_check(
        repo_root=tmp_path,
        output_dir=tmp_path / "data/publications/launch/surface-coherence",
    )

    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert "Surface Coherence Report" in report
    assert "apps/site/dist/index.html" in report


def test_run_surface_coherence_check_fails_on_stale_path_reference(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "## Public freshness model\n- live hosted state:\n- generated snapshot evidence:\n- deterministic smoke reports:\n",
        encoding="utf-8",
    )
    stale_path = tmp_path / "docs/canonical-ingress-flow.md"
    stale_path.parent.mkdir(parents=True, exist_ok=True)
    stale_path.write_text("data/publications/launch/first-user-smoke.md", encoding="utf-8")

    with pytest.raises(RuntimeError):
        run_surface_coherence_check(
            repo_root=tmp_path,
            output_dir=tmp_path / "data/publications/launch/surface-coherence",
        )
