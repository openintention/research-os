from __future__ import annotations


class RamaEventStore:
    """Placeholder for a future Rama-backed event store.

    Expected responsibilities:
    - append typed lineage events into one or more depots
    - expose workspace/frontier/claim queries through PStates or query topologies
    - keep the Python service layer substrate-agnostic

    This file exists so Codex has an obvious seam to grow into.
    """

    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError("Rama adapter is not implemented in the starter scaffold.")
