from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
import time
from typing import Callable
import json
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clients.tiny_loop.api import HttpResearchOSApi  # noqa: E402
from clients.tiny_loop.experiment import (  # noqa: E402
    EVAL_SPRINT_PROFILE,
    INFERENCE_SPRINT_PROFILE,
    ExperimentProfile,
    ExperimentResult,
    run_tiny_loop_experiment,
)

DEFAULT_BASE_URL = "https://openintention-api-production.up.railway.app"
DEFAULT_SITE_URL = "https://openintention.io"
DEFAULT_WINDOW_SECONDS = 8 * 60 * 60
DEFAULT_INTERVAL_SECONDS = 10

NIGHTLY_PROFILES: dict[str, ExperimentProfile] = {
    EVAL_SPRINT_PROFILE.name: EVAL_SPRINT_PROFILE,
    INFERENCE_SPRINT_PROFILE.name: INFERENCE_SPRINT_PROFILE,
}


@dataclass(frozen=True, slots=True)
class NightlyContributionIteration:
    index: int
    workspace_id: str
    claim_id: str
    reproduction_run_id: str | None
    discussion_url: str
    planner_action: str


@dataclass(frozen=True, slots=True)
class NightlyContributionWindowResult:
    actor_id: str
    profile: str
    effort_id: str
    effort_name: str
    base_url: str
    site_url: str
    window_seconds: int
    interval_seconds: float
    max_loops: int | None
    loops_completed: int
    iterations: list[NightlyContributionIteration]
    actor_workspace_count: int
    effort_workspace_count: int
    effort_claim_count: int
    frontier_member_count: int


def run_nightly_contribution_window(
    *,
    base_url: str,
    site_url: str,
    profile: str,
    actor_id: str | None,
    window_seconds: int,
    interval_seconds: float,
    max_loops: int | None,
    artifact_root: str,
    output_dir: str,
    monotonic_fn: Callable[[], float] = time.monotonic,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Path:
    result = execute_nightly_contribution_window(
        base_url=base_url,
        site_url=site_url,
        profile=profile,
        actor_id=actor_id,
        window_seconds=window_seconds,
        interval_seconds=interval_seconds,
        max_loops=max_loops,
        artifact_root=artifact_root,
        monotonic_fn=monotonic_fn,
        sleep_fn=sleep_fn,
    )
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / "nightly-contribution-window.md"
    report_path.write_text(build_nightly_contribution_window_report(result), encoding="utf-8")
    return report_path


def execute_nightly_contribution_window(
    *,
    base_url: str,
    site_url: str,
    profile: str,
    actor_id: str | None,
    window_seconds: int,
    interval_seconds: float,
    max_loops: int | None,
    artifact_root: str,
    monotonic_fn: Callable[[], float] = time.monotonic,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> NightlyContributionWindowResult:
    if window_seconds <= 0:
        raise ValueError("window_seconds must be greater than zero")
    if interval_seconds < 0:
        raise ValueError("interval_seconds must be zero or greater")
    if max_loops is not None and max_loops <= 0:
        raise ValueError("max_loops must be greater than zero when provided")

    selected_profile = NIGHTLY_PROFILES[profile]
    api = HttpResearchOSApi(base_url.rstrip("/"))
    effort = _require_effort(api, selected_profile)
    resolved_actor_id = actor_id or _default_actor_id()
    artifact_root_path = Path(artifact_root)
    artifact_root_path.mkdir(parents=True, exist_ok=True)

    deadline = monotonic_fn() + window_seconds
    iterations: list[NightlyContributionIteration] = []
    completed_results: list[ExperimentResult] = []
    loop_index = 0

    while True:
        if max_loops is not None and loop_index >= max_loops:
            break
        if loop_index > 0 and monotonic_fn() >= deadline:
            break

        loop_index += 1
        workspace_suffix = f"nightly-{loop_index:03d}"
        experiment = run_tiny_loop_experiment(
            api,
            artifact_root=artifact_root_path / workspace_suffix,
            profile=selected_profile,
            actor_id=resolved_actor_id,
            workspace_suffix=workspace_suffix,
        )
        completed_results.append(experiment)
        iterations.append(
            NightlyContributionIteration(
                index=loop_index,
                workspace_id=experiment.workspace_id,
                claim_id=experiment.claim_id,
                reproduction_run_id=experiment.reproduction_run_id,
                discussion_url=_discussion_url(base_url, experiment.workspace_id),
                planner_action=experiment.planner_action,
            )
        )

        if max_loops is not None and loop_index >= max_loops:
            break

        remaining_seconds = deadline - monotonic_fn()
        if remaining_seconds <= 0:
            break
        if interval_seconds > 0:
            sleep_fn(min(interval_seconds, remaining_seconds))

    workspaces = api.list_workspaces(effort_id=effort["effort_id"])
    actor_workspace_count = sum(1 for workspace in workspaces if workspace.get("actor_id") == resolved_actor_id)
    claims = _get_json(
        f"{base_url.rstrip('/')}/api/v1/claims?objective={selected_profile.objective}"
        f"&platform={selected_profile.platform}"
    )
    effort_workspace_ids = {workspace["workspace_id"] for workspace in workspaces}
    effort_claim_count = sum(1 for claim in claims if claim.get("workspace_id") in effort_workspace_ids)
    frontier = _get_json(
        f"{base_url.rstrip('/')}/api/v1/frontiers/{selected_profile.objective}/{selected_profile.platform}"
        f"?budget_seconds={selected_profile.budget_seconds}"
    )

    return NightlyContributionWindowResult(
        actor_id=resolved_actor_id,
        profile=selected_profile.name,
        effort_id=effort["effort_id"],
        effort_name=effort["name"],
        base_url=base_url.rstrip("/"),
        site_url=site_url.rstrip("/"),
        window_seconds=window_seconds,
        interval_seconds=interval_seconds,
        max_loops=max_loops,
        loops_completed=len(completed_results),
        iterations=iterations,
        actor_workspace_count=actor_workspace_count,
        effort_workspace_count=len(workspaces),
        effort_claim_count=effort_claim_count,
        frontier_member_count=len(frontier["members"]),
    )


def build_nightly_contribution_window_report(result: NightlyContributionWindowResult) -> str:
    effort_url = f"{result.site_url}/efforts/{result.effort_id}"
    iteration_lines = [
        (
            f"- loop {iteration.index}: workspace `{iteration.workspace_id}`, "
            f"claim `{iteration.claim_id}`, reproduction `{iteration.reproduction_run_id or 'none'}`, "
            f"planner `{iteration.planner_action}`, discussion `{iteration.discussion_url}`"
        )
        for iteration in result.iterations
    ] or ["- none"]

    return "\n".join(
        [
            "# Nightly Contribution Window",
            "",
            "## Window",
            f"- Actor: `{result.actor_id}`",
            f"- Profile: `{result.profile}`",
            f"- Effort: `{result.effort_name}` (`{result.effort_id}`)",
            f"- Duration budget: `{result.window_seconds}` seconds",
            f"- Interval between loops: `{result.interval_seconds}` seconds",
            f"- Max loops: `{result.max_loops if result.max_loops is not None else 'until window ends'}`",
            f"- Live effort page: `{effort_url}`",
            "",
            "## Loops Completed",
            f"- Completed loops: `{result.loops_completed}`",
            *iteration_lines,
            "",
            "## Live Evidence After This Window",
            f"- Workspaces by `{result.actor_id}` in effort: `{result.actor_workspace_count}`",
            f"- Total workspaces in effort: `{result.effort_workspace_count}`",
            f"- Claims in effort scope: `{result.effort_claim_count}`",
            f"- Frontier members: `{result.frontier_member_count}`",
            "",
            "## What To Hand Forward",
            f"- Live effort page: `{effort_url}`",
            f"- Latest discussion: `{result.iterations[-1].discussion_url if result.iterations else 'n/a'}`",
            "- Hand the live effort page or the latest discussion to the next human or agent.",
            "",
            "## Honesty Line",
            "- This is an opt-in local contribution window pointed at one hosted shared effort.",
            "- It does not auto-detect idleness and it is not a mesh worker system.",
            "- The default eval and inference loops are still proxy contribution paths.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a bounded nightly contribution window against one live OpenIntention effort."
    )
    parser.add_argument(
        "--profile",
        choices=sorted(NIGHTLY_PROFILES),
        default=EVAL_SPRINT_PROFILE.name,
        help="Which seeded effort to contribute to during the window.",
    )
    parser.add_argument(
        "--actor-id",
        default=None,
        help="Optional lightweight public handle to attach to the repeated hosted contributions.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Hosted OpenIntention API base URL.",
    )
    parser.add_argument(
        "--site-url",
        default=DEFAULT_SITE_URL,
        help="Public OpenIntention site URL.",
    )
    parser.add_argument(
        "--window-seconds",
        type=int,
        default=DEFAULT_WINDOW_SECONDS,
        help="How long this opt-in contribution window should keep running.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Pause between contribution loops inside the window.",
    )
    parser.add_argument(
        "--max-loops",
        type=int,
        default=None,
        help="Optional hard cap on loops inside this window.",
    )
    parser.add_argument(
        "--artifact-root",
        default="data/client-artifacts/nightly-window",
        help="Directory for local client-side artifacts created during the window.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/nightly-contribution-window",
        help="Directory to write the nightly contribution report into.",
    )
    args = parser.parse_args()

    report_path = run_nightly_contribution_window(
        base_url=args.base_url,
        site_url=args.site_url,
        profile=args.profile,
        actor_id=args.actor_id,
        window_seconds=args.window_seconds,
        interval_seconds=args.interval_seconds,
        max_loops=args.max_loops,
        artifact_root=args.artifact_root,
        output_dir=args.output_dir,
    )
    print(report_path)


def _require_effort(api: HttpResearchOSApi, profile: ExperimentProfile) -> dict[str, object]:
    efforts = api.list_efforts()
    effort = next((item for item in efforts if item["name"] == profile.effort_name), None)
    if effort is not None:
        return effort
    available = ", ".join(sorted(item["name"] for item in efforts)) or "none"
    raise RuntimeError(
        "nightly contribution window requires the canonical seeded effort; "
        f"available efforts: {available}"
    )


def _get_json(url: str) -> dict[str, object] | list[dict[str, object]]:
    with urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _discussion_url(base_url: str, workspace_id: str) -> str:
    return f"{base_url.rstrip('/')}/api/v1/publications/workspaces/{workspace_id}/discussion"


def _default_actor_id() -> str:
    preferred = os.environ.get("OPENINTENTION_ACTOR_ID") or os.environ.get("GITHUB_USER") or os.environ.get("USER")
    if preferred:
        return _normalize_handle(preferred)
    return "participant"


def _normalize_handle(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-_.").lower()
    return normalized or "participant"


if __name__ == "__main__":
    main()
