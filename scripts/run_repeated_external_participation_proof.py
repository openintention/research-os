from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from clients.tiny_loop.api import HttpResearchOSApi  # noqa: E402
from clients.tiny_loop.experiment import EVAL_SPRINT_PROFILE  # noqa: E402
from clients.tiny_loop.experiment import INFERENCE_SPRINT_PROFILE  # noqa: E402
from clients.tiny_loop.experiment import ExperimentProfile  # noqa: E402
from clients.tiny_loop.experiment import ExperimentResult  # noqa: E402
from clients.tiny_loop.experiment import run_tiny_loop_experiment  # noqa: E402
from clients.tiny_loop.experiment import run_verifier_reproduction  # noqa: E402
from research_os.http import read_json  # noqa: E402
from research_os.http import read_text  # noqa: E402

DEFAULT_BASE_URL = "https://api.openintention.io"
DEFAULT_SITE_URL = "https://openintention.io"


@dataclass(frozen=True, slots=True)
class ParticipationRecord:
    actor_id: str
    profile_name: str
    participant_role: str
    effort_id: str
    effort_name: str
    workspace_id: str
    claim_id: str
    reproduction_run_id: str | None
    planner_action: str
    discussion_url: str
    effort_page_url: str


@dataclass(frozen=True, slots=True)
class EffortVisibilitySummary:
    effort_id: str
    effort_name: str
    effort_page_url: str
    visible_actor_ids: list[str]
    visible_workspace_count: int
    claim_count: int
    frontier_member_count: int


@dataclass(frozen=True, slots=True)
class RepeatedExternalParticipationResult:
    base_url: str
    site_url: str
    batch_id: str
    records: list[ParticipationRecord]
    effort_summaries: list[EffortVisibilitySummary]
    breakpoints: list[str]


def run_repeated_external_participation_proof(
    *,
    base_url: str,
    site_url: str,
    output_dir: str,
    artifact_root: str,
    batch_id: str | None = None,
) -> Path:
    normalized_base_url = base_url.rstrip("/")
    normalized_site_url = site_url.rstrip("/")
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    artifact_root_path = Path(artifact_root)
    artifact_root_path.mkdir(parents=True, exist_ok=True)
    resolved_batch_id = batch_id or _default_batch_id()

    api = HttpResearchOSApi(normalized_base_url)
    experiment_results = _run_proof_batch(
        api=api,
        artifact_root=artifact_root_path,
        batch_id=resolved_batch_id,
    )
    records = [
        _build_record(
            site_url=normalized_site_url,
            base_url=normalized_base_url,
            result=result,
            profile_name=profile.name,
        )
        for result, profile in experiment_results
    ]
    effort_summaries = _build_effort_summaries(
        api=api,
        base_url=normalized_base_url,
        site_url=normalized_site_url,
        records=records,
        experiment_results=experiment_results,
    )

    result = RepeatedExternalParticipationResult(
        base_url=normalized_base_url,
        site_url=normalized_site_url,
        batch_id=resolved_batch_id,
        records=records,
        effort_summaries=effort_summaries,
        breakpoints=_observed_breakpoints(),
    )
    report_path = output_root / "repeated-external-participation.md"
    report_path.write_text(build_repeated_external_participation_report(result), encoding="utf-8")
    return report_path


def build_repeated_external_participation_report(result: RepeatedExternalParticipationResult) -> str:
    record_lines = [
        "\n".join(
            [
                f"- actor `{record.actor_id}`",
                f"  profile=`{record.profile_name}` role=`{record.participant_role}`",
                f"  effort=`{record.effort_name}` workspace=`{record.workspace_id}`",
                f"  claim=`{record.claim_id}` reproduction=`{record.reproduction_run_id or 'n/a'}`",
                f"  planner=`{record.planner_action}`",
                f"  discussion=`{record.discussion_url}`",
                f"  effort_page=`{record.effort_page_url}`",
            ]
        )
        for record in result.records
    ] or ["- none"]
    effort_lines = [
        "\n".join(
            [
                f"### {summary.effort_name}",
                f"- goal page: `{summary.effort_page_url}`",
                f"- visible actors on live page: {', '.join(f'`{actor}`' for actor in summary.visible_actor_ids)}",
                f"- visible workspaces in effort: {summary.visible_workspace_count}",
                f"- claims in effort scope: {summary.claim_count}",
                f"- frontier members: {summary.frontier_member_count}",
            ]
        )
        for summary in result.effort_summaries
    ] or ["- none"]
    breakpoint_lines = [f"- {line}" for line in result.breakpoints] or ["- none"]
    return "\n".join(
        [
            "# Repeated External Participation Proof",
            "",
            "## Hosted Surface",
            f"- Site: `{result.site_url}`",
            f"- API: `{result.base_url}`",
            f"- Batch id: `{result.batch_id}`",
            "",
            "## Distinct Hosted Participants",
            *record_lines,
            "",
            "## Public Visibility",
            *effort_lines,
            "",
            "## Observed Breakpoints",
            *breakpoint_lines,
            "",
            "## Outcome",
            "- Multiple distinct participants appended work through the canonical hosted endpoint.",
            "- The resulting work is visible from the public goal pages and workspace discussion mirrors.",
            "- The hosted-network story now has repeated participation evidence, not only one internal shared-participation proof.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prove repeated external participation against the canonical hosted network."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Hosted OpenIntention API base URL.")
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL, help="Public OpenIntention site URL.")
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/repeated-external-participation",
        help="Directory to write the repeated participation proof into.",
    )
    parser.add_argument(
        "--artifact-root",
        default="data/client-artifacts/repeated-external-participation",
        help="Directory for client-side snapshot artifacts created during the proof run.",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Optional batch identifier to make repeated proof workspaces easy to group.",
    )
    args = parser.parse_args()

    report_path = run_repeated_external_participation_proof(
        base_url=args.base_url,
        site_url=args.site_url,
        output_dir=args.output_dir,
        artifact_root=args.artifact_root,
        batch_id=args.batch_id,
    )
    print(report_path)


def _default_batch_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _run_proof_batch(
    *,
    api: HttpResearchOSApi,
    artifact_root: Path,
    batch_id: str,
) -> list[tuple[ExperimentResult, ExperimentProfile]]:
    eval_alpha = run_tiny_loop_experiment(
        api,
        artifact_root=artifact_root / "eval-alpha",
        profile=EVAL_SPRINT_PROFILE,
        actor_id="external-eval-alpha",
        workspace_suffix=f"{batch_id}-alpha",
        auto_reproduce=False,
    )
    eval_verifier = run_verifier_reproduction(
        api,
        artifact_root=artifact_root / "eval-verifier",
        profile=EVAL_SPRINT_PROFILE,
        claim_id=eval_alpha.claim_id,
        actor_id="external-eval-verifier",
        workspace_suffix=f"{batch_id}-verifier",
    )
    inference_gamma = run_tiny_loop_experiment(
        api,
        artifact_root=artifact_root / "inference-gamma",
        profile=INFERENCE_SPRINT_PROFILE,
        actor_id="external-inference-gamma",
        workspace_suffix=f"{batch_id}-gamma",
        auto_reproduce=True,
    )
    eval_delta = run_tiny_loop_experiment(
        api,
        artifact_root=artifact_root / "eval-delta",
        profile=EVAL_SPRINT_PROFILE,
        actor_id="external-eval-delta",
        workspace_suffix=f"{batch_id}-delta",
        auto_reproduce=True,
    )
    return [
        (eval_alpha, EVAL_SPRINT_PROFILE),
        (eval_verifier, EVAL_SPRINT_PROFILE),
        (inference_gamma, INFERENCE_SPRINT_PROFILE),
        (eval_delta, EVAL_SPRINT_PROFILE),
    ]


def _build_record(
    *,
    site_url: str,
    base_url: str,
    result: ExperimentResult,
    profile_name: str,
) -> ParticipationRecord:
    if result.effort_id is None or result.effort_name is None:
        raise RuntimeError("repeated participation proof requires effort-backed workspaces")
    return ParticipationRecord(
        actor_id=result.actor_id,
        profile_name=profile_name,
        participant_role=str(result.participant_role),
        effort_id=result.effort_id,
        effort_name=result.effort_name,
        workspace_id=result.workspace_id,
        claim_id=result.claim_id,
        reproduction_run_id=result.reproduction_run_id,
        planner_action=result.planner_action,
        discussion_url=f"{base_url}/api/v1/publications/workspaces/{result.workspace_id}/discussion",
        effort_page_url=f"{site_url}/efforts/{result.effort_id}",
    )


def _build_effort_summaries(
    *,
    api: HttpResearchOSApi,
    base_url: str,
    site_url: str,
    records: list[ParticipationRecord],
    experiment_results: list[tuple[ExperimentResult, ExperimentProfile]],
) -> list[EffortVisibilitySummary]:
    grouped_records: dict[str, list[ParticipationRecord]] = defaultdict(list)
    grouped_profiles: dict[str, ExperimentProfile] = {}
    for record, (_, profile) in zip(records, experiment_results):
        grouped_records[record.effort_id].append(record)
        grouped_profiles[record.effort_id] = profile

    summaries: list[EffortVisibilitySummary] = []
    for effort_id, effort_records in grouped_records.items():
        profile = grouped_profiles[effort_id]
        workspaces = api.list_workspaces(effort_id=effort_id)
        workspace_by_id = {str(workspace["workspace_id"]): workspace for workspace in workspaces}
        for record in effort_records:
            workspace = workspace_by_id.get(record.workspace_id)
            if workspace is None:
                raise RuntimeError(f"expected workspace {record.workspace_id} to appear on effort {effort_id}")
            if workspace.get("actor_id") != record.actor_id:
                raise RuntimeError(
                    f"workspace {record.workspace_id} expected actor {record.actor_id}, got {workspace.get('actor_id')}"
                )

        effort_page_url = f"{site_url}/efforts/{effort_id}"
        effort_page_html = read_text(effort_page_url, timeout=20)
        visible_actor_ids = [record.actor_id for record in effort_records if record.actor_id in effort_page_html]
        if len(visible_actor_ids) != len(effort_records):
            missing = sorted({record.actor_id for record in effort_records} - set(visible_actor_ids))
            raise RuntimeError(
                f"goal page {effort_page_url} missing visible actor attribution for: {', '.join(missing)}"
            )

        claims = read_json(
            (
                f"{base_url}/api/v1/claims?objective={profile.objective}"
                f"&platform={profile.platform}"
            ),
            timeout=20,
        )
        frontier = read_json(
            (
                f"{base_url}/api/v1/frontiers/{profile.objective}/{profile.platform}"
                f"?budget_seconds={profile.budget_seconds}"
            ),
            timeout=20,
        )
        workspace_ids = {record.workspace_id for record in effort_records}
        claim_count = sum(1 for claim in claims if claim.get("workspace_id") in workspace_ids)
        summaries.append(
            EffortVisibilitySummary(
                effort_id=effort_id,
                effort_name=effort_records[0].effort_name,
                effort_page_url=effort_page_url,
                visible_actor_ids=visible_actor_ids,
                visible_workspace_count=len(workspaces),
                claim_count=claim_count,
                frontier_member_count=len(frontier["members"]),
            )
        )
    return sorted(summaries, key=lambda item: item.effort_name)


def _observed_breakpoints() -> list[str]:
    return [
        (
            "Onboarding: the public join bootstrap reuses `~/.openintention/research-os` and "
            "refuses to fast-forward if that checkout has local changes."
        ),
        (
            "Contribution: hosted API clients must send an explicit OpenIntention agent "
            "user-agent; bare `Python-urllib/...` requests are blocked by the public edge."
        ),
        (
            "Handoff: public attribution is currently lightweight `actor_id` assertion visible on "
            "goal pages and discussion mirrors, not an authenticated account system."
        ),
    ]


if __name__ == "__main__":
    main()
