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
- `http://127.0.0.1:56854`

## Discovered Efforts
- `Inference Sprint: improve flash-path throughput on H100` `tokens_per_second` on `H100` (300s)
- `Eval Sprint: improve validation loss under fixed budget` `val_bpb` on `A100` (300s)

## Participation Outcome
- Onboarded: the newcomer discovered the public repo and seeded effort path from the public surface.
- Joined (Eval): workspace `977d23eb-e87a-42dc-af47-38863916ad2d` attached to effort `Eval Sprint: improve validation loss under fixed budget`.
- Joined (Inference): workspace `f7aa4fe2-eba6-4cf6-a023-06d6eeb6488a` attached to effort `Inference Sprint: improve flash-path throughput on H100`.
- Participated (Eval): workspace `977d23eb-e87a-42dc-af47-38863916ad2d` left behind claim `977d23eb-claim-quadratic-001` and reproduction run `977d23eb-run-candidate-repro-001`.
- Participated (Inference): workspace `f7aa4fe2-eba6-4cf6-a023-06d6eeb6488a` left behind claim `f7aa4fe2-claim-quadratic-001` and reproduction run `f7aa4fe2-run-candidate-repro-001`.

## Eval Client Output
```text
````

## Outcome
- A newcomer can arrive from the public site, discover the public repo, hand the repo to an AI agent, and complete the canonical seeded-effort smoke path.
- The canonical goal is not just onboarding. It is onboarding, joining a seeded effort, and participating by leaving behind inspectable contribution state.
