from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen


DEFAULT_SITE_URL = "https://openintention.io"
DEFAULT_PUBLIC_REPO_URL = "https://github.com/openintention/research-os"


@dataclass(frozen=True, slots=True)
class PublicIngressResult:
    site_url: str
    repo_url: str
    clone_path: str
    agent_brief_path: str
    smoke_report_path: str
    commands: list[str]
    smoke_report_excerpt: str


def run_public_ingress_smoke(
    *,
    site_url: str,
    output_dir: str,
    python_executable: str = sys.executable,
    repo_url: str | None = None,
    work_dir: str | None = None,
) -> Path:
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    landing_html = fetch_text(site_url)
    resolved_repo_url = repo_url or extract_public_repo_url(landing_html)

    work_root = Path(work_dir) if work_dir is not None else Path(tempfile.mkdtemp(prefix="openintention-public-ingress-"))
    work_root.mkdir(parents=True, exist_ok=True)
    clone_root = work_root / "clone"
    if clone_root.exists():
        shutil.rmtree(clone_root)

    command_log = [
        f"git clone --depth 1 {resolved_repo_url} <temp_clone_dir>/clone",
        "<host_python> -m venv <temp_clone_dir>/clone/.venv-public-ingress",
        "<temp_clone_dir>/clone/.venv-public-ingress/bin/python -m pip install -e .[dev]",
        "<temp_clone_dir>/clone/.venv-public-ingress/bin/python scripts/run_first_user_smoke.py --output-dir <artifact_dir>/first-user",
    ]

    _run_command(["git", "clone", "--depth", "1", resolved_repo_url, str(clone_root)])

    venv_dir = clone_root / ".venv-public-ingress"
    _run_command([python_executable, "-m", "venv", str(venv_dir)], cwd=clone_root)

    venv_python = _venv_python(venv_dir)
    _run_command([str(venv_python), "-m", "pip", "install", "-e", ".[dev]"], cwd=clone_root)

    smoke_output_dir = work_root / "first-user"
    _run_command(
        [
            str(venv_python),
            "scripts/run_first_user_smoke.py",
            "--output-dir",
            str(smoke_output_dir),
        ],
        cwd=clone_root,
    )

    agent_brief_path = clone_root / "docs" / "join-with-ai.md"
    if not agent_brief_path.exists():
        raise FileNotFoundError(f"missing agent brief at {agent_brief_path}")

    work_smoke_report_path = smoke_output_dir / "first-user-smoke.md"
    if not work_smoke_report_path.exists():
        raise FileNotFoundError(f"missing smoke report at {work_smoke_report_path}")
    smoke_report_path = output_root / "first-user-smoke.md"
    shutil.copyfile(work_smoke_report_path, smoke_report_path)

    result = PublicIngressResult(
        site_url=site_url,
        repo_url=resolved_repo_url,
        clone_path=str(clone_root),
        agent_brief_path="clone/docs/join-with-ai.md",
        smoke_report_path=str(smoke_report_path),
        commands=command_log,
        smoke_report_excerpt=_excerpt(smoke_report_path, lines=18),
    )
    report_path = output_root / "public-ingress-smoke.md"
    report_path.write_text(build_public_ingress_report(result), encoding="utf-8")
    return report_path


def build_public_ingress_report(result: PublicIngressResult) -> str:
    command_lines = [f"- `{command}`" for command in result.commands]
    return "\n".join(
        [
            "# Public Ingress Smoke Report",
            "",
            "## Public Entry",
            f"- Site: `{result.site_url}`",
            f"- Repo discovered from site: `{result.repo_url}`",
            "",
            "## Agent Brief",
            f"- `{result.agent_brief_path}`",
            "",
            "## Commands Executed",
            *command_lines,
            "",
            "## First User Smoke Excerpt",
            "````text",
            result.smoke_report_excerpt.strip(),
            "````",
            "",
            "## Outcome",
            "- A newcomer can arrive from the public site, discover the public repo, hand the repo to an AI agent, and complete the canonical seeded-effort smoke path.",
            "- The canonical goal is not just onboarding. It is onboarding, joining a seeded effort, and participating by leaving behind inspectable contribution state.",
        ]
    ) + "\n"


def extract_public_repo_url(landing_html: str) -> str:
    matches = re.findall(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", landing_html)
    if DEFAULT_PUBLIC_REPO_URL in matches:
        return DEFAULT_PUBLIC_REPO_URL
    if matches:
        return matches[0]
    raise ValueError("could not find a public GitHub repo URL in the landing page")


def fetch_text(url: str) -> str:
    request = Request(
        url,
        headers={"User-Agent": "OpenIntentionAgent/0.1 (+https://github.com/openintention/research-os)"},
    )
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the public ingress-to-participation flow.")
    parser.add_argument(
        "--site-url",
        default=DEFAULT_SITE_URL,
        help="Public site URL to use as the ingress surface.",
    )
    parser.add_argument(
        "--repo-url",
        default=None,
        help="Optional explicit public repo URL override.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/public-ingress",
        help="Directory to write the public-ingress verification artifacts into.",
    )
    parser.add_argument(
        "--work-dir",
        default=None,
        help="Optional working directory for the cloned repo and venv. Defaults to a system temp directory.",
    )
    args = parser.parse_args()

    report_path = run_public_ingress_smoke(
        site_url=args.site_url,
        repo_url=args.repo_url,
        output_dir=args.output_dir,
        work_dir=args.work_dir,
    )
    print(report_path)


def _run_command(command: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def _excerpt(path: Path, *, lines: int) -> str:
    content = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(content[:lines]).strip()


def _venv_python(venv_dir: Path) -> Path:
    return venv_dir / "bin" / "python"


if __name__ == "__main__":
    main()
