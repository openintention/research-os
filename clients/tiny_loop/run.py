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
    args = parser.parse_args()

    result = run_tiny_loop_experiment(
        HttpResearchOSApi(args.base_url),
        artifact_root=Path(args.artifact_root),
        profile=PROFILES[args.profile],
    )
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
