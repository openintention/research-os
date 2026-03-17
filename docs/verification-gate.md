# Layered Verification Gate

This is the repeatable verification ladder for `research-os` and `OpenIntention`.

Use it now, and keep using it later as the TDD loop for new work.

## Why this exists

OpenIntention is consumed through:
- the public site
- the public repo
- hosted API state
- and increasingly through external AI agents

That means verification cannot stop at unit tests or one happy-path smoke script.

The gate has to prove:
- control-plane correctness
- public-surface correctness
- hosted shared-state correctness
- and, when needed, real clean-room agent ingress

## Done rule

Nothing is done until the relevant end-to-end gate for the affected surface passes.

That means:
- compiling or a local code read is not enough
- unit tests alone are not enough when the changed surface is public, hosted, or worker-facing
- each issue should close with the smallest applicable threshold gate plus any feature-specific live proof the change introduced

If a change affects hosted participation, coordination, or observer-visible state, it must pass an end-to-end verification path before the issue is moved to `Done`.

## Thresholds

### Merge gate

Required:
- `L0`

Rule:
- before writing implementation, add or update the smallest failing deterministic test first
- after the fix, re-run `L0` plus the smallest feature-local check that covers the change

### Deploy gate

Required:
- `L0`
- `L1`
- `L2`

Use this before claiming the hosted product surface is still healthy after meaningful changes.

This is also the minimum bar before closing work that changes the hosted site, hosted API, shared participation, or other observer-visible network behavior.

### Launch-claim gate

Required:
- `L0`
- `L1`
- `L2`
- `L3`

Also require `L4` if the public claim includes worker or external-harness behavior.

Use this threshold before closing work that changes the claimed public product behavior for agents or humans.

## Layers

### L0: Fast deterministic core

Commands:

```bash
ruff check .
pytest -q
```

Pass criteria:
- lint is clean
- deterministic tests pass

### L1: Deterministic product path

Commands:

```bash
python3 scripts/run_surface_coherence_check.py
python3 scripts/run_first_user_smoke.py
python3 scripts/run_public_ingress_smoke.py
```

Pass criteria:
- docs and evidence surfaces still use one freshness model
- a newcomer can still complete the canonical local newcomer path
- the public site still leads to the repo and a fresh participation flow

Evidence:
- `data/publications/launch/surface-coherence/surface-coherence.md`
- `data/publications/launch/first-user/first-user-smoke.md`
- `data/publications/launch/public-ingress/public-ingress-smoke.md`

### L2: Hosted network floor

Commands:

```bash
python3 scripts/run_shared_participation_smoke.py --base-url https://api.openintention.io
python3 scripts/run_repeated_external_participation_proof.py --base-url https://api.openintention.io
python3 scripts/run_production_smoke.py --site-url https://openintention.io --api-base-url https://api.openintention.io
```

Pass criteria:
- contributor and verifier roles remain visible in one shared hosted goal
- repeated external participation still lands visible work through the canonical hosted endpoint
- the live site, live API, and goal pages are still coherent

### L3: Clean-room agent ingress

Manual checks:
- one Claude clean-room run
- one Codex clean-room run

Both should get only:
- `https://openintention.io`
- `https://github.com/openintention/research-os`

Pass criteria:
- the agent infers what is real vs proxy
- it finds the join path without hidden context
- it becomes onboarded, joined, and participated
- it can point to inspectable resulting evidence

Required evidence:
- prompt used
- workspace / claim / live URLs
- short verdict: onboarded, joined, participated

### L4: Worker proof

Command:

```bash
python3 scripts/run_overnight_autoresearch_worker_smoke.py
```

Pass criteria:
- the bounded worker path still imports kept external-harness results into shared state

Use this layer whenever public claims include the stronger worker or external-harness path.

If a change touches real worker coordination, importing external harness results, or the overnight worker path, do not call it done without this layer or an equivalent stronger live proof.

## TDD loop

For any new feature:

1. add the smallest failing deterministic test first
2. make it pass
3. rerun the smallest relevant layer
4. rerun the broader threshold gate

Examples:
- envelope-verification work should start with the smallest failing API validation test, then rerun `L0`, then rerun the deploy gate
- lease work should start with state-machine and idempotency tests, then rerun `L0`, then rerun the deploy gate once the hosted API surface changes

## Gate runner

Use the gate runner to execute the repeatable automated layers and produce one report:

```bash
python3 scripts/run_layered_verification_gate.py --gate merge
python3 scripts/run_layered_verification_gate.py --gate deploy
python3 scripts/run_layered_verification_gate.py --gate launch-claim --manual-check claude-clean-room="<note>" --manual-check codex-clean-room="<note>"
```

Add `--include-worker-layer` when the claim surface includes worker or external-harness behavior.

The runner writes its report under:
- `data/publications/launch/layered-verification/<gate>/layered-verification-report.md`
