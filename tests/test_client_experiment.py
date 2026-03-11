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

    def list_workspaces(self, effort_id: str | None = None) -> list[dict[str, Any]]:
        path = "/api/v1/workspaces"
        if effort_id:
            path = f"{path}?effort_id={effort_id}"
        response = self.client.get(path)
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

    def get_effort_overview(self, effort_id: str) -> dict[str, Any]:
        response = self.client.get(f"/api/v1/publications/efforts/{effort_id}")
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
    assert result.claim_id.endswith("-claim-quadratic-001")
    assert "Discussion: tiny-loop-val-loss" in result.discussion_markdown
    assert result.claim_id in result.discussion_markdown
    assert f"PR: {result.candidate_snapshot_id}" in result.pull_request_markdown
    assert result.reproduction_run_id in result.pull_request_markdown

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
    assert workspace["actor_id"] == result.actor_id
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
    assert workspace["actor_id"] == result.actor_id
    assert workspace["objective"] == INFERENCE_SPRINT_PROFILE.objective
    assert workspace["platform"] == INFERENCE_SPRINT_PROFILE.platform
    assert workspace["budget_seconds"] == INFERENCE_SPRINT_PROFILE.budget_seconds

    workspace_events = client.get(f"/api/v1/events?workspace_id={result.workspace_id}&kind=run.completed&limit=20")
    assert workspace_events.status_code == 200
    directions = {event["payload"]["direction"] for event in workspace_events.json()}
    assert directions == {"max"}


def test_tiny_loop_client_can_land_two_distinct_participants_into_same_seeded_effort(tmp_path):
    settings = Settings(
        db_path=str(tmp_path / "client-loop-shared.db"),
        artifact_root=str(tmp_path / "service-artifacts"),
    )
    app = create_app(settings)
    client = TestClient(app)

    effort_id = client.post(
        "/api/v1/efforts",
        json={
            "name": EVAL_SPRINT_PROFILE.effort_name,
            "objective": EVAL_SPRINT_PROFILE.objective,
            "platform": EVAL_SPRINT_PROFILE.platform,
            "budget_seconds": EVAL_SPRINT_PROFILE.budget_seconds,
            "summary": "Seeded eval effort for shared participation.",
            "tags": {"effort_type": "eval", "seeded": "true"},
        },
    ).json()["effort_id"]

    first = run_tiny_loop_experiment(
        ClientApiHarness(client),
        artifact_root=Path(tmp_path / "client-artifacts" / "alpha"),
        profile=EVAL_SPRINT_PROFILE,
        actor_id="participant-alpha",
        workspace_suffix="alpha",
    )
    second = run_tiny_loop_experiment(
        ClientApiHarness(client),
        artifact_root=Path(tmp_path / "client-artifacts" / "beta"),
        profile=EVAL_SPRINT_PROFILE,
        actor_id="participant-beta",
        workspace_suffix="beta",
    )

    assert first.workspace_id != second.workspace_id
    assert first.claim_id != second.claim_id
    assert first.candidate_snapshot_id != second.candidate_snapshot_id

    workspaces = client.get(f"/api/v1/workspaces?effort_id={effort_id}").json()
    assert {workspace["actor_id"] for workspace in workspaces} >= {"participant-alpha", "participant-beta"}
    assert {workspace["workspace_id"] for workspace in workspaces} >= {first.workspace_id, second.workspace_id}

    claims = client.get(
        f"/api/v1/claims?objective={EVAL_SPRINT_PROFILE.objective}&platform={EVAL_SPRINT_PROFILE.platform}"
    ).json()
    claim_ids = {claim["claim_id"] for claim in claims}
    assert {first.claim_id, second.claim_id}.issubset(claim_ids)
