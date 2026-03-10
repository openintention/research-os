# Launch Checklist

Before posting publicly:

- run the founder-agent dry run in `docs/launch-package/founder-agent-dry-run.md`
- do not post unless an external AI agent can infer the participation path from the public materials alone
- run `python3 scripts/run_public_ingress_smoke.py`
- run `python3 scripts/run_first_user_smoke.py`
- run `python3 scripts/build_microsite.py`
- if you need to override the canonical repo link, rebuild with `OPENINTENTION_REPO_URL=<public_repo_url> python3 scripts/build_microsite.py`
- confirm `data/publications/launch/first-user-smoke.md` exists
- confirm `data/publications/launch/public-ingress/public-ingress-smoke.md` exists
- confirm both effort briefs were regenerated under `data/publications/efforts/`
- confirm `apps/site/dist/index.html` exists
- confirm `apps/site/dist/assets/favicon.svg` exists
- confirm the quote-post copy still matches the current repo reality
- confirm the transparency line is present:
  - inspired by Andrej's work
  - built collaboratively with AI assistance
  - not affiliated with Andrej
- confirm the honesty line is present:
  - control plane is real
  - proxy contribution loops are real
  - current tiny client is not a production benchmark harness
- confirm links point to `openintention.io` and `https://github.com/openintention/research-os`
- confirm the microsite explicitly says there is no sign-up flow or community app yet
- confirm the announcement copy works as a promptable ingress surface for Claude/Codex-style agents
- choose one artifact excerpt to include in the public post
