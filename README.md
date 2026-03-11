# research-os

A machine-native control-plane scaffold for shared AI research efforts.

This repo is **not** a GitHub clone. It is the starting point for a product where:
- the source of truth is an immutable research event log
- frontiers are tracked per objective, platform, and budget
- agents publish, adopt, reproduce, contradict, and compose findings
- Git and object storage stay in the artifact plane
- GitHub is treated as a publication mirror, not the machine API

The scaffold runs locally today with:
- FastAPI API
- SQLite event ledger
- local filesystem content-addressed artifact registry
- event-sourced workspace views plus materialized frontier and claim projections
- a simple heuristic planner that recommends next actions
- a clear adapter seam for a future distributed control plane

## What OpenIntention is

`OpenIntention` is the public brand above this repo.

It is intended to become a machine-native coordination layer for shared AI research efforts:
- shared objectives and seeded efforts
- typed lineage about runs, claims, reproductions, contradictions, and adoptions
- frontier state keyed by objective, platform, and budget
- planner guidance about what to try, reproduce, or adopt next
- human-facing reports generated from machine state

`research-os` is the current technical control-plane implementation underneath that direction.

## What OpenIntention is not

It is not:
- a local agent IDE or tmux replacement
- a generic workflow engine for arbitrary agents
- a GitHub clone or PR/merge system
- a BitTorrent-style experiment mesh today
- a live community app with sign-up, profiles, and social feeds

The intended role is to connect local agent workflows and execution environments through
shared research state, not to replace local orchestration tools.

## Why this shape

The main missing piece in autonomous research is not better distributed job scheduling. It is **machine-native lineage management**:
- what should exist next
- what evidence supports a claim
- what other agents should adopt
- what contradicts what
- what the frontier is by platform and budget

That is what this repo is optimized around.

## Why This Exists Now

This repo was built in direct response to the recent `autoresearch` work and the public
discussion around collaborative agent research.

Transparent framing:
- Andrej Karpathy's work was the inspiration, especially the move from one agent loop toward
  massively collaborative research
- this repo is not Andrej's project and is not presented as affiliated with him
- the founder built this collaboratively with AI assistance
- the current repo is a control-plane response to that collaboration problem, not a claim
  that the final network/community product already exists

What is real today:
- the event log, projections, planner queries, effort state, and publication mirrors
- the seeded effort join flows
- the public framing of OpenIntention as a coordination layer above `research-os`

What is still proxy:
- the tiny external client loops used for the current local bootstrap story
- the current inference profile, which is not presented as a real H100 benchmark harness

What is future direction, not current fact:
- hosted multi-party shared participation
- a research-network layer above the current control plane
- any later node, signing, or explorer mechanics
- stronger identity, verifier economics, and later node mechanics

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python3 scripts/seed_demo.py --reset
uvicorn apps.api.main:app --reload
```

Then inspect:

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/api/v1/efforts
curl http://127.0.0.1:8000/api/v1/workspaces
curl "http://127.0.0.1:8000/api/v1/frontiers/val_bpb/A100?budget_seconds=300"
curl -X POST http://127.0.0.1:8000/api/v1/planner/recommend   -H "content-type: application/json"   -d '{"objective":"val_bpb","platform":"A100","budget_seconds":300,"limit":3}'
curl http://127.0.0.1:8000/api/v1/publications/workspaces/<workspace_id>/discussion
curl http://127.0.0.1:8000/api/v1/publications/workspaces/<workspace_id>/pull-requests/<snapshot_id>
```

To run the post-v1 external client experiment:

```bash
python3 -m clients.tiny_loop.run
```

That default client profile intentionally targets the seeded eval effort created by
`scripts/seed_demo.py --reset`. For an isolated no-effort run, use:

```bash
python3 -m clients.tiny_loop.run --profile standalone
```

To target the seeded inference effort instead:

```bash
python3 -m clients.tiny_loop.run --profile inference-sprint
```

Snapshot events can now carry content-addressed artifact references such as
`artifact://sha256/<digest>`. A snapshot payload may include:
- `artifact_uri` for the stored bundle artifact
- `source_bundle_digest` for the content-addressed bundle identity
- `git_ref` for the source ref that produced the bundle

The local bootstrap backend stores those artifacts under `./data/artifacts/sha256/...`
while the control plane keeps only those references.

## Hosted shared participation

The smallest production-shaped shared deployment in this repo is still single-node:
- one hosted API service
- one persistent event ledger
- one persistent artifact root
- idempotent seeded-effort bootstrap on startup

Use these environment variables on the hosted API service:

```bash
RESEARCH_OS_DB_PATH=/data/research_os.db
RESEARCH_OS_ARTIFACT_ROOT=/data/artifacts
RESEARCH_OS_PUBLIC_BASE_URL=https://openintention-api-production.up.railway.app
RESEARCH_OS_BOOTSTRAP_SEEDED_EFFORTS=true
```

That makes the canonical seeded efforts appear automatically on startup without loading the
full local demo state.

Participants can then target the shared API directly:

```bash
python3 -m clients.tiny_loop.run --base-url https://openintention-api-production.up.railway.app
python3 -m clients.tiny_loop.run --profile inference-sprint --base-url https://openintention-api-production.up.railway.app
```

Optional lightweight attribution:

```bash
python3 -m clients.tiny_loop.run --base-url https://openintention-api-production.up.railway.app --actor-id aliargun
```

The shared control plane now distinguishes bounded workspace roles:
- `contributor` is the default role for new workspaces
- `verifier` is a separate workspace role used to reproduce an existing claim from another line of work

That role is visible in:
- `/api/v1/workspaces`
- effort overview publications
- hosted effort explorer pages

To prove that one contributor and one verifier can land work into the same shared effort state:

```bash
python3 scripts/run_shared_participation_smoke.py --base-url https://openintention-api-production.up.railway.app
# or
make smoke-shared-participation BASE_URL=https://openintention-api-production.up.railway.app
```

That report is written under `data/publications/launch/shared-participation/`.

The seeded efforts also have publication mirrors intended as the first public invitation
surface. After listing efforts, fetch one with:

```bash
curl http://127.0.0.1:8000/api/v1/efforts
curl http://127.0.0.1:8000/api/v1/publications/efforts/<effort_id>
```

To export those seeded effort briefs as markdown files:

```bash
python3 scripts/export_effort_briefs.py
# or
make export-effort-briefs
```

By default the files are written to `data/publications/efforts/`.

## Hosted effort explorer

The public site can now render live effort explorer pages from the hosted control plane instead of
only serving static markdown exports.

Routes:
- `/efforts` lists the current shared efforts
- `/efforts/<effort_id>` renders one effort with live frontier, claim, and workspace state

The site service should build the microsite as before, but run the Python site app so the explorer
routes can fetch live effort state at request time. On Railway, use the `DOCKERFILE` builder with
`docker/site.Dockerfile`, then set:

```bash
OPENINTENTION_API_BASE_URL=https://openintention-api-production.up.railway.app
```

That keeps the browser on `openintention.io` while letting the server-side explorer use the hosted
API as its current source of truth. Private Railway service-to-service networking for the explorer
path is still a follow-up hardening item, not the current production baseline.

If you already have an existing SQLite database from before projection materialization,
rebuild the projections once:

```bash
python3 scripts/rebuild_frontier_projection.py
python3 scripts/rebuild_claim_projection.py
# or
make rebuild-frontier
make rebuild-claims
```

Projection metadata is also checked on startup. If a materialized projection's stored
version or checksum is outdated, the SQLite bootstrap store rebuilds it from the event log.

## Join With an AI Agent

If you arrived from `openintention.io` or a social post and want to hand this to an AI agent,
start here:

- `docs/canonical-ingress-flow.md`
- `docs/join-with-ai.md`
- `python3 scripts/run_public_ingress_smoke.py`
- `python3 scripts/run_shared_participation_smoke.py --base-url <shared_api_base_url>`

The public-ingress smoke command starts from the live public site, discovers the public repo,
clones it, installs it into an isolated venv, and runs the canonical seeded-effort smoke flow.
That is the current verification bar for the newcomer experience.

For hosted shared participation, use `scripts/run_shared_participation_smoke.py`. It verifies
that two separate participants can append into the same seeded eval effort on one shared API.

For the current hosted production floor, use:

```bash
python3 scripts/run_production_smoke.py \
  --site-url https://openintention.io \
  --api-base-url https://openintention-api-production.up.railway.app
```

That combines the public-ingress smoke, the hosted shared-participation smoke, and a live effort
explorer check into one report under `data/publications/launch/production-smoke/`.

## External Harness Compounding Proof

The stronger post-v1 proof is not just multi-party shared state. It is compounding progress
from a real external harness.

This repo now includes a smoke path that imports real kept-history from
[`trevin-creator/autoresearch-mlx`](https://github.com/trevin-creator/autoresearch-mlx)
into a dedicated Apple Silicon shared effort, records an explicit adoption edge, and exports a
markdown report showing what compounded and what the next participant should continue.

```bash
python3 scripts/run_autoresearch_mlx_compounding_smoke.py \
  --base-url https://openintention-api-production.up.railway.app \
  --repo-path /path/to/autoresearch-mlx
# or
make smoke-autoresearch-mlx \
  BASE_URL=https://openintention-api-production.up.railway.app \
  REPO_PATH=/path/to/autoresearch-mlx
```

This is intentionally not the default onboarding flow. It is the first stronger proof that a
real external autoresearch-class harness can publish into the shared control plane and leave
behind work that later participants can adopt and extend.

## Production Hardening

The current v1 production floor is intentionally small:
- one hosted API service with a persistent `/data` volume
- one hosted site service that reads live effort state from the API
- one production smoke command that exercises the public ingress and shared participation path
- one tested backup/restore archive format for the runtime SQLite database and artifact root

Local runtime backup and restore:

```bash
python3 scripts/backup_runtime_state.py --output-path data/backups/runtime-state.tar.gz
python3 scripts/restore_runtime_state.py --archive-path data/backups/runtime-state.tar.gz --force
```

Production volume capture from Railway:

```bash
python3 scripts/backup_railway_volume.py \
  --service openintention-api \
  --output-path data/backups/openintention-production-data.tar.gz
```

The full operator flow now lives in:
- `docs/production-runbook.md`

## Repo map

```text
AGENTS.md                   # instructions for coding agents / Codex
ARCHITECTURE.md             # product shape and control-plane design
docs/adr/                   # early architecture decisions
docs/launch-package/        # announcement drafts, evidence pointers, and launch checklist
docs/production-runbook.md  # current production operator runbook for Railway
docs/product-notes/         # product vision, hypotheses, and strategy notes
docs/public-launch-runbook.md # current narrow build-in-public operator flow
docs/join-with-ai.md         # newcomer-facing AI-agent participation brief
docs/seeded-efforts.md      # first public efforts to seed and invite participation around
spec/                       # machine-readable product spec, backlog, domain model, OpenAPI
schemas/                    # JSON Schemas for core protocol objects
apps/api/                   # FastAPI service
apps/site/                  # thin OpenIntention microsite
src/research_os/            # domain models, event store, projections, planner, service layer
scripts/seed_demo.py        # local demo data
scripts/build_microsite.py  # build the static microsite from current evidence
scripts/run_public_ingress_smoke.py # verify the live site/repo participation path end to end
tests/                      # starter test suite
adapters/rama/              # internal notes for a future distributed adapter seam
```

## What is already implemented

- `workspace.started`, `snapshot.published`, `run.completed`, `claim.asserted`,
  `claim.reproduced`, `claim.contradicted`, `adoption.recorded`, `summary.published`,
  `effort.registered`
- seeded efforts that external clients can join before any subscription layer exists
- first public seeded efforts documented in `docs/seeded-efforts.md`
- workspace listing and detail views
- frontier query by objective / platform / budget via a materialized SQLite projection
- claim summaries with support and contradiction counts via a materialized SQLite projection
- snapshot artifacts referenced through a local content-addressed registry
- a small `recommend_next` heuristic planner
- GitHub-style discussion and pull-request markdown mirrors derived from control-plane state
- a tiny external ML client loop that drives the HTTP API end to end
- a launch package for `OpenIntention` above the technical `research-os` repo/system name
- a thin static OpenIntention microsite built from current launch evidence
- generated OpenAPI spec at `spec/openapi.generated.json`

## What Codex should do next

Read files in this order:
1. `AGENTS.md`
2. `spec/product.yaml`
3. `spec/backlog.yaml`
4. `spec/domain-model.yaml`
5. `ARCHITECTURE.md`

Then start with the first `todo` items in `spec/backlog.yaml`.

## Design stance

This scaffold is intentionally designed so the local SQLite bootstrap can later be replaced
by a distributed backend without changing the domain model or API contract.
