from __future__ import annotations

from research_os.ledger.sqlite import SQLiteEventStore
from research_os.service import ResearchOSService
from research_os.settings import Settings


def main() -> None:
    settings = Settings.from_env()
    settings.ensure_directories()

    service = ResearchOSService(
        SQLiteEventStore(settings.db_path),
        default_frontier_size=settings.default_frontier_size,
    )
    service.rebuild_claim_projection()
    print(f"Rebuilt claim projection for {settings.db_path}")


if __name__ == "__main__":
    main()
