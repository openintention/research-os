# Proof Effort Lifecycle

OpenIntention keeps the event log immutable.

That means public proof efforts are never edited in place, reset, or silently cleaned up.
When a public proof effort has become noisy, stale, or demo-heavy enough that new work should start
from a fresh window, the operator should **roll it over** instead of mutating history.

## Policy

Continue an existing proof effort when:
- the current effort is still the active public proof window
- new participants should keep building on its visible state
- the frontier, claims, and publications are still legible enough to continue

Roll over a proof effort when:
- repeated demos or verification runs have made the current proof window noisy
- the public explorer should point new work at a cleaner successor effort
- you want a fresh proof window without deleting or rewriting the old one

Do not:
- delete old proof efforts from the event log
- rewrite old effort history in place
- silently reuse a stale proof effort forever

## Operator Path

Roll an effort forward with:

```bash
python3 scripts/rollover_proof_effort.py \
  --base-url http://127.0.0.1:8000 \
  --effort-name "Eval Sprint: improve validation loss under fixed budget"
```

This creates a successor effort and appends a typed `effort.rolled_over` event for the previous
effort.

The previous effort becomes a **historical proof run** and the new effort becomes the next **current
proof effort**.

## Public Surfaces

After rollover:
- the old effort stays visible and inspectable
- the old effort is marked historical
- the old effort points to its successor
- the successor becomes the effort new work should join

Use the smoke path to rehearse the full operator flow:

```bash
python3 scripts/run_proof_effort_rollover_smoke.py \
  --base-url http://127.0.0.1:8000
```
