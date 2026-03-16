from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from research_os.artifacts.local import LocalArtifactRegistry  # noqa: E402
from research_os.domain.models import CreateEffortRequest, CreateWorkspaceRequest, EventEnvelope, EventKind  # noqa: E402
from research_os.ledger.sqlite import SQLiteEventStore  # noqa: E402
from research_os.service import ResearchOSService  # noqa: E402
from research_os.settings import Settings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo research OS data.")
    parser.add_argument("--reset", action="store_true", help="Delete the local SQLite DB before seeding.")
    args = parser.parse_args()

    settings = Settings.from_env()
    db_path = Path(settings.db_path)

    if args.reset and db_path.exists():
        db_path.unlink()

    settings.ensure_directories()
    store = SQLiteEventStore(settings.db_path)
    service = ResearchOSService(store, default_frontier_size=settings.default_frontier_size)
    artifact_registry = LocalArtifactRegistry(settings.artifact_root)

    eval_effort = service.create_effort(
        CreateEffortRequest(
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
            actor_id="seed",
        )
    )
    inference_effort = service.create_effort(
        CreateEffortRequest(
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
            actor_id="seed",
        )
    )

    snapshot_artifacts = {
        "snap-baseline": artifact_registry.put_bytes(b"demo snapshot bundle: snap-baseline"),
        "snap-attn-v2": artifact_registry.put_bytes(b"demo snapshot bundle: snap-attn-v2"),
        "snap-opt-cosine": artifact_registry.put_bytes(b"demo snapshot bundle: snap-opt-cosine"),
        "snap-arch-mix": artifact_registry.put_bytes(b"demo snapshot bundle: snap-arch-mix"),
        "snap-h100-kernel": artifact_registry.put_bytes(b"demo snapshot bundle: snap-h100-kernel"),
    }

    ws_attn = service.create_workspace(
        CreateWorkspaceRequest(
            name="attention-sweep-a100",
            objective="val_bpb",
            platform="A100",
            budget_seconds=300,
            effort_id=eval_effort.effort_id,
            description="Explore attention variants under a fixed 5 minute budget.",
            tags={"topic": "attention", "device": "A100"},
            actor_id="seed",
        )
    )
    ws_opt = service.create_workspace(
        CreateWorkspaceRequest(
            name="optimizer-schedule-a100",
            objective="val_bpb",
            platform="A100",
            budget_seconds=300,
            effort_id=eval_effort.effort_id,
            description="Test optimizer and schedule changes.",
            tags={"topic": "optimizer", "device": "A100"},
            actor_id="seed",
        )
    )
    ws_arch = service.create_workspace(
        CreateWorkspaceRequest(
            name="novel-arch-a100",
            objective="val_bpb",
            platform="A100",
            budget_seconds=300,
            effort_id=eval_effort.effort_id,
            description="Try architecture-level changes.",
            tags={"topic": "architecture", "device": "A100"},
            actor_id="seed",
        )
    )
    ws_h100 = service.create_workspace(
        CreateWorkspaceRequest(
            name="flash-path-h100",
            objective="tokens_per_second",
            platform="H100",
            budget_seconds=300,
            effort_id=inference_effort.effort_id,
            description="Demonstrate platform-specific frontier separation.",
            tags={"topic": "kernel", "device": "H100"},
            actor_id="seed",
        )
    )

    events = [
        EventEnvelope(
            kind=EventKind.SNAPSHOT_PUBLISHED,
            workspace_id=ws_attn.workspace_id,
            aggregate_id="snap-baseline",
            aggregate_kind="snapshot",
            payload={
                "snapshot_id": "snap-baseline",
                "artifact_uri": snapshot_artifacts["snap-baseline"].uri,
                "source_bundle_digest": snapshot_artifacts["snap-baseline"].digest,
                "git_ref": "refs/workspaces/attention-sweep-a100-baseline",
                "notes": "Shared baseline snapshot for eval effort comparisons.",
            },
            tags={"topic": "baseline", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.SNAPSHOT_PUBLISHED,
            workspace_id=ws_attn.workspace_id,
            aggregate_id="snap-attn-v2",
            aggregate_kind="snapshot",
            payload={
                "snapshot_id": "snap-attn-v2",
                "parent_snapshot_ids": ["snap-baseline"],
                "artifact_uri": snapshot_artifacts["snap-attn-v2"].uri,
                "source_bundle_digest": snapshot_artifacts["snap-attn-v2"].digest,
                "git_ref": "refs/workspaces/attention-sweep-a100",
                "notes": "Introduce grouped-query attention variant.",
            },
            tags={"topic": "attention", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id=ws_attn.workspace_id,
            aggregate_id="run-attn-001",
            aggregate_kind="run",
            payload={
                "run_id": "run-attn-001",
                "snapshot_id": "snap-attn-v2",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.252,
                "direction": "min",
                "status": "success",
                "seed": 11,
                "notes": "Improves over baseline in same wall-clock budget.",
            },
            tags={"topic": "attention", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_ASSERTED,
            workspace_id=ws_attn.workspace_id,
            aggregate_id="claim-attn-001",
            aggregate_kind="claim",
            payload={
                "claim_id": "claim-attn-001",
                "statement": "Grouped-query attention reduces val_bpb by 0.018 at 5 minutes on A100.",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-attn-v2",
                "baseline_snapshot_id": "snap-baseline",
                "objective": "val_bpb",
                "platform": "A100",
                "metric_name": "val_bpb",
                "delta": -0.018,
                "confidence": 0.62,
                "evidence_run_ids": ["run-attn-001"],
            },
            tags={"topic": "attention", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.SNAPSHOT_PUBLISHED,
            workspace_id=ws_opt.workspace_id,
            aggregate_id="snap-baseline",
            aggregate_kind="snapshot",
            payload={
                "snapshot_id": "snap-baseline",
                "artifact_uri": snapshot_artifacts["snap-baseline"].uri,
                "source_bundle_digest": snapshot_artifacts["snap-baseline"].digest,
                "git_ref": "refs/workspaces/optimizer-schedule-a100-baseline",
                "notes": "Shared baseline snapshot for eval effort comparisons.",
            },
            tags={"topic": "baseline", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.SNAPSHOT_PUBLISHED,
            workspace_id=ws_opt.workspace_id,
            aggregate_id="snap-opt-cosine",
            aggregate_kind="snapshot",
            payload={
                "snapshot_id": "snap-opt-cosine",
                "parent_snapshot_ids": ["snap-baseline"],
                "artifact_uri": snapshot_artifacts["snap-opt-cosine"].uri,
                "source_bundle_digest": snapshot_artifacts["snap-opt-cosine"].digest,
                "git_ref": "refs/workspaces/optimizer-schedule-a100",
                "notes": "Switch to cosine decay with warmup.",
            },
            tags={"topic": "optimizer", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id=ws_opt.workspace_id,
            aggregate_id="run-opt-001",
            aggregate_kind="run",
            payload={
                "run_id": "run-opt-001",
                "snapshot_id": "snap-opt-cosine",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.248,
                "direction": "min",
                "status": "success",
                "seed": 17,
            },
            tags={"topic": "optimizer", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_ASSERTED,
            workspace_id=ws_opt.workspace_id,
            aggregate_id="claim-opt-001",
            aggregate_kind="claim",
            payload={
                "claim_id": "claim-opt-001",
                "statement": "Cosine schedule reduces val_bpb by 0.011 at 5 minutes on A100.",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-opt-cosine",
                "baseline_snapshot_id": "snap-baseline",
                "objective": "val_bpb",
                "platform": "A100",
                "metric_name": "val_bpb",
                "delta": -0.011,
                "confidence": 0.71,
                "evidence_run_ids": ["run-opt-001"],
            },
            tags={"topic": "optimizer", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.SNAPSHOT_PUBLISHED,
            workspace_id=ws_attn.workspace_id,
            aggregate_id="snap-opt-repro",
            aggregate_kind="snapshot",
            payload={
                "snapshot_id": "snap-opt-repro",
                "artifact_uri": snapshot_artifacts["snap-opt-cosine"].uri,
                "source_bundle_digest": snapshot_artifacts["snap-opt-cosine"].digest,
                "git_ref": "refs/workspaces/attention-sweep-a100-opt-repro",
                "notes": "Adopt optimizer candidate into attention workspace for independent rerun.",
            },
            tags={"topic": "optimizer", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id=ws_attn.workspace_id,
            aggregate_id="run-opt-repro-001",
            aggregate_kind="run",
            payload={
                "run_id": "run-opt-repro-001",
                "snapshot_id": "snap-opt-repro",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.249,
                "direction": "min",
                "status": "success",
                "seed": 19,
            },
            tags={"topic": "optimizer", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_REPRODUCED,
            workspace_id=ws_attn.workspace_id,
            aggregate_id="claim-opt-001",
            aggregate_kind="claim",
            payload={
                "claim_id": "claim-opt-001",
                "evidence_run_id": "run-opt-repro-001",
                "notes": "Independent rerun confirms effect direction.",
            },
            tags={"topic": "optimizer", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.SNAPSHOT_PUBLISHED,
            workspace_id=ws_arch.workspace_id,
            aggregate_id="snap-baseline",
            aggregate_kind="snapshot",
            payload={
                "snapshot_id": "snap-baseline",
                "artifact_uri": snapshot_artifacts["snap-baseline"].uri,
                "source_bundle_digest": snapshot_artifacts["snap-baseline"].digest,
                "git_ref": "refs/workspaces/novel-arch-a100-baseline",
                "notes": "Shared baseline snapshot for eval effort comparisons.",
            },
            tags={"topic": "baseline", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.SNAPSHOT_PUBLISHED,
            workspace_id=ws_arch.workspace_id,
            aggregate_id="snap-arch-mix",
            aggregate_kind="snapshot",
            payload={
                "snapshot_id": "snap-arch-mix",
                "parent_snapshot_ids": ["snap-baseline"],
                "artifact_uri": snapshot_artifacts["snap-arch-mix"].uri,
                "source_bundle_digest": snapshot_artifacts["snap-arch-mix"].digest,
                "git_ref": "refs/workspaces/novel-arch-a100",
                "notes": "Introduce a new mixer block.",
            },
            tags={"topic": "architecture", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id=ws_arch.workspace_id,
            aggregate_id="run-arch-001",
            aggregate_kind="run",
            payload={
                "run_id": "run-arch-001",
                "snapshot_id": "snap-arch-mix",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.241,
                "direction": "min",
                "status": "success",
                "seed": 23,
            },
            tags={"topic": "architecture", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_ASSERTED,
            workspace_id=ws_arch.workspace_id,
            aggregate_id="claim-arch-001",
            aggregate_kind="claim",
            payload={
                "claim_id": "claim-arch-001",
                "statement": "Mixer block cuts val_bpb by 0.019 at 5 minutes on A100.",
                "claim_type": "improvement",
                "candidate_snapshot_id": "snap-arch-mix",
                "baseline_snapshot_id": "snap-baseline",
                "objective": "val_bpb",
                "platform": "A100",
                "metric_name": "val_bpb",
                "delta": -0.019,
                "confidence": 0.57,
                "evidence_run_ids": ["run-arch-001"],
            },
            tags={"topic": "architecture", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.ADOPTION_RECORDED,
            workspace_id=ws_arch.workspace_id,
            aggregate_id="adopt-opt-001",
            aggregate_kind="adoption",
            payload={
                "subject_type": "claim",
                "subject_id": "claim-opt-001",
                "from_workspace_id": ws_opt.workspace_id,
                "reason": "Adopt the optimizer schedule into the architecture branch.",
            },
            tags={"topic": "adoption", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.SNAPSHOT_PUBLISHED,
            workspace_id=ws_opt.workspace_id,
            aggregate_id="snap-attn-contradiction",
            aggregate_kind="snapshot",
            payload={
                "snapshot_id": "snap-attn-contradiction",
                "artifact_uri": snapshot_artifacts["snap-attn-v2"].uri,
                "source_bundle_digest": snapshot_artifacts["snap-attn-v2"].digest,
                "git_ref": "refs/workspaces/optimizer-schedule-a100-attn-rerun",
                "notes": "Rerun attention candidate under optimizer workspace conditions.",
            },
            tags={"topic": "attention", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id=ws_opt.workspace_id,
            aggregate_id="run-attn-contradiction-001",
            aggregate_kind="run",
            payload={
                "run_id": "run-attn-contradiction-001",
                "snapshot_id": "snap-attn-contradiction",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.261,
                "direction": "min",
                "status": "success",
                "seed": 29,
            },
            tags={"topic": "attention", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.CLAIM_CONTRADICTED,
            workspace_id=ws_opt.workspace_id,
            aggregate_id="claim-attn-001",
            aggregate_kind="claim",
            payload={
                "claim_id": "claim-attn-001",
                "evidence_run_id": "run-attn-contradiction-001",
                "notes": "Observed smaller effect when rerun under independent seed.",
            },
            tags={"topic": "attention", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.SUMMARY_PUBLISHED,
            workspace_id=ws_arch.workspace_id,
            aggregate_id="summary-arch-overnight",
            aggregate_kind="summary",
            payload={
                "summary_id": "summary-arch-overnight",
                "title": "Novel architecture overnight report",
                "format": "markdown",
                "artifact_uri": "file://artifacts/summary-arch-overnight.md",
            },
            tags={"topic": "report", "device": "A100"},
        ),
        EventEnvelope(
            kind=EventKind.SNAPSHOT_PUBLISHED,
            workspace_id=ws_h100.workspace_id,
            aggregate_id="snap-baseline",
            aggregate_kind="snapshot",
            payload={
                "snapshot_id": "snap-baseline",
                "artifact_uri": snapshot_artifacts["snap-baseline"].uri,
                "source_bundle_digest": snapshot_artifacts["snap-baseline"].digest,
                "git_ref": "refs/workspaces/flash-path-h100-baseline",
                "notes": "Shared baseline snapshot for inference effort comparisons.",
            },
            tags={"topic": "baseline", "device": "H100"},
        ),
        EventEnvelope(
            kind=EventKind.SNAPSHOT_PUBLISHED,
            workspace_id=ws_h100.workspace_id,
            aggregate_id="snap-h100-kernel",
            aggregate_kind="snapshot",
            payload={
                "snapshot_id": "snap-h100-kernel",
                "parent_snapshot_ids": ["snap-baseline"],
                "artifact_uri": snapshot_artifacts["snap-h100-kernel"].uri,
                "source_bundle_digest": snapshot_artifacts["snap-h100-kernel"].digest,
                "git_ref": "refs/workspaces/flash-path-h100",
            },
            tags={"topic": "kernel", "device": "H100"},
        ),
        EventEnvelope(
            kind=EventKind.RUN_COMPLETED,
            workspace_id=ws_h100.workspace_id,
            aggregate_id="run-h100-001",
            aggregate_kind="run",
            payload={
                "run_id": "run-h100-001",
                "snapshot_id": "snap-h100-kernel",
                "objective": "tokens_per_second",
                "platform": "H100",
                "budget_seconds": 300,
                "metric_name": "tokens_per_second",
                "metric_value": 1284.0,
                "direction": "max",
                "status": "success",
            },
            tags={"topic": "kernel", "device": "H100"},
        ),
    ]

    for event in events:
        service.append_event(event)

    print(f"Seeded demo data into {settings.db_path}")


if __name__ == "__main__":
    main()
