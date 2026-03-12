from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import create_app
from research_os.artifacts.local import LocalArtifactRegistry
from research_os.settings import Settings


def test_workspace_discussion_publication_is_rendered_from_workspace_state(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "publication-workspace.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)
    artifact_registry = LocalArtifactRegistry(settings.artifact_root)
    snapshot_artifact = artifact_registry.put_bytes(b"workspace discussion snapshot bundle")

    workspace_id = client.post(
        "/api/v1/workspaces",
        json={
            "name": "publisher-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "description": "Publication mirror workspace",
        },
    ).json()["workspace_id"]

    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "snapshot.published",
                "workspace_id": workspace_id,
                "aggregate_id": "snap-pub-1",
                "aggregate_kind": "snapshot",
                "payload": {
                    "snapshot_id": "snap-pub-1",
                    "artifact_uri": snapshot_artifact.uri,
                    "source_bundle_digest": snapshot_artifact.digest,
                    "source_bundle_manifest_uri": "artifact://sha256/" + "a" * 64,
                    "source_bundle_manifest_digest": "sha256:" + "a" * 64,
                    "source_bundle_manifest_signature": "sig-workspace-demo",
                    "source_bundle_manifest_signature_scheme": "ed25519",
                    "source_bundle_manifest_provenance_schema": "openintention-artifact-manifest-v1",
                    "source_bundle_manifest_provenance_version": "1",
                    "git_ref": "refs/workspaces/publisher-demo",
                },
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "claim.asserted",
                "workspace_id": workspace_id,
                "aggregate_id": "claim-pub-1",
                "aggregate_kind": "claim",
                "payload": {
                    "claim_id": "claim-pub-1",
                    "statement": "The publication snapshot improves validation bpb.",
                    "claim_type": "improvement",
                    "candidate_snapshot_id": "snap-pub-1",
                    "objective": "val_bpb",
                    "platform": "A100",
                },
            },
        ).status_code
        == 201
    )

    response = client.get(f"/api/v1/publications/workspaces/{workspace_id}/discussion")
    assert response.status_code == 200
    body = response.json()["body"]
    assert response.json()["kind"] == "github.discussion"
    assert "Discussion: publisher-demo" in body
    assert "Role: `contributor`" in body
    assert "Publication mirror workspace" in body
    assert "claim-pub-1" in body
    assert "snapshot.published" in body
    assert "Manifest URI" in body
    assert "openintention-artifact-manifest-v1" in body


def test_snapshot_pull_request_publication_is_rendered_from_snapshot_and_runs(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "publication-snapshot.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)
    artifact_registry = LocalArtifactRegistry(settings.artifact_root)
    snapshot_artifact = artifact_registry.put_bytes(b"snapshot pull request bundle")

    workspace_id = client.post(
        "/api/v1/workspaces",
        json={
            "name": "publisher-snapshot-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    ).json()["workspace_id"]

    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "snapshot.published",
                "workspace_id": workspace_id,
                "aggregate_id": "snap-pr-1",
                "aggregate_kind": "snapshot",
                "payload": {
                    "snapshot_id": "snap-pr-1",
                    "parent_snapshot_ids": ["snap-base"],
                    "artifact_uri": snapshot_artifact.uri,
                    "source_bundle_digest": snapshot_artifact.digest,
                    "source_bundle_manifest_uri": "artifact://sha256/" + "d" * 64,
                    "source_bundle_manifest_digest": "sha256:" + "d" * 64,
                    "source_bundle_manifest_signature": "sig-pr-demo",
                    "source_bundle_manifest_signature_scheme": "ed25519",
                    "source_bundle_manifest_provenance_schema": "openintention-artifact-manifest-v1",
                    "source_bundle_manifest_provenance_version": "1",
                    "git_ref": "refs/workspaces/publisher-snapshot-demo",
                    "notes": "Try the improved optimizer schedule.",
                },
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "run.completed",
                "workspace_id": workspace_id,
                "aggregate_id": "run-pr-1",
                "aggregate_kind": "run",
                "payload": {
                    "run_id": "run-pr-1",
                    "snapshot_id": "snap-pr-1",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "budget_seconds": 300,
                    "metric_name": "val_bpb",
                    "metric_value": 1.19,
                    "direction": "min",
                    "status": "success",
                },
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "claim.asserted",
                "workspace_id": workspace_id,
                "aggregate_id": "claim-pr-1",
                "aggregate_kind": "claim",
                "payload": {
                    "claim_id": "claim-pr-1",
                    "statement": "The optimizer schedule improves validation bpb.",
                    "claim_type": "improvement",
                    "candidate_snapshot_id": "snap-pr-1",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "candidate_snapshot_manifest_uri": "artifact://sha256/" + "d" * 64,
                    "candidate_snapshot_manifest_digest": "sha256:" + "d" * 64,
                    "candidate_snapshot_manifest_signature": "sig-pr-claim",
                    "candidate_snapshot_manifest_signature_scheme": "ed25519",
                    "candidate_snapshot_manifest_provenance_schema": "openintention-artifact-manifest-v1",
                    "candidate_snapshot_manifest_provenance_version": "1",
                },
            },
        ).status_code
        == 201
    )

    response = client.get(f"/api/v1/publications/workspaces/{workspace_id}/pull-requests/snap-pr-1")
    assert response.status_code == 200
    body = response.json()["body"]
    assert response.json()["kind"] == "github.pull_request"
    assert "PR: snap-pr-1" in body
    assert "refs/workspaces/publisher-snapshot-demo" in body
    assert snapshot_artifact.digest in body
    assert str(snapshot_artifact.uri) in body
    assert "Snapshot Provenance" in body
    assert "Manifest URI" in body
    assert "Candidate Claim Provenance" in body
    assert "Manifest URI" in body
    assert "run-pr-1" in body
    assert "claim-pr-1" in body


def test_snapshot_pull_request_hides_local_file_artifact_paths(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "publication-snapshot-local-file.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    workspace_id = client.post(
        "/api/v1/workspaces",
        json={
            "name": "publisher-local-file-demo",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    ).json()["workspace_id"]

    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "snapshot.published",
                "workspace_id": workspace_id,
                "aggregate_id": "snap-local-file-1",
                "aggregate_kind": "snapshot",
                "payload": {
                    "snapshot_id": "snap-local-file-1",
                    "artifact_uri": "file:///tmp/local-artifact-bundle.json",
                    "source_bundle_digest": "sha256:demo-local-file",
                    "git_ref": "refs/workspaces/publisher-local-file-demo",
                },
            },
        ).status_code
        == 201
    )

    response = client.get(f"/api/v1/publications/workspaces/{workspace_id}/pull-requests/snap-local-file-1")
    assert response.status_code == 200
    body = response.json()["body"]
    assert "file:///tmp/local-artifact-bundle.json" not in body
    assert "local artifact plane path hidden (digest=sha256:demo-local-file)" in body


def test_eval_effort_overview_publication_is_rendered_from_effort_state(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "publication-effort-eval.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    effort_id = client.post(
        "/api/v1/efforts",
        json={
            "name": "Eval Sprint: improve validation loss under fixed budget",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "summary": "Seeded eval effort for short fixed-budget loops.",
            "tags": {"effort_type": "eval", "seeded": "true"},
        },
    ).json()["effort_id"]
    workspace_id = client.post(
        "/api/v1/workspaces",
        json={
            "name": "eval-participant",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "effort_id": effort_id,
            "actor_id": "participant-alpha",
        },
    ).json()["workspace_id"]
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "snapshot.published",
                "workspace_id": workspace_id,
                "aggregate_id": "snap-effort-1",
                "aggregate_kind": "snapshot",
                "payload": {
                    "snapshot_id": "snap-effort-1",
                    "artifact_uri": "artifact://sha256/" + "a" * 64,
                },
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "run.completed",
                "workspace_id": workspace_id,
                "aggregate_id": "run-effort-1",
                "aggregate_kind": "run",
                "payload": {
                    "run_id": "run-effort-1",
                    "snapshot_id": "snap-effort-1",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "budget_seconds": 300,
                    "metric_name": "val_bpb",
                    "metric_value": 1.18,
                    "direction": "min",
                    "status": "success",
                },
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "claim.asserted",
                "workspace_id": workspace_id,
                "aggregate_id": "claim-effort-1",
                "aggregate_kind": "claim",
                "payload": {
                    "claim_id": "claim-effort-1",
                    "statement": "The candidate lowers validation bpb.",
                    "claim_type": "improvement",
                    "candidate_snapshot_id": "snap-effort-1",
                    "objective": "val_bpb",
                    "platform": "A100",
                },
            },
        ).status_code
        == 201
    )

    response = client.get(f"/api/v1/publications/efforts/{effort_id}")
    assert response.status_code == 200
    body = response.json()["body"]
    assert response.json()["kind"] == "github.issue"
    assert "Effort: Eval Sprint: improve validation loss under fixed budget" in body
    assert "eval-participant" in body
    assert "claim-effort-1" in body
    assert "docs/seeded-efforts.md" in body
    assert "/Users/aliargun/Documents/GitHub/research-os/docs/seeded-efforts.md" not in body
    assert "actor=participant-alpha" in body
    assert "role=contributor" in body
    assert "python3 -m clients.tiny_loop.run" in body


def test_inference_effort_overview_publication_uses_inference_join_profile(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "publication-effort-inference.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    effort_id = client.post(
        "/api/v1/efforts",
        json={
            "name": "Inference Sprint: improve flash-path throughput on H100",
            "objective": "tokens_per_second",
            "platform": "H100",
            "budget_seconds": 300,
            "summary": "Seeded inference effort for bounded throughput loops.",
            "tags": {"effort_type": "inference", "seeded": "true"},
        },
    ).json()["effort_id"]
    workspace_id = client.post(
        "/api/v1/workspaces",
        json={
            "name": "inference-participant",
            "objective": "tokens_per_second",
            "platform": "H100",
            "budget_seconds": 300,
            "effort_id": effort_id,
        },
    ).json()["workspace_id"]
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "snapshot.published",
                "workspace_id": workspace_id,
                "aggregate_id": "snap-inference-1",
                "aggregate_kind": "snapshot",
                "payload": {
                    "snapshot_id": "snap-inference-1",
                    "artifact_uri": "artifact://sha256/" + "a" * 64,
                },
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "run.completed",
                "workspace_id": workspace_id,
                "aggregate_id": "run-inference-1",
                "aggregate_kind": "run",
                "payload": {
                    "run_id": "run-inference-1",
                    "snapshot_id": "snap-inference-1",
                    "objective": "tokens_per_second",
                    "platform": "H100",
                    "budget_seconds": 300,
                    "metric_name": "tokens_per_second",
                    "metric_value": 1284.0,
                    "direction": "max",
                    "status": "success",
                },
            },
        ).status_code
        == 201
    )

    response = client.get(f"/api/v1/publications/efforts/{effort_id}")
    assert response.status_code == 200
    body = response.json()["body"]
    assert "Effort: Inference Sprint: improve flash-path throughput on H100" in body
    assert "inference-participant" in body
    assert "tokens_per_second" in body
    assert "python3 -m clients.tiny_loop.run --profile inference-sprint" in body


def test_effort_overview_publication_uses_configured_public_base_url(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "publication-effort-public-base-url.db"),
        artifact_root=str(tmp_path / "artifacts"),
        public_base_url="https://api.openintention.io",
    )
    app = create_app(settings)
    client = TestClient(app)

    effort_id = client.post(
        "/api/v1/efforts",
        json={
            "name": "Eval Sprint: improve validation loss under fixed budget",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "summary": "Seeded eval effort for hosted participation.",
            "tags": {"effort_type": "eval", "seeded": "true"},
        },
    ).json()["effort_id"]

    response = client.get(f"/api/v1/publications/efforts/{effort_id}")
    assert response.status_code == 200
    body = response.json()["body"]
    assert "--base-url https://api.openintention.io" in body
    assert "--actor-id <handle>" in body


def test_effort_overview_publication_uses_explicit_join_command_tag(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "publication-effort-explicit-join-command.db"),
        artifact_root=str(tmp_path / "artifacts"),
        public_base_url="https://openintention-api-production.up.railway.app",
    )
    app = create_app(settings)
    client = TestClient(app)

    effort_id = client.post(
        "/api/v1/efforts",
        json={
            "name": "MLX History Sprint: improve val_bpb on Apple Silicon",
            "objective": "val_bpb",
            "platform": "Apple-Silicon-MLX",
            "budget_seconds": 300,
                "summary": "Compounding external harness effort.",
                "tags": {
                    "effort_type": "mlx_history",
                    "join_brief_path": "README.md#external-mlx-compounding-proof",
                    "join_command": (
                        "python3 scripts/run_mlx_history_compounding_smoke.py "
                        "--repo-path <path_to_mlx_history> "
                    "--base-url https://openintention-api-production.up.railway.app"
                ),
            },
        },
    ).json()["effort_id"]

    response = client.get(f"/api/v1/publications/efforts/{effort_id}")
    assert response.status_code == 200
    body = response.json()["body"]
    assert "README.md#external-mlx-compounding-proof" in body
    assert "python3 scripts/run_mlx_history_compounding_smoke.py" in body
    assert "clients.tiny_loop.run" not in body


def test_effort_overview_publication_infers_mlx_history_brief_for_legacy_efforts(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "publication-effort-legacy-mlx-history.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    effort_id = client.post(
        "/api/v1/efforts",
        json={
            "name": "Legacy MLX History Effort",
            "objective": "val_bpb",
            "platform": "Apple-Silicon-MLX",
            "budget_seconds": 300,
            "summary": "Legacy effort missing a brief override tag.",
            "tags": {
                "effort_type": "mlx_history",
                "external_harness": "mlx-history",
                "join_command": "python3 scripts/run_mlx_history_compounding_smoke.py --repo-path /tmp/mlx-history --base-url http://testserver",
            },
        },
    ).json()["effort_id"]

    response = client.get(f"/api/v1/publications/efforts/{effort_id}")
    assert response.status_code == 200
    body = response.json()["body"]
    assert "README.md#external-mlx-compounding-proof" in body
    assert "python3 scripts/run_mlx_history_compounding_smoke.py" in body
    assert "docs/seeded-efforts.md" not in body


def test_effort_overview_publication_marks_historical_proof_runs(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "publication-effort-historical-proof.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    effort_id = client.post(
        "/api/v1/efforts",
        json={
            "name": "MLX History Sprint: improve val_bpb on Apple Silicon",
            "objective": "val_bpb",
            "platform": "Apple-Silicon-MLX",
            "budget_seconds": 300,
            "summary": "Historical proof run.",
            "tags": {
                "external_harness": "mlx-history",
                "public_proof": "true",
                "proof_series": "mlx-history-apple-silicon-300",
                "proof_version": "1",
            },
        },
    ).json()["effort_id"]
    successor_id = client.post(
        "/api/v1/efforts",
        json={
            "name": "MLX History Sprint: improve val_bpb on Apple Silicon (proof v2)",
            "objective": "val_bpb",
            "platform": "Apple-Silicon-MLX",
            "budget_seconds": 300,
            "summary": "Current proof run.",
            "tags": {
                "external_harness": "mlx-history",
                "public_proof": "true",
                "proof_series": "mlx-history-apple-silicon-300",
                "proof_version": "2",
            },
        },
    ).json()["effort_id"]
    assert (
        client.post(
            "/api/v1/events",
            json={
                "kind": "effort.rolled_over",
                "aggregate_id": effort_id,
                "aggregate_kind": "effort",
                "payload": {
                    "effort_id": effort_id,
                    "successor_effort_id": successor_id,
                },
                "tags": {
                    "public_proof": "true",
                    "proof_series": "mlx-history-apple-silicon-300",
                    "proof_version": "1",
                    "proof_status": "historical",
                },
            },
        ).status_code
        == 201
    )

    response = client.get(f"/api/v1/publications/efforts/{effort_id}")
    assert response.status_code == 200
    body = response.json()["body"]
    assert "Proof state: `historical`" in body
    assert successor_id in body
