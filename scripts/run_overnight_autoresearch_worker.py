from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from clients.tiny_loop.api import HttpResearchOSApi  # noqa: E402
from research_os.integrations.mlx_history import MlxHistoryResult, load_results_tsv  # noqa: E402
from scripts.run_mlx_history_compounding_smoke import (  # noqa: E402
    DEFAULT_REPO_URL,
    EFFORT_BUDGET_SECONDS,
    EFFORT_OBJECTIVE,
    EFFORT_PLATFORM,
    ImportedContribution,
    _ensure_effort,
    _get_json,
    _import_contribution,
    _record_adoption,
)

DEFAULT_BASE_URL = "https://api.openintention.io"
DEFAULT_SITE_URL = "https://openintention.io"
DEFAULT_WINDOW_SECONDS = 8 * 60 * 60
DEFAULT_INTERVAL_SECONDS = 15 * 60
DEFAULT_COMMAND_TIMEOUT_SECONDS = 5 * 60
DEFAULT_BUDGET_CAP_SECONDS = 40 * 60


@dataclass(frozen=True, slots=True)
class ContributionReference:
    actor_id: str
    workspace_id: str
    claim_id: str
    candidate_commit: str


@dataclass(frozen=True, slots=True)
class RunnerCommandResult:
    status: str
    duration_seconds: float
    exit_code: int | None
    output: str
    log_path: str


@dataclass(frozen=True, slots=True)
class OvernightWorkerIteration:
    index: int
    runner_status: str
    duration_seconds: float
    exit_code: int | None
    imported_candidate_commit: str | None
    imported_baseline_commit: str | None
    workspace_id: str | None
    claim_id: str | None
    discussion_url: str | None
    adoption_event_id: str | None
    note: str
    log_path: str


@dataclass(frozen=True, slots=True)
class OvernightWorkerResult:
    actor_id: str
    base_url: str
    site_url: str
    repo_path: str
    repo_url: str
    runner_command: str
    effort_id: str
    effort_name: str
    window_seconds: int
    interval_seconds: float
    max_loops: int | None
    command_timeout_seconds: int
    budget_cap_seconds: int | None
    loops_completed: int
    imported_iterations: int
    total_runner_seconds: float
    stop_reason: str
    iterations: list[OvernightWorkerIteration]
    effort_workspace_count: int
    effort_claim_count: int
    frontier_member_count: int


def run_overnight_autoresearch_worker(
    *,
    base_url: str,
    site_url: str,
    repo_path: str,
    runner_command: str,
    actor_id: str | None,
    window_seconds: int,
    interval_seconds: float,
    max_loops: int | None,
    command_timeout_seconds: int,
    budget_cap_seconds: int | None,
    artifact_root: str,
    output_dir: str,
    repo_url: str | None = None,
    results_path: str | None = None,
    monotonic_fn: Callable[[], float] = time.monotonic,
    sleep_fn: Callable[[float], None] = time.sleep,
    run_command_fn: Callable[[str, Path, int, Path], RunnerCommandResult] | None = None,
) -> Path:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    log_root = output_root / "logs"
    log_root.mkdir(parents=True, exist_ok=True)

    result = execute_overnight_autoresearch_worker(
        base_url=base_url,
        site_url=site_url,
        repo_path=repo_path,
        runner_command=runner_command,
        actor_id=actor_id,
        window_seconds=window_seconds,
        interval_seconds=interval_seconds,
        max_loops=max_loops,
        command_timeout_seconds=command_timeout_seconds,
        budget_cap_seconds=budget_cap_seconds,
        artifact_root=artifact_root,
        repo_url=repo_url,
        results_path=results_path,
        log_root=log_root,
        monotonic_fn=monotonic_fn,
        sleep_fn=sleep_fn,
        run_command_fn=run_command_fn or _run_runner_command,
    )
    report_path = output_root / "overnight-autoresearch-worker.md"
    report_path.write_text(build_overnight_worker_report(result), encoding="utf-8")
    return report_path


def execute_overnight_autoresearch_worker(
    *,
    base_url: str,
    site_url: str,
    repo_path: str,
    runner_command: str,
    actor_id: str | None,
    window_seconds: int,
    interval_seconds: float,
    max_loops: int | None,
    command_timeout_seconds: int,
    budget_cap_seconds: int | None,
    artifact_root: str,
    repo_url: str | None = None,
    results_path: str | None = None,
    log_root: str | Path,
    monotonic_fn: Callable[[], float] = time.monotonic,
    sleep_fn: Callable[[float], None] = time.sleep,
    run_command_fn: Callable[[str, Path, int, Path], RunnerCommandResult] | None = None,
) -> OvernightWorkerResult:
    if window_seconds <= 0:
        raise ValueError("window_seconds must be greater than zero")
    if interval_seconds < 0:
        raise ValueError("interval_seconds must be zero or greater")
    if max_loops is not None and max_loops <= 0:
        raise ValueError("max_loops must be greater than zero when provided")
    if command_timeout_seconds <= 0:
        raise ValueError("command_timeout_seconds must be greater than zero")
    if budget_cap_seconds is not None and budget_cap_seconds <= 0:
        raise ValueError("budget_cap_seconds must be greater than zero when provided")
    if not runner_command.strip():
        raise ValueError("runner_command must be provided")

    normalized_base_url = base_url.rstrip("/")
    normalized_site_url = site_url.rstrip("/")
    resolved_actor_id = actor_id or _default_actor_id()
    repo_root = Path(repo_path).resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"repo_path does not exist: {repo_root}")
    results_file = (repo_root / results_path).resolve() if results_path is not None else repo_root / "results.tsv"
    resolved_repo_url = repo_url or _resolve_repo_url(repo_root)
    log_root_path = Path(log_root)
    log_root_path.mkdir(parents=True, exist_ok=True)
    artifact_root_path = Path(artifact_root)
    artifact_root_path.mkdir(parents=True, exist_ok=True)
    resolved_run_command_fn = run_command_fn or _run_runner_command

    api = HttpResearchOSApi(normalized_base_url)
    effort = _ensure_effort(api, base_url=normalized_base_url)
    deadline = monotonic_fn() + window_seconds
    total_runner_seconds = 0.0
    iterations: list[OvernightWorkerIteration] = []
    stop_reason = "window_end"
    loop_index = 0

    while True:
        if max_loops is not None and loop_index >= max_loops:
            stop_reason = "max_loops_reached"
            break
        if loop_index > 0 and monotonic_fn() >= deadline:
            stop_reason = "window_elapsed"
            break
        if budget_cap_seconds is not None and total_runner_seconds >= budget_cap_seconds:
            stop_reason = "budget_cap_reached"
            break

        remaining_window_seconds = max(1, int(deadline - monotonic_fn()))
        remaining_budget_seconds = (
            max(1, int(budget_cap_seconds - total_runner_seconds))
            if budget_cap_seconds is not None
            else command_timeout_seconds
        )
        timeout_seconds = min(command_timeout_seconds, remaining_window_seconds, remaining_budget_seconds)

        loop_index += 1
        log_path = log_root_path / f"loop-{loop_index:03d}.log"
        command_result = resolved_run_command_fn(runner_command, repo_root, timeout_seconds, log_path)
        total_runner_seconds += command_result.duration_seconds

        if not results_file.exists():
            iterations.append(
                OvernightWorkerIteration(
                    index=loop_index,
                    runner_status=command_result.status,
                    duration_seconds=command_result.duration_seconds,
                    exit_code=command_result.exit_code,
                    imported_candidate_commit=None,
                    imported_baseline_commit=None,
                    workspace_id=None,
                    claim_id=None,
                    discussion_url=None,
                    adoption_event_id=None,
                    note=f"results.tsv not found at `{results_file}` after the runner command",
                    log_path=str(command_result.log_path),
                )
            )
            stop_reason = "missing_results_tsv"
            break

        workspaces = api.list_workspaces(effort_id=str(effort["effort_id"]))
        results = load_results_tsv(results_file)
        keep_pair = _next_keep_pair(results, imported_candidate_commits=_imported_candidate_commits(workspaces))

        imported_contribution: ImportedContribution | None = None
        adoption_event_id: str | None = None
        note: str
        if keep_pair is None:
            note = "No new kept external-harness result was available to import after this loop."
        else:
            baseline, candidate = keep_pair
            imported_contribution = _import_contribution(
                api,
                effort_id=str(effort["effort_id"]),
                actor_id=resolved_actor_id,
                workspace_name="mlx-history-worker",
                baseline=baseline,
                candidate=candidate,
                repo_url=resolved_repo_url,
                artifact_root=artifact_root_path / "mlx-history-worker",
                workspace_tags={
                    "worker_mode": "overnight-autoresearch",
                    "worker_window": "true",
                },
                event_tags={
                    "worker_mode": "overnight-autoresearch",
                    "worker_window": "true",
                },
            )
            prior_reference = _find_contribution_reference(
                api.list_workspaces(effort_id=str(effort["effort_id"])),
                candidate_commit=baseline.commit,
            )
            if prior_reference is not None and prior_reference.workspace_id != imported_contribution.workspace_id:
                adoption_event_id = _record_adoption(
                    api,
                    from_contribution=prior_reference,
                    to_contribution=imported_contribution,
                )
            note = (
                f"Imported kept result `{candidate.commit}` over `{baseline.commit}` into shared state."
            )

        iterations.append(
            OvernightWorkerIteration(
                index=loop_index,
                runner_status=command_result.status,
                duration_seconds=command_result.duration_seconds,
                exit_code=command_result.exit_code,
                imported_candidate_commit=(
                    imported_contribution.candidate_commit if imported_contribution is not None else None
                ),
                imported_baseline_commit=(
                    imported_contribution.baseline_commit if imported_contribution is not None else None
                ),
                workspace_id=imported_contribution.workspace_id if imported_contribution is not None else None,
                claim_id=imported_contribution.claim_id if imported_contribution is not None else None,
                discussion_url=(
                    _discussion_url(normalized_base_url, imported_contribution.workspace_id)
                    if imported_contribution is not None
                    else None
                ),
                adoption_event_id=adoption_event_id,
                note=note,
                log_path=str(command_result.log_path),
            )
        )

        if command_result.status == "failed":
            stop_reason = "runner_failed"
            break
        if command_result.status == "timed_out":
            stop_reason = "runner_timed_out"
            break
        if budget_cap_seconds is not None and total_runner_seconds >= budget_cap_seconds:
            stop_reason = "budget_cap_reached"
            break
        if max_loops is not None and loop_index >= max_loops:
            stop_reason = "max_loops_reached"
            break
        remaining_seconds = deadline - monotonic_fn()
        if remaining_seconds <= 0:
            stop_reason = "window_elapsed"
            break
        if interval_seconds > 0:
            sleep_fn(min(interval_seconds, remaining_seconds))

    workspaces = api.list_workspaces(effort_id=str(effort["effort_id"]))
    claims = _get_json(
        f"{normalized_base_url}/api/v1/claims?objective={EFFORT_OBJECTIVE}&platform={EFFORT_PLATFORM}"
    )
    effort_workspace_ids = {workspace["workspace_id"] for workspace in workspaces}
    effort_claim_count = sum(1 for claim in claims if claim.get("workspace_id") in effort_workspace_ids)
    frontier = _get_json(
        f"{normalized_base_url}/api/v1/frontiers/{EFFORT_OBJECTIVE}/{EFFORT_PLATFORM}"
        f"?budget_seconds={EFFORT_BUDGET_SECONDS}"
    )

    return OvernightWorkerResult(
        actor_id=resolved_actor_id,
        base_url=normalized_base_url,
        site_url=normalized_site_url,
        repo_path=str(repo_root),
        repo_url=resolved_repo_url,
        runner_command=runner_command,
        effort_id=str(effort["effort_id"]),
        effort_name=str(effort["name"]),
        window_seconds=window_seconds,
        interval_seconds=interval_seconds,
        max_loops=max_loops,
        command_timeout_seconds=command_timeout_seconds,
        budget_cap_seconds=budget_cap_seconds,
        loops_completed=len(iterations),
        imported_iterations=sum(1 for iteration in iterations if iteration.workspace_id is not None),
        total_runner_seconds=total_runner_seconds,
        stop_reason=stop_reason,
        iterations=iterations,
        effort_workspace_count=len(workspaces),
        effort_claim_count=effort_claim_count,
        frontier_member_count=len(frontier["members"]),
    )


def build_overnight_worker_report(result: OvernightWorkerResult) -> str:
    effort_url = f"{result.site_url}/efforts/{result.effort_id}"
    iteration_lines = [
        _render_iteration_line(iteration)
        for iteration in result.iterations
    ] or ["- none"]
    latest_handoff = next(
        (iteration.discussion_url for iteration in reversed(result.iterations) if iteration.discussion_url is not None),
        None,
    )
    return "\n".join(
        [
            "# Overnight Autoresearch Worker",
            "",
            "## Worker",
            f"- Actor: `{result.actor_id}`",
            f"- Effort: `{result.effort_name}` (`{result.effort_id}`)",
            f"- Repo path: `{result.repo_path}`",
            f"- Repo URL: `{result.repo_url}`",
            f"- Runner command: `{result.runner_command}`",
            f"- Window seconds: `{result.window_seconds}`",
            f"- Interval seconds: `{result.interval_seconds}`",
            f"- Command timeout seconds: `{result.command_timeout_seconds}`",
            f"- Budget cap seconds: `{result.budget_cap_seconds if result.budget_cap_seconds is not None else 'none'}`",
            f"- Max loops: `{result.max_loops if result.max_loops is not None else 'until window ends'}`",
            f"- Live effort page: `{effort_url}`",
            "",
            "## Outcome",
            f"- Loops completed: `{result.loops_completed}`",
            f"- Imported iterations: `{result.imported_iterations}`",
            f"- Total runner seconds: `{result.total_runner_seconds:.2f}`",
            f"- Stop reason: `{result.stop_reason}`",
            "",
            "## Iterations",
            *iteration_lines,
            "",
            "## Live Evidence After This Window",
            f"- Workspaces in effort: `{result.effort_workspace_count}`",
            f"- Claims in effort scope: `{result.effort_claim_count}`",
            f"- Frontier members: `{result.frontier_member_count}`",
            "",
            "## Handoff",
            f"- Live effort page: `{effort_url}`",
            f"- Latest discussion: `{latest_handoff or 'n/a'}`",
            "- Hand the live effort page or the latest discussion to the next human or agent.",
            "",
            "## Honesty Line",
            "- This is the advanced path: it runs a real external command against a local repo and only imports kept results.",
            "- It is still one machine under one operator. It is not a mesh worker network.",
            "- The seeded eval and inference nightly path remains the cheaper proxy contribution window.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a bounded overnight autoresearch worker against the live OpenIntention API."
    )
    parser.add_argument("--repo-path", required=True, help="Path to the local external-harness repo.")
    parser.add_argument(
        "--runner-command",
        required=True,
        help="Command to execute inside the repo each iteration before importing any newly kept results.",
    )
    parser.add_argument(
        "--actor-id",
        default=None,
        help="Optional lightweight public handle to attach to imported workspaces and events.",
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
        "--repo-url",
        default=None,
        help="Canonical repo URL for the external harness. Defaults to the git remote origin when available.",
    )
    parser.add_argument(
        "--results-path",
        default=None,
        help="Optional relative path to results.tsv inside the repo. Defaults to <repo>/results.tsv.",
    )
    parser.add_argument(
        "--window-seconds",
        type=int,
        default=DEFAULT_WINDOW_SECONDS,
        help="How long the worker window should stay active.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Pause between worker iterations.",
    )
    parser.add_argument(
        "--max-loops",
        type=int,
        default=None,
        help="Optional hard cap on worker iterations.",
    )
    parser.add_argument(
        "--command-timeout-seconds",
        type=int,
        default=DEFAULT_COMMAND_TIMEOUT_SECONDS,
        help="Per-iteration timeout for the external command.",
    )
    parser.add_argument(
        "--budget-cap-seconds",
        type=int,
        default=DEFAULT_BUDGET_CAP_SECONDS,
        help="Hard cap on cumulative external command runtime across the worker window.",
    )
    parser.add_argument(
        "--artifact-root",
        default="data/client-artifacts/overnight-worker",
        help="Directory for local content-addressed worker artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/overnight-autoresearch-worker",
        help="Directory to write the overnight worker report into.",
    )
    args = parser.parse_args()

    report_path = run_overnight_autoresearch_worker(
        base_url=args.base_url,
        site_url=args.site_url,
        repo_path=args.repo_path,
        runner_command=args.runner_command,
        actor_id=args.actor_id,
        window_seconds=args.window_seconds,
        interval_seconds=args.interval_seconds,
        max_loops=args.max_loops,
        command_timeout_seconds=args.command_timeout_seconds,
        budget_cap_seconds=args.budget_cap_seconds,
        artifact_root=args.artifact_root,
        output_dir=args.output_dir,
        repo_url=args.repo_url,
        results_path=args.results_path,
    )
    print(report_path)


def _render_iteration_line(iteration: OvernightWorkerIteration) -> str:
    imported_segment = "no shared import"
    if iteration.workspace_id is not None and iteration.claim_id is not None:
        imported_segment = (
            f"imported `{iteration.imported_candidate_commit}` over `{iteration.imported_baseline_commit}` "
            f"into workspace `{iteration.workspace_id}` / claim `{iteration.claim_id}`"
        )
    handoff_segment = f", discussion `{iteration.discussion_url}`" if iteration.discussion_url is not None else ""
    adoption_segment = f", adoption `{iteration.adoption_event_id}`" if iteration.adoption_event_id is not None else ""
    exit_segment = f", exit `{iteration.exit_code}`" if iteration.exit_code is not None else ""
    return (
        f"- loop {iteration.index}: runner `{iteration.runner_status}`{exit_segment}, "
        f"duration `{iteration.duration_seconds:.2f}s`, {imported_segment}{handoff_segment}{adoption_segment}, "
        f"log `{iteration.log_path}`. {iteration.note}"
    )


def _next_keep_pair(
    results: list[MlxHistoryResult],
    *,
    imported_candidate_commits: set[str],
) -> tuple[MlxHistoryResult, MlxHistoryResult] | None:
    kept_results = [result for result in results if result.status == "keep"]
    for baseline, candidate in zip(kept_results, kept_results[1:]):
        if candidate.commit not in imported_candidate_commits:
            return baseline, candidate
    return None


def _imported_candidate_commits(workspaces: list[dict[str, object]]) -> set[str]:
    imported: set[str] = set()
    for workspace in workspaces:
        tags = workspace.get("tags")
        if not isinstance(tags, dict):
            continue
        if tags.get("external_harness") != "mlx-history" and "candidate_commit" not in tags:
            continue
        candidate_commit = tags.get("candidate_commit")
        if isinstance(candidate_commit, str) and candidate_commit:
            imported.add(candidate_commit)
            continue
        name = workspace.get("name")
        if isinstance(name, str) and "-" in name:
            imported.add(name.rsplit("-", maxsplit=1)[-1])
    return imported


def _find_contribution_reference(
    workspaces: list[dict[str, object]],
    *,
    candidate_commit: str,
) -> ContributionReference | None:
    for workspace in workspaces:
        tags = workspace.get("tags")
        if isinstance(tags, dict) and tags.get("external_harness") not in {None, "mlx-history"}:
            continue
        tag_commit = tags.get("candidate_commit") if isinstance(tags, dict) else None
        name = workspace.get("name")
        name_commit = name.rsplit("-", maxsplit=1)[-1] if isinstance(name, str) and "-" in name else None
        if candidate_commit not in {tag_commit, name_commit}:
            continue
        workspace_id = str(workspace["workspace_id"])
        actor_id = str(workspace.get("actor_id") or "unknown")
        claim_ids = workspace.get("claim_ids")
        claim_id = None
        if isinstance(claim_ids, list) and claim_ids:
            first_claim = claim_ids[0]
            if isinstance(first_claim, str):
                claim_id = first_claim
        if claim_id is None:
            claim_id = f"{workspace_id.split('-', maxsplit=1)[0]}-claim-{candidate_commit}"
        return ContributionReference(
            actor_id=actor_id,
            workspace_id=workspace_id,
            claim_id=claim_id,
            candidate_commit=candidate_commit,
        )
    return None


def _run_runner_command(command: str, cwd: Path, timeout_seconds: int, log_path: Path) -> RunnerCommandResult:
    started_at = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            executable="/bin/bash",
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_seconds,
        )
        duration_seconds = time.monotonic() - started_at
        output = completed.stdout or ""
        log_path.write_text(output, encoding="utf-8")
        return RunnerCommandResult(
            status="success" if completed.returncode == 0 else "failed",
            duration_seconds=duration_seconds,
            exit_code=completed.returncode,
            output=output,
            log_path=str(log_path),
        )
    except subprocess.TimeoutExpired as exc:
        duration_seconds = time.monotonic() - started_at
        output = (exc.stdout or "") + (exc.stderr or "")
        log_path.write_text(output, encoding="utf-8")
        return RunnerCommandResult(
            status="timed_out",
            duration_seconds=duration_seconds,
            exit_code=None,
            output=output,
            log_path=str(log_path),
        )


def _resolve_repo_url(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return DEFAULT_REPO_URL
    resolved = completed.stdout.strip()
    return resolved or DEFAULT_REPO_URL


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
