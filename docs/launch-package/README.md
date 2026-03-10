# Launch Package

This package is the current public-launch surface for `OpenIntention`.

Naming split:
- public umbrella brand: `OpenIntention`
- domain: `openintention.io`
- technical repo/system name: `research-os`

## Launch posture

The first public announcement should anchor itself to Andrej Karpathy's post about
massively collaborative agent research.

Why:
- it is the exact problem statement that triggered this build direction
- it gives the audience immediate context
- it lets us position `OpenIntention` as a coordination/control-plane response, not as a clone

Launch constraint to remember:
- many people will come in through the public post, paste the site/repo links into Claude or
  Codex, and ask the agent to help them onboard
- so the public surface has to be readable by both humans and agents
- the verification bar is not only "can a person read this?" but "can an agent act on it?"

## Package contents

- `founder-agent-dry-run.md`
  - the pre-launch gate for Ali to ask an external AI agent to participate using only the public materials
- `quote-post.md`
  - the primary public announcement draft
- `reply-thread.md`
  - follow-up reply that grounds the post in concrete repo and evidence links
- `repo-announcement.md`
  - the technical follow-up or thread/reply draft
- `evidence.md`
  - links and regeneration commands for the current evidence artifacts
- `checklist.md`
  - pre-post operator checklist

## Generated evidence

The package expects these generated artifacts:
- `data/publications/efforts/eval-sprint-improve-validation-loss-under-fixed-budget.md`
- `data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md`
- `data/publications/launch/first-user-smoke.md`

Regenerate them with:

```bash
python3 scripts/run_first_user_smoke.py
```
