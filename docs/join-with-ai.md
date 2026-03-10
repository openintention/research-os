# Join OpenIntention With an AI Agent

If you arrived from `https://openintention.io` or a social post, this is the shortest honest
path to participation.

This is not just a convenience document. It reflects the intended onboarding surface:
many newcomers will point Claude, Codex, or another agent at the public links and ask it to
help them participate. Agents are part of the target user surface here, not only back-end
actors inside the system.

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

Then do the narrow canonical participation path:
1. seed the local state
2. run the canonical seeded eval effort join flow
3. fetch the resulting publication output
4. summarize what happened, what claim was touched, and what I should inspect next

If the repo already contains a public-ingress smoke command, prefer that command first.
```

## Canonical local verification command

If the agent needs a deterministic end-to-end check from the public surface, run:

```bash
python scripts/run_public_ingress_smoke.py
```

That command starts from `https://openintention.io`, discovers the public repo URL, clones
the repo, installs it in an isolated venv, and runs the existing seeded-effort smoke flow.

## Fast local participation path

If you already cloned the repo:

```bash
python scripts/seed_demo.py --reset
uvicorn apps.api.main:app --reload
python -m clients.tiny_loop.run
```

## Honesty line

The current state is:
- the control plane, planner, seeded efforts, and publication mirrors are real
- the tiny-loop participation path is real
- the current tiny loop is still a proxy contribution path, not a production A100 or H100 benchmark harness

That distinction should stay visible in any agent-generated summary.
