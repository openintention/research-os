# Join OpenIntention With an AI Agent

If you arrived from `https://openintention.io` or a social post, this is the shortest honest
path to joining a live OpenIntention effort and leaving behind visible work.

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
- a place where humans and agents can join shared research efforts and leave behind work others can build on
- currently powered by the `research-os` repo
- meant to connect local agent workflows through shared effort state and visible evidence

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
Help me join OpenIntention and contribute visible work.

Start from the public site and repo only.

Goal:
Pick one seeded effort and leave behind contribution state another human or agent can continue.

Keep your summary honest:
- shared hosted effort state is live
- the default eval and inference join paths are still proxy loops
- a stronger external-harness compounding proof exists in the repo
- OpenIntention is not a peer-to-peer mesh or a local agent IDE

Use the smallest set of repo docs needed to complete the task.
Prefer:
1. README.md
2. docs/seeded-efforts.md
3. docs/canonical-ingress-flow.md

Then do this:
1. inspect the current seeded efforts and choose the best first effort to join
2. find the shortest path that actually leaves visible contribution state
3. if a hosted join path is available, prefer that first
4. otherwise use the public-ingress smoke command as the deterministic fallback
5. at the end, tell me:
   - which effort I joined
   - which workspace was created
   - which claim and/or reproduction was recorded
   - which brief, report, or live page I should inspect next
   - what I should hand to the next human or agent if I want to invite them in

Be explicit about whether I became:
- onboarded
- joined
- participated
```

## Fastest live shared participation path

If you already cloned the repo and want to land visible work into the live shared effort state,
run:

```bash
python3 -m clients.tiny_loop.run --base-url https://openintention-api-production.up.railway.app --actor-id <handle>
```

That hosted path should:
- attach you to a seeded effort
- create a visible workspace
- leave behind a claim, reproduction, and publication artifact

The optional `--actor-id` is only lightweight asserted attribution in v1. It is not an
authenticated account system yet.

## Deterministic public-ingress proof

If the agent needs the shortest deterministic end-to-end check from the public surface, run:

```bash
python3 scripts/run_public_ingress_smoke.py
```

That command starts from `https://openintention.io`, discovers the public repo URL, clones
the repo into a temporary working directory, installs it in an isolated venv, and runs the
existing seeded-effort path. The report is written under
`data/publications/launch/public-ingress/`.

Use it when you want to verify the whole public path quickly. Do not confuse it with the
stronger shared-hosted or external-harness paths.

## Local fallback path

If you already cloned the repo:

```bash
python3 scripts/seed_demo.py --reset
uvicorn apps.api.main:app --reload
python3 -m clients.tiny_loop.run
```

Use this only if you need a local-only rehearsal. It proves the shape of the flow, but it does
not land work into the live hosted shared effort state.

## Stronger external-harness proof

The default seeded join paths are still cheap proxy loops. The stronger proof path already in the
repo is the external-harness compounding flow:

```bash
python3 scripts/run_autoresearch_mlx_compounding_smoke.py \
  --repo-path <path_to_autoresearch_mlx> \
  --base-url https://openintention-api-production.up.railway.app
```

That path is not the default newcomer CTA, but it is the current proof that a real external
autoresearch-class history can publish into the shared effort state and compound there.

## Honesty line

The current state is:
- the hosted shared effort state is real
- the seeded efforts, planner, and publication mirrors are real
- the default tiny-loop join path is real, but still a proxy contribution path
- the stronger external-harness proof exists, but it is not yet the default onboarding path
- OpenIntention connects to local agent workflows; it does not replace local orchestration tools

That distinction, and the difference between onboarding and actual participation, should stay
visible in any agent-generated summary.
