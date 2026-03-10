from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

from research_os.settings import Settings


@dataclass(frozen=True, slots=True)
class SmokeResult:
    base_url: str
    efforts: list[dict[str, object]]
    eval_client_output: str
    inference_client_output: str
    exported_brief_paths: list[str]


def run_first_user_smoke(
    *,
    db_path: str,
    artifact_root: str,
    output_dir: str,
    python_executable: str = sys.executable,
) -> Path:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["RESEARCH_OS_DB_PATH"] = db_path
    env["RESEARCH_OS_ARTIFACT_ROOT"] = artifact_root

    _run_command([python_executable, "scripts/seed_demo.py", "--reset"], env=env)

    port = _find_open_port()
    base_url = f"http://127.0.0.1:{port}"
    server_log_path = output_root / "server.log"
    with server_log_path.open("w", encoding="utf-8") as server_log:
        server = subprocess.Popen(
            [
                python_executable,
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
                    python_executable,
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
                    python_executable,
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
                    python_executable,
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
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_healthz(base_url: str, *, timeout_seconds: float = 10.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(f"{base_url}/healthz", timeout=1):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"timed out waiting for {base_url}/healthz")


def _find_open_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


if __name__ == "__main__":
    main()
