from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from research_os.domain.models import ClaimSummary


ClaimUpsideScorer = Callable[[ClaimSummary], float]
FrontierDistanceCalculator = Callable[[float, float], float]
ObjectiveMatcher = Callable[[str], bool]


def _neutral_frontier_distance(best_metric_value: float, candidate_metric_value: float) -> float:
    return abs(candidate_metric_value - best_metric_value)


@dataclass(frozen=True, slots=True)
class ObjectiveRankingPolicy:
    name: str
    matcher: ObjectiveMatcher
    claim_upside: ClaimUpsideScorer
    frontier_distance: FrontierDistanceCalculator = _neutral_frontier_distance


def register_objective_policy(
    policy: ObjectiveRankingPolicy,
    *,
    prepend: bool = True,
) -> Callable[[], None]:
    if prepend:
        _REGISTERED_POLICIES.insert(0, policy)
    else:
        _REGISTERED_POLICIES.insert(len(_REGISTERED_POLICIES) - 1, policy)

    def unregister() -> None:
        try:
            _REGISTERED_POLICIES.remove(policy)
        except ValueError:
            return

    return unregister


def resolve_objective_policy(objective: str) -> ObjectiveRankingPolicy:
    for policy in _REGISTERED_POLICIES:
        if policy.matcher(objective):
            return policy
    return NEUTRAL_OBJECTIVE_POLICY


def _normalize_objective(objective: str) -> str:
    return objective.strip().lower()


def _matches_explicit_prefix(objective: str, prefix: str) -> bool:
    return _normalize_objective(objective).startswith(prefix)


def _matches_any_token(objective: str, tokens: tuple[str, ...]) -> bool:
    normalized = _normalize_objective(objective)
    return any(token in normalized for token in tokens)


def _minimize_claim_upside(claim: ClaimSummary) -> float:
    delta = claim.delta or 0.0
    return max(-delta, 0.0)


def _maximize_claim_upside(claim: ClaimSummary) -> float:
    delta = claim.delta or 0.0
    return max(delta, 0.0)


def _neutral_claim_upside(claim: ClaimSummary) -> float:
    return abs(claim.delta or 0.0)


def _minimize_frontier_distance(best_metric_value: float, candidate_metric_value: float) -> float:
    return max(candidate_metric_value - best_metric_value, 0.0)


def _maximize_frontier_distance(best_metric_value: float, candidate_metric_value: float) -> float:
    return max(best_metric_value - candidate_metric_value, 0.0)


MINIMIZE_OBJECTIVE_POLICY = ObjectiveRankingPolicy(
    name="minimize",
    matcher=lambda objective: _matches_explicit_prefix(objective, "min:")
    or _matches_any_token(
        objective,
        ("loss", "error", "latency", "cost", "bpb", "perplexity", "rmse", "mae"),
    ),
    claim_upside=_minimize_claim_upside,
    frontier_distance=_minimize_frontier_distance,
)

MAXIMIZE_OBJECTIVE_POLICY = ObjectiveRankingPolicy(
    name="maximize",
    matcher=lambda objective: _matches_explicit_prefix(objective, "max:")
    or _matches_any_token(
        objective,
        ("accuracy", "throughput", "reward", "precision", "recall", "auc", "pass_rate", "tokens_per_second"),
    ),
    claim_upside=_maximize_claim_upside,
    frontier_distance=_maximize_frontier_distance,
)

NEUTRAL_OBJECTIVE_POLICY = ObjectiveRankingPolicy(
    name="neutral",
    matcher=lambda objective: True,
    claim_upside=_neutral_claim_upside,
)

_REGISTERED_POLICIES = [
    MAXIMIZE_OBJECTIVE_POLICY,
    MINIMIZE_OBJECTIVE_POLICY,
    NEUTRAL_OBJECTIVE_POLICY,
]
