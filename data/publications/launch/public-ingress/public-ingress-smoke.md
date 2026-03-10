# Public Ingress Smoke Report

## Public Entry
- Site: `https://openintention.io`
- Repo discovered from site: `https://github.com/openintention/research-os`

## Agent Brief
- `clone/docs/join-with-ai.md`

## Commands Executed
- `git clone --depth 1 https://github.com/openintention/research-os <temp_clone_dir>/clone`
- `<host_python> -m venv <temp_clone_dir>/clone/.venv-public-ingress`
- `<temp_clone_dir>/clone/.venv-public-ingress/bin/python -m pip install -e .[dev]`
- `<temp_clone_dir>/clone/.venv-public-ingress/bin/python scripts/run_first_user_smoke.py --output-dir <artifact_dir>/first-user`

## First User Smoke Excerpt
````text
# First User Smoke Report

## Base URL
- `http://127.0.0.1:61353`

## Discovered Efforts
- `Inference Sprint: improve flash-path throughput on H100` `tokens_per_second` on `H100` (300s)
- `Eval Sprint: improve validation loss under fixed budget` `val_bpb` on `A100` (300s)

## Eval Client Output
```text
effort_name=Eval Sprint: improve validation loss under fixed budget
effort_id=82f48279-bb9d-4e09-b4af-1df0625f85cb
workspace_id=c2c26a24-e9b0-4a12-a16c-bf8f66f33576
planner_action=reproduce_claim
claim_id=claim-quadratic-001
reproduction_run_id=run-candidate-repro-001
````

## Outcome
- A newcomer can arrive from the public site, discover the public repo, hand the repo to an AI agent, and complete the canonical seeded-effort smoke path.
