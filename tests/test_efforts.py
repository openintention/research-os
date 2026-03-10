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
