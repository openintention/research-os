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
