from __future__ import annotations

import pytest

from scripts.run_mlx_history_compounding_smoke import _build_imported_contribution_from_workspace
from scripts.run_mlx_history_compounding_smoke import _ensure_effort
from scripts.run_mlx_history_compounding_smoke import _find_existing_workspace
from scripts.run_mlx_history_compounding_smoke import _record_adoption
from research_os.domain.models import EventKind
from scripts.run_mlx_history_compounding_smoke import (
    CompoundingMlxHistoryResult,
    ImportedContribution,
    build_compounding_report,
)
from research_os.integrations.mlx_history import MlxHistoryResult


def test_build_compounding_report_highlights_adoption_and_next_step() -> None:
    report = build_compounding_report(
        CompoundingMlxHistoryResult(
            base_url="https://api.openintention.io",
            effort_id="effort-mlx",
            effort_name="MLX History Sprint: improve val_bpb on Apple Silicon",
            alpha=ImportedContribution(
                actor_id="mlx-alpha",
                workspace_id="ws-alpha",
                workspace_name="mlx-history-alpha",
                baseline_commit="383abb4",
                candidate_commit="4161af3",
                claim_id="claim-alpha",
                run_id="run-alpha",
                metric_value=2.533728,
                delta=-0.133272,
            ),
            beta=ImportedContribution(
                actor_id="mlx-beta",
                workspace_id="ws-beta",
                workspace_name="mlx-history-beta",
                baseline_commit="4161af3",
                candidate_commit="5efc7aa",
                claim_id="claim-beta",
                run_id="run-beta",
                metric_value=1.807902,
                delta=-0.725826,
            ),
            adoption_event_id="adopt-beta",
            workspace_ids=["ws-alpha", "ws-beta"],
            claim_ids=["claim-alpha", "claim-beta"],
            frontier_member_count=2,
            planner_action="reproduce_claim",
            planner_reason="The latest external-harness claim still needs independent reproduction.",
            planner_inputs={"claim_id": "claim-beta"},
            effort_overview_excerpt="# Effort",
        )
    )

    assert "MLX History Compounding Smoke Report" in report
    assert "mlx-beta` adopted `claim-alpha`" in report
    assert "Action: `reproduce_claim`" in report
    assert "claim-beta" in report
    assert "The next participant can continue" in report


def test_find_existing_workspace_matches_by_name_and_actor() -> None:
    workspaces = [
        {"workspace_id": "ws-1", "name": "mlx-history-alpha-4161af3", "actor_id": "mlx-alpha"},
        {"workspace_id": "ws-2", "name": "mlx-history-alpha-4161af3", "actor_id": "mlx-other"},
    ]

    workspace = _find_existing_workspace(
        workspaces,
        name="mlx-history-alpha-4161af3",
        actor_id="mlx-alpha",
    )

    assert workspace == workspaces[0]


def test_build_imported_contribution_from_workspace_reuses_existing_scope() -> None:
    contribution = _build_imported_contribution_from_workspace(
        {"workspace_id": "2785c9d9-7b37-4c06-9c8b-1759d9013a2b"},
        actor_id="mlx-alpha",
        workspace_name="mlx-history-alpha",
        baseline=MlxHistoryResult(
            commit="383abb4",
            val_bpb=2.667,
            memory_gb=26.9,
            status="keep",
            description="baseline",
        ),
        candidate=MlxHistoryResult(
            commit="4161af3",
            val_bpb=2.533728,
            memory_gb=26.9,
            status="keep",
            description="increase matrix LR to 0.04",
        ),
    )

    assert contribution.workspace_id == "2785c9d9-7b37-4c06-9c8b-1759d9013a2b"
    assert contribution.claim_id == "2785c9d9-claim-4161af3"
    assert contribution.run_id == "2785c9d9-run-4161af3"
    assert contribution.delta == pytest.approx(-0.133272)


def test_record_adoption_is_idempotent(monkeypatch) -> None:
    class FakeApi:
        base_url = "https://example.invalid"

        def __init__(self) -> None:
            self.appended_payloads: list[dict[str, object]] = []

        def append_event(self, payload: dict[str, object]) -> dict[str, object]:
            self.appended_payloads.append(payload)
            return payload

    def fake_get_json(url: str) -> list[dict[str, object]]:
        assert f"kind={EventKind.ADOPTION_RECORDED.value}" in url
        return [
            {
                "event_id": "existing-adoption",
                "payload": {"subject_id": "claim-alpha"},
            }
        ]

    monkeypatch.setattr(
        "scripts.run_mlx_history_compounding_smoke._get_json",
        fake_get_json,
    )
    api = FakeApi()
    event_id = _record_adoption(
        api,
        from_contribution=ImportedContribution(
            actor_id="mlx-alpha",
            workspace_id="ws-alpha",
            workspace_name="mlx-history-alpha",
            baseline_commit="383abb4",
            candidate_commit="4161af3",
            claim_id="claim-alpha",
            run_id="run-alpha",
            metric_value=2.533728,
            delta=-0.133272,
        ),
        to_contribution=ImportedContribution(
            actor_id="mlx-beta",
            workspace_id="ws-beta",
            workspace_name="mlx-history-beta",
            baseline_commit="4161af3",
            candidate_commit="5efc7aa",
            claim_id="claim-beta",
            run_id="run-beta",
            metric_value=1.807902,
            delta=-0.725826,
        ),
    )

    assert event_id == "existing-adoption"
    assert api.appended_payloads == []


def test_ensure_effort_prefers_current_series_member_over_historical_and_legacy() -> None:
    class FakeApi:
        def __init__(self) -> None:
            self.created_payloads: list[dict[str, object]] = []
            self.efforts = [
                {
                    "effort_id": "effort-legacy",
                    "name": "Autoresearch MLX Sprint: improve val_bpb on Apple Silicon",
                    "objective": "val_bpb",
                    "platform": "Apple-Silicon-MLX",
                    "budget_seconds": 300,
                    "summary": "Legacy effort",
                    "tags": {
                        "external_harness": "autoresearch-mlx",
                        "proof_status": "historical",
                    },
                    "successor_effort_id": "effort-current",
                    "updated_at": "2026-03-11T12:00:00Z",
                },
                {
                    "effort_id": "effort-old",
                    "name": "MLX History Sprint: improve val_bpb on Apple Silicon",
                    "objective": "val_bpb",
                    "platform": "Apple-Silicon-MLX",
                    "budget_seconds": 300,
                    "summary": "Old historical proof run",
                    "tags": {
                        "external_harness": "mlx-history",
                        "public_proof": "true",
                        "proof_series": "mlx-history-apple-silicon-300",
                        "proof_version": "1",
                        "proof_status": "historical",
                    },
                    "successor_effort_id": "effort-current",
                    "updated_at": "2026-03-11T13:00:00Z",
                },
                {
                    "effort_id": "effort-current",
                    "name": "MLX History Sprint: improve val_bpb on Apple Silicon (proof v2)",
                    "objective": "val_bpb",
                    "platform": "Apple-Silicon-MLX",
                    "budget_seconds": 300,
                    "summary": "Current proof run",
                    "tags": {
                        "external_harness": "mlx-history",
                        "public_proof": "true",
                        "proof_series": "mlx-history-apple-silicon-300",
                        "proof_version": "2",
                    },
                    "successor_effort_id": None,
                    "updated_at": "2026-03-11T14:00:00Z",
                },
            ]

        def list_efforts(self) -> list[dict[str, object]]:
            return self.efforts

        def create_effort(self, payload: dict[str, object]) -> dict[str, object]:
            self.created_payloads.append(payload)
            return {"effort_id": "effort-created"}

    api = FakeApi()
    effort = _ensure_effort(api, base_url="https://api.example.com")

    assert effort["effort_id"] == "effort-current"
    assert api.created_payloads == []


def test_ensure_effort_creates_first_mlx_history_proof_when_missing() -> None:
    class FakeApi:
        def __init__(self) -> None:
            self.created_payloads: list[dict[str, object]] = []
            self.efforts: list[dict[str, object]] = []

        def list_efforts(self) -> list[dict[str, object]]:
            return list(self.efforts)

        def create_effort(self, payload: dict[str, object]) -> dict[str, object]:
            self.created_payloads.append(payload)
            created = {
                "effort_id": "effort-created",
                "name": payload["name"],
                "objective": payload["objective"],
                "platform": payload["platform"],
                "budget_seconds": payload["budget_seconds"],
                "summary": payload["summary"],
                "tags": payload["tags"],
                "workspace_ids": [],
                "successor_effort_id": None,
                "updated_at": "2026-03-13T00:00:00Z",
            }
            self.efforts.append(created)
            return {"effort_id": "effort-created"}

    api = FakeApi()
    effort = _ensure_effort(api, base_url="https://api.example.com")

    assert effort["effort_id"] == "effort-created"
    assert api.created_payloads[0]["tags"]["external_harness"] == "mlx-history"
    assert api.created_payloads[0]["tags"]["proof_series"] == "mlx-history-apple-silicon-300"
    assert "run_overnight_autoresearch_worker.py" in api.created_payloads[0]["tags"]["join_command"]
