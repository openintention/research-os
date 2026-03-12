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
from research_os.domain.models import EventKind  # noqa: E402
from research_os.integrations.mlx_history import (  # noqa: E402
    MlxHistoryResult,
    commit_url,
    load_results_tsv,
)

EFFORT_NAME = "MLX History Sprint: improve val_bpb on Apple Silicon"
EFFORT_OBJECTIVE = "val_bpb"
EFFORT_PLATFORM = "Apple-Silicon-MLX"
EFFORT_BUDGET_SECONDS = 300
EFFORT_SUMMARY = (
    "Shared MLX history effort for compounding Apple Silicon val_bpb improvements "
    "through adoption, continuation, and visible frontier progress."
)
DEFAULT_REPO_URL = "https://github.com/example/mlx-history"


@dataclass(frozen=True, slots=True)
class ImportedContribution:
    actor_id: str
    workspace_id: str
    workspace_name: str
    baseline_commit: str
    candidate_commit: str
    claim_id: str
    run_id: str
    metric_value: float
    delta: float


@dataclass(frozen=True, slots=True)
class CompoundingMlxHistoryResult:
    base_url: str
    effort_id: str
    effort_name: str
    alpha: ImportedContribution
    beta: ImportedContribution
    adoption_event_id: str
    workspace_ids: list[str]
    claim_ids: list[str]
    frontier_member_count: int
    planner_action: str
    planner_reason: str
    planner_inputs: dict[str, object]
    effort_overview_excerpt: str


def run_mlx_history_compounding_smoke(
    *,
    base_url: str,
    repo_path: str,
    output_dir: str,
    repo_url: str = DEFAULT_REPO_URL,
) -> Path:
    normalized_base_url = base_url.rstrip("/")
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    api = HttpResearchOSApi(normalized_base_url)
    effort = _ensure_effort(api, base_url=normalized_base_url)

    results = load_results_tsv(Path(repo_path) / "results.tsv")
    baseline = _require_commit(results, "383abb4")
    alpha_result = _require_commit(results, "4161af3")
    beta_result = _require_commit(results, "5efc7aa")

    alpha = _import_contribution(
        api,
        effort_id=effort["effort_id"],
        actor_id="mlx-alpha",
        workspace_name="mlx-history-alpha",
        baseline=baseline,
        candidate=alpha_result,
        repo_url=repo_url,
    )
    beta = _import_contribution(
        api,
        effort_id=effort["effort_id"],
        actor_id="mlx-beta",
        workspace_name="mlx-history-beta",
        baseline=alpha_result,
        candidate=beta_result,
        repo_url=repo_url,
    )
    adoption_event_id = _record_adoption(api, from_contribution=alpha, to_contribution=beta)

    workspaces = api.list_workspaces(effort_id=effort["effort_id"])
    claims = _get_json(
        f"{normalized_base_url}/api/v1/claims?objective={EFFORT_OBJECTIVE}&platform={EFFORT_PLATFORM}"
    )
    frontier = _get_json(
        f"{normalized_base_url}/api/v1/frontiers/{EFFORT_OBJECTIVE}/{EFFORT_PLATFORM}"
        f"?budget_seconds={EFFORT_BUDGET_SECONDS}"
    )
    publication = api.get_effort_overview(effort["effort_id"])
    planner = api.recommend_next(
        {
            "objective": EFFORT_OBJECTIVE,
            "platform": EFFORT_PLATFORM,
            "budget_seconds": EFFORT_BUDGET_SECONDS,
            "workspace_id": beta.workspace_id,
            "limit": 1,
        }
    )
    recommendation = planner["recommendations"][0]

    result = CompoundingMlxHistoryResult(
        base_url=normalized_base_url,
        effort_id=effort["effort_id"],
        effort_name=effort["name"],
        alpha=alpha,
        beta=beta,
        adoption_event_id=adoption_event_id,
        workspace_ids=[workspace["workspace_id"] for workspace in workspaces],
        claim_ids=[claim["claim_id"] for claim in claims],
        frontier_member_count=len(frontier["members"]),
        planner_action=recommendation["action"],
        planner_reason=recommendation["reason"],
        planner_inputs=recommendation["inputs"],
        effort_overview_excerpt=_excerpt(publication["body"], lines=28),
    )

    report_path = output_root / "mlx-history-compounding-smoke.md"
    report_path.write_text(build_compounding_report(result), encoding="utf-8")
    return report_path


def build_compounding_report(result: CompoundingMlxHistoryResult) -> str:
    workspace_lines = [f"- `{workspace_id}`" for workspace_id in result.workspace_ids] or ["- none"]
    claim_lines = [f"- `{claim_id}`" for claim_id in result.claim_ids] or ["- none"]
    return "\n".join(
        [
            "# MLX History Compounding Smoke Report",
            "",
            "## Shared Control Plane",
            f"- Base URL: `{result.base_url}`",
            f"- Effort: `{result.effort_name}` (`{result.effort_id}`)",
            "",
            "## Contribution Chain",
            (
                f"- `mlx-alpha` imported `{result.alpha.candidate_commit}` "
                f"over `{result.alpha.baseline_commit}` "
                f"(workspace `{result.alpha.workspace_id}`, claim `{result.alpha.claim_id}`, "
                f"delta `{result.alpha.delta:.6f}`)"
            ),
            (
                f"- `mlx-beta` adopted `{result.alpha.claim_id}` and advanced to "
                f"`{result.beta.candidate_commit}` over `{result.beta.baseline_commit}` "
                f"(workspace `{result.beta.workspace_id}`, claim `{result.beta.claim_id}`, "
                f"delta `{result.beta.delta:.6f}`)"
            ),
            f"- Adoption event: `{result.adoption_event_id}`",
            "",
            "## Shared State After Compounding",
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
            "## Planner Next Step",
            f"- Action: `{result.planner_action}`",
            f"- Reason: {result.planner_reason}",
            f"- Inputs: `{json.dumps(result.planner_inputs, sort_keys=True)}`",
            "",
            "## Outcome",
            "- A real external MLX history published into the shared control plane.",
            "- The later contribution explicitly adopted earlier visible work instead of landing as an isolated run.",
            "- The next participant can continue from the shared frontier, claims, and planner recommendation.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import MLX history into a shared effort and prove compounding continuation."
    )
    parser.add_argument("--base-url", required=True, help="Hosted API base URL for the shared control plane.")
    parser.add_argument("--repo-path", required=True, help="Path to a local clone of MLX history.")
    parser.add_argument(
        "--repo-url",
        default=DEFAULT_REPO_URL,
        help="Canonical upstream repo URL used to build artifact references.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/compounding-mlx-history",
        help="Directory to write the compounding proof markdown report into.",
    )
    args = parser.parse_args()

    report_path = run_mlx_history_compounding_smoke(
        base_url=args.base_url,
        repo_path=args.repo_path,
        repo_url=args.repo_url,
        output_dir=args.output_dir,
    )
    print(report_path)


def _ensure_effort(api: HttpResearchOSApi, *, base_url: str) -> dict[str, object]:
    efforts = api.list_efforts()
    effort = next((item for item in efforts if item["name"] == EFFORT_NAME), None)
    if effort is not None:
        return effort

    created = api.create_effort(
        {
            "name": EFFORT_NAME,
            "objective": EFFORT_OBJECTIVE,
            "platform": EFFORT_PLATFORM,
            "budget_seconds": EFFORT_BUDGET_SECONDS,
            "summary": EFFORT_SUMMARY,
            "actor_id": "openintention-pm",
            "tags": {
                "effort_type": "mlx_history",
                "external_harness": "mlx-history",
                "seeded": "true",
                "public_proof": "true",
                "proof_series": "mlx-history-apple-silicon-300",
                "proof_version": "1",
                "join_brief_path": "README.md#external-mlx-compounding-proof",
                "join_command": (
                    "python3 scripts/run_mlx_history_compounding_smoke.py "
                    f"--repo-path <path_to_mlx_history> --base-url {base_url}"
                ),
            },
        }
    )
    effort_id = created["effort_id"]
    return next(item for item in api.list_efforts() if item["effort_id"] == effort_id)


def _import_contribution(
    api: HttpResearchOSApi,
    *,
    effort_id: str,
    actor_id: str,
    workspace_name: str,
    baseline: MlxHistoryResult,
    candidate: MlxHistoryResult,
    repo_url: str,
) -> ImportedContribution:
    workspace_label = f"{workspace_name}-{candidate.commit}"
    if existing_workspace := _find_existing_workspace(
        api.list_workspaces(effort_id=effort_id),
        name=workspace_label,
        actor_id=actor_id,
    ):
        return _build_imported_contribution_from_workspace(
            existing_workspace,
            actor_id=actor_id,
            workspace_name=workspace_name,
            baseline=baseline,
            candidate=candidate,
        )

    workspace = api.create_workspace(
        {
            "name": workspace_label,
            "objective": EFFORT_OBJECTIVE,
            "platform": EFFORT_PLATFORM,
            "budget_seconds": EFFORT_BUDGET_SECONDS,
            "effort_id": effort_id,
            "description": (
                f"Imported MLX history result `{candidate.commit}` building on "
                f"`{baseline.commit}`."
            ),
            "tags": {"external_harness": "mlx-history", "imported": "true"},
            "actor_id": actor_id,
        }
    )
    workspace_id = workspace["workspace_id"]
    scope = workspace_id.split("-", maxsplit=1)[0]
    baseline_snapshot_id = f"{scope}-snap-{baseline.commit}"
    candidate_snapshot_id = f"{scope}-snap-{candidate.commit}"
    run_id = f"{scope}-run-{candidate.commit}"
    claim_id = f"{scope}-claim-{candidate.commit}"

    api.append_event(
        {
            "kind": EventKind.SNAPSHOT_PUBLISHED,
            "workspace_id": workspace_id,
            "aggregate_id": baseline_snapshot_id,
            "aggregate_kind": "snapshot",
            "actor_id": actor_id,
            "payload": {
                "snapshot_id": baseline_snapshot_id,
                "parent_snapshot_ids": [],
                "artifact_uri": commit_url(repo_url, baseline.commit),
                "source_bundle_digest": baseline.commit,
                "git_ref": baseline.commit,
                "notes": baseline.description,
            },
            "tags": {"external_harness": "mlx-history", "commit": baseline.commit},
        }
    )
    api.append_event(
        {
            "kind": EventKind.SNAPSHOT_PUBLISHED,
            "workspace_id": workspace_id,
            "aggregate_id": candidate_snapshot_id,
            "aggregate_kind": "snapshot",
            "actor_id": actor_id,
            "payload": {
                "snapshot_id": candidate_snapshot_id,
                "parent_snapshot_ids": [baseline_snapshot_id],
                "artifact_uri": commit_url(repo_url, candidate.commit),
                "source_bundle_digest": candidate.commit,
                "git_ref": candidate.commit,
                "notes": candidate.description,
            },
            "tags": {"external_harness": "mlx-history", "commit": candidate.commit},
        }
    )
    api.append_event(
        {
            "kind": EventKind.RUN_COMPLETED,
            "workspace_id": workspace_id,
            "aggregate_id": run_id,
            "aggregate_kind": "run",
            "actor_id": actor_id,
            "payload": {
                "run_id": run_id,
                "snapshot_id": candidate_snapshot_id,
                "objective": EFFORT_OBJECTIVE,
                "platform": EFFORT_PLATFORM,
                "budget_seconds": EFFORT_BUDGET_SECONDS,
                "metric_name": "val_bpb",
                "metric_value": candidate.val_bpb,
                "direction": "min",
                "status": "success",
                "memory_gb": candidate.memory_gb,
                "external_harness": "mlx-history",
                "description": candidate.description,
            },
            "tags": {"external_harness": "mlx-history", "commit": candidate.commit},
        }
    )
    api.append_event(
        {
            "kind": EventKind.CLAIM_ASSERTED,
            "workspace_id": workspace_id,
            "aggregate_id": claim_id,
            "aggregate_kind": "claim",
            "actor_id": actor_id,
            "payload": {
                "claim_id": claim_id,
                "statement": (
                    f"`{candidate.description}` improved val_bpb from "
                    f"{baseline.val_bpb:.6f} to {candidate.val_bpb:.6f} on MLX history."
                ),
                "claim_type": "improvement",
                "candidate_snapshot_id": candidate_snapshot_id,
                "baseline_snapshot_id": baseline_snapshot_id,
                "objective": EFFORT_OBJECTIVE,
                "platform": EFFORT_PLATFORM,
                "metric_name": "val_bpb",
                "delta": candidate.val_bpb - baseline.val_bpb,
                "confidence": 0.7,
                "evidence_run_ids": [run_id],
            },
            "tags": {"external_harness": "mlx-history", "commit": candidate.commit},
        }
    )

    return ImportedContribution(
        actor_id=actor_id,
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        baseline_commit=baseline.commit,
        candidate_commit=candidate.commit,
        claim_id=claim_id,
        run_id=run_id,
        metric_value=candidate.val_bpb,
        delta=candidate.val_bpb - baseline.val_bpb,
    )


def _record_adoption(
    api: HttpResearchOSApi,
    *,
    from_contribution: ImportedContribution,
    to_contribution: ImportedContribution,
) -> str:
    event_id = f"{to_contribution.workspace_id.split('-', maxsplit=1)[0]}-adopt-{from_contribution.claim_id}"
    existing_events = _get_json(
        f"{api.base_url}/api/v1/events?workspace_id={to_contribution.workspace_id}"
        f"&kind={EventKind.ADOPTION_RECORDED.value}&limit=1000"
    )
    matching_event = next(
        (
            event
            for event in existing_events
            if event["payload"].get("subject_id") == from_contribution.claim_id
        ),
        None,
    )
    if matching_event is not None:
        return str(matching_event["event_id"])

    api.append_event(
        {
            "kind": EventKind.ADOPTION_RECORDED,
            "workspace_id": to_contribution.workspace_id,
            "aggregate_id": event_id,
            "aggregate_kind": "adoption",
            "actor_id": to_contribution.actor_id,
            "payload": {
                "subject_type": "claim",
                "subject_id": from_contribution.claim_id,
                "from_workspace_id": from_contribution.workspace_id,
                "reason": (
                    "Continue the MLX history line from the earlier kept improvement "
                    f"`{from_contribution.candidate_commit}`."
                ),
            },
            "tags": {"external_harness": "mlx-history", "adopted_claim": from_contribution.claim_id},
        }
    )
    return event_id


def _require_commit(results: list[MlxHistoryResult], commit: str) -> MlxHistoryResult:
    for result in results:
        if result.commit == commit:
            return result
    available = ", ".join(result.commit for result in results) or "none"
    raise RuntimeError(f"commit `{commit}` not found in results.tsv; available: {available}")


def _excerpt(body: str, *, lines: int) -> str:
    return "\n".join(body.splitlines()[:lines]).strip()


def _find_existing_workspace(
    workspaces: list[dict[str, object]],
    *,
    name: str,
    actor_id: str,
) -> dict[str, object] | None:
    return next(
        (
            workspace
            for workspace in workspaces
            if workspace.get("name") == name and workspace.get("actor_id") == actor_id
        ),
        None,
    )


def _build_imported_contribution_from_workspace(
    workspace: dict[str, object],
    *,
    actor_id: str,
    workspace_name: str,
    baseline: MlxHistoryResult,
    candidate: MlxHistoryResult,
) -> ImportedContribution:
    workspace_id = str(workspace["workspace_id"])
    scope = workspace_id.split("-", maxsplit=1)[0]
    return ImportedContribution(
        actor_id=actor_id,
        workspace_id=workspace_id,
        workspace_name=workspace_name,
        baseline_commit=baseline.commit,
        candidate_commit=candidate.commit,
        claim_id=f"{scope}-claim-{candidate.commit}",
        run_id=f"{scope}-run-{candidate.commit}",
        metric_value=candidate.val_bpb,
        delta=candidate.val_bpb - baseline.val_bpb,
    )


def _get_json(url: str) -> dict[str, object] | list[dict[str, object]]:
    with urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    main()
