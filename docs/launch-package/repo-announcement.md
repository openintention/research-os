# Repo Announcement Draft

`OpenIntention` is the public umbrella.
`research-os` is the technical control plane underneath it.

Transparent framing:
- this build direction was directly inspired by Andrej Karpathy's `autoresearch` work and
  his public writing on collaborative agent research
- this is not his project and is not presented as affiliated
- it was built collaboratively with AI assistance

The problem it is trying to solve is not "how do I run one more agent loop?"
It is "what is the shared machine-native substrate for collaborative research once many
agents or contributors are working across multiple directions and platforms at once?"

This is especially relevant now that the surrounding `autoresearch` discussion has shifted
from "this is a neat loop" to:
- the improvements are real
- they stack
- they transfer
- multi-agent collaboration is the next obvious stress point

What is in the repo today:
- immutable lineage events
- materialized frontier and claim state
- effort primitives for shared objectives
- publication mirrors for workspaces, snapshots, and efforts
- deterministic markdown export for effort briefs
- a tiny external client that can join seeded eval and inference efforts

What is not being claimed:
- this is not yet a production multi-agent network
- the current tiny-loop contribution paths are proxy loops
- the current inference profile is not presented as real H100 benchmarking evidence

What to inspect first:
- `docs/seeded-efforts.md`
- `docs/public-launch-runbook.md`
- `docs/launch-package/evidence.md`
