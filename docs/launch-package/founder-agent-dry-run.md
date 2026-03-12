# Founder Agent Dry Run

This is a pre-launch gate.

Before Ali posts publicly, he should behave like the first real newcomer and ask an external
AI agent to participate in OpenIntention.

The point is not only to verify product behavior. It is to verify that the announcement copy,
site, and repo together are sufficient as an onboarding surface for a human-plus-agent pair.

## Inputs to give the agent

Give the agent only:
- the final founder-post draft
- `https://openintention.io`
- `https://github.com/openintention/research-os`

Do not give it hidden internal context from this chat.

## Prompt to use

```text
Help me participate in OpenIntention.

Start from this public announcement text, the public site, and the public repo only.

Your job:
1. infer what OpenIntention is
2. infer what is real today versus what is still proxy behavior
3. onboard me into the narrow canonical participation path
4. execute the path if possible
5. summarize what happened, what evidence was created, and what I should inspect next

Be explicit if anything is ambiguous, missing, or misleading from the public materials.

Public links:
- https://openintention.io
- https://github.com/openintention/research-os
```

## Pass criteria

- the agent finds the repo and site without extra help
- the agent understands that `OpenIntention` is the public brand and `research-os` is the technical repo
- the agent identifies the seeded eval and inference efforts
- the agent correctly distinguishes real control-plane behavior from proxy client behavior
- the agent can find and use the join path or the canonical public-ingress smoke command
- the agent produces an inspectable summary of what happened

## Fail criteria

- the agent thinks there is already a community app or sign-up flow
- the agent cannot tell what is real versus proxy
- the agent cannot discover how to participate
- the agent requires hidden context that is not available from the public surfaces
- the agent implies outside affiliation or origin that is not stated in the public materials

## If it fails

- do not post yet
- fix the public artifact that caused confusion:
  - founder-post draft
  - reply thread
  - `openintention.io`
  - repo docs
- rerun this dry run until the path is clear
