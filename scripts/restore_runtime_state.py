from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research_os.ops.runtime_backup import restore_runtime_backup  # noqa: E402
from research_os.settings import Settings  # noqa: E402


def main() -> None:
    settings = Settings.from_env()

    parser = argparse.ArgumentParser(
        description="Restore the runtime database and artifact root from one tar.gz archive."
    )
    parser.add_argument("--archive-path", required=True, help="Backup archive created by backup_runtime_state.py.")
    parser.add_argument("--db-path", default=settings.db_path, help="Target SQLite file path.")
    parser.add_argument("--artifact-root", default=settings.artifact_root, help="Target artifact root path.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing runtime files at the target paths.",
    )
    args = parser.parse_args()

    summary = restore_runtime_backup(
        archive_path=args.archive_path,
        db_path=args.db_path,
        artifact_root=args.artifact_root,
        force=args.force,
    )
    print(summary.db_path)


if __name__ == "__main__":
    main()
