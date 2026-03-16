# Launch Package

This package is the reusable launch-operations surface for `OpenIntention`.

Naming split:
- public umbrella brand: `OpenIntention`
- domain: `openintention.io`
- technical repo/system name: `research-os`

## Launch posture

Keep this package focused on reusable operator checks and evidence regeneration.
Narrative launch drafts and channel-specific post copy should live outside this public repo.

Launch constraint to remember:
- many people will come in through the public post, paste the site/repo links into Claude or
  Codex, and ask the agent to help them onboard
- so the public surface has to be readable by both humans and agents
- the verification bar is not only "can a person read this?" but "can an agent act on it?"

## Package contents

- `external-agent-dry-run.md`
  - the pre-launch gate for asking an external AI agent to participate using only the public materials
- `evidence.md`
  - links and regeneration commands for the current evidence artifacts
- `checklist.md`
  - pre-post operator checklist

## Generated evidence

The package expects these generated artifacts:
- `data/publications/efforts/eval-sprint-improve-validation-loss-under-fixed-budget.md`
- `data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md`
- `data/publications/launch/public-ingress/public-ingress-smoke.md`
- `data/publications/launch/public-ingress/first-user-smoke.md`
- `data/publications/launch/repeated-external-participation/repeated-external-participation.md`

Regenerate them with:

```bash
python3 scripts/run_public_ingress_smoke.py
python3 scripts/run_repeated_external_participation_proof.py --base-url https://api.openintention.io
python3 scripts/export_effort_briefs.py
python3 scripts/build_microsite.py
python3 scripts/run_surface_coherence_check.py
```
