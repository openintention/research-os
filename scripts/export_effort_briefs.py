from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from research_os.ledger.sqlite import SQLiteEventStore  # noqa: E402
from research_os.service import ResearchOSService  # noqa: E402
from research_os.settings import Settings  # noqa: E402


def export_effort_briefs(*, db_path: str, output_dir: str) -> list[Path]:
    service = ResearchOSService(SQLiteEventStore(db_path))
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    written_paths: list[Path] = []
    for effort in sorted(service.list_efforts(), key=lambda item: item.name):
        publication = service.render_effort_overview(effort.effort_id)
        if publication is None:
            continue

        path = output_root / f"{_slugify(effort.name)}.md"
        path.write_text(publication.body + "\n", encoding="utf-8")
        written_paths.append(path)

    return written_paths


def main() -> None:
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description="Export seeded effort briefs as markdown files.")
    parser.add_argument(
        "--output-dir",
        default="data/publications/efforts",
        help="Directory to write exported effort markdown files into.",
    )
    args = parser.parse_args()

    written_paths = export_effort_briefs(db_path=settings.db_path, output_dir=args.output_dir)
    for path in written_paths:
        print(path)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "effort"


if __name__ == "__main__":
    main()
