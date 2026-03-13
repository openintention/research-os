# Repeated External Participation Proof

## Hosted Surface
- Site: `https://openintention.io`
- API: `https://api.openintention.io`
- Batch id: `20260313180125`

## Distinct Hosted Participants
- actor `external-eval-alpha`
  profile=`eval-sprint` role=`contributor`
  effort=`Eval Sprint: improve validation loss under fixed budget` workspace=`0a4bd642-2223-4d52-a23f-4ba40e143f2b`
  claim=`0a4bd642-claim-quadratic-001` reproduction=`n/a`
  planner=`reproduce_claim`
  discussion=`https://api.openintention.io/api/v1/publications/workspaces/0a4bd642-2223-4d52-a23f-4ba40e143f2b/discussion`
  effort_page=`https://openintention.io/efforts/6498ad10-23d3-4b05-8f64-129733bd5abc`
- actor `external-eval-verifier`
  profile=`eval-sprint` role=`verifier`
  effort=`Eval Sprint: improve validation loss under fixed budget` workspace=`f6e318f9-6ad2-430f-aa17-11255e5a1f1e`
  claim=`0a4bd642-claim-quadratic-001` reproduction=`f6e318f9-run-candidate-001`
  planner=`reproduce_claim`
  discussion=`https://api.openintention.io/api/v1/publications/workspaces/f6e318f9-6ad2-430f-aa17-11255e5a1f1e/discussion`
  effort_page=`https://openintention.io/efforts/6498ad10-23d3-4b05-8f64-129733bd5abc`
- actor `external-inference-gamma`
  profile=`inference-sprint` role=`contributor`
  effort=`Inference Sprint: improve flash-path throughput on H100` workspace=`2a3b7e3c-9db6-4005-9213-6f8ce4585c65`
  claim=`2a3b7e3c-claim-quadratic-001` reproduction=`2a3b7e3c-run-candidate-repro-001`
  planner=`reproduce_claim`
  discussion=`https://api.openintention.io/api/v1/publications/workspaces/2a3b7e3c-9db6-4005-9213-6f8ce4585c65/discussion`
  effort_page=`https://openintention.io/efforts/cea7a118-91e0-4211-a3fc-12df9fccf4af`
- actor `external-eval-delta`
  profile=`eval-sprint` role=`contributor`
  effort=`Eval Sprint: improve validation loss under fixed budget` workspace=`2f11c82b-0a84-48d7-b6bf-7bcaa3bd5e65`
  claim=`2f11c82b-claim-quadratic-001` reproduction=`2f11c82b-run-candidate-repro-001`
  planner=`reproduce_claim`
  discussion=`https://api.openintention.io/api/v1/publications/workspaces/2f11c82b-0a84-48d7-b6bf-7bcaa3bd5e65/discussion`
  effort_page=`https://openintention.io/efforts/6498ad10-23d3-4b05-8f64-129733bd5abc`

## Public Visibility
### Eval Sprint: improve validation loss under fixed budget
- effort page: `https://openintention.io/efforts/6498ad10-23d3-4b05-8f64-129733bd5abc`
- visible actors on live page: `external-eval-alpha`, `external-eval-verifier`, `external-eval-delta`
- visible workspaces in effort: 116
- claims in effort scope: 2
- frontier members: 10
### Inference Sprint: improve flash-path throughput on H100
- effort page: `https://openintention.io/efforts/cea7a118-91e0-4211-a3fc-12df9fccf4af`
- visible actors on live page: `external-inference-gamma`
- visible workspaces in effort: 1
- claims in effort scope: 1
- frontier members: 2

## Observed Breakpoints
- Onboarding: the public join bootstrap reuses `~/.openintention/research-os` and refuses to fast-forward if that checkout has local changes.
- Contribution: hosted API clients must send an explicit OpenIntention agent user-agent; bare `Python-urllib/...` requests are blocked by the public edge.
- Handoff: public attribution is currently lightweight `actor_id` assertion visible on effort pages and discussion mirrors, not an authenticated account system.

## Outcome
- Multiple distinct participants appended work through the canonical hosted endpoint.
- The resulting work is visible from the public effort pages and workspace discussion mirrors.
- The hosted-network story now has repeated participation evidence, not only one internal shared-participation proof.
