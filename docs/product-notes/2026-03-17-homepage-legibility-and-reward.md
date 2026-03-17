# Homepage Legibility and Reward

Date: 2026-03-17

## Status

This note captures the PM review of the current public surface and the resulting execution plan.

It follows from:
- `docs/product-notes/2026-03-17-openintention-goals-and-contributions.md`
- `docs/product-notes/2026-03-10-openintention-brand-architecture.md`

## Diagnosis

The architecture is ahead of the explanation.

The homepage, README, and goal pages still speak in builder/operator vocabulary:
efforts, frontiers, claims, projections, smoke reports, deterministic proofs, publication mirrors.

A newcomer cannot answer "what do I get?" within 10 seconds of landing on the page.

The system is no longer blocked on architecture clarity. It is blocked on product legibility
and reward.

## What the homepage gets right

- The hero headline is strong: "Turn an ML goal into shared progress for humans and agents."
- The problem statement is relatable: most ML work disappears into local loops.
- The one-command join path is a real differentiator.
- The transparency about what is real vs. proxy vs. future is honest and trust-building.
- The visual design speaks to the right audience.

## What the homepage gets wrong

### 1. The site talks to itself

Terms like "deterministic join proof," "repeated hosted participation proof," and "snapshot
briefs" mean nothing to a newcomer. These are verification artifacts for the builder, not
value propositions for the visitor.

### 2. The CTA requires a decision before action

The two-goal chooser (Eval Sprint vs. Inference Sprint) forces the visitor to understand
the difference before they can act. The homepage should have one clear thing to do.

### 3. The payoff after joining is weak

After running the command, the visitor should see their own contribution on a live goal page.
Today the link back is buried and the goal page does not highlight what just happened.

### 4. The proof section serves QA, not motivation

"Open deterministic join proof" and "Open repeated hosted participation proof" prove the
system works to us. A visitor wants to see what others achieved: metric movement, contributor
count, latest finding.

### 5. The README does too many jobs

~640 lines mixing product pitch, API reference, operator deployment, smoke tests, provenance
schema, and backup procedures. A visitor hitting the GitHub repo gets overwhelmed before they
find the one thing they can do.

## Audience for now

One person: an agent-native ML builder who already uses Claude or Codex and cares about
experiments compounding instead of disappearing.

Do not broaden the audience yet. Do not promise user-defined goals yet. Seeded goals are
the real product today.

Lean into "be early" rather than trying to look established.

## Execution plan

### P0: Tighten homepage CTA and reassurance (ANJ-93)

Replace the two-goal chooser with a single default action.

Lead CTA: `Join Eval in 1 command`
Reassurance line: `5 minutes. No special hardware. Leaves a visible workspace and claim.`

Keep inference-sprint as a secondary path but do not give it equal visual weight.

### P0: Post-join success deep link and highlighted contribution state (ANJ-94)

After the join command completes:
1. The script output should include a direct URL to the user's workspace on the live goal page
2. The goal page should visually highlight the most recent contribution
3. The handoff should be explicit: "here's what the next contributor should do"

### P0: Outcome-first homepage proof section (ANJ-95)

Replace the current proof section with:
- What improved (metric movement toward the goal)
- Who contributed (contributor count and latest participant)
- What the latest handoff is

Demote verification/smoke artifacts to a technical footer or `/evidence`. Do not remove
them — just move them out of the main story.

### P1: README split (ANJ-96)

First 50-80 lines: what is OpenIntention, why it matters, how to try it.
Everything else: dedicated docs links.

Keep the honest real/proxy/future framing, but after the action, not before.

### P1: Trust handling for curl | bash

Keep the one-liner, but pair it with:
- "View install script" link
- "Manual path" alternative

Prominently, not buried.

## Product test

The homepage is working when a newcomer can:
1. Understand what they get within 10 seconds
2. Act with one command within 30 seconds
3. See their own contribution on a live page within 5 minutes
4. Know what to hand to the next person or agent

If that does not happen, we are still explaining infrastructure, not delivering a product.
