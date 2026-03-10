from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from apps.api.main import create_app
from clients.tiny_loop.experiment import (
    EVAL_SPRINT_PROFILE,
    INFERENCE_SPRINT_PROFILE,
    STANDALONE_PROFILE,
    run_tiny_loop_experiment,
)
from research_os.settings import Settings


@dataclass(slots=True)
class ClientApiHarness:
    client: TestClient

    def list_efforts(self) -> list[dict[str, Any]]:
        response = self.client.get("/api/v1/efforts")
        assert response.status_code == 200
        return response.json()

    def create_workspace(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.post("/api/v1/workspaces", json=payload)
        assert response.status_code == 201
        return response.json()

    def append_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.post("/api/v1/events", json=payload)
        assert response.status_code == 201
        return response.json()

    def recommend_next(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.post("/api/v1/planner/recommend", json=payload)
        assert response.status_code == 200
        return response.json()

    def get_workspace_discussion(self, workspace_id: str) -> dict[str, Any]:
        response = self.client.get(f"/api/v1/publications/workspaces/{workspace_id}/discussion")
        assert response.status_code == 200
        return response.json()

    def get_snapshot_pull_request(self, workspace_id: str, snapshot_id: str) -> dict[str, Any]:
        response = self.client.get(
            f"/api/v1/publications/workspaces/{workspace_id}/pull-requests/{snapshot_id}"
        )
        assert response.status_code == 200
        return response.json()


def test_tiny_loop_client_runs_end_to_end_against_api(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "client-loop.db"),
        artifact_root=str(tmp_path / "service-artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    result = run_tiny_loop_experiment(
        ClientApiHarness(client),
        artifact_root=Path(tmp_path / "client-artifacts"),
        profile=STANDALONE_PROFILE,
    )

    assert result.planner_action == "reproduce_claim"
    assert result.claim_id == "claim-quadratic-001"
    assert "Discussion: tiny-loop-val-loss" in result.discussion_markdown
    assert "claim-quadratic-001" in result.discussion_markdown
    assert "PR: snap-quadratic-candidate" in result.pull_request_markdown
    assert "run-candidate-repro-001" in result.pull_request_markdown

    workspace_events = client.get(f"/api/v1/events?workspace_id={result.workspace_id}&limit=50")
    assert workspace_events.status_code == 200
    kinds = [event["kind"] for event in workspace_events.json()]
    assert "workspace.started" in kinds
    assert "snapshot.published" in kinds
    assert "run.completed" in kinds
    assert "claim.asserted" in kinds
    assert "claim.reproduced" in kinds


def test_tiny_loop_client_can_target_seeded_eval_effort(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "client-loop-seeded.db"),
        artifact_root=str(tmp_path / "service-artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    effort_response = client.post(
        "/api/v1/efforts",
        json={
            "name": EVAL_SPRINT_PROFILE.effort_name,
            "objective": EVAL_SPRINT_PROFILE.objective,
            "platform": EVAL_SPRINT_PROFILE.platform,
            "budget_seconds": EVAL_SPRINT_PROFILE.budget_seconds,
            "summary": "Seeded eval effort for bounded validation-loss improvement loops.",
            "tags": {"effort_type": "eval", "seeded": "true"},
        },
    )
    assert effort_response.status_code == 201

    result = run_tiny_loop_experiment(
        ClientApiHarness(client),
        artifact_root=Path(tmp_path / "client-artifacts"),
        profile=EVAL_SPRINT_PROFILE,
    )

    assert result.effort_name == EVAL_SPRINT_PROFILE.effort_name
    workspace_response = client.get(f"/api/v1/workspaces/{result.workspace_id}")
    assert workspace_response.status_code == 200
    workspace = workspace_response.json()
    assert workspace["effort_id"] == result.effort_id
    assert workspace["objective"] == EVAL_SPRINT_PROFILE.objective
    assert workspace["platform"] == EVAL_SPRINT_PROFILE.platform
    assert workspace["budget_seconds"] == EVAL_SPRINT_PROFILE.budget_seconds


def test_tiny_loop_client_can_target_seeded_inference_effort(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "client-loop-inference.db"),
        artifact_root=str(tmp_path / "service-artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    effort_response = client.post(
        "/api/v1/efforts",
        json={
            "name": INFERENCE_SPRINT_PROFILE.effort_name,
            "objective": INFERENCE_SPRINT_PROFILE.objective,
            "platform": INFERENCE_SPRINT_PROFILE.platform,
            "budget_seconds": INFERENCE_SPRINT_PROFILE.budget_seconds,
            "summary": "Seeded inference effort for bounded throughput-improvement loops.",
            "tags": {"effort_type": "inference", "seeded": "true"},
        },
    )
    assert effort_response.status_code == 201

    result = run_tiny_loop_experiment(
        ClientApiHarness(client),
        artifact_root=Path(tmp_path / "client-artifacts"),
        profile=INFERENCE_SPRINT_PROFILE,
    )

    assert result.effort_name == INFERENCE_SPRINT_PROFILE.effort_name
    workspace_response = client.get(f"/api/v1/workspaces/{result.workspace_id}")
    assert workspace_response.status_code == 200
    workspace = workspace_response.json()
    assert workspace["effort_id"] == result.effort_id
    assert workspace["objective"] == INFERENCE_SPRINT_PROFILE.objective
    assert workspace["platform"] == INFERENCE_SPRINT_PROFILE.platform
    assert workspace["budget_seconds"] == INFERENCE_SPRINT_PROFILE.budget_seconds

    workspace_events = client.get(f"/api/v1/events?workspace_id={result.workspace_id}&kind=run.completed&limit=20")
    assert workspace_events.status_code == 200
    directions = {event["payload"]["direction"] for event in workspace_events.json()}
    assert directions == {"max"}
