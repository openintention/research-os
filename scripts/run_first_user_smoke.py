from __future__ import annotations

import argparse
from dataclasses import dataclass
from dataclasses import field
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse
from urllib.request import ProxyHandler
from urllib.request import build_opener

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from research_os.http import build_request  # noqa: E402
from research_os.http import open_url  # noqa: E402
from research_os.settings import Settings  # noqa: E402


@dataclass(frozen=True, slots=True)
class SmokeResult:
    base_url: str
    efforts: list[dict[str, object]]
    eval_client_output: str
    inference_client_output: str
    exported_brief_paths: list[str]
    eval_workspace_provenance_excerpt: list[str] = field(default_factory=list)
    inference_workspace_provenance_excerpt: list[str] = field(default_factory=list)


def run_first_user_smoke(
    *,
    db_path: str,
    artifact_root: str,
    output_dir: str,
    python_executable: str | None = None,
) -> Path:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    resolved_python_executable = _resolve_python_executable(python_executable)

    env = os.environ.copy()
    env["RESEARCH_OS_DB_PATH"] = db_path
    env["RESEARCH_OS_ARTIFACT_ROOT"] = artifact_root

    _run_command([resolved_python_executable, "scripts/seed_demo.py", "--reset"], env=env)

    port = _find_open_port()
    base_url = f"http://127.0.0.1:{port}"
    server_log_path = output_root / "server.log"
    with server_log_path.open("w", encoding="utf-8") as server_log:
        server = subprocess.Popen(
            [
                resolved_python_executable,
                "-m",
                "uvicorn",
                "apps.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            _wait_for_healthz(base_url)
            efforts = _get_json(f"{base_url}/api/v1/efforts")
            eval_client_output = _run_command(
                [
                    resolved_python_executable,
                    "-m",
                    "clients.tiny_loop.run",
                    "--base-url",
                    base_url,
                    "--artifact-root",
                    str(output_root / "client-artifacts" / "eval"),
                ],
                env=env,
            )
            inference_client_output = _run_command(
                [
                    resolved_python_executable,
                    "-m",
                    "clients.tiny_loop.run",
                    "--profile",
                    "inference-sprint",
                    "--base-url",
                    base_url,
                    "--artifact-root",
                    str(output_root / "client-artifacts" / "inference"),
                ],
                env=env,
            )
            exported_briefs_output = _run_command(
                [
                    resolved_python_executable,
                    "scripts/export_effort_briefs.py",
                    "--output-dir",
                    str(output_root / "effort-briefs"),
                ],
                env=env,
            )
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)

    result = SmokeResult(
        base_url=base_url,
        efforts=efforts,
        eval_client_output=eval_client_output,
        inference_client_output=inference_client_output,
        exported_brief_paths=[line for line in exported_briefs_output.splitlines() if line.strip()],
        eval_workspace_provenance_excerpt=_extract_workspace_provenance_excerpt(
            base_url=base_url,
            workspace_id=_extract_fields(eval_client_output).get("workspace_id"),
        ),
        inference_workspace_provenance_excerpt=_extract_workspace_provenance_excerpt(
            base_url=base_url,
            workspace_id=_extract_fields(inference_client_output).get("workspace_id"),
        ),
    )
    report_path = output_root / "first-user-smoke.md"
    report_path.write_text(build_smoke_report(result), encoding="utf-8")
    return report_path


def build_smoke_report(result: SmokeResult) -> str:
    effort_lines = [
        f"- `{effort['name']}` `{effort['objective']}` on `{effort['platform']}` ({effort['budget_seconds']}s)"
        for effort in result.efforts
    ] or ["- No efforts discovered."]
    exported_lines = [f"- `{path}`" for path in result.exported_brief_paths] or ["- No exported briefs recorded."]
    eval_fields = _extract_fields(result.eval_client_output)
    inference_fields = _extract_fields(result.inference_client_output)

    joined_lines = [
        _joined_line("Eval", eval_fields),
        _joined_line("Inference", inference_fields),
    ]
    participation_lines = [
        _participated_line("Eval", eval_fields),
        _participated_line("Inference", inference_fields),
    ]

    return "\n".join(
        [
            "# First User Smoke Report",
            "",
            "## Base URL",
            f"- `{result.base_url}`",
            "",
            "## Discovered Efforts",
            *effort_lines,
            "",
            "## Participation Outcome",
            "- Onboarded: the newcomer discovered the public repo and seeded goal path from the public surface.",
            *joined_lines,
            *participation_lines,
            "",
            "## Verifier-Ready Provenance",
            "### Eval Sprint Workspace",
            *(result.eval_workspace_provenance_excerpt if result.eval_workspace_provenance_excerpt else ["- Not available yet."]),
            "",
            "### Inference Sprint Workspace",
            *(
                result.inference_workspace_provenance_excerpt
                if result.inference_workspace_provenance_excerpt
                else ["- Not available yet."]
            ),
            "",
            "## Eval Client Output",
            "```text",
            result.eval_client_output.strip(),
            "```",
            "",
            "## Inference Client Output",
            "```text",
            result.inference_client_output.strip(),
            "```",
            "",
            "## Exported Briefs",
            *exported_lines,
        ]
    ) + "\n"


def _extract_fields(output: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in output.splitlines():
        match = re.match(r"^([a-z_]+)=(.+)$", line.strip())
        if match:
            fields[match.group(1)] = match.group(2)
    return fields


def _joined_line(label: str, fields: dict[str, str]) -> str:
    effort = fields.get("effort_name")
    workspace = fields.get("workspace_id")
    if effort and workspace:
        return f"- Joined ({label}): workspace `{workspace}` attached to effort `{effort}`."
    if workspace:
        return f"- Joined ({label}): workspace `{workspace}` created."
    return f"- Joined ({label}): not proven from client output."


def _participated_line(label: str, fields: dict[str, str]) -> str:
    claim = fields.get("claim_id")
    reproduction = fields.get("reproduction_run_id")
    workspace = fields.get("workspace_id")
    if workspace and claim and reproduction:
        return (
            f"- Participated ({label}): workspace `{workspace}` left behind claim "
            f"`{claim}` and reproduction run `{reproduction}`."
        )
    return f"- Participated ({label}): durable contribution state not fully proven from client output."


def _extract_workspace_provenance_excerpt(*, base_url: str, workspace_id: str | None) -> list[str]:
    if not workspace_id:
        return []
    try:
        request = build_request(
            f"{base_url}/api/v1/publications/workspaces/{workspace_id}/discussion",
            headers={"accept": "application/json"},
        )
        with _open_request(request, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
        lines = [
            line.strip()
            for line in str(body.get("body", "")).splitlines()
            if "manifest" in line.lower() or "provenance" in line.lower()
        ]
        return lines[:20] if lines else ["- No provenance fields are currently exposed in this workspace discussion."]
    except Exception:
        return ["- Provenance evidence fetch failed at build time."]


def main() -> None:
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description="Run the first-user launch smoke flow.")
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch",
        help="Directory to write the smoke report and supporting artifacts into.",
    )
    args = parser.parse_args()

    report_path = run_first_user_smoke(
        db_path=settings.db_path,
        artifact_root=settings.artifact_root,
        output_dir=args.output_dir,
    )
    print(report_path)


def _run_command(command: list[str], *, env: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _get_json(url: str) -> list[dict[str, object]]:
    request = build_request(url, headers={"accept": "application/json"})
    with _open_request(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_healthz(base_url: str, *, timeout_seconds: float = 10.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with _open_request(build_request(f"{base_url}/healthz"), timeout=1):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"timed out waiting for {base_url}/healthz")


def _find_open_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _resolve_python_executable(python_executable: str | None) -> str:
    if python_executable is not None:
        return python_executable

    active_venv = os.environ.get("VIRTUAL_ENV")
    if active_venv:
        candidate = Path(active_venv) / "bin" / "python"
        if candidate.exists():
            return str(candidate)

    repo_venv = REPO_ROOT / ".venv" / "bin" / "python"
    if repo_venv.exists():
        return str(repo_venv)

    return sys.executable


def _open_request(request, *, timeout: float):
    hostname = (urlparse(request.full_url).hostname or "").lower()
    if hostname in {"127.0.0.1", "localhost"}:
        opener = build_opener(ProxyHandler({}))
        return opener.open(request, timeout=timeout)
    return open_url(request, timeout=timeout)


if __name__ == "__main__":
    main()
