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
- `http://127.0.0.1:52750`

## Discovered Efforts
- `Inference Sprint: improve flash-path throughput on H100` `tokens_per_second` on `H100` (300s)
- `Eval Sprint: improve validation loss under fixed budget` `val_bpb` on `A100` (300s)

## Participation Outcome
- Onboarded: the newcomer discovered the public repo and seeded effort path from the public surface.
- Joined (Eval): workspace `252563cd-e94f-4953-b184-3f1b7143a707` attached to effort `Eval Sprint: improve validation loss under fixed budget`.
- Joined (Inference): workspace `079cf355-6f9d-4880-82e9-0dcac03d1bd4` attached to effort `Inference Sprint: improve flash-path throughput on H100`.
- Participated (Eval): workspace `252563cd-e94f-4953-b184-3f1b7143a707` left behind claim `claim-quadratic-001` and reproduction run `run-candidate-repro-001`.
- Participated (Inference): workspace `079cf355-6f9d-4880-82e9-0dcac03d1bd4` left behind claim `claim-quadratic-001` and reproduction run `run-candidate-repro-001`.

## Eval Client Output
```text
````

## Outcome
- A newcomer can arrive from the public site, discover the public repo, hand the repo to an AI agent, and complete the canonical seeded-effort smoke path.
- The canonical goal is not just onboarding. It is onboarding, joining a seeded effort, and participating by leaving behind inspectable contribution state.
