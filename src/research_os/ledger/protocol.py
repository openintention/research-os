from __future__ import annotations

from typing import Protocol

from research_os.domain.models import ClaimSummary, EventEnvelope, EventKind, FrontierView


class EventStore(Protocol):
    def init_schema(self) -> None: ...

    def append(self, event: EventEnvelope) -> None: ...

    def list(
        self,
        *,
        workspace_id: str | None = None,
        kind: EventKind | None = None,
        limit: int | None = None,
    ) -> list[EventEnvelope]: ...

    def get_frontier(
        self,
        *,
        objective: str,
        platform: str,
        budget_seconds: int | None = None,
        limit: int = 10,
    ) -> FrontierView: ...

    def rebuild_frontier_projection(self) -> None: ...

    def list_claims(
        self,
        *,
        objective: str | None = None,
        platform: str | None = None,
    ) -> list[ClaimSummary]: ...

    def rebuild_claim_projection(self) -> None: ...
