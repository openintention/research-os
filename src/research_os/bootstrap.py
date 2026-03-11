from __future__ import annotations

from dataclasses import dataclass

from research_os.domain.models import CreateEffortRequest, EffortView
from research_os.service import ResearchOSService


@dataclass(frozen=True, slots=True)
class SeededEffortDefinition:
    name: str
    objective: str
    platform: str
    budget_seconds: int
    summary: str
    tags: dict[str, str]


SEEDED_EFFORTS: tuple[SeededEffortDefinition, ...] = (
    SeededEffortDefinition(
        name="Eval Sprint: improve validation loss under fixed budget",
        objective="val_bpb",
        platform="A100",
        budget_seconds=300,
        summary=(
            "Seeded eval / benchmark effort for short A100 loops that improve validation "
            "loss without broadening scope."
        ),
        tags={
            "effort_type": "eval",
            "seeded": "true",
            "public_proof": "true",
            "proof_series": "eval-a100-300",
            "proof_version": "1",
        },
    ),
    SeededEffortDefinition(
        name="Inference Sprint: improve flash-path throughput on H100",
        objective="tokens_per_second",
        platform="H100",
        budget_seconds=300,
        summary=(
            "Seeded inference optimization effort for faster H100 decode paths with clear "
            "hardware-aware contribution boundaries."
        ),
        tags={
            "effort_type": "inference",
            "seeded": "true",
            "public_proof": "true",
            "proof_series": "inference-h100-300",
            "proof_version": "1",
        },
    ),
)


def ensure_seeded_efforts(
    service: ResearchOSService,
    *,
    actor_id: str = "openintention-seed",
) -> list[EffortView]:
    existing_by_name = {effort.name: effort for effort in service.list_efforts()}
    seeded_efforts: list[EffortView] = []

    for definition in SEEDED_EFFORTS:
        effort = existing_by_name.get(definition.name)
        if effort is None:
            service.create_effort(
                CreateEffortRequest(
                    name=definition.name,
                    objective=definition.objective,
                    platform=definition.platform,
                    budget_seconds=definition.budget_seconds,
                    summary=definition.summary,
                    tags=definition.tags,
                    actor_id=actor_id,
                )
            )
            effort = service.get_effort_by_name(definition.name)
        if effort is None:
            raise RuntimeError(f"failed to bootstrap seeded effort '{definition.name}'")
        seeded_efforts.append(effort)

    return seeded_efforts
