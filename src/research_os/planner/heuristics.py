from __future__ import annotations

from typing import Iterable

from research_os.domain.models import ClaimSummary, EventEnvelope, FrontierMember, RecommendNextRequest, RecommendNextResponse, Recommendation
from research_os.planner.policies import resolve_objective_policy
from research_os.projections.claims import build_claim_summaries
from research_os.projections.frontier import build_frontier


def recommend_next(events: Iterable[EventEnvelope], request: RecommendNextRequest) -> RecommendNextResponse:
    policy = resolve_objective_policy(request.objective)
    all_events = list(events)
    frontier = build_frontier(
        all_events,
        objective=request.objective,
        platform=request.platform,
        budget_seconds=request.budget_seconds,
        limit=max(request.limit, 5),
    )
    claims = build_claim_summaries(all_events, objective=request.objective, platform=request.platform)
    frontier_by_snapshot = {member.snapshot_id: member for member in frontier.members}
    best_member = frontier.members[0] if frontier.members else None

    recommendations: list[Recommendation] = []

    scored_claims = []
    for claim in claims:
        reproducibility_gap = _reproducibility_gap(claim)
        if reproducibility_gap <= 0:
            continue
        frontier_proximity = _frontier_proximity(
            policy,
            frontier_by_snapshot=frontier_by_snapshot,
            best_member=best_member,
            claim=claim,
        )
        upside = policy.claim_upside(claim)
        priority = 60 + reproducibility_gap * 20 + min(int(upside * 1000), 30) + int(frontier_proximity * 15)
        scored_claims.append((priority, upside, frontier_proximity, claim))

    scored_claims.sort(key=lambda item: (item[0], item[1], item[2], item[3].confidence or 0.0), reverse=True)

    for priority, _, frontier_proximity, claim in scored_claims:
        if len(recommendations) >= request.limit:
            break
        recommendations.append(
            Recommendation(
                action="reproduce_claim",
                priority=priority,
                reason=(
                    "This claim still has a reproducibility gap and enough frontier relevance to "
                    "justify more evidence collection."
                ),
                inputs={
                    "claim_id": claim.claim_id,
                    "snapshot_id": claim.candidate_snapshot_id,
                    "workspace_id": claim.workspace_id,
                    "frontier_proximity": round(frontier_proximity, 3),
                    "reproducibility_gap": _reproducibility_gap(claim),
                },
            )
        )

    if len(recommendations) < request.limit and len(frontier.members) >= 2:
        top_members = frontier.members[:2]
        novelty = _frontier_pair_novelty(top_members[0], top_members[1])
        recommendations.append(
            Recommendation(
                action="compose_frontier_snapshots",
                priority=70 + int(novelty * 20),
                reason=(
                    "The top frontier lines come from different snapshots. Try combining their "
                    "compatible ideas instead of only extending one."
                ),
                inputs={
                    "snapshot_ids": [member.snapshot_id for member in top_members],
                    "run_ids": [member.run_id for member in top_members],
                    "novelty_estimate": round(novelty, 3),
                },
            )
        )

    if len(recommendations) < request.limit and request.workspace_id:
        adopted_claim_ids = _adopted_subject_ids(
            all_events,
            workspace_id=request.workspace_id,
            subject_type="claim",
        )
        adoption_candidates = []
        for claim in claims:
            if claim.workspace_id in (None, request.workspace_id):
                continue
            if claim.status != "supported":
                continue
            if claim.claim_id in adopted_claim_ids:
                continue

            frontier_proximity = _frontier_proximity(
                policy,
                frontier_by_snapshot=frontier_by_snapshot,
                best_member=best_member,
                claim=claim,
            )
            novelty = _adoption_novelty(
                best_member=best_member,
                candidate_member=frontier_by_snapshot.get(claim.candidate_snapshot_id),
            )
            priority = 55 + claim.support_count * 15 + int(frontier_proximity * 15) + int(novelty * 10)
            adoption_candidates.append((priority, novelty, frontier_proximity, claim))

        adoption_candidates.sort(
            key=lambda item: (item[0], item[1], item[2], item[3].confidence or 0.0),
            reverse=True,
        )
        if adoption_candidates:
            priority, novelty, frontier_proximity, claim = adoption_candidates[0]
            recommendations.append(
                Recommendation(
                    action="adopt_claim",
                    priority=priority,
                    reason=(
                        "Another workspace has a supported claim on a frontier-relevant line. "
                        "Adopt the finding without merging branches."
                    ),
                    inputs={
                        "claim_id": claim.claim_id,
                        "source_workspace_id": claim.workspace_id,
                        "snapshot_id": claim.candidate_snapshot_id,
                        "frontier_proximity": round(frontier_proximity, 3),
                        "novelty_estimate": round(novelty, 3),
                    },
                )
            )

    if len(recommendations) < request.limit and frontier.members:
        best = frontier.members[0]
        novelty = _frontier_novelty(best, frontier.members[1:])
        recommendations.append(
            Recommendation(
                action="explore_frontier_neighborhood",
                priority=50 + int(novelty * 15),
                reason="The best current frontier member is a good local base for another iteration.",
                inputs={
                    "snapshot_id": best.snapshot_id,
                    "run_id": best.run_id,
                    "novelty_estimate": round(novelty, 3),
                },
            )
        )

    if len(recommendations) < request.limit:
        recommendations.append(
            Recommendation(
                action="open_new_workspace",
                priority=40,
                reason=(
                    "No urgent cross-pollination task is visible. Start a new workspace and explore "
                    "a distinct hypothesis."
                ),
                inputs={
                    "objective": request.objective,
                    "platform": request.platform,
                    "budget_seconds": request.budget_seconds,
                },
            )
        )

    return RecommendNextResponse(recommendations=recommendations[: request.limit])


def _reproducibility_gap(claim: ClaimSummary) -> int:
    target_support = 2
    return max(target_support - claim.support_count, 0) + claim.contradiction_count


def _frontier_proximity(
    policy,
    *,
    frontier_by_snapshot: dict[str, FrontierMember],
    best_member: FrontierMember | None,
    claim: ClaimSummary,
) -> float:
    if best_member is None:
        return 0.0

    candidate_member = frontier_by_snapshot.get(claim.candidate_snapshot_id)
    if candidate_member is None:
        return 0.0

    distance = policy.frontier_distance(best_member.metric_value, candidate_member.metric_value)
    scale = max(abs(best_member.metric_value), 1.0)
    normalized_distance = min(distance / scale, 1.0)
    return 1.0 - normalized_distance


def _frontier_pair_novelty(left: FrontierMember, right: FrontierMember) -> float:
    left_tags = set(left.tags.items())
    right_tags = set(right.tags.items())
    tag_union = left_tags | right_tags
    if not tag_union:
        tag_novelty = 0.0
    else:
        tag_novelty = 1.0 - (len(left_tags & right_tags) / len(tag_union))

    workspace_bonus = 0.25 if left.workspace_id != right.workspace_id else 0.0
    return min(tag_novelty + workspace_bonus, 1.0)


def _frontier_novelty(best: FrontierMember, others: list[FrontierMember]) -> float:
    if not others:
        return 0.0
    return max(_frontier_pair_novelty(best, other) for other in others)


def _adoption_novelty(
    *,
    best_member: FrontierMember | None,
    candidate_member: FrontierMember | None,
) -> float:
    if best_member is None or candidate_member is None:
        return 0.0
    return _frontier_pair_novelty(best_member, candidate_member)


def _adopted_subject_ids(
    events: list[EventEnvelope],
    *,
    workspace_id: str,
    subject_type: str,
) -> set[str]:
    return {
        event.payload["subject_id"]
        for event in events
        if event.workspace_id == workspace_id
        and event.kind.value == "adoption.recorded"
        and event.payload.get("subject_type") == subject_type
    }
