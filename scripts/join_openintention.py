from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlencode

from research_os.http import read_json


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://api.openintention.io"
DEFAULT_SITE_URL = "https://openintention.io"


@dataclass(frozen=True, slots=True)
class HostedJoinResult:
    actor_id: str
    profile: str
    base_url: str
    site_url: str
    effort_id: str | None
    effort_name: str | None
    workspace_id: str | None
    claim_id: str | None
    reproduction_run_id: str | None
    participant_role: str | None
    provenance_snippet: list[str] = field(default_factory=list)
    output: str = ""


def run_hosted_join(
    *,
    actor_id: str | None,
    profile: str,
    base_url: str,
    site_url: str,
    artifact_root: str,
    output_dir: str,
    python_executable: str = sys.executable,
    venv_dir: str = ".venv-openintention-join",
    bootstrap_environment: bool = True,
) -> Path:
    output_root = (REPO_ROOT / output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    artifact_root_path = (REPO_ROOT / artifact_root).resolve()
    artifact_root_path.mkdir(parents=True, exist_ok=True)

    resolved_actor_id = actor_id or _default_actor_id()
    venv_python = Path(python_executable)
    if bootstrap_environment:
        venv_path = (REPO_ROOT / venv_dir).resolve()
        venv_python = _venv_python(venv_path)

        if not venv_python.exists():
            _run_command([python_executable, "-m", "venv", str(venv_path)], cwd=REPO_ROOT)

        _run_command([str(venv_python), "-m", "pip", "install", "-e", "."], cwd=REPO_ROOT)

    command = [
        str(venv_python),
        "-m",
        "clients.tiny_loop.run",
        "--base-url",
        base_url,
        "--profile",
        profile,
        "--actor-id",
        resolved_actor_id,
        "--artifact-root",
        str(artifact_root_path),
    ]
    output = _run_command(command, cwd=REPO_ROOT)
    fields = _extract_fields(output)
    result = HostedJoinResult(
        actor_id=resolved_actor_id,
        profile=profile,
        base_url=base_url,
        site_url=site_url,
        effort_id=fields.get("effort_id"),
        effort_name=fields.get("effort_name"),
        workspace_id=fields.get("workspace_id"),
        claim_id=fields.get("claim_id"),
        reproduction_run_id=fields.get("reproduction_run_id"),
        participant_role=fields.get("participant_role"),
        provenance_snippet=_extract_provenance(fields.get("workspace_id"), base_url),
        output=output,
    )

    report_path = output_root / "hosted-join.md"
    report_path.write_text(build_join_report(result), encoding="utf-8")
    return report_path


def build_join_report(result: HostedJoinResult) -> str:
    effort_url = _live_goal_url(result)
    discussion_url = (
        f"{result.base_url.rstrip('/')}/api/v1/publications/workspaces/{result.workspace_id}/discussion"
        if result.workspace_id is not None
        else "n/a"
    )
    return "\n".join(
        [
            "# Joined OpenIntention",
            "",
            "## Joined",
            f"- Actor: `{result.actor_id}`",
            f"- Profile: `{result.profile}`",
            f"- Participant role: `{result.participant_role or 'unknown'}`",
            f"- Effort: `{result.effort_name or 'unknown'}`",
            f"- Workspace: `{result.workspace_id or 'unknown'}`",
            "",
            "## Contribution",
            f"- Claim: `{result.claim_id or 'unknown'}`",
            f"- Reproduction run: `{result.reproduction_run_id or 'unknown'}`",
            "",
            "## Inspect Next",
            f"- Live goal page: `{effort_url}`",
            f"- Workspace discussion: `{discussion_url}`",
            "- The live goal URL is intended to land back on your own highlighted contribution.",
            "- Hand the live goal page or this report to the next human or agent.",
            "",
            "## Verifier-Ready Provenance",
            *(result.provenance_snippet if result.provenance_snippet else ["- Not available yet."]),
            "",
            "## Command Output",
            "```text",
            result.output.strip(),
            "```",
            "",
            "## Honesty Line",
            "- This lands visible work in the live hosted shared goal state.",
            "- The default eval and inference contribution paths are still proxy loops.",
            "- A stronger external-harness compounding path exists separately in the repo.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Join the live OpenIntention effort path.")
    parser.add_argument(
        "--actor-id",
        default=None,
        help="Optional lightweight handle to attach to the hosted workspace and events.",
    )
    parser.add_argument(
        "--profile",
        choices=("eval-sprint", "inference-sprint"),
        default="eval-sprint",
        help="Which seeded goal path to join.",
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
        "--artifact-root",
        default="data/client-artifacts/hosted-join",
        help="Directory for local client-side snapshot bundles.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/hosted-join",
        help="Directory to write the hosted join report into.",
    )
    parser.add_argument(
        "--venv-dir",
        default=".venv-openintention-join",
        help="Virtual environment path used to bootstrap the join command.",
    )
    parser.add_argument(
        "--no-bootstrap",
        action="store_true",
        help="Run inside the current Python environment without creating the nested hosted-join venv.",
    )
    args = parser.parse_args()

    print("Joining OpenIntention from the public repo into the live hosted goal state...")
    report_path = run_hosted_join(
        actor_id=args.actor_id,
        profile=args.profile,
        base_url=args.base_url,
        site_url=args.site_url,
        artifact_root=args.artifact_root,
        output_dir=args.output_dir,
        venv_dir=args.venv_dir,
        bootstrap_environment=not args.no_bootstrap,
    )
    report_text = report_path.read_text(encoding="utf-8")
    print()
    print(report_text)
    print(f"live_goal_url={_live_goal_url_from_report(report_text)}")
    print(f"report_path={report_path}")


def _default_actor_id() -> str:
    preferred = os.environ.get("OPENINTENTION_ACTOR_ID") or os.environ.get("GITHUB_USER") or os.environ.get("USER")
    if preferred:
        return _normalize_handle(preferred)
    return "participant"


def _normalize_handle(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-_.").lower()
    return normalized or "participant"


def _extract_fields(output: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in output.splitlines():
        match = re.match(r"^([a-z_]+)=(.+)$", line.strip())
        if match:
            fields[match.group(1)] = match.group(2)
    return fields


def _extract_provenance(workspace_id: str | None, base_url: str) -> list[str]:
    if not workspace_id:
        return []
    try:
        discussion = _fetch_workspace_discussion(base_url, workspace_id)
    except Exception:
        return ["- Provenance evidence fetch failed at build time."]
    if not discussion:
        return []
    lines = [line.strip() for line in discussion.splitlines() if "manifest" in line.lower() or "provenance" in line.lower()]
    return lines[:12] if lines else ["- No provenance fields are currently exposed in this workspace discussion."]


def _fetch_workspace_discussion(base_url: str, workspace_id: str) -> str:
    url = f"{base_url.rstrip('/')}/api/v1/publications/workspaces/{workspace_id}/discussion"
    payload = read_json(url, timeout=10)
    return str(payload.get("body", ""))


def _run_command(command: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return completed.stdout


def _venv_python(venv_dir: Path) -> Path:
    return venv_dir / "bin" / "python"


def _live_goal_url(result: HostedJoinResult) -> str:
    if result.effort_id is None:
        return "n/a"
    query: dict[str, str] = {}
    if result.workspace_id is not None:
        query["workspace"] = result.workspace_id
        query["joined"] = "1"
    if result.actor_id:
        query["actor"] = result.actor_id
    if result.claim_id is not None:
        query["claim"] = result.claim_id
    if result.reproduction_run_id is not None and result.reproduction_run_id != "n/a":
        query["reproduction"] = result.reproduction_run_id
    query_string = f"?{urlencode(query)}" if query else ""
    fragment = f"#workspace-{result.workspace_id}" if result.workspace_id is not None else ""
    return f"{result.site_url.rstrip('/')}/efforts/{result.effort_id}{query_string}{fragment}"


def _live_goal_url_from_report(report: str) -> str:
    for line in report.splitlines():
        if line.startswith("- Live goal page: `") and line.endswith("`"):
            return line.removeprefix("- Live goal page: `").removesuffix("`")
    return "n/a"


if __name__ == "__main__":
    main()
