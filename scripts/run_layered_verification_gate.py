from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SITE_URL = "https://openintention.io"
DEFAULT_API_BASE_URL = "https://api.openintention.io"
DEFAULT_OUTPUT_ROOT = "data/publications/launch/layered-verification"

MERGE_GATE = "merge"
DEPLOY_GATE = "deploy"
LAUNCH_CLAIM_GATE = "launch-claim"


@dataclass(frozen=True, slots=True)
class AutomatedCheck:
    check_id: str
    label: str
    command: tuple[str, ...]
    pass_criteria: tuple[str, ...]
    evidence_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ManualCheck:
    check_id: str
    label: str
    instructions: tuple[str, ...]
    required_evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LayerDefinition:
    layer_id: str
    label: str
    execution_mode: str
    thresholds: tuple[str, ...]
    automated_checks: tuple[AutomatedCheck, ...] = ()
    manual_checks: tuple[ManualCheck, ...] = ()


@dataclass(frozen=True, slots=True)
class AutomatedCheckResult:
    check_id: str
    label: str
    command: str
    status: str
    return_code: int
    pass_criteria: tuple[str, ...]
    evidence_paths: tuple[str, ...]
    output_excerpt: str


@dataclass(frozen=True, slots=True)
class ManualCheckResult:
    check_id: str
    label: str
    status: str
    instructions: tuple[str, ...]
    required_evidence: tuple[str, ...]
    evidence_note: str | None


@dataclass(frozen=True, slots=True)
class LayerResult:
    layer_id: str
    label: str
    execution_mode: str
    thresholds: tuple[str, ...]
    automated_results: tuple[AutomatedCheckResult, ...]
    manual_results: tuple[ManualCheckResult, ...]


@dataclass(frozen=True, slots=True)
class GateResult:
    gate: str
    site_url: str
    api_base_url: str
    output_root: str
    overall_status: str
    layers: tuple[LayerResult, ...]


def run_layered_verification_gate(
    *,
    gate: str,
    site_url: str,
    api_base_url: str,
    output_root: str,
    manual_checks: dict[str, str],
    include_worker_layer: bool = False,
) -> Path:
    output_root_path = Path(output_root).resolve()
    gate_root = output_root_path / gate
    gate_root.mkdir(parents=True, exist_ok=True)

    layer_results: list[LayerResult] = []
    overall_status = "passed"
    for layer in _build_layers(
        gate=gate,
        site_url=site_url,
        api_base_url=api_base_url,
        gate_root=gate_root,
        include_worker_layer=include_worker_layer,
    ):
        automated_results = tuple(_run_automated_check(check) for check in layer.automated_checks)
        manual_results = tuple(_resolve_manual_check(check, manual_checks) for check in layer.manual_checks)

        if any(result.status == "failed" for result in automated_results):
            overall_status = "failed"
        elif any(result.status == "pending-manual" for result in manual_results) and overall_status != "failed":
            overall_status = "manual-follow-up-required"

        layer_results.append(
            LayerResult(
                layer_id=layer.layer_id,
                label=layer.label,
                execution_mode=layer.execution_mode,
                thresholds=layer.thresholds,
                automated_results=automated_results,
                manual_results=manual_results,
            )
        )

    result = GateResult(
        gate=gate,
        site_url=site_url,
        api_base_url=api_base_url,
        output_root=str(gate_root),
        overall_status=overall_status,
        layers=tuple(layer_results),
    )
    report_path = gate_root / "layered-verification-report.md"
    report_path.write_text(build_layered_verification_report(result), encoding="utf-8")
    if overall_status != "passed":
        raise RuntimeError(f"{gate} gate finished with status `{overall_status}`: {report_path}")
    return report_path


def build_layered_verification_report(result: GateResult) -> str:
    layer_sections = [_render_layer(layer) for layer in result.layers]
    return "\n".join(
        [
            "# Layered Verification Gate",
            "",
            f"- Gate: `{result.gate}`",
            f"- Site URL: `{result.site_url}`",
            f"- API base URL: `{result.api_base_url}`",
            f"- Output root: `{result.output_root}`",
            f"- Overall status: `{result.overall_status}`",
            "",
            "## Thresholds",
            "- `merge`: L0 only, plus the smallest feature-local failing deterministic test first.",
            "- `deploy`: L0 + L1 + L2.",
            "- `launch-claim`: L0 + L1 + L2 + L3, plus L4 if worker or external-harness behavior is part of the claim.",
            "",
            "## TDD Loop",
            "1. Add or update the smallest failing deterministic test first.",
            "2. Make that test pass.",
            "3. Re-run the smallest relevant verification layer.",
            "4. Re-run the broader threshold gate before merge, deploy, or launch claims.",
            "",
            *layer_sections,
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the repeatable layered verification gate.")
    parser.add_argument(
        "--gate",
        choices=(MERGE_GATE, DEPLOY_GATE, LAUNCH_CLAIM_GATE),
        required=True,
        help="Verification threshold to execute.",
    )
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL, help="OpenIntention site URL.")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL, help="Hosted API base URL.")
    parser.add_argument(
        "--output-root",
        default=DEFAULT_OUTPUT_ROOT,
        help="Root directory for layered gate artifacts.",
    )
    parser.add_argument(
        "--manual-check",
        action="append",
        default=[],
        metavar="CHECK_ID=NOTE",
        help="Mark one manual clean-room check as complete with an evidence note.",
    )
    parser.add_argument(
        "--include-worker-layer",
        action="store_true",
        help="Include the deterministic worker proof layer in the selected gate.",
    )
    args = parser.parse_args()

    manual_checks = _parse_manual_checks(args.manual_check)
    report_path = run_layered_verification_gate(
        gate=args.gate,
        site_url=args.site_url,
        api_base_url=args.api_base_url,
        output_root=args.output_root,
        manual_checks=manual_checks,
        include_worker_layer=args.include_worker_layer,
    )
    print(report_path)


def _parse_manual_checks(entries: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise ValueError(f"manual check must use CHECK_ID=NOTE format: {entry}")
        check_id, note = entry.split("=", 1)
        check_id = check_id.strip()
        note = note.strip()
        if not check_id or not note:
            raise ValueError(f"manual check must include both id and note: {entry}")
        parsed[check_id] = note
    return parsed


def _build_layers(
    *,
    gate: str,
    site_url: str,
    api_base_url: str,
    gate_root: Path,
    include_worker_layer: bool,
) -> tuple[LayerDefinition, ...]:
    layers: list[LayerDefinition] = [_layer_l0(gate_root)]
    if gate in {DEPLOY_GATE, LAUNCH_CLAIM_GATE}:
        layers.append(_layer_l1(gate_root))
        layers.append(_layer_l2(gate_root, site_url=site_url, api_base_url=api_base_url))
    if gate == LAUNCH_CLAIM_GATE:
        layers.append(_layer_l3())
    if include_worker_layer:
        layers.append(_layer_l4(gate_root))
    return tuple(layers)


def _layer_l0(gate_root: Path) -> LayerDefinition:
    _ = gate_root
    return LayerDefinition(
        layer_id="L0",
        label="Fast deterministic core",
        execution_mode="automated",
        thresholds=(MERGE_GATE, DEPLOY_GATE, LAUNCH_CLAIM_GATE),
        automated_checks=(
            AutomatedCheck(
                check_id="ruff",
                label="Ruff check",
                command=(sys.executable, "-m", "ruff", "check", "."),
                pass_criteria=("No lint violations.",),
            ),
            AutomatedCheck(
                check_id="pytest",
                label="Pytest suite",
                command=(sys.executable, "-m", "pytest", "-q"),
                pass_criteria=("All deterministic tests pass.",),
            ),
        ),
    )


def _layer_l1(gate_root: Path) -> LayerDefinition:
    first_user_output = gate_root / "first-user"
    public_ingress_output = gate_root / "public-ingress"
    surface_output = gate_root / "surface-coherence"
    return LayerDefinition(
        layer_id="L1",
        label="Deterministic product path",
        execution_mode="automated",
        thresholds=(DEPLOY_GATE, LAUNCH_CLAIM_GATE),
        automated_checks=(
            AutomatedCheck(
                check_id="surface-coherence",
                label="Surface coherence",
                command=(
                    sys.executable,
                    "scripts/run_surface_coherence_check.py",
                    "--output-dir",
                    str(surface_output),
                ),
                pass_criteria=(
                    "Docs, bundled evidence, and smoke paths use one freshness model.",
                ),
                evidence_paths=(str(surface_output / "surface-coherence.md"),),
            ),
            AutomatedCheck(
                check_id="first-user-smoke",
                label="First user smoke",
                command=(
                    sys.executable,
                    "scripts/run_first_user_smoke.py",
                    "--output-dir",
                    str(first_user_output),
                ),
                pass_criteria=(
                    "Local newcomer flow produces onboarded, joined, and participated evidence.",
                ),
                evidence_paths=(str(first_user_output / "first-user-smoke.md"),),
            ),
            AutomatedCheck(
                check_id="public-ingress-smoke",
                label="Public ingress smoke",
                command=(
                    sys.executable,
                    "scripts/run_public_ingress_smoke.py",
                    "--output-dir",
                    str(public_ingress_output),
                ),
                pass_criteria=(
                    "Public site -> repo -> fresh checkout participation path remains intact.",
                ),
                evidence_paths=(str(public_ingress_output / "public-ingress-smoke.md"),),
            ),
        ),
    )


def _layer_l2(gate_root: Path, *, site_url: str, api_base_url: str) -> LayerDefinition:
    shared_output = gate_root / "shared-participation"
    shared_artifacts = gate_root / "client-artifacts" / "shared-participation"
    repeated_output = gate_root / "repeated-external-participation"
    repeated_artifacts = gate_root / "client-artifacts" / "repeated-external-participation"
    production_output = gate_root / "production-smoke"
    return LayerDefinition(
        layer_id="L2",
        label="Hosted network floor",
        execution_mode="automated-live",
        thresholds=(DEPLOY_GATE, LAUNCH_CLAIM_GATE),
        automated_checks=(
            AutomatedCheck(
                check_id="shared-participation",
                label="Shared participation smoke",
                command=(
                    sys.executable,
                    "scripts/run_shared_participation_smoke.py",
                    "--base-url",
                    api_base_url,
                    "--output-dir",
                    str(shared_output),
                    "--artifact-root",
                    str(shared_artifacts),
                ),
                pass_criteria=(
                    "Contributor and verifier land into one hosted seeded goal with visible separate workspaces.",
                ),
                evidence_paths=(str(shared_output / "shared-participation-smoke.md"),),
            ),
            AutomatedCheck(
                check_id="repeated-hosted-participation",
                label="Repeated hosted participation proof",
                command=(
                    sys.executable,
                    "scripts/run_repeated_external_participation_proof.py",
                    "--base-url",
                    api_base_url,
                    "--site-url",
                    site_url,
                    "--output-dir",
                    str(repeated_output),
                    "--artifact-root",
                    str(repeated_artifacts),
                ),
                pass_criteria=(
                    "Multiple distinct participants append visible work through the canonical hosted endpoint.",
                ),
                evidence_paths=(str(repeated_output / "repeated-external-participation.md"),),
            ),
            AutomatedCheck(
                check_id="production-smoke",
                label="Production smoke",
                command=(
                    sys.executable,
                    "scripts/run_production_smoke.py",
                    "--site-url",
                    site_url,
                    "--api-base-url",
                    api_base_url,
                    "--output-dir",
                    str(production_output),
                ),
                pass_criteria=(
                    "Public site, hosted API, and effort explorer all remain reachable and coherent.",
                ),
                evidence_paths=(str(production_output / "production-smoke.md"),),
            ),
        ),
    )


def _layer_l3() -> LayerDefinition:
    return LayerDefinition(
        layer_id="L3",
        label="Clean-room agent ingress",
        execution_mode="manual-clean-room",
        thresholds=(LAUNCH_CLAIM_GATE,),
        manual_checks=(
            ManualCheck(
                check_id="claude-clean-room",
                label="Claude clean-room run",
                instructions=(
                    "Give Claude only the public site and public repo links.",
                    "Confirm it infers the product boundary, finds the join path, and leaves behind inspectable evidence.",
                ),
                required_evidence=(
                    "Prompt used",
                    "Resulting workspace/claim/live URLs",
                    "Short verdict: onboarded, joined, participated",
                ),
            ),
            ManualCheck(
                check_id="codex-clean-room",
                label="Codex clean-room run",
                instructions=(
                    "Give Codex only the public site and public repo links.",
                    "Confirm it can repeat the same newcomer path without hidden context.",
                ),
                required_evidence=(
                    "Prompt used",
                    "Resulting workspace/claim/live URLs",
                    "Short verdict: onboarded, joined, participated",
                ),
            ),
        ),
    )


def _layer_l4(gate_root: Path) -> LayerDefinition:
    worker_output = gate_root / "overnight-worker"
    return LayerDefinition(
        layer_id="L4",
        label="Worker proof",
        execution_mode="automated",
        thresholds=(LAUNCH_CLAIM_GATE,),
        automated_checks=(
            AutomatedCheck(
                check_id="overnight-worker-smoke",
                label="Overnight worker smoke",
                command=(
                    sys.executable,
                    "scripts/run_overnight_autoresearch_worker_smoke.py",
                    "--output-dir",
                    str(worker_output),
                ),
                pass_criteria=(
                    "Bounded worker path imports kept external-harness results into shared state.",
                ),
                evidence_paths=(str(worker_output / "overnight-autoresearch-worker-smoke.md"),),
            ),
        ),
    )


def _run_automated_check(check: AutomatedCheck) -> AutomatedCheckResult:
    completed = subprocess.run(
        list(check.command),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    combined_output = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part.strip()
    )
    return AutomatedCheckResult(
        check_id=check.check_id,
        label=check.label,
        command=shlex.join(check.command),
        status="passed" if completed.returncode == 0 else "failed",
        return_code=completed.returncode,
        pass_criteria=check.pass_criteria,
        evidence_paths=check.evidence_paths,
        output_excerpt=_excerpt(combined_output),
    )


def _resolve_manual_check(check: ManualCheck, evidence_notes: dict[str, str]) -> ManualCheckResult:
    note = evidence_notes.get(check.check_id)
    return ManualCheckResult(
        check_id=check.check_id,
        label=check.label,
        status="passed" if note is not None else "pending-manual",
        instructions=check.instructions,
        required_evidence=check.required_evidence,
        evidence_note=note,
    )


def _render_layer(layer: LayerResult) -> str:
    lines = [
        f"## {layer.layer_id}: {layer.label}",
        f"- Mode: `{layer.execution_mode}`",
        f"- Thresholds: {', '.join(f'`{item}`' for item in layer.thresholds)}",
        "",
    ]
    if layer.automated_results:
        lines.append("### Automated checks")
        for result in layer.automated_results:
            lines.extend(
                [
                    f"- `{result.label}` status=`{result.status}` return_code={result.return_code}",
                    f"  command=`{result.command}`",
                ]
            )
            if result.evidence_paths:
                lines.append(f"  evidence={', '.join(f'`{path}`' for path in result.evidence_paths)}")
            for criterion in result.pass_criteria:
                lines.append(f"  pass_criterion={criterion}")
            if result.output_excerpt:
                lines.append("  excerpt:")
                lines.append("```text")
                lines.append(result.output_excerpt)
                lines.append("```")
        lines.append("")
    if layer.manual_results:
        lines.append("### Manual clean-room checks")
        for result in layer.manual_results:
            lines.append(f"- `{result.label}` status=`{result.status}`")
            for instruction in result.instructions:
                lines.append(f"  instruction={instruction}")
            for evidence in result.required_evidence:
                lines.append(f"  required_evidence={evidence}")
            if result.evidence_note is not None:
                lines.append(f"  note={result.evidence_note}")
        lines.append("")
    return "\n".join(lines)


def _excerpt(text: str, *, max_lines: int = 12) -> str:
    if not text.strip():
        return ""
    return "\n".join(text.splitlines()[:max_lines]).strip()


if __name__ == "__main__":
    main()
