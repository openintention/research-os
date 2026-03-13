# Production Runbook

This is the minimum operator runbook for the current OpenIntention v1 production floor.

It is intentionally small and only covers the real deployed shape:
- one Railway API service
- one Railway site service
- one mounted `/data` volume on the API
- one public ingress surface at `https://openintention.io`

## Current production services

- Railway project: `openintention`
- API service: `openintention-api`
- Site service: `openintention-site`
- API base URL: `https://api.openintention.io`
- Public site URL: `https://openintention.io`
- Mounted volume: `/data` on `openintention-api`

## Required production variables

### API

```bash
RESEARCH_OS_DB_PATH=/data/research_os.db
RESEARCH_OS_ARTIFACT_ROOT=/data/artifacts
RESEARCH_OS_PUBLIC_BASE_URL=https://api.openintention.io
RESEARCH_OS_BOOTSTRAP_SEEDED_EFFORTS=true
```

### Site

```bash
OPENINTENTION_API_BASE_URL=https://api.openintention.io
OPENINTENTION_API_FETCH_BASE_URL=http://${{openintention-api.RAILWAY_PRIVATE_DOMAIN}}:8080
OPENINTENTION_REPO_URL=https://github.com/openintention/research-os
```

`OPENINTENTION_API_BASE_URL` is the public URL exposed in user-facing links and join commands.
`OPENINTENTION_API_FETCH_BASE_URL` is the private Railway service-to-service URL used by the
server-rendered effort explorer at request time.

## Deploy

Deploy the current repo to Railway:

```bash
railway up --service openintention-api --ci -m "Deploy API"
railway up --service openintention-site --ci -m "Deploy site"
```

After deploy, verify service status:

```bash
railway service status --all --json
```

## Restart

Restart without rebuilding:

```bash
railway restart --service openintention-api
railway restart --service openintention-site
```

## Failure triage

Check current service status:

```bash
railway status --json
railway service status --all --json
```

Read recent logs:

```bash
railway logs --service openintention-api --lines 200 --json
railway logs --service openintention-site --lines 200 --json
```

Quick live checks:

```bash
curl -fsSL https://api.openintention.io/healthz
curl -fsSL https://openintention.io/efforts | head
```

Verify the site is wired to the private fetch base:

```bash
railway variable list --service openintention-site --json | jq '.OPENINTENTION_API_FETCH_BASE_URL'
```

## Production smoke

Run the production smoke floor:

```bash
python3 scripts/run_production_smoke.py \
  --site-url https://openintention.io \
  --api-base-url https://api.openintention.io
```

This should produce:
- `data/publications/launch/production-smoke/production-smoke.md`
- `data/publications/launch/production-smoke/public-ingress/public-ingress-smoke.md`
- `data/publications/launch/production-smoke/shared-participation/shared-participation-smoke.md`

## Proof effort rollover

Long-lived public proof efforts should be rolled forward, not reset in place.

Operator command:

```bash
python3 scripts/rollover_proof_effort.py \
  --base-url https://api.openintention.io \
  --effort-name "Eval Sprint: improve validation loss under fixed budget"
```

Use the same command with `--successor-name`, `--proof-series`, repeated `--set-tag`, and optional
`--drop-tag` whenever a proof-series rollover also needs a refreshed external-harness join surface.

Rehearsal path:

```bash
python3 scripts/run_proof_effort_rollover_smoke.py \
  --base-url http://127.0.0.1:8000
```

## Backup

### Local or attached runtime state

Create one archive containing the SQLite database, artifact root, and a manifest:

```bash
python3 scripts/backup_runtime_state.py --output-path data/backups/runtime-state.tar.gz
```

Restore it into a fresh or empty target:

```bash
python3 scripts/restore_runtime_state.py \
  --archive-path data/backups/runtime-state.tar.gz \
  --force
```

### Production volume capture from Railway

Download the live `/data` volume as an off-volume archive:

```bash
python3 scripts/backup_railway_volume.py \
  --service openintention-api \
  --output-path data/backups/openintention-production-data.tar.gz
```

This is the current non-destructive production backup path.

## Recovery

The tested recovery path today is:
1. capture a backup archive
2. restore it into a fresh local runtime target with `restore_runtime_state.py`
3. if production recovery is needed, stop or restart the API after replacing `/data`

For a Railway service recovery, the safest current operator path is:
- take a fresh off-volume backup first
- attach to the API service with `railway ssh --service openintention-api`
- replace `/data/research_os.db` and `/data/artifacts` from a known-good archive
- restart the API service
- rerun `scripts/run_production_smoke.py`

We have verified the archive format and restore path locally. We have not yet performed a
destructive restore against the live production volume.

## Residual risks

- the production volume is single-region and single-node today
- proof efforts are append-only, so operators still need judgment about when to roll to a fresh proof window
