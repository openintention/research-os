from __future__ import annotations

from research_os.domain.models import EventEnvelope, EventKind, RecommendNextRequest
from research_os.ledger.sqlite import SQLiteEventStore
from research_os.planner.policies import ObjectiveRankingPolicy, register_objective_policy
from research_os.service import ResearchOSService


def _start_workspace(
    service: ResearchOSService,
    *,
    workspace_id: str,
    objective: str,
    platform: str = "A100",
    budget_seconds: int = 300,
) -> None:
    service.append_event(
        EventEnvelope(
            kind=EventKind.WORKSPACE_STARTED,
            workspace_id=workspace_id,
            aggregate_id=workspace_id,
            aggregate_kind="workspace",
            payload={
                "name": workspace_id,
                "objective": objective,
                "platform": platform,
                "budget_seconds": budget_seconds,
            },
        )
    )


def _append_claim(
    service: ResearchOSService,
    *,
    workspace_id: str,
    claim_id: str,
    objective: str,
    platform: str = "A100",
    delta: float | None = None,
    confidence: float | None = None,
) -> None:
    payload: dict[str, object] = {
        "claim_id": claim_id,
        "statement": f"{claim_id} statement",
        "claim_type": "improvement",
        "candidate_snapshot_id": f"{claim_id}-snapshot",
        "objective": objective,
        "platform": platform,
    }
    if delta is not None:
        payload["delta"] = delta
    if confidence is not None:
        payload["confidence"] = confidence
    workspace = service.get_workspace(workspace_id)
    assert workspace is not None
    snapshot_id = str(payload["candidate_snapshot_id"])
    if snapshot_id not in workspace.snapshot_ids:
        service.append_event(
            EventEnvelope(
                kind=EventKind.SNAPSHOT_PUBLISHED,
                workspace_id=workspace_id,
                aggregate_id=snapshot_id,
                aggregate_kind="snapshot",
                payload={
                    "snapshot_id": snapshot_id,
                    "artifact_uri": "artifact://sha256/" + "a" * 64,
                },
            )
        )

    service.append_event(
        EventEnvelope(
            kind=EventKind.CLAIM_ASSERTED,
            workspace_id=workspace_id,
            aggregate_id=claim_id,
            aggregate_kind="claim",
            payload=payload,
        )
    )


def _append_run(
    service: ResearchOSService,
    *,
    workspace_id: str,
    run_id: str,
    snapshot_id: str,
    objective: str,
    metric_value: float,
    platform: str = "A100",
    budget_seconds: int = 300,
    direction: str = "min",
    tags: dict[str, str] | None = None,
) -> None:
    workspace = service.get_workspace(workspace_id)
    assert workspace is not None
    if snapshot_id not in workspace.snapshot_ids:
        service.append_event(
            EventEnvelope(
                kind=EventKind.SNAPSHOT_PUBLISHED,
                workspace_id=workspace_id,
                aggregate_id=snapshot_id,
                aggregate_kind="snapshot",
                payload={
                    "snapshot_id": snapshot_id,
                    "artifact_uri": "artifact://sha256/" + "a" * 64,
                },
            )
        )
    service.append_event(
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id=workspace_id,
            aggregate_id=run_id,
            aggregate_kind="run",
            payload={
                "run_id": run_id,
                "snapshot_id": snapshot_id,
                "objective": objective,
                "platform": platform,
                "budget_seconds": budget_seconds,
                "metric_name": objective,
                "metric_value": metric_value,
                "direction": direction,
                "status": "success",
            },
            tags=tags or {},
        )
    )


def test_planner_prefers_unreproduced_claim(tmp_path):
    store = SQLiteEventStore(str(tmp_path / "planner.db"))
    service = ResearchOSService(store)

    _start_workspace(service, workspace_id="ws-1", objective="val_bpb")
    _append_run(
        service,
        workspace_id="ws-1",
        run_id="run-1",
        snapshot_id="snap-1",
        objective="val_bpb",
        metric_value=1.2,
    )
    _append_claim(
        service,
        workspace_id="ws-1",
        claim_id="claim-1",
        objective="val_bpb",
        delta=-0.02,
    )

    response = service.recommend_next(
        RecommendNextRequest(objective="val_bpb", platform="A100", budget_seconds=300, limit=1)
    )
    assert response.recommendations[0].action == "reproduce_claim"
    assert response.recommendations[0].inputs["claim_id"] == "claim-1"


def test_planner_can_target_one_explicit_claim_on_a_busy_effort(tmp_path):
    store = SQLiteEventStore(str(tmp_path / "planner-targeted.db"))
    service = ResearchOSService(store)

    _start_workspace(service, workspace_id="ws-target", objective="val_bpb")
    _start_workspace(service, workspace_id="ws-distractor", objective="val_bpb")
    _append_run(
        service,
        workspace_id="ws-target",
        run_id="run-target",
        snapshot_id="claim-target-snapshot",
        objective="val_bpb",
        metric_value=1.35,
    )
    _append_run(
        service,
        workspace_id="ws-distractor",
        run_id="run-distractor",
        snapshot_id="claim-distractor-snapshot",
        objective="val_bpb",
        metric_value=1.21,
    )
    _append_claim(
        service,
        workspace_id="ws-target",
        claim_id="claim-target",
        objective="val_bpb",
        delta=-0.01,
    )
    _append_claim(
        service,
        workspace_id="ws-distractor",
        claim_id="claim-distractor",
        objective="val_bpb",
        delta=-0.03,
    )

    global_response = service.recommend_next(
        RecommendNextRequest(objective="val_bpb", platform="A100", budget_seconds=300, limit=1)
    )
    assert global_response.recommendations[0].inputs["claim_id"] == "claim-distractor"

    targeted_response = service.recommend_next(
        RecommendNextRequest(
            objective="val_bpb",
            platform="A100",
            budget_seconds=300,
            target_claim_id="claim-target",
            limit=1,
        )
    )
    assert targeted_response.recommendations[0].action == "reproduce_claim"
    assert targeted_response.recommendations[0].inputs["claim_id"] == "claim-target"
    assert targeted_response.recommendations[0].inputs["targeted"] is True


def test_planner_prioritizes_larger_reproducibility_gap(tmp_path):
    store = SQLiteEventStore(str(tmp_path / "planner-gap.db"))
    service = ResearchOSService(store)

    _start_workspace(service, workspace_id="ws-gap", objective="val_bpb")
    _append_run(
        service,
        workspace_id="ws-gap",
        run_id="run-gap-1",
        snapshot_id="claim-gap-pending-snapshot",
        objective="val_bpb",
        metric_value=1.2,
    )
    _append_run(
        service,
        workspace_id="ws-gap",
        run_id="run-gap-2",
        snapshot_id="claim-gap-supported-snapshot",
        objective="val_bpb",
        metric_value=1.21,
    )
    _append_claim(
        service,
        workspace_id="ws-gap",
        claim_id="claim-gap-pending",
        objective="val_bpb",
        delta=-0.02,
    )
    _append_claim(
        service,
        workspace_id="ws-gap",
        claim_id="claim-gap-supported",
        objective="val_bpb",
        delta=-0.02,
    )
    service.append_event(
        EventEnvelope(
            kind=EventKind.CLAIM_REPRODUCED,
            workspace_id="ws-gap",
            aggregate_id="claim-gap-supported",
            aggregate_kind="claim",
            payload={"claim_id": "claim-gap-supported", "evidence_run_id": "run-gap-2"},
        )
    )

    response = service.recommend_next(
        RecommendNextRequest(objective="val_bpb", platform="A100", budget_seconds=300, limit=1)
    )
    assert response.recommendations[0].inputs["claim_id"] == "claim-gap-pending"
    assert response.recommendations[0].inputs["reproducibility_gap"] == 2


def test_planner_minimize_policy_prefers_negative_delta(tmp_path):
    store = SQLiteEventStore(str(tmp_path / "planner-min.db"))
    service = ResearchOSService(store)

    _start_workspace(service, workspace_id="ws-min", objective="val_bpb")
    _append_claim(
        service,
        workspace_id="ws-min",
        claim_id="claim-improves-loss",
        objective="val_bpb",
        delta=-0.01,
    )
    _append_claim(
        service,
        workspace_id="ws-min",
        claim_id="claim-regresses-loss",
        objective="val_bpb",
        delta=0.08,
    )

    response = service.recommend_next(
        RecommendNextRequest(objective="val_bpb", platform="A100", budget_seconds=300, limit=1)
    )
    assert response.recommendations[0].inputs["claim_id"] == "claim-improves-loss"


def test_planner_maximize_policy_prefers_positive_delta(tmp_path):
    store = SQLiteEventStore(str(tmp_path / "planner-max.db"))
    service = ResearchOSService(store)

    _start_workspace(service, workspace_id="ws-max", objective="accuracy")
    _append_claim(
        service,
        workspace_id="ws-max",
        claim_id="claim-improves-accuracy",
        objective="accuracy",
        delta=0.03,
    )
    _append_claim(
        service,
        workspace_id="ws-max",
        claim_id="claim-regresses-accuracy",
        objective="accuracy",
        delta=-0.12,
    )

    response = service.recommend_next(
        RecommendNextRequest(objective="accuracy", platform="A100", budget_seconds=300, limit=1)
    )
    assert response.recommendations[0].inputs["claim_id"] == "claim-improves-accuracy"


def test_planner_treats_tokens_per_second_as_maximize_objective(tmp_path):
    store = SQLiteEventStore(str(tmp_path / "planner-throughput.db"))
    service = ResearchOSService(store)

    _start_workspace(service, workspace_id="ws-throughput", objective="tokens_per_second", platform="H100")
    _append_claim(
        service,
        workspace_id="ws-throughput",
        claim_id="claim-faster-path",
        objective="tokens_per_second",
        platform="H100",
        delta=42.0,
    )
    _append_claim(
        service,
        workspace_id="ws-throughput",
        claim_id="claim-slower-path",
        objective="tokens_per_second",
        platform="H100",
        delta=-18.0,
    )

    response = service.recommend_next(
        RecommendNextRequest(objective="tokens_per_second", platform="H100", budget_seconds=300, limit=1)
    )
    assert response.recommendations[0].inputs["claim_id"] == "claim-faster-path"


def test_planner_prefers_claim_closer_to_frontier_when_gap_matches(tmp_path):
    store = SQLiteEventStore(str(tmp_path / "planner-frontier-distance.db"))
    service = ResearchOSService(store)

    _start_workspace(service, workspace_id="ws-distance", objective="val_bpb")
    _append_run(
        service,
        workspace_id="ws-distance",
        run_id="run-close",
        snapshot_id="claim-close-snapshot",
        objective="val_bpb",
        metric_value=1.21,
        tags={"topic": "close"},
    )
    _append_run(
        service,
        workspace_id="ws-distance",
        run_id="run-far",
        snapshot_id="claim-far-snapshot",
        objective="val_bpb",
        metric_value=1.45,
        tags={"topic": "far"},
    )
    _append_claim(
        service,
        workspace_id="ws-distance",
        claim_id="claim-close",
        objective="val_bpb",
        delta=-0.01,
    )
    _append_claim(
        service,
        workspace_id="ws-distance",
        claim_id="claim-far",
        objective="val_bpb",
        delta=-0.01,
    )

    response = service.recommend_next(
        RecommendNextRequest(objective="val_bpb", platform="A100", budget_seconds=300, limit=1)
    )
    assert response.recommendations[0].inputs["claim_id"] == "claim-close"
    assert response.recommendations[0].inputs["frontier_proximity"] > 0.8


def test_planner_allows_custom_objective_policy_registration(tmp_path):
    store = SQLiteEventStore(str(tmp_path / "planner-custom.db"))
    service = ResearchOSService(store)

    _start_workspace(service, workspace_id="ws-custom", objective="balanced_tradeoff")
    _append_claim(
        service,
        workspace_id="ws-custom",
        claim_id="claim-low-confidence",
        objective="balanced_tradeoff",
        delta=0.5,
        confidence=0.1,
    )
    _append_claim(
        service,
        workspace_id="ws-custom",
        claim_id="claim-high-confidence",
        objective="balanced_tradeoff",
        delta=0.01,
        confidence=0.9,
    )

    unregister = register_objective_policy(
        ObjectiveRankingPolicy(
            name="balanced_tradeoff",
            matcher=lambda objective: objective == "balanced_tradeoff",
            claim_upside=lambda claim: claim.confidence or 0.0,
            frontier_distance=lambda best_metric_value, candidate_metric_value: abs(
                candidate_metric_value - best_metric_value
            ),
        )
    )
    try:
        response = service.recommend_next(
            RecommendNextRequest(
                objective="balanced_tradeoff",
                platform="A100",
                budget_seconds=300,
                limit=1,
            )
        )
    finally:
        unregister()

    assert response.recommendations[0].inputs["claim_id"] == "claim-high-confidence"


def test_planner_compose_priority_increases_with_frontier_novelty(tmp_path):
    def compose_priority(tags_for_second: dict[str, str]) -> int:
        store = SQLiteEventStore(str(tmp_path / f"{tags_for_second['topic']}-novelty.db"))
        service = ResearchOSService(store)
        _start_workspace(service, workspace_id="ws-novelty", objective="val_bpb")
        _start_workspace(service, workspace_id="ws-other", objective="val_bpb")
        _append_run(
            service,
            workspace_id="ws-novelty",
            run_id="run-novelty-1",
            snapshot_id="snap-novelty-1",
            objective="val_bpb",
            metric_value=1.2,
            tags={"topic": "attention"},
        )
        _append_run(
            service,
            workspace_id="ws-other",
            run_id="run-novelty-2",
            snapshot_id="snap-novelty-2",
            objective="val_bpb",
            metric_value=1.21,
            tags=tags_for_second,
        )
        response = service.recommend_next(
            RecommendNextRequest(objective="val_bpb", platform="A100", budget_seconds=300, limit=1)
        )
        return response.recommendations[0].priority

    low_novelty_priority = compose_priority({"topic": "attention"})
    high_novelty_priority = compose_priority({"topic": "optimizer"})

    assert high_novelty_priority > low_novelty_priority


def test_planner_suggests_adopting_supported_external_claim(tmp_path):
    store = SQLiteEventStore(str(tmp_path / "planner-adopt.db"))
    service = ResearchOSService(store)

    _start_workspace(service, workspace_id="ws-target", objective="val_bpb")
    _start_workspace(service, workspace_id="ws-source", objective="val_bpb")
    _append_run(
        service,
        workspace_id="ws-target",
        run_id="run-target-1",
        snapshot_id="snap-target-1",
        objective="val_bpb",
        metric_value=1.22,
        tags={"topic": "attention"},
    )
    _append_run(
        service,
        workspace_id="ws-source",
        run_id="run-source-1",
        snapshot_id="claim-source-1-snapshot",
        objective="val_bpb",
        metric_value=1.21,
        tags={"topic": "optimizer"},
    )
    _append_claim(
        service,
        workspace_id="ws-source",
        claim_id="claim-source-1",
        objective="val_bpb",
        delta=-0.02,
    )
    service.append_event(
        EventEnvelope(
            kind=EventKind.CLAIM_REPRODUCED,
            workspace_id="ws-source",
            aggregate_id="claim-source-1",
            aggregate_kind="claim",
            payload={"claim_id": "claim-source-1", "evidence_run_id": "run-source-1"},
        )
    )

    response = service.recommend_next(
        RecommendNextRequest(
            objective="val_bpb",
            platform="A100",
            budget_seconds=300,
            workspace_id="ws-target",
            limit=5,
        )
    )
    actions = {recommendation.action for recommendation in response.recommendations}
    assert "adopt_claim" in actions

    adopt = next(
        recommendation
        for recommendation in response.recommendations
        if recommendation.action == "adopt_claim"
    )
    assert adopt.inputs["claim_id"] == "claim-source-1"
    assert adopt.inputs["source_workspace_id"] == "ws-source"
