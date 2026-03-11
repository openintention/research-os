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
- API base URL: `https://openintention-api-production.up.railway.app`
- Public site URL: `https://openintention.io`
- Mounted volume: `/data` on `openintention-api`

## Required production variables

### API

```bash
RESEARCH_OS_DB_PATH=/data/research_os.db
RESEARCH_OS_ARTIFACT_ROOT=/data/artifacts
RESEARCH_OS_PUBLIC_BASE_URL=https://openintention-api-production.up.railway.app
RESEARCH_OS_BOOTSTRAP_SEEDED_EFFORTS=true
```

### Site

```bash
OPENINTENTION_API_BASE_URL=https://openintention-api-production.up.railway.app
OPENINTENTION_REPO_URL=https://github.com/openintention/research-os
```

The site currently uses the public API URL. Private Railway service-to-service networking for the
explorer path is still a follow-up hardening item.

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
curl -fsSL https://openintention-api-production.up.railway.app/healthz
curl -fsSL https://openintention.io/efforts | head
```

## Production smoke

Run the production smoke floor:

```bash
python3 scripts/run_production_smoke.py \
  --site-url https://openintention.io \
  --api-base-url https://openintention-api-production.up.railway.app
```

This should produce:
- `data/publications/launch/production-smoke/production-smoke.md`
- `data/publications/launch/production-smoke/public-ingress/public-ingress-smoke.md`
- `data/publications/launch/production-smoke/shared-participation/shared-participation-smoke.md`

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

- the site explorer currently depends on the public API URL rather than proven private Railway networking
- the production volume is single-region and single-node today
- proof efforts are append-only, so long-running public efforts still need a rollover/reset policy
