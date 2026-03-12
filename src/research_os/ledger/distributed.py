from __future__ import annotations


class DistributedEventStore:
    """Placeholder for a future distributed event store.

    Expected responsibilities:
    - append typed lineage events into one or more immutable partitions
    - expose workspace/frontier/claim queries through indexed state or query services
    - keep the Python service layer substrate-agnostic

    This file exists so Codex has an obvious seam to grow into.
    """

    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError("Distributed adapter is not implemented in the starter scaffold.")
