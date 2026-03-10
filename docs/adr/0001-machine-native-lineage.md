# ADR 0001: Machine-native lineage over merge-centric workflow

## Status
Accepted

## Context
Human-centric source control assumes a small number of collaborators and a small number of
temporary branches that eventually merge back into a canonical trunk.

Autonomous research systems do not satisfy that assumption. Thousands of agents may run
permanent lines of exploration that never merge, yet still exchange useful findings.

## Decision
Use typed research events and derived projections as the source of truth.
Treat branches and PR-like artifacts as generated views, not canonical state.

## Consequences
- the system can represent adoption without merge
- the system can track reproduction and contradiction explicitly
- frontier state becomes hardware- and budget-aware
- publication mirrors can be regenerated from the control plane
