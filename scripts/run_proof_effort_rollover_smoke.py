from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clients.tiny_loop.api import HttpResearchOSApi  # noqa: E402
from scripts.rollover_proof_effort import rollover_proof_effort  # noqa: E402

DEFAULT_EFFORT_NAME = "Eval Sprint: improve validation loss under fixed budget"


@dataclass(frozen=True, slots=True)
class ProofEffortRolloverSmokeResult:
    base_url: str
    source_effort_id: str
    successor_effort_id: str
    source_name: str
    successor_name: str
    proof_series: str
    source_overview_excerpt: str
    successor_overview_excerpt: str


def run_proof_effort_rollover_smoke(
    *,
    base_url: str,
    effort_name: str = DEFAULT_EFFORT_NAME,
    output_dir: str,
) -> Path:
    normalized_base_url = base_url.rstrip("/")
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    result = rollover_proof_effort(
        base_url=normalized_base_url,
        effort_name=effort_name,
        actor_id="openintention-rollover-smoke",
        reason="verify immutable proof rollover handling",
    )

    api = HttpResearchOSApi(normalized_base_url)
    source_overview = api.get_effort_overview(result.source_effort_id)
    successor_overview = api.get_effort_overview(result.successor_effort_id)
    efforts = api.list_efforts()
    source = next(item for item in efforts if item["effort_id"] == result.source_effort_id)
    successor = next(item for item in efforts if item["effort_id"] == result.successor_effort_id)

    smoke = ProofEffortRolloverSmokeResult(
        base_url=normalized_base_url,
        source_effort_id=result.source_effort_id,
        successor_effort_id=result.successor_effort_id,
        source_name=result.source_name,
        successor_name=result.successor_name,
        proof_series=str(source.get("tags", {}).get("proof_series") or successor.get("tags", {}).get("proof_series")),
        source_overview_excerpt=_excerpt(source_overview["body"], lines=16),
        successor_overview_excerpt=_excerpt(successor_overview["body"], lines=16),
    )

    report_path = output_root / "proof-effort-rollover-smoke.md"
    report_path.write_text(build_rollover_smoke_report(smoke), encoding="utf-8")
    return report_path


def build_rollover_smoke_report(result: ProofEffortRolloverSmokeResult) -> str:
    return "\n".join(
        [
            "# Proof Effort Rollover Smoke Report",
            "",
            "## Shared Control Plane",
            f"- Base URL: `{result.base_url}`",
            f"- Source effort: `{result.source_name}` (`{result.source_effort_id}`)",
            f"- Successor effort: `{result.successor_name}` (`{result.successor_effort_id}`)",
            f"- Proof series: `{result.proof_series}`",
            "",
            "## Historical Source Overview",
            "```text",
            result.source_overview_excerpt.strip(),
            "```",
            "",
            "## Current Successor Overview",
            "```text",
            result.successor_overview_excerpt.strip(),
            "```",
            "",
            "## Outcome",
            "- The previous proof effort remains inspectable and historical.",
            "- A successor effort is created for the next proof window.",
            "- Operators can advance public proof work without deleting immutable history.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify proof-effort rollover against a shared control plane.")
    parser.add_argument("--base-url", required=True, help="Hosted or local API base URL.")
    parser.add_argument(
        "--effort-name",
        default=DEFAULT_EFFORT_NAME,
        help="Proof effort name to roll over for the smoke path.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/proof-effort-rollover",
        help="Directory to write the rollover smoke report into.",
    )
    args = parser.parse_args()
    report_path = run_proof_effort_rollover_smoke(
        base_url=args.base_url,
        effort_name=args.effort_name,
        output_dir=args.output_dir,
    )
    print(report_path)


def _excerpt(body: str, *, lines: int) -> str:
    return "\n".join(body.splitlines()[:lines]).strip()


if __name__ == "__main__":
    main()
