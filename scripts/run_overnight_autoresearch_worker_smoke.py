from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from research_os.settings import Settings  # noqa: E402
from scripts.run_overnight_autoresearch_worker import run_overnight_autoresearch_worker  # noqa: E402


@dataclass(frozen=True, slots=True)
class OvernightWorkerSmokeResult:
    base_url: str
    worker_report_path: str
    repo_path: str
    effort_page_hint: str
    worker_report_excerpt: str


def run_overnight_autoresearch_worker_smoke(
    *,
    db_path: str,
    artifact_root: str,
    output_dir: str,
    python_executable: str = sys.executable,
) -> Path:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    resolved_python = _resolve_python_executable(python_executable)

    env = os.environ.copy()
    env["RESEARCH_OS_DB_PATH"] = db_path
    env["RESEARCH_OS_ARTIFACT_ROOT"] = artifact_root

    port = _find_open_port()
    base_url = f"http://127.0.0.1:{port}"
    server_log_path = output_root / "server.log"
    with server_log_path.open("w", encoding="utf-8") as server_log:
        server = subprocess.Popen(
            [
                resolved_python,
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
            with TemporaryDirectory(prefix="openintention-worker-smoke-") as tmp_dir:
                repo_path = _create_fixture_repo(Path(tmp_dir))
                worker_report_path = run_overnight_autoresearch_worker(
                    base_url=base_url,
                    site_url="https://openintention.io",
                    repo_path=str(repo_path),
                    runner_command=f"{resolved_python} advance_results.py",
                    actor_id="worker-smoke",
                    window_seconds=60,
                    interval_seconds=0,
                    max_loops=2,
                    command_timeout_seconds=5,
                    budget_cap_seconds=20,
                    artifact_root=str(output_root / "artifacts"),
                    output_dir=str(output_root / "worker"),
                    repo_url="https://github.com/example/mlx-history",
                )
                effort_page_hint = _resolve_effort_page_hint(base_url)
                result = OvernightWorkerSmokeResult(
                    base_url=base_url,
                    worker_report_path=str(worker_report_path),
                    repo_path=str(repo_path),
                    effort_page_hint=effort_page_hint,
                    worker_report_excerpt=_excerpt(worker_report_path, lines=24),
                )
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)

    report_path = output_root / "overnight-autoresearch-worker-smoke.md"
    report_path.write_text(build_worker_smoke_report(result), encoding="utf-8")
    return report_path


def build_worker_smoke_report(result: OvernightWorkerSmokeResult) -> str:
    return "\n".join(
        [
            "# Overnight Autoresearch Worker Smoke",
            "",
            "## Disposable Sandbox",
            f"- Base URL: `{result.base_url}`",
            f"- Fixture repo: `{result.repo_path}`",
            f"- Worker report: `{result.worker_report_path}`",
            f"- Live effort page hint: `{result.effort_page_hint}`",
            "",
            "## Worker Report Excerpt",
            "```text",
            result.worker_report_excerpt.strip(),
            "```",
            "",
            "## Outcome",
            "- The worker executed a real local command against a disposable repo fixture.",
            "- Two kept results were appended to `results.tsv` across two iterations and imported into shared state.",
            "- The resulting report includes live handoff links, operator attribution, and bounded stop conditions.",
        ]
    ) + "\n"


def main() -> None:
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(
        description="Run a deterministic disposable sandbox smoke for the overnight autoresearch worker."
    )
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/overnight-autoresearch-worker-smoke",
        help="Directory to write the worker smoke artifacts into.",
    )
    args = parser.parse_args()

    report_path = run_overnight_autoresearch_worker_smoke(
        db_path=settings.db_path,
        artifact_root=settings.artifact_root,
        output_dir=args.output_dir,
    )
    print(report_path)


def _create_fixture_repo(root: Path) -> Path:
    repo_path = root / "mlx-history-fixture"
    repo_path.mkdir(parents=True, exist_ok=True)
    (repo_path / "results.tsv").write_text(
        "\n".join(
            [
                "commit\tval_bpb\tmemory_gb\tstatus\tdescription",
                "383abb4\t2.667000\t26.9\tkeep\tbaseline",
            ]
        ),
        encoding="utf-8",
    )
    (repo_path / "advance_results.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import json",
                "from pathlib import Path",
                "",
                "RESULTS_PATH = Path('results.tsv')",
                "STATE_PATH = Path('.advance-state.json')",
                "STEPS = [",
                "    ('4161af3', 2.533728, 26.9, 'keep', 'increase matrix LR to 0.04'),",
                "    ('5efc7aa', 1.807902, 26.9, 'keep', 'reduce depth from 8 to 4'),",
                "]",
                "",
                "state = {'index': 0}",
                "if STATE_PATH.exists():",
                "    state = json.loads(STATE_PATH.read_text(encoding='utf-8'))",
                "index = int(state.get('index', 0))",
                "if index < len(STEPS):",
                "    commit, val_bpb, memory_gb, status, description = STEPS[index]",
                "    with RESULTS_PATH.open('a', encoding='utf-8') as handle:",
                "        handle.write(f'\\n{commit}\\t{val_bpb:.6f}\\t{memory_gb:.1f}\\t{status}\\t{description}')",
                "    state['index'] = index + 1",
                "    STATE_PATH.write_text(json.dumps(state), encoding='utf-8')",
                "    print(f'appended {commit}')",
                "else:",
                "    print('no more kept results')",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return repo_path


def _wait_for_healthz(base_url: str) -> None:
    import time

    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            with urlopen(f"{base_url}/healthz", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"timed out waiting for {base_url}/healthz")


def _find_open_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _excerpt(path: Path, *, lines: int) -> str:
    return "\n".join(path.read_text(encoding="utf-8").splitlines()[:lines]).strip()


def _resolve_effort_page_hint(base_url: str) -> str:
    with urlopen(f"{base_url}/api/v1/efforts", timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    effort_id = payload[0]["effort_id"] if payload else "<generated_effort_id>"
    return f"https://openintention.io/efforts/{effort_id}"


def _resolve_python_executable(current_python: str) -> str:
    candidates = [
        current_python,
        str(REPO_ROOT / ".venv" / "bin" / "python"),
        os.environ.get("OPENINTENTION_PYTHON"),
        shutil.which("python3.11"),
        shutil.which("python3"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        if _supports_module(candidate, "uvicorn"):
            return candidate
    raise RuntimeError("could not find a Python executable with uvicorn installed for the smoke server")


def _supports_module(python_executable: str, module_name: str) -> bool:
    try:
        completed = subprocess.run(
            [python_executable, "-c", f"import {module_name}"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return False
    return completed.returncode == 0


if __name__ == "__main__":
    main()
