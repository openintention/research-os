from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.run_nightly_contribution_window import run_nightly_contribution_window  # noqa: E402

DEFAULT_BASE_URL = "https://api.openintention.io"
DEFAULT_SITE_URL = "https://openintention.io"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a deterministic two-loop nightly contribution rehearsal against the hosted goal state."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Hosted OpenIntention API base URL.")
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL, help="Public OpenIntention site URL.")
    parser.add_argument(
        "--profile",
        choices=("eval-sprint", "inference-sprint"),
        default="eval-sprint",
        help="Which seeded goal to rehearse the nightly window against.",
    )
    parser.add_argument(
        "--actor-id",
        default="nightly-window-smoke",
        help="Lightweight actor handle attached to the rehearsal workspaces.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/nightly-contribution-window-smoke",
        help="Directory to write the nightly smoke report into.",
    )
    parser.add_argument(
        "--artifact-root",
        default="data/client-artifacts/nightly-window-smoke",
        help="Directory for client-side artifacts created during the smoke run.",
    )
    args = parser.parse_args()

    report_path = run_nightly_contribution_window(
        base_url=args.base_url,
        site_url=args.site_url,
        profile=args.profile,
        actor_id=args.actor_id,
        window_seconds=60,
        interval_seconds=0,
        max_loops=2,
        artifact_root=args.artifact_root,
        output_dir=args.output_dir,
    )
    print(report_path)


if __name__ == "__main__":
    main()
