from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clients.tiny_loop.api import HttpResearchOSApi  # noqa: E402
from clients.tiny_loop.experiment import (  # noqa: E402
    EVAL_SPRINT_PROFILE,
    ExperimentResult,
    run_tiny_loop_experiment,
)


@dataclass(frozen=True, slots=True)
class SharedParticipationResult:
    base_url: str
    effort_id: str
    effort_name: str
    first: ExperimentResult
    second: ExperimentResult
    workspace_ids: list[str]
    claim_ids: list[str]
    frontier_member_count: int
    effort_overview_excerpt: str


def run_shared_participation_smoke(
    *,
    base_url: str,
    output_dir: str,
    artifact_root: str,
) -> Path:
    normalized_base_url = base_url.rstrip("/")
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    artifact_root_path = Path(artifact_root)
    artifact_root_path.mkdir(parents=True, exist_ok=True)

    api = HttpResearchOSApi(normalized_base_url)
    effort = _require_eval_effort(api)

    first = run_tiny_loop_experiment(
        api,
        artifact_root=artifact_root_path / "participant-alpha",
        profile=EVAL_SPRINT_PROFILE,
        actor_id="participant-alpha",
        workspace_suffix="alpha",
    )
    second = run_tiny_loop_experiment(
        api,
        artifact_root=artifact_root_path / "participant-beta",
        profile=EVAL_SPRINT_PROFILE,
        actor_id="participant-beta",
        workspace_suffix="beta",
    )

    workspaces = api.list_workspaces(effort_id=effort["effort_id"])
    claims = _get_json(
        f"{normalized_base_url}/api/v1/claims?objective={EVAL_SPRINT_PROFILE.objective}"
        f"&platform={EVAL_SPRINT_PROFILE.platform}"
    )
    frontier = _get_json(
        f"{normalized_base_url}/api/v1/frontiers/{EVAL_SPRINT_PROFILE.objective}/{EVAL_SPRINT_PROFILE.platform}"
        f"?budget_seconds={EVAL_SPRINT_PROFILE.budget_seconds}"
    )
    publication = api.get_effort_overview(effort["effort_id"])

    result = SharedParticipationResult(
        base_url=normalized_base_url,
        effort_id=effort["effort_id"],
        effort_name=effort["name"],
        first=first,
        second=second,
        workspace_ids=[workspace["workspace_id"] for workspace in workspaces],
        claim_ids=[claim["claim_id"] for claim in claims],
        frontier_member_count=len(frontier["members"]),
        effort_overview_excerpt=_excerpt(publication["body"], lines=24),
    )

    report_path = output_root / "shared-participation-smoke.md"
    report_path.write_text(build_shared_participation_report(result), encoding="utf-8")
    return report_path


def build_shared_participation_report(result: SharedParticipationResult) -> str:
    workspace_lines = [f"- `{workspace_id}`" for workspace_id in result.workspace_ids] or ["- none"]
    claim_lines = [f"- `{claim_id}`" for claim_id in result.claim_ids] or ["- none"]
    return "\n".join(
        [
            "# Shared Participation Smoke Report",
            "",
            "## Shared Control Plane",
            f"- Base URL: `{result.base_url}`",
            f"- Effort: `{result.effort_name}` (`{result.effort_id}`)",
            "",
            "## Participant Runs",
            (
                f"- `participant-alpha` -> workspace `{result.first.workspace_id}`, "
                f"claim `{result.first.claim_id}`, reproduction `{result.first.reproduction_run_id}`"
            ),
            (
                f"- `participant-beta` -> workspace `{result.second.workspace_id}`, "
                f"claim `{result.second.claim_id}`, reproduction `{result.second.reproduction_run_id}`"
            ),
            "",
            "## Shared State After Both Runs",
            f"- Workspaces attached to effort: {len(result.workspace_ids)}",
            *workspace_lines,
            f"- Claims in effort scope: {len(result.claim_ids)}",
            *claim_lines,
            f"- Frontier members: {result.frontier_member_count}",
            "",
            "## Effort Overview Excerpt",
            "```text",
            result.effort_overview_excerpt.strip(),
            "```",
            "",
            "## Outcome",
            "- Two independent participants landed work into the same hosted seeded effort state.",
            "- The shared control plane can now point to distinct workspaces, claims, and frontier state created by separate participants.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify shared participation against one hosted control plane.")
    parser.add_argument("--base-url", required=True, help="Hosted API base URL for the shared control plane.")
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/shared-participation",
        help="Directory to write the shared participation smoke report into.",
    )
    parser.add_argument(
        "--artifact-root",
        default="data/client-artifacts/shared-participation",
        help="Directory for client-side snapshot bundles created during the smoke run.",
    )
    args = parser.parse_args()

    report_path = run_shared_participation_smoke(
        base_url=args.base_url,
        output_dir=args.output_dir,
        artifact_root=args.artifact_root,
    )
    print(report_path)


def _excerpt(body: str, *, lines: int) -> str:
    return "\n".join(body.splitlines()[:lines]).strip()


def _get_json(url: str) -> dict[str, object] | list[dict[str, object]]:
    with urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _require_eval_effort(api: HttpResearchOSApi) -> dict[str, object]:
    efforts = api.list_efforts()
    effort = next((item for item in efforts if item["name"] == EVAL_SPRINT_PROFILE.effort_name), None)
    if effort is not None:
        return effort

    available = ", ".join(sorted(item["name"] for item in efforts)) or "none"
    raise RuntimeError(
        "shared participation smoke requires the canonical eval seeded effort; "
        f"available efforts: {available}"
    )


if __name__ == "__main__":
    main()
