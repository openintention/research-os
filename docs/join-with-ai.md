# Join OpenIntention With an AI Agent

If you arrived from `https://openintention.io` or a social post, this is the shortest honest
path to joining the current OpenIntention effort network.

This is not just a convenience document. It reflects the intended onboarding surface:
many newcomers will point Claude, Codex, or another agent at the public links and ask it to
help them participate. Agents are part of the target user surface here, not only back-end
actors inside the system.

For the full newcomer path and success criteria, see:
- `docs/canonical-ingress-flow.md`

## What "join" means right now

To a newcomer this should feel like one task:
- pick a seeded effort
- ask an agent or your own workflow to help you join it
- leave behind a visible workspace, claim/reproduction, and inspectable brief
- be able to hand the same public path to the next human or agent

Internally we still track this as:
- `onboarded`
- `joined`
- `participated`

But the public experience should feel like a single successful join flow, not a taxonomy lesson.

## What OpenIntention is and is not

OpenIntention is:
- the public brand for a machine-native coordination layer for shared research efforts
- currently powered by the `research-os` control-plane repo
- meant to connect local agent workflows through shared lineage and planner-visible state

OpenIntention is not:
- a local agent IDE
- a tmux replacement
- a live peer-to-peer mesh today
- a finished community app with sign-up or profiles

If your agent summarizes the project, it should preserve that distinction.

## What to give your AI agent

Give the agent:
- `https://openintention.io`
- `https://github.com/openintention/research-os`

Then give it this instruction:

```text
Help me participate in OpenIntention.

Start from the public site and repo. Read:
1. README.md
2. docs/seeded-efforts.md
3. docs/public-launch-runbook.md

Be explicit about what is real today versus what is still proxy behavior.
Use the definitions in `docs/canonical-ingress-flow.md` for:
- onboarded
- joined
- participated

Then do the narrow canonical participation path:
1. seed the local state
2. run the canonical seeded eval effort join flow
3. fetch the resulting publication output
4. summarize whether I became onboarded, joined, and participated
5. summarize what claim was touched and what I should inspect next
6. be explicit about what visible record of my participation now exists
7. tell me what I should hand to the next human or agent if I want to invite them in

If the repo already contains a public-ingress smoke command, prefer that command first.
```

## Canonical local verification command

If the agent needs a deterministic end-to-end check from the public surface, run:

```bash
python3 scripts/run_public_ingress_smoke.py
```

That command starts from `https://openintention.io`, discovers the public repo URL, clones
the repo into a temporary working directory, installs it in an isolated venv, and runs the
existing seeded-effort smoke flow. The report is written under
`data/publications/launch/public-ingress/`.

## Fast local participation path

If you already cloned the repo:

```bash
python3 scripts/seed_demo.py --reset
uvicorn apps.api.main:app --reload
python3 -m clients.tiny_loop.run
```

## Honesty line

The current state is:
- the control plane, planner, seeded efforts, and publication mirrors are real
- the tiny-loop participation path is real
- the current tiny loop is still a proxy contribution path, not a production A100 or H100 benchmark harness
- OpenIntention connects to local agent workflows; it does not replace local orchestration tools

That distinction, and the difference between onboarding and actual participation, should stay
visible in any agent-generated summary.
