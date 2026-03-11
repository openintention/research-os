from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research_os.ops.runtime_backup import create_runtime_backup  # noqa: E402
from research_os.settings import Settings  # noqa: E402


def main() -> None:
    settings = Settings.from_env()

    parser = argparse.ArgumentParser(
        description="Archive the current runtime database and artifact root into one tar.gz file."
    )
    parser.add_argument("--db-path", default=settings.db_path, help="Path to the runtime SQLite file.")
    parser.add_argument(
        "--artifact-root",
        default=settings.artifact_root,
        help="Path to the runtime artifact root directory.",
    )
    parser.add_argument(
        "--output-path",
        default="data/backups/runtime-state.tar.gz",
        help="Output tar.gz path for the backup archive.",
    )
    args = parser.parse_args()

    summary = create_runtime_backup(
        db_path=args.db_path,
        artifact_root=args.artifact_root,
        output_path=args.output_path,
    )
    print(summary.archive_path)


if __name__ == "__main__":
    main()
