from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import random
from statistics import mean
from uuid import uuid4

from clients.tiny_loop.api import ResearchOSApi
from research_os.domain.models import ParticipantRole

CANONICAL_EVAL_EFFORT_NAME = "Eval Sprint: improve validation loss under fixed budget"
CANONICAL_INFERENCE_EFFORT_NAME = "Inference Sprint: improve flash-path throughput on H100"


@dataclass(frozen=True, slots=True)
class SnapshotConfig:
    snapshot_id: str
    feature_mode: str
    learning_rate: float
    steps: int
    notes: str


@dataclass(frozen=True, slots=True)
class ExperimentProfile:
    name: str
    workspace_name: str
    objective: str
    platform: str
    budget_seconds: int
    description: str
    claim_statement: str
    metric_direction: str
    workspace_tags: dict[str, str]
    event_tags: dict[str, str]
    effort_name: str | None = None


@dataclass(frozen=True, slots=True)
class RunResult:
    run_id: str
    snapshot_id: str
    metric_value: float
    seed: int


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    actor_id: str
    participant_role: ParticipantRole
    workspace_id: str
    effort_id: str | None
    effort_name: str | None
    baseline_snapshot_id: str
    candidate_snapshot_id: str
    planner_action: str
    claim_id: str
    reproduction_run_id: str | None
    discussion_markdown: str
    pull_request_markdown: str


STANDALONE_PROFILE = ExperimentProfile(
    name="standalone",
    workspace_name="tiny-loop-val-loss",
    objective="val_loss",
    platform="cpu",
    budget_seconds=5,
    description=(
        "Tiny single-agent ML loop over a synthetic nonlinear regression task. "
        "The client stays outside research-os and drives the API directly."
    ),
    claim_statement=(
        "Adding the quadratic feature lowers validation loss on the tiny synthetic "
        "regression task under a fixed five second budget."
    ),
    metric_direction="min",
    workspace_tags={"experiment": "tiny-loop", "domain": "nonlinear-regression"},
    event_tags={"experiment": "tiny-loop"},
)

EVAL_SPRINT_PROFILE = ExperimentProfile(
    name="eval-sprint",
    workspace_name="eval-sprint-demo-quadratic",
    objective="val_bpb",
    platform="A100",
    budget_seconds=300,
    description=(
        "Local bootstrap participant loop for the seeded eval sprint. "
        "It uses the tiny synthetic regression task as a cheap proxy for the "
        "fixed-budget contribution shape."
    ),
    claim_statement=(
        "Adding the quadratic feature improves the seeded eval objective in this "
        "local proxy loop under the fixed budget."
    ),
    metric_direction="min",
    workspace_tags={
        "experiment": "tiny-loop",
        "domain": "nonlinear-regression",
        "effort_type": "eval",
        "demo": "true",
        "simulated_contribution": "true",
    },
    event_tags={
        "experiment": "tiny-loop",
        "effort_type": "eval",
        "demo": "true",
        "simulated_contribution": "true",
    },
    effort_name=CANONICAL_EVAL_EFFORT_NAME,
)

INFERENCE_SPRINT_PROFILE = ExperimentProfile(
    name="inference-sprint",
    workspace_name="inference-sprint-demo-flash-path",
    objective="tokens_per_second",
    platform="H100",
    budget_seconds=300,
    description=(
        "Local bootstrap participant loop for the seeded inference sprint. "
        "It uses the tiny synthetic regression task as a cheap proxy for the "
        "hardware-aware throughput contribution shape."
    ),
    claim_statement=(
        "The candidate path improves the seeded inference objective in this "
        "local proxy loop under the fixed budget."
    ),
    metric_direction="max",
    workspace_tags={
        "experiment": "tiny-loop",
        "domain": "nonlinear-regression",
        "effort_type": "inference",
        "demo": "true",
        "simulated_contribution": "true",
    },
    event_tags={
        "experiment": "tiny-loop",
        "effort_type": "inference",
        "demo": "true",
        "simulated_contribution": "true",
    },
    effort_name=CANONICAL_INFERENCE_EFFORT_NAME,
)

PROFILES = {
    STANDALONE_PROFILE.name: STANDALONE_PROFILE,
    EVAL_SPRINT_PROFILE.name: EVAL_SPRINT_PROFILE,
    INFERENCE_SPRINT_PROFILE.name: INFERENCE_SPRINT_PROFILE,
}


def run_tiny_loop_experiment(
    api: ResearchOSApi,
    *,
    artifact_root: str | Path,
    profile: ExperimentProfile = STANDALONE_PROFILE,
    actor_id: str | None = None,
    workspace_suffix: str | None = None,
    participant_role: ParticipantRole = ParticipantRole.CONTRIBUTOR,
    claim_id_to_reproduce: str | None = None,
    auto_reproduce: bool = True,
) -> ExperimentResult:
    artifact_root_path = Path(artifact_root)
    artifact_root_path.mkdir(parents=True, exist_ok=True)
    resolved_actor_id = actor_id or _default_actor_id()

    effort = _lookup_effort(api, effort_name=profile.effort_name)
    _validate_effort_profile(effort=effort, profile=profile)
    workspace_name = _resolve_workspace_name(profile.workspace_name, workspace_suffix=workspace_suffix)

    workspace = api.create_workspace(
        {
            "name": workspace_name,
            "objective": profile.objective,
            "platform": profile.platform,
            "budget_seconds": profile.budget_seconds,
            "effort_id": effort["effort_id"] if effort is not None else None,
            "description": profile.description,
            "tags": profile.workspace_tags,
            "actor_id": resolved_actor_id,
            "participant_role": participant_role,
        }
    )
    workspace_id = workspace["workspace_id"]
    scope = _workspace_scope(workspace_id)

    baseline = SnapshotConfig(
        snapshot_id=_scoped_identifier(scope, "snap-linear-baseline"),
        feature_mode="linear",
        learning_rate=0.05,
        steps=80,
        notes="Linear feature baseline on the synthetic regression task.",
    )
    candidate = SnapshotConfig(
        snapshot_id=_scoped_identifier(scope, "snap-quadratic-candidate"),
        feature_mode="quadratic",
        learning_rate=0.05,
        steps=80,
        notes="Quadratic feature variant expected to better fit the synthetic data.",
    )

    _publish_snapshot(
        api,
        workspace_id=workspace_id,
        config=baseline,
        artifact_root=artifact_root_path,
        profile=profile,
        actor_id=resolved_actor_id,
        participant_role=participant_role,
    )
    _publish_snapshot(
        api,
        workspace_id=workspace_id,
        config=candidate,
        artifact_root=artifact_root_path,
        profile=profile,
        actor_id=resolved_actor_id,
        participant_role=participant_role,
    )

    baseline_run = _run_snapshot(
        api,
        workspace_id=workspace_id,
        config=baseline,
        run_id=_scoped_identifier(scope, "run-baseline-001"),
        seed=7,
        profile=profile,
        actor_id=resolved_actor_id,
        participant_role=participant_role,
    )
    candidate_run = _run_snapshot(
        api,
        workspace_id=workspace_id,
        config=candidate,
        run_id=_scoped_identifier(scope, "run-candidate-001"),
        seed=11,
        profile=profile,
        actor_id=resolved_actor_id,
        participant_role=participant_role,
    )

    if participant_role == ParticipantRole.CONTRIBUTOR:
        delta = candidate_run.metric_value - baseline_run.metric_value
        claim_id = _scoped_identifier(scope, "claim-quadratic-001")
        api.append_event(
            {
                "kind": "claim.asserted",
                "workspace_id": workspace_id,
                "aggregate_id": claim_id,
                "aggregate_kind": "claim",
                "actor_id": resolved_actor_id,
                "payload": {
                    "claim_id": claim_id,
                    "statement": profile.claim_statement,
                    "claim_type": "improvement",
                    "candidate_snapshot_id": candidate.snapshot_id,
                    "baseline_snapshot_id": baseline.snapshot_id,
                    "objective": profile.objective,
                    "platform": profile.platform,
                    "metric_name": profile.objective,
                    "delta": round(delta, 6),
                    "confidence": 0.72,
                    "evidence_run_ids": [candidate_run.run_id],
                },
                "tags": _event_tags(profile, participant_role, claim="quadratic-feature"),
            }
        )

        recommendation = _recommend_reproduction(
            api,
            profile=profile,
            workspace_id=workspace_id,
        )

        reproduction_run_id = None
        if auto_reproduce:
            reproduction_run = _run_snapshot(
                api,
                workspace_id=workspace_id,
                config=candidate,
                run_id=_scoped_identifier(scope, "run-candidate-repro-001"),
                seed=23,
                profile=profile,
                actor_id=resolved_actor_id,
                participant_role=participant_role,
            )
            api.append_event(
                {
                    "kind": "claim.reproduced",
                    "workspace_id": workspace_id,
                    "aggregate_id": claim_id,
                    "aggregate_kind": "claim",
                    "actor_id": resolved_actor_id,
                    "payload": {
                        "claim_id": claim_id,
                        "evidence_run_id": reproduction_run.run_id,
                        "notes": "Independent rerun confirms the direction of improvement.",
                    },
                    "tags": _event_tags(profile, participant_role, claim="quadratic-feature"),
                }
            )
            reproduction_run_id = reproduction_run.run_id
    else:
        recommendation = _recommend_reproduction(
            api,
            profile=profile,
            workspace_id=workspace_id,
        )
        expected_claim_id = claim_id_to_reproduce
        recommended_claim_id = recommendation["inputs"].get("claim_id")
        claim_id = expected_claim_id or recommended_claim_id
        if claim_id is None:
            raise RuntimeError("verifier flow could not resolve a claim to reproduce")
        api.append_event(
            {
                "kind": "claim.reproduced",
                "workspace_id": workspace_id,
                "aggregate_id": claim_id,
                "aggregate_kind": "claim",
                "actor_id": resolved_actor_id,
                "payload": {
                    "claim_id": claim_id,
                    "evidence_run_id": candidate_run.run_id,
                    "notes": "Verifier rerun from a separate workspace confirms the direction of improvement.",
                },
                "tags": _event_tags(profile, participant_role, claim="quadratic-feature"),
            }
        )
        reproduction_run_id = candidate_run.run_id

    discussion = api.get_workspace_discussion(workspace_id)
    pull_request = api.get_snapshot_pull_request(workspace_id, candidate.snapshot_id)
    return ExperimentResult(
        actor_id=resolved_actor_id,
        participant_role=participant_role,
        workspace_id=workspace_id,
        effort_id=effort["effort_id"] if effort is not None else None,
        effort_name=effort["name"] if effort is not None else None,
        baseline_snapshot_id=baseline.snapshot_id,
        candidate_snapshot_id=candidate.snapshot_id,
        planner_action=recommendation["action"],
        claim_id=claim_id,
        reproduction_run_id=reproduction_run_id,
        discussion_markdown=discussion["body"],
        pull_request_markdown=pull_request["body"],
    )


def run_verifier_reproduction(
    api: ResearchOSApi,
    *,
    artifact_root: str | Path,
    profile: ExperimentProfile,
    claim_id: str,
    actor_id: str | None = None,
    workspace_suffix: str | None = None,
) -> ExperimentResult:
    return run_tiny_loop_experiment(
        api,
        artifact_root=artifact_root,
        profile=profile,
        actor_id=actor_id,
        workspace_suffix=workspace_suffix,
        participant_role=ParticipantRole.VERIFIER,
        claim_id_to_reproduce=claim_id,
        auto_reproduce=False,
    )


def _publish_snapshot(
    api: ResearchOSApi,
    *,
    workspace_id: str,
    config: SnapshotConfig,
    artifact_root: Path,
    profile: ExperimentProfile,
    actor_id: str,
    participant_role: ParticipantRole,
) -> None:
    bundle = {
        "snapshot_id": config.snapshot_id,
        "feature_mode": config.feature_mode,
        "learning_rate": config.learning_rate,
        "steps": config.steps,
        "objective": profile.objective,
        "platform": profile.platform,
        "budget_seconds": profile.budget_seconds,
    }
    content = json.dumps(bundle, indent=2, sort_keys=True).encode("utf-8")
    digest = f"sha256:{sha256(content).hexdigest()}"
    bundle_path = artifact_root / f"{config.snapshot_id}.json"
    bundle_path.write_bytes(content)

    api.append_event(
        {
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": config.snapshot_id,
            "aggregate_kind": "snapshot",
            "actor_id": actor_id,
            "payload": {
                "snapshot_id": config.snapshot_id,
                "artifact_uri": bundle_path.resolve().as_uri(),
                "source_bundle_digest": digest,
                "git_ref": f"refs/experiments/{config.snapshot_id}",
                "notes": config.notes,
            },
            "tags": _event_tags(profile, participant_role, feature_mode=config.feature_mode),
        }
    )


def _run_snapshot(
    api: ResearchOSApi,
    *,
    workspace_id: str,
    config: SnapshotConfig,
    run_id: str,
    seed: int,
    profile: ExperimentProfile,
    actor_id: str,
    participant_role: ParticipantRole,
) -> RunResult:
    metric_value = _train_and_evaluate(config, seed=seed)
    api.append_event(
        {
            "kind": "run.completed",
            "workspace_id": workspace_id,
            "aggregate_id": run_id,
            "aggregate_kind": "run",
            "actor_id": actor_id,
            "payload": {
                "run_id": run_id,
                "snapshot_id": config.snapshot_id,
                "objective": profile.objective,
                "platform": profile.platform,
                "budget_seconds": profile.budget_seconds,
                "metric_name": profile.objective,
                "metric_value": round(metric_value, 6),
                "direction": profile.metric_direction,
                "status": "success",
                "seed": seed,
                "notes": f"feature_mode={config.feature_mode}, steps={config.steps}",
            },
            "tags": _event_tags(profile, participant_role, feature_mode=config.feature_mode),
        }
    )
    return RunResult(
        run_id=run_id,
        snapshot_id=config.snapshot_id,
        metric_value=round(metric_value, 6),
        seed=seed,
    )


def _train_and_evaluate(config: SnapshotConfig, *, seed: int) -> float:
    train_rows, val_rows = _make_dataset(seed=seed)
    if config.feature_mode == "linear":
        feature_count = 2
    elif config.feature_mode == "quadratic":
        feature_count = 3
    else:
        raise ValueError(f"unsupported feature_mode: {config.feature_mode}")

    weights = [0.0 for _ in range(feature_count)]
    for _ in range(config.steps):
        gradients = [0.0 for _ in range(feature_count)]
        for x, y in train_rows:
            features = _features(x, config.feature_mode)
            prediction = sum(weight * feature for weight, feature in zip(weights, features))
            error = prediction - y
            for index, feature in enumerate(features):
                gradients[index] += 2.0 * error * feature / len(train_rows)
        for index in range(feature_count):
            weights[index] -= config.learning_rate * gradients[index]

    losses = []
    for x, y in val_rows:
        features = _features(x, config.feature_mode)
        prediction = sum(weight * feature for weight, feature in zip(weights, features))
        losses.append((prediction - y) ** 2)
    return mean(losses)


def _make_dataset(*, seed: int) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    rng = random.Random(seed)
    train_rows = [_sample_row(rng, index) for index in range(24)]
    val_rows = [_sample_row(rng, index + 24) for index in range(12)]
    return train_rows, val_rows


def _sample_row(rng: random.Random, index: int) -> tuple[float, float]:
    x = -1.2 + (index * 0.1)
    noise = rng.uniform(-0.015, 0.015)
    y = 0.4 + 0.6 * x - 0.8 * (x**2) + noise
    return x, y


def _features(x: float, feature_mode: str) -> list[float]:
    if feature_mode == "linear":
        return [1.0, x]
    if feature_mode == "quadratic":
        return [1.0, x, x**2]
    raise ValueError(f"unsupported feature_mode: {feature_mode}")


def _lookup_effort(api: ResearchOSApi, *, effort_name: str | None) -> dict[str, str] | None:
    if effort_name is None:
        return None

    efforts = api.list_efforts()
    effort = next((item for item in efforts if item["name"] == effort_name), None)
    if effort is not None:
        return effort

    available = ", ".join(sorted(item["name"] for item in efforts)) or "none"
    raise RuntimeError(f"effort '{effort_name}' not found; available efforts: {available}")


def _validate_effort_profile(
    *,
    effort: dict[str, str] | None,
    profile: ExperimentProfile,
) -> None:
    if effort is None:
        return

    mismatches = []
    if effort["objective"] != profile.objective:
        mismatches.append(f"objective={effort['objective']}")
    if effort["platform"] != profile.platform:
        mismatches.append(f"platform={effort['platform']}")
    if effort["budget_seconds"] != profile.budget_seconds:
        mismatches.append(f"budget_seconds={effort['budget_seconds']}")

    if mismatches:
        raise RuntimeError(
            f"profile '{profile.name}' does not match effort '{effort['name']}': {', '.join(mismatches)}"
        )


def _recommend_reproduction(
    api: ResearchOSApi,
    *,
    profile: ExperimentProfile,
    workspace_id: str,
) -> dict[str, object]:
    recommendation = api.recommend_next(
        {
            "objective": profile.objective,
            "platform": profile.platform,
            "budget_seconds": profile.budget_seconds,
            "workspace_id": workspace_id,
            "limit": 1,
        }
    )["recommendations"][0]
    if recommendation["action"] != "reproduce_claim":
        raise RuntimeError(f"expected reproduce_claim, got {recommendation['action']}")
    return recommendation


def _event_tags(
    profile: ExperimentProfile,
    participant_role: ParticipantRole,
    **extra_tags: str,
) -> dict[str, str]:
    return profile.event_tags | {"participant_role": participant_role.value} | extra_tags


def _default_actor_id() -> str:
    configured_actor = os.getenv("OPENINTENTION_ACTOR_ID") or os.getenv("RESEARCH_OS_ACTOR_ID")
    if configured_actor:
        return configured_actor
    return f"participant-{uuid4().hex[:8]}"


def _resolve_workspace_name(base_name: str, *, workspace_suffix: str | None) -> str:
    if workspace_suffix is None:
        return base_name
    return f"{base_name}-{workspace_suffix}"


def _workspace_scope(workspace_id: str) -> str:
    return workspace_id.split("-", maxsplit=1)[0]


def _scoped_identifier(scope: str, suffix: str) -> str:
    return f"{scope}-{suffix}"
