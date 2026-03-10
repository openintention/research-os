# ADR 0002: Keep a Rama adapter seam from day one

## Status
Accepted

## Context
A future production control plane may want:
- immutable distributed event logs
- durable indexed state
- low-latency query serving
- hardware-aware distributed execution

## Decision
Define the domain model and service layer so the local event store can be replaced later.
Do not leak SQLite assumptions into domain or API code.

## Consequences
- local bootstrap remains lightweight
- migration to a distributed substrate stays feasible
- planner logic remains substrate-independent
