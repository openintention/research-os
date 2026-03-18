from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SurfaceCoherenceResult:
    checked_files: list[str]
    required_artifacts: list[str]


REQUIRED_ARTIFACTS = (
    "data/publications/launch/public-ingress/public-ingress-smoke.md",
    "data/publications/launch/public-ingress/first-user-smoke.md",
    "data/publications/launch/repeated-external-participation/repeated-external-participation.md",
    "data/publications/efforts/eval-sprint-improve-validation-loss-under-fixed-budget.md",
    "data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md",
    "apps/site/dist/index.html",
    "apps/site/dist/evidence/public-ingress-smoke.html",
    "apps/site/dist/evidence/repeated-external-participation.html",
    "apps/site/dist/evidence/eval-effort.html",
    "apps/site/dist/evidence/inference-effort.html",
    "apps/site/dist/evidence/join-with-ai.html",
)

REQUIRED_PHRASES = {
    "README.md": [
        "## Public freshness model",
        "- live hosted state:",
        "- generated snapshot evidence:",
        "- deterministic smoke reports:",
    ],
    "docs/join-with-ai.md": [
        "## Freshness model",
        "- live hosted state:",
        "- generated snapshot evidence:",
        "- deterministic smoke reports:",
        "opt-in bounded contribution window",
    ],
    "docs/canonical-ingress-flow.md": [
        "## Freshness model",
        "data/publications/launch/public-ingress/first-user-smoke.md",
        "data/publications/launch/hosted-join/hosted-join.md",
    ],
    "docs/public-launch-runbook.md": [
        "## Freshness model",
        "python3 scripts/run_surface_coherence_check.py",
        "python3 scripts/run_repeated_external_participation_proof.py --base-url https://api.openintention.io",
    ],
    "docs/launch-package/checklist.md": [
        "python3 scripts/run_surface_coherence_check.py",
        "/efforts` is live hosted state",
        "bundled evidence pages are generated snapshots",
        "smoke reports are deterministic proofs, not live counters",
    ],
    "docs/launch-package/evidence.md": [
        "data/publications/launch/public-ingress/first-user-smoke.md",
        "data/publications/launch/hosted-join/hosted-join.md",
        "data/publications/launch/repeated-external-participation/repeated-external-participation.md",
        "python3 scripts/run_surface_coherence_check.py",
    ],
    "docs/launch-package/README.md": [
        "data/publications/launch/public-ingress/public-ingress-smoke.md",
        "data/publications/launch/public-ingress/first-user-smoke.md",
        "data/publications/launch/repeated-external-participation/repeated-external-participation.md",
        "python3 scripts/run_surface_coherence_check.py",
    ],
    "apps/site/dist/index.html": [
        "Join Eval in 1 command",
        "Your result shows up live",
        "What happens when you join",
        "View install script",
        "Manual join path",
        "Why this is worth joining now",
        "Deterministic ingress proof",
    ],
    "apps/site/dist/evidence/public-ingress-smoke.html": [
        "Deterministic smoke report",
        "not a live goal counter",
    ],
    "apps/site/dist/evidence/repeated-external-participation.html": [
        "Hosted network proof",
        "multiple distinct participants landing visible work",
    ],
    "apps/site/dist/evidence/eval-effort.html": [
        "Generated snapshot",
        "Use /efforts for live goal state.",
    ],
    "apps/site/dist/evidence/inference-effort.html": [
        "Generated snapshot",
        "Use /efforts for live goal state.",
    ],
    "apps/site/dist/evidence/join-with-ai.html": [
        "Repo brief",
        "copied from the repo at build time",
    ],
}

FORBIDDEN_PHRASES = {
    "docs/canonical-ingress-flow.md": [
        "data/publications/launch/first-user-smoke.md",
    ],
    "docs/launch-package/checklist.md": [
        "data/publications/launch/first-user-smoke.md",
    ],
    "docs/launch-package/evidence.md": [
        "data/publications/launch/first-user-smoke.md",
    ],
    "docs/launch-package/README.md": [
        "data/publications/launch/first-user-smoke.md",
    ],
    "apps/site/dist/index.html": [
        "Both seeded efforts already have visible work",
        "Already live now",
        "Seeded efforts and proof effort visible",
        "Visible proof bundled",
        "Open deterministic join proof",
        "Open repeated hosted participation proof",
    ],
}


def run_surface_coherence_check(*, repo_root: Path, output_dir: Path) -> Path:
    missing_artifacts: list[str] = []
    for relative_path in REQUIRED_ARTIFACTS:
        if not (repo_root / relative_path).exists():
            missing_artifacts.append(relative_path)

    missing_phrases: list[str] = []
    forbidden_hits: list[str] = []
    checked_files: list[str] = []

    for relative_path, phrases in REQUIRED_PHRASES.items():
        target = repo_root / relative_path
        if not target.exists():
            missing_artifacts.append(relative_path)
            continue
        text = target.read_text(encoding="utf-8")
        checked_files.append(relative_path)
        for phrase in phrases:
            if phrase not in text:
                missing_phrases.append(f"{relative_path}: missing `{phrase}`")

    for relative_path, phrases in FORBIDDEN_PHRASES.items():
        target = repo_root / relative_path
        if not target.exists():
            missing_artifacts.append(relative_path)
            continue
        text = target.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase in text:
                forbidden_hits.append(f"{relative_path}: still contains `{phrase}`")

    if missing_artifacts or missing_phrases or forbidden_hits:
        problems = missing_artifacts + missing_phrases + forbidden_hits
        raise RuntimeError("surface coherence check failed:\n- " + "\n- ".join(problems))

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "surface-coherence.md"
    report_path.write_text(
        build_surface_coherence_report(
            SurfaceCoherenceResult(
                checked_files=checked_files,
                required_artifacts=list(REQUIRED_ARTIFACTS),
            )
        ),
        encoding="utf-8",
    )
    return report_path


def build_surface_coherence_report(result: SurfaceCoherenceResult) -> str:
    artifact_lines = [f"- `{path}`" for path in result.required_artifacts]
    checked_lines = [f"- `{path}`" for path in result.checked_files]
    return "\n".join(
        [
            "# Surface Coherence Report",
            "",
            "## Freshness Model",
            "- `/efforts` is treated as live hosted state.",
            "- Bundled evidence pages are treated as generated snapshots.",
            "- Smoke reports are treated as deterministic proofs, not live counters.",
            "",
            "## Required Artifacts Present",
            *artifact_lines,
            "",
            "## Checked Surfaces",
            *checked_lines,
            "",
            "## Outcome",
            "- Public docs, bundled microsite evidence, and launch artifacts use the same freshness vocabulary.",
            "- Canonical evidence paths match the current generated artifact layout.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify that launch docs, bundled site evidence, and generated artifacts use a coherent freshness model."
    )
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/surface-coherence",
        help="Directory to write the coherence report into.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    report_path = run_surface_coherence_check(
        repo_root=repo_root,
        output_dir=repo_root / args.output_dir,
    )
    print(report_path)


if __name__ == "__main__":
    main()
