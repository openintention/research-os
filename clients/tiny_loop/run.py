from __future__ import annotations

import argparse
from pathlib import Path

from clients.tiny_loop.api import HttpResearchOSApi
from clients.tiny_loop.experiment import EVAL_SPRINT_PROFILE, PROFILES, run_tiny_loop_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the tiny external ML loop against research-os.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for the research-os API.",
    )
    parser.add_argument(
        "--artifact-root",
        default="data/client-artifacts/tiny-loop",
        help="Directory for the client-side snapshot bundles.",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default=EVAL_SPRINT_PROFILE.name,
        help="Which client profile to run. The default targets the canonical seeded eval effort.",
    )
    parser.add_argument(
        "--actor-id",
        default=None,
        help="Optional lightweight participant handle to attach to the workspace and events.",
    )
    parser.add_argument(
        "--workspace-suffix",
        default=None,
        help="Optional suffix appended to the workspace name for repeated shared-effort runs.",
    )
    args = parser.parse_args()

    result = run_tiny_loop_experiment(
        HttpResearchOSApi(args.base_url),
        artifact_root=Path(args.artifact_root),
        profile=PROFILES[args.profile],
        actor_id=args.actor_id,
        workspace_suffix=args.workspace_suffix,
    )
    print(f"actor_id={result.actor_id}")
    print(f"participant_role={result.participant_role}")
    if result.effort_id is not None:
        print(f"effort_name={result.effort_name}")
        print(f"effort_id={result.effort_id}")
    print(f"workspace_id={result.workspace_id}")
    print(f"planner_action={result.planner_action}")
    print(f"claim_id={result.claim_id}")
    print(f"reproduction_run_id={result.reproduction_run_id}")
    print()
    print("discussion_markdown:")
    print(result.discussion_markdown)
    print()
    print("pull_request_markdown:")
    print(result.pull_request_markdown)


if __name__ == "__main__":
    main()
