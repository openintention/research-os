# ADR 0003: Build a thin external client before subscriptions

## Status
Accepted

## Context
The local bootstrap version of `research-os` now has:
- materialized frontier and claim projections
- content-addressed snapshot references
- objective-aware planner scoring
- publication mirrors derived from control-plane state

The next product question is no longer whether the control plane can expose useful state.
The next question is whether an external agent loop can use that state in a believable,
forkable workflow.

Recent public response to small, forkable autonomous research loops reinforced a specific
demand shape:
- a small surface area
- one clear metric
- one fixed budget
- one visible overnight loop
- something builders can fork immediately

That suggests subscriptions and notifications should be shaped by observed client pain,
not designed in the abstract before a real external loop exists.

## Decision
Build a real, narrow, single-agent client experiment outside the control plane before
building subscriptions and notifications.

The client should:
- stay external to `research-os`
- use the HTTP API boundary instead of importing service internals
- run a cheap, real ML loop in a tiny domain
- optimize for forkability and inspectability over raw capability

Subscriptions and notifications remain valuable, but they should follow this client
experiment and be informed by the interaction pattern it reveals.

## Consequences
- the next validation artifact is a client loop, not more coordination infrastructure
- `research-os` remains clearly positioned as the control plane
- the first public build story stays narrow and legible
- future subscription design can target real polling and fan-out pain instead of guesses
