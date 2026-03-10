# Evidence

This launch package should point to generated evidence, not only prose.

## Generated artifacts

- `data/publications/efforts/eval-sprint-improve-validation-loss-under-fixed-budget.md`
- `data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md`
- `data/publications/launch/first-user-smoke.md`

## Regeneration command

```bash
python scripts/run_first_user_smoke.py
```

That command should:
- seed the local state
- run the eval proxy contribution
- run the inference proxy contribution
- export the effort briefs
- write a first-user smoke report

To rebuild the static microsite evidence surface after that:

```bash
python scripts/build_microsite.py
# or
make build-microsite
```

If the public repo is live, attach it directly to the microsite build:

```bash
OPENINTENTION_REPO_URL=<public_repo_url> python scripts/build_microsite.py
```

Canonical public repo:
- `https://github.com/openintention/research-os`

## Minimum evidence to attach publicly

- one excerpt from the eval effort brief
- one excerpt from the inference effort brief
- one short snippet from `first-user-smoke.md`
- one exact local command that someone else can run
