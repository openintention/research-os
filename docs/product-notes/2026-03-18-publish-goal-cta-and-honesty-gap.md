# Publish-Goal CTA And Honesty Gap

Date: 2026-03-18

## Why this note exists

The product becomes easier to understand when described as:

`Publish an ML goal and invite others to join.`

That is more self-explanatory than:
- `turn an ML goal into shared progress`
- `join a seeded effort`
- `control plane for shared research`

But the current product does not yet support true self-serve public goal publishing.

This note defines:
- the north-star product framing
- the current truthful public promise
- the minimum feature gap before the publish-goal CTA can become literal

It builds on:
- `docs/product-notes/2026-03-17-openintention-goals-and-contributions.md`
- `docs/product-notes/2026-03-17-goal-to-effort-translation.md`
- `docs/product-notes/2026-03-17-homepage-legibility-and-reward.md`

See also:
- `docs/product-notes/2026-03-18-canonical-public-messaging.md`

## What is clearer than the current framing

The public product is easier to grasp when the user model is:

1. publish a goal
2. invite others to join it
3. let humans and agents contribute visible work
4. watch the goal move through shared evidence and handoffs

This is clearer because it explains:
- what a user can do here
- why other people matter
- what OpenIntention is coordinating

It also matches the name better:
- the intention is made public
- the goal is explicit
- the resulting work stays attached to that goal

## Current truthful framing

Today the honest product story is still:

`Join a live ML goal and leave visible work behind.`

More fully:

`OpenIntention lets people and agents join seeded ML goals, contribute visible work, and leave behind evidence and handoffs the next contributor can continue.`

This is what is actually shipped:
- seeded goals exist
- the live goal pages are real
- people and agents can join them
- contributions are visible
- handoffs are real

This is what is not yet shipped:
- self-serve public goal creation
- a first-class publish flow on the web
- moderation/review for newly published goals
- public goal-author ownership and lifecycle controls

## North-star framing

The right product direction is:

`Publish an ML goal. Let people and agents move it forward.`

That should eventually become the product's cleanest explanation because it names:
- the object: a goal
- the action: publish
- the network effect: others join and contribute

But it should not become the literal primary CTA until the feature exists.

## The honesty gap

If the homepage says `Publish an ML goal` today, the product would create a trust break.

A visitor would reasonably expect:
- a form or command to create a goal
- a resulting public goal page
- a way to invite others into it
- some visibility into ownership, edits, or revisions

Today we only have the second half of that story:
- live goal participation
- visible contribution
- auditable continuation

We do not yet have the first half:
- user-authored goal publication

So the correct rule is:

Use publish/join language as the north-star product model.

Do not use `Publish an ML goal` as the main clickable CTA until self-serve goal publishing is real.

## What the homepage should say until then

Until the publish path exists, the homepage should stay grounded in the shipped wedge:

- headline can move closer to the publish/join model
- the primary action should remain a join action
- the page should explain that the visitor is joining a live seeded goal

Good near-term forms:
- `Join a live ML goal in one command.`
- `Make ML work compound instead of disappear.`
- `See the live Eval goal.`

Avoid for now:
- `Publish an ML goal`
- `Start your own goal`
- `Post a goal`

## Minimum feature before the CTA becomes literal

Before `Publish an ML goal` can become the primary CTA, the product needs at least:

1. A goal publication path
   A real web or CLI flow to create a new goal from user input.

2. Goal operationalization
   The input must become operational enough for contribution:
   - objective
   - metric
   - direction
   - constraints
   - budget
   - evidence requirement
   - stop condition

3. Goal page creation
   The publish flow must create a live public goal page with a stable URL.

4. Invitation path
   The author must be able to hand others a join path tied to that goal.

5. Basic governance
   Some minimum review, moderation, or visibility rules are needed so goal creation does not turn
   the surface into noise.

## PM implication

The current product wedge is still:

`join a live seeded goal`

The future product category is:

`publish or join ML goals that humans and agents can move forward together`

That means the sequencing should be:

1. keep the public surface honest around seeded-goal participation
2. use publish/join framing in product notes and strategy
3. build self-serve goal publishing
4. only then promote `Publish an ML goal` to the main CTA

## Recommended next issue

The next product issue to make this real is:

`Build self-serve publish-goal path with operationalization and public goal-page creation.`
