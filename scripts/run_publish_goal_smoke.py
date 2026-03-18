from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from clients.tiny_loop.api import HttpResearchOSApi  # noqa: E402
from research_os.http import build_request  # noqa: E402
from research_os.http import open_url  # noqa: E402
from scripts.join_openintention import run_hosted_join  # noqa: E402


DEFAULT_SITE_URL = "https://openintention.io"
DEFAULT_API_BASE_URL = "https://api.openintention.io"


@dataclass(frozen=True, slots=True)
class PublishGoalSmokeResult:
    site_url: str
    api_base_url: str
    effort_id: str
    title: str
    author_id: str
    goal_page_url: str
    join_report_path: str
    workspace_id: str | None
    claim_id: str | None
    join_mode: str
    goal_page_excerpt: str


def run_publish_goal_smoke(
    *,
    site_url: str,
    api_base_url: str,
    output_dir: str,
    artifact_root: str,
    python_executable: str = sys.executable,
) -> Path:
    normalized_site_url = site_url.rstrip("/")
    normalized_api_base_url = api_base_url.rstrip("/")
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    artifact_root_path = Path(artifact_root).resolve()
    artifact_root_path.mkdir(parents=True, exist_ok=True)

    suffix = uuid4().hex[:8]
    author_id = f"goal-author-{suffix}"
    title = f"OpenIntention publish-goal smoke {suffix}"
    payload = {
        "title": title,
        "summary": "Verify that a newly published goal becomes a live goal page and accepts a visible follow-on contribution.",
        "objective": "val_loss",
        "metric_name": "validation loss",
        "direction": "min",
        "platform": "cpu",
        "budget_seconds": 300,
        "constraints": [
            "Keep runtime under five minutes.",
            "Leave behind a result the next contributor can inspect.",
        ],
        "evidence_requirement": "Leave behind at least one run and one visible finding or reproduction.",
        "stop_condition": "Stop after the first follow-on contribution lands on the live goal page.",
        "actor_id": author_id,
    }

    created = _post_json(f"{normalized_site_url}/publish", payload)
    effort_id = str(created["effort_id"])
    goal_page_url = str(created["goal_page_url"])
    join_mode = str(created["join_mode"])

    api = HttpResearchOSApi(normalized_api_base_url)
    effort = api.get_effort(effort_id)
    if effort.get("tags", {}).get("goal_origin") != "user-published":
        raise RuntimeError(f"expected user-published goal tags for {effort_id}")
    if str(effort.get("author_id")) != author_id:
        raise RuntimeError(f"expected published author `{author_id}` on {effort_id}")

    join_report_path = run_hosted_join(
        actor_id=f"goal-joiner-{suffix}",
        profile="eval-sprint",
        effort_id=effort_id,
        base_url=normalized_api_base_url,
        site_url=normalized_site_url,
        artifact_root=str(artifact_root_path / "join"),
        output_dir=str(output_root / "hosted-join"),
        python_executable=python_executable,
        bootstrap_environment=False,
    )
    join_report = join_report_path.read_text(encoding="utf-8")
    workspace_id = _extract_field(join_report, "- Workspace: `")
    claim_id = _extract_field(join_report, "- Claim: `")

    workspaces = api.list_workspaces(effort_id=effort_id)
    if workspace_id is None or not any(item["workspace_id"] == workspace_id for item in workspaces):
        raise RuntimeError(f"expected joined workspace `{workspace_id}` to appear on effort `{effort_id}`")

    goal_page_html = _fetch_text(goal_page_url)
    for expected in (
        title,
        "Goal contract",
        "validation loss",
        author_id,
        "User-published goal, proxy join path",
    ):
        if expected not in goal_page_html:
            raise RuntimeError(f"goal page missing `{expected}`: {goal_page_url}")

    result = PublishGoalSmokeResult(
        site_url=normalized_site_url,
        api_base_url=normalized_api_base_url,
        effort_id=effort_id,
        title=title,
        author_id=author_id,
        goal_page_url=goal_page_url,
        join_report_path=str(join_report_path),
        workspace_id=workspace_id,
        claim_id=claim_id,
        join_mode=join_mode,
        goal_page_excerpt=_excerpt(goal_page_html, lines=24),
    )
    report_path = output_root / "publish-goal-smoke.md"
    report_path.write_text(build_publish_goal_smoke_report(result), encoding="utf-8")
    return report_path


def build_publish_goal_smoke_report(result: PublishGoalSmokeResult) -> str:
    return "\n".join(
        [
            "# Publish Goal Smoke Report",
            "",
            "## Publish Step",
            f"- Site: `{result.site_url}`",
            f"- API: `{result.api_base_url}`",
            f"- Title: `{result.title}`",
            f"- Author: `{result.author_id}`",
            f"- Effort: `{result.effort_id}`",
            f"- Join mode: `{result.join_mode}`",
            "",
            "## Follow-On Join",
            f"- Join report: `{result.join_report_path}`",
            f"- Workspace: `{result.workspace_id or 'unknown'}`",
            f"- Claim: `{result.claim_id or 'unknown'}`",
            "",
            "## Live Goal Page",
            f"- URL: `{result.goal_page_url}`",
            "```text",
            result.goal_page_excerpt,
            "```",
            "",
            "## Outcome",
            "- A user-authored goal was published through the public publish path.",
            "- A second participant joined the published goal and left visible contribution state behind.",
            "- The live goal page rendered the published goal contract and the follow-on contribution path.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the publish-goal path end to end.")
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL, help="Public site URL.")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL, help="Hosted API base URL.")
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/publish-goal-smoke",
        help="Directory to write the publish-goal smoke report into.",
    )
    parser.add_argument(
        "--artifact-root",
        default="data/client-artifacts/publish-goal-smoke",
        help="Directory for client-side artifacts created during the smoke run.",
    )
    args = parser.parse_args()

    report_path = run_publish_goal_smoke(
        site_url=args.site_url,
        api_base_url=args.api_base_url,
        output_dir=args.output_dir,
        artifact_root=args.artifact_root,
    )
    print(report_path)


def _fetch_text(url: str) -> str:
    request = build_request(url, headers={"User-Agent": "OpenIntentionPublishGoalSmoke/0.1"})
    with open_url(request, timeout=20) as response:
        return response.read().decode("utf-8")


def _post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    import json

    request = build_request(
        url,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "OpenIntentionPublishGoalSmoke/0.1",
        },
        data=json.dumps(payload).encode("utf-8"),
    )
    with open_url(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_field(report: str, prefix: str) -> str | None:
    for line in report.splitlines():
        if line.startswith(prefix) and line.endswith("`"):
            return line.removeprefix(prefix).removesuffix("`")
    return None


def _excerpt(text: str, *, lines: int) -> str:
    return "\n".join(text.splitlines()[:lines]).strip()


if __name__ == "__main__":
    main()
