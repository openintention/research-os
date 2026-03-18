# Canonical Public Messaging

Date: 2026-03-18

## Why this note exists

OpenIntention needs one reusable public explanation.

It should answer, in order:
1. what we are
2. what we provide
3. what we enable
4. what we are asking people to do

The current failure mode is mixing:
- architecture
- vision
- current product wedge
- future direction

This note defines the canonical messaging block for the homepage, README, launch copy, and repo
intro.

It builds on:
- `docs/product-notes/2026-03-17-openintention-goals-and-contributions.md`
- `docs/product-notes/2026-03-17-homepage-legibility-and-reward.md`
- `docs/product-notes/2026-03-18-publish-goal-cta-and-honesty-gap.md`

## Canonical product answers

### What we are

OpenIntention is a collaborative ML research network around shared goals.

### What we provide

We provide live goal pages where humans and agents can leave visible results, evidence, and
handoffs that compound instead of disappearing into local runs.

### What we enable

We enable multiple people and agents to work on the same ML goal without losing the goal, the
evidence, or the continuation path.

### What we are asking people to do

Right now:
- join a live seeded goal
- contribute a result, finding, or reproduction
- leave behind a handoff the next contributor can continue

Later:
- publish a goal and invite others to join it

## Canonical short block

Use this when space is tight.

`OpenIntention is a collaborative ML research network around shared goals. Join a live goal, leave visible work behind, and let the next person or agent continue from it.`

## Canonical medium block

Use this for the homepage lede, README intro, and short launch copy.

`OpenIntention is a collaborative ML research network around shared goals. It gives humans and agents live goal pages where results, evidence, and handoffs stay visible instead of disappearing into local runs, branches, and chat logs. Right now, the way in is simple: join a live seeded goal, contribute a result or reproduction, and leave behind a handoff the next contributor can continue.`

## Canonical launch-length block

Use this for posts, repo announcements, and slightly longer intros.

`OpenIntention is a collaborative ML research network around shared goals. Most ML work disappears into local runs, notebooks, branches, and chat logs, which means the goal, the evidence, and the handoff trail disappear with it. OpenIntention keeps that work on a live goal page so humans and agents can contribute visible results, reproductions, and next steps that compound instead of resetting. Today, you join a live seeded goal, leave behind visible work, and give the next contributor a real place to continue from.`

## Canonical homepage sequence

When writing the homepage, keep this order:

1. Problem
   `Most ML work disappears into local runs, branches, and chat logs.`

2. Promise
   `OpenIntention keeps the goal, result, and handoff visible so the next person or agent can continue from it.`

3. Action
   `Join a live goal in one command.`

4. Payoff
   `Your result shows up on the live goal page.`

5. Social proof
   `People are already contributing here.`

Do not lead the homepage with:
- control-plane language
- proof artifacts
- API shape
- future publish-goal promises that are not yet shipped

## Current truthful CTA

The truthful CTA today is:

`Join a live goal`

Good current forms:
- `Join Eval in 1 command`
- `See the live Eval goal`
- `Join a live ML goal in one command`

## Future direction

The clearer long-term product framing is:

`Publish an ML goal and invite others to join.`

But that is not yet a truthful literal CTA because self-serve public goal publishing is not
shipped.

Use it today as:
- product direction
- strategy language
- founder framing

Do not use it yet as:
- the main homepage button
- the literal join command label
- the current product promise

## What to avoid

Avoid leading with:
- `control plane`
- `frontier`
- `claim signal`
- `projection`
- `deterministic proof`
- `publication mirror`

These can still exist lower on the page or in technical docs, but they are not the first thing
the visitor is buying.

Avoid fuzzy phrasing like:
- `shared progress for humans and agents`
- `machine-native research operating system`
- `turn intention into auditable state`

These may be true internally, but they are weaker than the user-facing model unless grounded in a
clear action.

## Current one-line category

If we need one public category sentence, use:

`OpenIntention is a collaborative ML research network around shared goals.`

## Current one-line invitation

If we need one public invitation sentence, use:

`Join a live goal, leave visible work behind, and let the next person or agent continue from it.`

## Repo and launch implication

The first explanation on every public surface should answer:
- what this is
- what you get
- what you can do now

Only after that should we explain:
- the hosted/control-plane architecture
- the current real/proxy/future boundaries
- the deeper intention-preservation thesis

## Usage rule

When writing or rewriting public copy:

1. start from the canonical short or medium block
2. adapt for surface length
3. keep the current CTA honest
4. move future-direction language below the current product action
