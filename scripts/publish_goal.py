from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from clients.tiny_loop.api import HttpResearchOSApi


DEFAULT_BASE_URL = "https://api.openintention.io"
DEFAULT_SITE_URL = "https://openintention.io"


@dataclass(frozen=True, slots=True)
class PublishedGoalResult:
    effort_id: str
    bootstrap_event_id: str
    title: str
    objective: str
    metric_name: str
    direction: str
    platform: str
    budget_seconds: int
    author_id: str
    constraints: list[str]
    evidence_requirement: str
    stop_condition: str
    summary: str
    base_url: str
    site_url: str


def publish_goal(
    *,
    title: str,
    summary: str,
    objective: str,
    metric_name: str,
    direction: str,
    platform: str,
    budget_seconds: int,
    constraints: list[str],
    evidence_requirement: str,
    stop_condition: str,
    actor_id: str,
    base_url: str,
    site_url: str,
    output_dir: str,
) -> Path:
    api = HttpResearchOSApi(base_url)
    payload = {
        "title": title,
        "summary": summary,
        "objective": objective,
        "metric_name": metric_name,
        "direction": direction,
        "platform": platform,
        "budget_seconds": budget_seconds,
        "constraints": constraints,
        "evidence_requirement": evidence_requirement,
        "stop_condition": stop_condition,
        "actor_id": actor_id,
    }
    created = api.publish_goal(payload)
    report = build_publish_goal_report(
        PublishedGoalResult(
            effort_id=str(created["effort_id"]),
            bootstrap_event_id=str(created["bootstrap_event_id"]),
            title=title,
            objective=objective,
            metric_name=metric_name,
            direction=direction,
            platform=platform,
            budget_seconds=budget_seconds,
            author_id=actor_id,
            constraints=constraints,
            evidence_requirement=evidence_requirement,
            stop_condition=stop_condition,
            summary=summary,
            base_url=base_url,
            site_url=site_url,
        )
    )
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / "published-goal.md"
    report_path.write_text(report, encoding="utf-8")
    return report_path


def build_publish_goal_report(result: PublishedGoalResult) -> str:
    constraint_lines = [f"- Constraint: {item}" for item in result.constraints]
    goal_url = f"{result.site_url.rstrip('/')}/efforts/{result.effort_id}?published=1&author={result.author_id}"
    join_command = (
        f"curl -fsSL {result.site_url.rstrip('/')}/join | bash -s -- "
        f"--effort-id {result.effort_id} --actor-id <handle>"
    )
    return "\n".join(
        [
            "# Published Goal",
            "",
            "## Goal",
            f"- Title: `{result.title}`",
            f"- Objective: `{result.objective}`",
            f"- Metric: `{result.metric_name}`",
            f"- Direction: `{result.direction}`",
            f"- Platform: `{result.platform}`",
            f"- Budget seconds: `{result.budget_seconds}`",
            f"- Author: `{result.author_id}`",
            f"- Summary: {result.summary}",
            *constraint_lines,
            f"- Evidence requirement: {result.evidence_requirement}",
            f"- Stop condition: {result.stop_condition}",
            "",
            "## Publish Output",
            f"- Effort ID: `{result.effort_id}`",
            f"- Bootstrap event: `{result.bootstrap_event_id}`",
            f"- Live goal page: `{goal_url}`",
            "",
            "## Invite The Next Contributor",
            f"- Join command: `{join_command}`",
            "- Hand the live goal page or the join command to the next human or agent.",
            "",
            "## Honesty Line",
            "- User-authored goals are public and attributable only by lightweight asserted actor handle in v1.",
            "- The default join path for these published goals currently runs through the tiny-loop proxy contribution path.",
            "- Operator review may remove malformed or spam public goals.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a new public OpenIntention goal.")
    parser.add_argument("--title", required=True, help="Public goal title.")
    parser.add_argument("--summary", required=True, help="Short public summary of the goal.")
    parser.add_argument("--objective", required=True, help="Machine-facing objective key.")
    parser.add_argument("--metric-name", required=True, help="Metric shown to contributors.")
    parser.add_argument("--direction", choices=("min", "max"), required=True, help="Whether lower or higher is better.")
    parser.add_argument("--platform", required=True, help="Platform label for this goal.")
    parser.add_argument("--budget-seconds", type=int, default=300, help="Declared budget for one contribution run.")
    parser.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="Constraint line to attach to the goal. Repeat for multiple constraints.",
    )
    parser.add_argument("--evidence-requirement", required=True, help="What counts as acceptable evidence.")
    parser.add_argument("--stop-condition", required=True, help="When the goal should stop or be reconsidered.")
    parser.add_argument("--actor-id", required=True, help="Lightweight public author handle.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Hosted OpenIntention API base URL.")
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL, help="Public OpenIntention site URL.")
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/published-goal",
        help="Directory to write the published-goal report into.",
    )
    args = parser.parse_args()

    report_path = publish_goal(
        title=args.title,
        summary=args.summary,
        objective=args.objective,
        metric_name=args.metric_name,
        direction=args.direction,
        platform=args.platform,
        budget_seconds=args.budget_seconds,
        constraints=args.constraint,
        evidence_requirement=args.evidence_requirement,
        stop_condition=args.stop_condition,
        actor_id=args.actor_id,
        base_url=args.base_url,
        site_url=args.site_url,
        output_dir=args.output_dir,
    )
    print(report_path)


if __name__ == "__main__":
    main()
