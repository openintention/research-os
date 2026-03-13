# Join OpenIntention With an AI Agent

If you arrived from `https://openintention.io` or a social post, this is the shortest honest
path to joining a live OpenIntention effort and leaving behind visible work other people can
continue.

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

## Freshness model

Keep these three surfaces separate when you inspect the project:

- live hosted state:
  - `https://openintention.io/efforts`
  - hosted API endpoints and publication mirrors
  - use this for the current shared effort state
- generated snapshot evidence:
  - `data/publications/efforts/*.md`
  - the bundled evidence pages under `apps/site/dist/evidence/`
  - refresh with `python3 scripts/export_effort_briefs.py` and `python3 scripts/build_microsite.py`
- deterministic smoke reports:
  - `data/publications/launch/public-ingress/`
  - `data/publications/launch/shared-participation/`
  - `data/publications/launch/nightly-contribution-window-smoke/`
  - `data/publications/launch/overnight-autoresearch-worker-smoke/`
  - use these to prove a path works end to end, not as live counters

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

API contract note: when sending provenance for snapshot/claim payloads, clients can now add:
- `<payload>_manifest_uri`
- `<payload>_manifest_digest`
- `<payload>_manifest_signature`
- `<payload>_signature_scheme`
- `<payload>_provenance_schema`
- `<payload>_provenance_version`

Canonical value for this release:
- provenance schema: `openintention-artifact-manifest-v1`
- provenance version: `1`

Where `<payload>` is either `source_bundle` (snapshot) or `candidate_snapshot` (claim).
Legacy payloads that only include the base provenance fields are still accepted for now.

Then do this:
1. inspect the current seeded efforts and choose the best first effort to join
2. find the shortest path that actually leaves visible contribution state
3. if `curl -fsSL https://openintention.io/join | bash` exists, prefer that first
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

If you already cloned the repo and want the shortest path into the live shared effort state, run:

```bash
curl -fsSL https://openintention.io/join | bash
```

To join the inference effort instead:

```bash
curl -fsSL https://openintention.io/join | bash -s -- --profile inference-sprint
```

To attach a lightweight public handle in v1:

```bash
curl -fsSL https://openintention.io/join | bash -s -- --actor-id <handle>
```

That hosted path should:
- attach you to a seeded effort
- create a visible workspace
- leave behind a claim, reproduction, and publication artifact

The optional `--actor-id` is only lightweight asserted attribution in v1. It is not an
authenticated account system yet.

## Run a bounded overnight contribution window

If you want to keep helping one seeded effort while you are away from the keyboard, run a
bounded overnight contribution window:

```bash
curl -fsSL https://openintention.io/join | bash -s -- --nightly --actor-id <handle> --window-seconds 28800
```

To point the same window at the inference effort instead:

```bash
curl -fsSL https://openintention.io/join | bash -s -- --nightly --profile inference-sprint --actor-id <handle> --window-seconds 28800
```

That path is still honest and narrow:
- it is one local machine intentionally running repeated loops for one hosted effort
- you choose the effort and the time budget
- it leaves behind the same live evidence as a manual join
- it does not auto-detect idleness, rotate effort, or turn your machine into a mesh node
- this is an opt-in bounded contribution window, not a mesh worker or always-on daemon

## Run the real overnight autoresearch worker

If you want the stronger advanced path, use the worker mode instead of `--nightly`:

```bash
curl -fsSL https://openintention.io/join | bash -s -- \
  --worker \
  --repo-path <path_to_mlx_history> \
  --runner-command "<external_harness_command>" \
  --actor-id <handle> \
  --window-seconds 28800 \
  --budget-cap-seconds 2400
```

That path is different on purpose:
- it runs a real local command against an external repo before every import attempt
- it only imports newly kept `results.tsv` outcomes into the hosted shared effort
- each imported keep leaves behind operator-attributed workspace, claim, and discussion state
- it is still one operator on one machine with explicit wall-clock and compute caps
- it is not a mesh worker, verifier network, or always-on daemon

## Deterministic public-ingress proof

If the agent needs the shortest deterministic end-to-end check from the public surface, run:

```bash
python3 scripts/run_public_ingress_smoke.py
```

That command starts from `https://openintention.io`, discovers the public repo URL, clones
the repo into a temporary working directory, installs it in an isolated venv, and verifies the
existing seeded-effort path. The report is written under
`data/publications/launch/public-ingress/`.

Use it when you want to verify the whole public path quickly. Do not confuse it with the
actual hosted join path or the stronger external-harness paths.

For the deterministic advanced-worker rehearsal, run:

```bash
python3 scripts/run_overnight_autoresearch_worker_smoke.py
```

That smoke stands up a disposable local API and a disposable external-harness repo fixture, then
proves the worker imports two kept results into shared state with bounded stop conditions.

## Local fallback path

If you already cloned the repo:

```bash
python3 scripts/seed_demo.py --reset
uvicorn apps.api.main:app --reload
python3 -m clients.tiny_loop.run
```

Use this only if you need a local-only rehearsal. It proves the shape of the flow, but it does
not land work into the live hosted shared effort state.

## Stronger external MLX proof

The default seeded join paths are still cheap proxy loops. The earlier proof path still in the
repo is the one-shot external-harness compounding flow:

```bash
python3 scripts/run_mlx_history_compounding_smoke.py \
  --repo-path <path_to_mlx_history> \
  --base-url https://openintention-api-production.up.railway.app
```

That proof is still useful, but the current advanced operator path is the real overnight worker
above.

## Honesty line

The current state is:
- the hosted shared effort state is real
- the seeded efforts, planner, and publication mirrors are real
- the default tiny-loop join path is real, but still a proxy contribution path
- the real overnight worker exists for the narrow MLX/results.tsv adapter, but it is not yet the default onboarding path
- OpenIntention connects to local agent workflows; it does not replace local orchestration tools

That distinction, and the difference between onboarding and actual participation, should stay
visible in any agent-generated summary.
