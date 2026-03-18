from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import create_app
from research_os.settings import Settings


def test_create_list_and_join_seeded_effort(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "efforts.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    effort_response = client.post(
        "/api/v1/efforts",
        json={
            "name": "tiny quadratic regression effort",
            "objective": "val_loss",
            "platform": "cpu",
            "budget_seconds": 5,
            "summary": "Seeded effort for cheap nonlinear-regression loops.",
            "tags": {"seeded": "true", "domain": "tiny-regression"},
        },
    )
    assert effort_response.status_code == 201
    effort_id = effort_response.json()["effort_id"]

    workspace_response = client.post(
        "/api/v1/workspaces",
        json={
            "name": "participant-loop",
            "objective": "val_loss",
            "platform": "cpu",
            "budget_seconds": 5,
            "effort_id": effort_id,
        },
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["workspace_id"]

    efforts_response = client.get("/api/v1/efforts")
    assert efforts_response.status_code == 200
    efforts = efforts_response.json()
    assert len(efforts) == 1
    assert efforts[0]["effort_id"] == effort_id
    assert efforts[0]["workspace_ids"] == [workspace_id]

    workspaces_response = client.get("/api/v1/workspaces")
    assert workspaces_response.status_code == 200
    assert workspaces_response.json()[0]["effort_id"] == effort_id


def test_list_workspaces_can_filter_by_effort_id(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "effort-filter.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    first_effort_id = client.post(
        "/api/v1/efforts",
        json={"name": "effort-one", "objective": "val_loss", "platform": "cpu", "budget_seconds": 5},
    ).json()["effort_id"]
    second_effort_id = client.post(
        "/api/v1/efforts",
        json={"name": "effort-two", "objective": "val_loss", "platform": "cpu", "budget_seconds": 5},
    ).json()["effort_id"]

    first_workspace_id = client.post(
        "/api/v1/workspaces",
        json={
            "name": "participant-one",
            "objective": "val_loss",
            "platform": "cpu",
            "budget_seconds": 5,
            "effort_id": first_effort_id,
        },
    ).json()["workspace_id"]
    client.post(
        "/api/v1/workspaces",
        json={
            "name": "participant-two",
            "objective": "val_loss",
            "platform": "cpu",
            "budget_seconds": 5,
            "effort_id": second_effort_id,
        },
    )

    filtered_response = client.get(f"/api/v1/workspaces?effort_id={first_effort_id}")
    assert filtered_response.status_code == 200
    filtered_workspaces = filtered_response.json()
    assert len(filtered_workspaces) == 1
    assert filtered_workspaces[0]["workspace_id"] == first_workspace_id
    assert filtered_workspaces[0]["effort_id"] == first_effort_id


def test_effort_rollover_marks_source_historical_and_links_successor(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "effort-rollover.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    source_effort_id = client.post(
        "/api/v1/efforts",
        json={
            "name": "Eval Sprint: improve validation loss under fixed budget",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "tags": {
                "effort_type": "eval",
                "public_proof": "true",
                "proof_series": "eval-a100-300",
                "proof_version": "1",
            },
        },
    ).json()["effort_id"]
    successor_effort_id = client.post(
        "/api/v1/efforts",
        json={
            "name": "Eval Sprint: improve validation loss under fixed budget (proof v2)",
            "objective": "val_bpb",
            "platform": "A100",
            "budget_seconds": 300,
            "tags": {
                "effort_type": "eval",
                "public_proof": "true",
                "proof_series": "eval-a100-300",
                "proof_version": "2",
            },
        },
    ).json()["effort_id"]

    response = client.post(
        "/api/v1/events",
        json={
            "kind": "effort.rolled_over",
            "aggregate_id": source_effort_id,
            "aggregate_kind": "effort",
            "payload": {
                "effort_id": source_effort_id,
                "successor_effort_id": successor_effort_id,
            },
            "tags": {
                "public_proof": "true",
                "proof_series": "eval-a100-300",
                "proof_version": "1",
                "proof_status": "historical",
            },
        },
    )
    assert response.status_code == 201

    efforts = {effort["effort_id"]: effort for effort in client.get("/api/v1/efforts").json()}
    assert efforts[source_effort_id]["successor_effort_id"] == successor_effort_id
    assert efforts[source_effort_id]["tags"]["proof_status"] == "historical"
    assert efforts[successor_effort_id]["successor_effort_id"] is None


def test_publish_goal_creates_effort_with_goal_contract(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "publish-goal.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    response = client.post(
        "/api/v1/goals/publish",
        json={
            "title": "Improve validation loss on cpu",
            "summary": "Create a public goal with enough contract detail for the next contributor to join.",
            "objective": "val_loss",
            "metric_name": "validation loss",
            "direction": "min",
            "platform": "cpu",
            "budget_seconds": 5,
            "constraints": ["Keep runtime under five seconds."],
            "evidence_requirement": "Leave behind a run and a claim or reproduction.",
            "stop_condition": "Stop after the first visible reproduction lands.",
            "actor_id": "goal-author",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["goal_path"] == f"/efforts/{payload['effort_id']}"
    effort = client.get(f"/api/v1/efforts/{payload['effort_id']}")
    assert effort.status_code == 200
    effort_payload = effort.json()
    assert effort_payload["metric_name"] == "validation loss"
    assert effort_payload["direction"] == "min"
    assert effort_payload["constraints"] == ["Keep runtime under five seconds."]
    assert effort_payload["evidence_requirement"] == "Leave behind a run and a claim or reproduction."
    assert effort_payload["stop_condition"] == "Stop after the first visible reproduction lands."
    assert effort_payload["author_id"] == "goal-author"
    assert effort_payload["tags"]["goal_origin"] == "user-published"
    assert effort_payload["tags"]["join_mode"] == "tiny-loop-proxy"


def test_publish_goal_requires_minimum_contract(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "publish-goal-invalid.db"),
        artifact_root=str(tmp_path / "artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    response = client.post(
        "/api/v1/goals/publish",
        json={
            "title": "short",
            "summary": "too short",
            "objective": "val_loss",
            "metric_name": "validation loss",
            "direction": "min",
            "platform": "cpu",
            "budget_seconds": 5,
            "constraints": [],
            "evidence_requirement": "none",
            "stop_condition": "none",
            "actor_id": "goal-author",
        },
    )

    assert response.status_code == 400
    assert "published goals require at least one constraint" in response.json()["detail"]
