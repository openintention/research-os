# ADR 0005: V1 participant visibility is effort-centric

## Status
Accepted

## Context
As OpenIntention moves from a local proof toward hosted/shared participation, the web
surface needs a clear v1 answer for participant visibility.

The product needs enough visibility for collaboration:
- who is contributing to an effort
- what they have done
- who asserted, reproduced, or contradicted a claim
- who is currently active in an effort

But it should not accidentally become:
- a social network
- a profile product
- a reputation system
- a strong identity system before the trust model exists

This matters directly for the next product work:
- `ANJ-24` hosted/shared seeded efforts
- `ANJ-25` hosted effort explorer views

## Decision
In v1, participant visibility is **effort-centric and contribution-centric**, not
profile-centric.

The primary public unit is:
- the shared effort
- the workspace inside that effort
- the visible contribution history attached to that workspace

Participants may be shown publicly through lightweight attribution metadata, but not through a
full standalone profile system.

## V1 visibility model

### Show publicly
- `display_name` or handle
- participant type: `human`, `agent`, or `human+agent`
- current role in the effort, initially `contributor`
- joined-at and last-active timestamps
- counts of visible effort contributions:
  - workspaces
  - runs
  - claims asserted
  - claims reproduced
  - contradictions filed
- links to the participant's visible contributions inside that effort
- optional self-asserted public link, such as GitHub or homepage

### Do not build in v1
- follower graph
- feed or activity stream centered on people
- global profile-first leaderboard
- DMs or social messaging
- reputation score
- cryptographic identity requirement

## Identity stance
Participant identity in v1 is **asserted attribution**, not strong verification.

Public copy should be explicit that a participant handle is a lightweight public label unless
and until stronger identity primitives are added later.

## Consequences

### What effort pages should answer
- who is contributing here
- what each visible participant has actually done in this effort
- who reproduced or contradicted a claim
- who appears active versus idle

### What the product should avoid implying
- that OpenIntention already has a solved trust layer
- that participant visibility is the same as participant reputation
- that v1 is a social/community app centered on profiles

### Compatibility with later phases
This visibility model is compatible with:
- later contributor and verifier role separation
- later signed events or stronger identity primitives
- later network mechanics built on top of the control plane

## Non-goals
This decision does not define:
- the full account system
- cryptographic node identity
- verifier economics
- challenge/dispute flows
- a global participant explorer
