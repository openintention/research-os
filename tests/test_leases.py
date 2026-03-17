from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from apps.api.main import create_app
from research_os.settings import Settings


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, *, seconds: int) -> None:
        self._now = self._now + timedelta(seconds=seconds)


def _create_client(tmp_path, *, clock: MutableClock) -> TestClient:
    settings = Settings(
        db_path=str(tmp_path / "leases.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings, now_fn=clock.now)
    return TestClient(app)


def _create_workspace(
    client: TestClient,
    *,
    name: str,
    participant_role: str = "contributor",
) -> str:
    response = client.post(
        "/api/v1/workspaces",
        json={
            "name": name,
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "participant_role": participant_role,
            "actor_id": name,
        },
    )
    assert response.status_code == 201
    return response.json()["workspace_id"]


def _create_effort(
    client: TestClient,
    *,
    name: str,
    objective: str = "val_bpb",
    platform: str = "A100",
    budget_seconds: int = 300,
) -> str:
    response = client.post(
        "/api/v1/efforts",
        json={
            "name": name,
            "objective": objective,
            "platform": platform,
            "budget_seconds": budget_seconds,
            "actor_id": "lease-test",
        },
    )
    assert response.status_code == 201
    return response.json()["effort_id"]


def _append_snapshot(client: TestClient, *, workspace_id: str, snapshot_id: str) -> None:
    response = client.post(
        "/api/v1/events",
        json={
            "kind": "snapshot.published",
            "workspace_id": workspace_id,
            "aggregate_id": snapshot_id,
            "aggregate_kind": "snapshot",
            "payload": {
                "snapshot_id": snapshot_id,
                "artifact_uri": "artifact://sha256/" + "a" * 64,
            },
        },
    )
    assert response.status_code == 201


def _append_run(
    client: TestClient,
    *,
    workspace_id: str,
    run_id: str,
    snapshot_id: str,
) -> None:
    response = client.post(
        "/api/v1/events",
        json={
            "kind": "run.completed",
            "workspace_id": workspace_id,
            "aggregate_id": run_id,
            "aggregate_kind": "run",
            "payload": {
                "run_id": run_id,
                "snapshot_id": snapshot_id,
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "metric_name": "val_bpb",
                "metric_value": 1.23,
                "direction": "min",
                "status": "success",
            },
        },
    )
    assert response.status_code == 201


def _append_claim(client: TestClient, *, workspace_id: str, claim_id: str, snapshot_id: str, run_id: str) -> None:
    response = client.post(
        "/api/v1/events",
        json={
            "kind": "claim.asserted",
            "workspace_id": workspace_id,
            "aggregate_id": claim_id,
            "aggregate_kind": "claim",
            "payload": {
                "claim_id": claim_id,
                "statement": "Quadratic candidate improves validation loss.",
                "claim_type": "improvement",
                "candidate_snapshot_id": snapshot_id,
                "objective": "val_bpb",
                "platform": "A100",
                "metric_name": "val_bpb",
                "delta": -0.02,
                "evidence_run_ids": [run_id],
            },
        },
    )
    assert response.status_code == 201


def _append_reproduction(
    client: TestClient,
    *,
    workspace_id: str,
    claim_id: str,
    run_id: str,
) -> None:
    response = client.post(
        "/api/v1/events",
        json={
            "kind": "claim.reproduced",
            "workspace_id": workspace_id,
            "aggregate_id": claim_id,
            "aggregate_kind": "claim",
            "payload": {
                "claim_id": claim_id,
                "evidence_run_id": run_id,
            },
        },
    )
    assert response.status_code == 201


def _seed_claim_flow(client: TestClient) -> tuple[str, str]:
    source_workspace_id = _create_workspace(client, name="source-worker")
    _append_snapshot(client, workspace_id=source_workspace_id, snapshot_id="snap-source-1")
    _append_run(
        client,
        workspace_id=source_workspace_id,
        snapshot_id="snap-source-1",
        run_id="run-source-1",
    )
    _append_claim(
        client,
        workspace_id=source_workspace_id,
        claim_id="claim-source-1",
        snapshot_id="snap-source-1",
        run_id="run-source-1",
    )
    verifier_workspace_id = _create_workspace(client, name="verifier-worker", participant_role="verifier")
    return source_workspace_id, verifier_workspace_id


def test_lease_endpoints_bind_to_planner_work_items_and_are_idempotent(tmp_path) -> None:
    clock = MutableClock(datetime(2026, 3, 16, tzinfo=timezone.utc))
    client = _create_client(tmp_path, clock=clock)
    _, verifier_workspace_id = _seed_claim_flow(client)

    planner_response = client.post(
        "/api/v1/planner/recommend",
        json={
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "limit": 1,
        },
    )
    assert planner_response.status_code == 200
    recommendation = planner_response.json()["recommendations"][0]
    assert recommendation["planner_fingerprint"].startswith("sha256:")
    assert recommendation["work_item_type"] == "reproduce_claim"
    assert recommendation["subject_type"] == "claim"
    assert recommendation["subject_id"] == "claim-source-1"

    acquire_payload = {
        "request_id": "lease-acquire-1",
        "node_id": "node_verifierworker0001",
        "planner_fingerprint": recommendation["planner_fingerprint"],
        "ttl_seconds": 120,
        "participant_role": "verifier",
        "work_item_type": recommendation["work_item_type"],
        "subject_type": recommendation["subject_type"],
        "subject_id": recommendation["subject_id"],
        "objective": "val_bpb",
        "platform": "A100",
        "budget_seconds": 300,
        "workspace_id": verifier_workspace_id,
    }
    acquire_response = client.post("/api/v1/leases/acquire", json=acquire_payload)
    assert acquire_response.status_code == 200
    lease = acquire_response.json()
    assert lease["status"] == "acquired"
    assert lease["holder_workspace_id"] == verifier_workspace_id
    assert lease["holder_node_id"] == "node_verifierworker0001"
    assert lease["renewal_count"] == 0

    repeated_acquire = client.post("/api/v1/leases/acquire", json=acquire_payload)
    assert repeated_acquire.status_code == 200
    assert repeated_acquire.json()["lease_id"] == lease["lease_id"]

    competing_acquire = client.post(
        "/api/v1/leases/acquire",
        json={**acquire_payload, "request_id": "lease-acquire-2"},
    )
    assert competing_acquire.status_code == 200
    assert competing_acquire.json()["lease_id"] == lease["lease_id"]

    renew_response = client.post(
        f"/api/v1/leases/{lease['lease_id']}/renew",
        json={
            "request_id": "lease-renew-1",
            "node_id": "node_verifierworker0001",
            "ttl_seconds": 60,
        },
    )
    assert renew_response.status_code == 200
    renewed = renew_response.json()
    assert renewed["status"] == "renewed"
    assert renewed["renewal_count"] == 1

    repeated_renew = client.post(
        f"/api/v1/leases/{lease['lease_id']}/renew",
        json={
            "request_id": "lease-renew-1",
            "node_id": "node_verifierworker0001",
            "ttl_seconds": 60,
        },
    )
    assert repeated_renew.status_code == 200
    assert repeated_renew.json()["renewal_count"] == 1

    release_response = client.post(
        f"/api/v1/leases/{lease['lease_id']}/release",
        json={
            "request_id": "lease-release-1",
            "node_id": "node_verifierworker0001",
        },
    )
    assert release_response.status_code == 200
    released = release_response.json()
    assert released["status"] == "released"
    assert released["released_at"] is not None

    reacquire_response = client.post(
        "/api/v1/leases/acquire",
        json={**acquire_payload, "request_id": "lease-acquire-3"},
    )
    assert reacquire_response.status_code == 200
    reacquired = reacquire_response.json()
    assert reacquired["lease_id"] != lease["lease_id"]
    assert reacquired["status"] == "acquired"

    fail_response = client.post(
        f"/api/v1/leases/{reacquired['lease_id']}/fail",
        json={
            "request_id": "lease-fail-1",
            "node_id": "node_verifierworker0001",
            "failure_reason": "worker crashed before publishing verifier evidence",
        },
    )
    assert fail_response.status_code == 200
    failed = fail_response.json()
    assert failed["status"] == "failed"
    assert failed["failure_reason"] == "worker crashed before publishing verifier evidence"


def test_list_leases_can_filter_by_effort_id(tmp_path) -> None:
    clock = MutableClock(datetime(2026, 3, 16, tzinfo=timezone.utc))
    client = _create_client(tmp_path, clock=clock)
    effort_alpha = _create_effort(client, name="effort alpha")
    effort_beta = _create_effort(client, name="effort beta")

    alpha_response = client.post(
        "/api/v1/leases/acquire",
        json={
            "request_id": "lease-effort-alpha-1",
            "node_id": "node_effortworkeralpha01",
            "planner_fingerprint": "sha256:" + "a" * 64,
            "ttl_seconds": 120,
            "participant_role": "contributor",
            "work_item_type": "explore_effort",
            "subject_type": "effort",
            "subject_id": effort_alpha,
            "effort_id": effort_alpha,
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    assert alpha_response.status_code == 200

    beta_response = client.post(
        "/api/v1/leases/acquire",
        json={
            "request_id": "lease-effort-beta-1",
            "node_id": "node_effortworkerbeta01",
            "planner_fingerprint": "sha256:" + "b" * 64,
            "ttl_seconds": 120,
            "participant_role": "contributor",
            "work_item_type": "explore_effort",
            "subject_type": "effort",
            "subject_id": effort_beta,
            "effort_id": effort_beta,
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
        },
    )
    assert beta_response.status_code == 200

    filtered_response = client.get(f"/api/v1/leases?effort_id={effort_alpha}")
    assert filtered_response.status_code == 200
    body = filtered_response.json()
    assert len(body) == 1
    assert body[0]["lease"]["effort_id"] == effort_alpha
    assert body[0]["lease"]["subject_id"] == effort_alpha
    assert body[0]["liveness_status"] == "missing"

    unfiltered_response = client.get("/api/v1/leases")
    assert unfiltered_response.status_code == 200
    assert len(unfiltered_response.json()) == 2


def test_expired_verifier_lease_cannot_renew_but_late_lineage_still_counts(tmp_path) -> None:
    clock = MutableClock(datetime(2026, 3, 16, tzinfo=timezone.utc))
    client = _create_client(tmp_path, clock=clock)
    _, verifier_workspace_id = _seed_claim_flow(client)

    planner_response = client.post(
        "/api/v1/planner/recommend",
        json={
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "limit": 1,
        },
    )
    recommendation = planner_response.json()["recommendations"][0]
    acquire_response = client.post(
        "/api/v1/leases/acquire",
        json={
            "request_id": "lease-expire-acquire-1",
            "node_id": "node_verifierworker0002",
            "planner_fingerprint": recommendation["planner_fingerprint"],
            "ttl_seconds": 30,
            "participant_role": "verifier",
            "work_item_type": recommendation["work_item_type"],
            "subject_type": recommendation["subject_type"],
            "subject_id": recommendation["subject_id"],
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "workspace_id": verifier_workspace_id,
        },
    )
    assert acquire_response.status_code == 200
    lease_id = acquire_response.json()["lease_id"]

    clock.advance(seconds=31)

    renew_response = client.post(
        f"/api/v1/leases/{lease_id}/renew",
        json={
            "request_id": "lease-expire-renew-1",
            "node_id": "node_verifierworker0002",
            "ttl_seconds": 30,
        },
    )
    assert renew_response.status_code == 409
    assert "expired" in renew_response.json()["detail"]

    _append_snapshot(client, workspace_id=verifier_workspace_id, snapshot_id="snap-verifier-1")
    _append_run(
        client,
        workspace_id=verifier_workspace_id,
        snapshot_id="snap-verifier-1",
        run_id="run-verifier-1",
    )
    _append_reproduction(
        client,
        workspace_id=verifier_workspace_id,
        claim_id="claim-source-1",
        run_id="run-verifier-1",
    )

    complete_response = client.post(
        f"/api/v1/leases/{lease_id}/complete",
        json={
            "request_id": "lease-expire-complete-1",
            "node_id": "node_verifierworker0002",
            "workspace_id": verifier_workspace_id,
            "observed_run_id": "run-verifier-1",
            "observed_claim_id": "claim-source-1",
        },
    )
    assert complete_response.status_code == 200
    completed = complete_response.json()
    assert completed["status"] == "expired"
    assert completed["stale_completion"] is True
    assert completed["completed_at"] is not None

    claims_response = client.get("/api/v1/claims?objective=val_bpb&platform=A100")
    assert claims_response.status_code == 200
    claim = next(item for item in claims_response.json() if item["claim_id"] == "claim-source-1")
    assert claim["support_count"] == 1
    assert claim["status"] == "supported"


def test_verifier_completion_requires_verifier_lineage_event(tmp_path) -> None:
    clock = MutableClock(datetime(2026, 3, 16, tzinfo=timezone.utc))
    client = _create_client(tmp_path, clock=clock)
    _, verifier_workspace_id = _seed_claim_flow(client)

    planner_response = client.post(
        "/api/v1/planner/recommend",
        json={
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "limit": 1,
        },
    )
    recommendation = planner_response.json()["recommendations"][0]
    acquire_response = client.post(
        "/api/v1/leases/acquire",
        json={
            "request_id": "lease-complete-acquire-1",
            "node_id": "node_verifierworker0003",
            "planner_fingerprint": recommendation["planner_fingerprint"],
            "ttl_seconds": 60,
            "participant_role": "verifier",
            "work_item_type": recommendation["work_item_type"],
            "subject_type": recommendation["subject_type"],
            "subject_id": recommendation["subject_id"],
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "workspace_id": verifier_workspace_id,
        },
    )
    lease_id = acquire_response.json()["lease_id"]

    _append_snapshot(client, workspace_id=verifier_workspace_id, snapshot_id="snap-verifier-2")
    _append_run(
        client,
        workspace_id=verifier_workspace_id,
        snapshot_id="snap-verifier-2",
        run_id="run-verifier-2",
    )

    complete_response = client.post(
        f"/api/v1/leases/{lease_id}/complete",
        json={
            "request_id": "lease-complete-1",
            "node_id": "node_verifierworker0003",
            "workspace_id": verifier_workspace_id,
            "observed_run_id": "run-verifier-2",
            "observed_claim_id": "claim-source-1",
        },
    )
    assert complete_response.status_code == 400
    assert "verifier" in complete_response.json()["detail"]
