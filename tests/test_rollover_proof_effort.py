from __future__ import annotations

from scripts.rollover_proof_effort import build_rollover_report
from scripts.rollover_proof_effort import rollover_proof_effort


def test_rollover_proof_effort_creates_successor_and_historical_event() -> None:
    class FakeApi:
        def __init__(self) -> None:
            self.base_url = "https://api.openintention.io"
            self.created_payloads: list[dict[str, object]] = []
            self.appended_payloads: list[dict[str, object]] = []
            self.efforts = [
                {
                    "effort_id": "effort-v1",
                    "name": "Eval Sprint: improve validation loss under fixed budget",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "budget_seconds": 300,
                    "summary": "Eval proof",
                    "tags": {
                        "effort_type": "eval",
                        "public_proof": "true",
                        "proof_series": "eval-a100-300",
                        "proof_version": "1",
                    },
                    "successor_effort_id": None,
                    "updated_at": "2026-03-11T16:00:00Z",
                }
            ]

        def list_efforts(self) -> list[dict[str, object]]:
            return self.efforts

        def create_effort(self, payload: dict[str, object]) -> dict[str, object]:
            self.created_payloads.append(payload)
            return {"effort_id": "effort-v2"}

        def append_event(self, payload: dict[str, object]) -> dict[str, object]:
            self.appended_payloads.append(payload)
            return payload

    fake_api = FakeApi()

    import scripts.rollover_proof_effort as module

    module.HttpResearchOSApi = lambda base_url: fake_api  # type: ignore[assignment]
    result = rollover_proof_effort(
        base_url="https://api.openintention.io",
        effort_id="effort-v1",
        actor_id="operator",
        reason="clear a fresh proof window",
    )

    assert result.successor_effort_id == "effort-v2"
    assert result.successor_version == 2
    assert fake_api.created_payloads[0]["name"].endswith("(proof v2)")
    assert fake_api.created_payloads[0]["tags"]["proof_version"] == "2"
    assert fake_api.appended_payloads[0]["kind"] == "effort.rolled_over"
    assert fake_api.appended_payloads[0]["tags"]["proof_status"] == "historical"


def test_build_rollover_report_mentions_successor_and_series() -> None:
    report = build_rollover_report(
        result=type(
            "Result",
            (),
            {
                "source_effort_id": "effort-v1",
                "source_name": "Eval Sprint",
                "successor_effort_id": "effort-v2",
                "successor_name": "Eval Sprint (proof v2)",
                "series": "eval-a100-300",
                "source_version": 1,
                "successor_version": 2,
            },
        )()
    )

    assert "Proof Effort Rollover Report" in report
    assert "effort-v2" in report
    assert "eval-a100-300" in report


def test_rollover_proof_effort_allows_successor_metadata_overrides() -> None:
    class FakeApi:
        def __init__(self) -> None:
            self.created_payloads: list[dict[str, object]] = []
            self.appended_payloads: list[dict[str, object]] = []
            self.efforts = [
                {
                    "effort_id": "effort-legacy",
                    "name": "Autoresearch MLX Sprint: improve val_bpb on Apple Silicon",
                    "objective": "val_bpb",
                    "platform": "Apple-Silicon-MLX",
                    "budget_seconds": 300,
                    "summary": "Legacy external harness effort.",
                    "tags": {
                        "effort_type": "autoresearch_mlx",
                        "external_harness": "autoresearch-mlx",
                        "join_command": "python3 scripts/run_autoresearch_mlx_compounding_smoke.py",
                    },
                    "successor_effort_id": None,
                    "updated_at": "2026-03-11T16:00:00Z",
                }
            ]

        def list_efforts(self) -> list[dict[str, object]]:
            return self.efforts

        def create_effort(self, payload: dict[str, object]) -> dict[str, object]:
            self.created_payloads.append(payload)
            return {"effort_id": "effort-current"}

        def append_event(self, payload: dict[str, object]) -> dict[str, object]:
            self.appended_payloads.append(payload)
            return payload

    fake_api = FakeApi()

    import scripts.rollover_proof_effort as module

    module.HttpResearchOSApi = lambda base_url: fake_api  # type: ignore[assignment]
    rollover_proof_effort(
        base_url="https://api.openintention.io",
        effort_id="effort-legacy",
        actor_id="operator",
        successor_name="MLX History Sprint: improve val_bpb on Apple Silicon (proof v2)",
        successor_summary="Current external harness effort.",
        proof_series="mlx-history-apple-silicon-300",
        successor_tags={
            "effort_type": "mlx_history",
            "external_harness": "mlx-history",
            "join_brief_path": "README.md#real-overnight-autoresearch-worker",
        },
        drop_successor_tags={"join_command"},
    )

    created = fake_api.created_payloads[0]
    assert created["name"] == "MLX History Sprint: improve val_bpb on Apple Silicon (proof v2)"
    assert created["summary"] == "Current external harness effort."
    assert created["tags"]["effort_type"] == "mlx_history"
    assert created["tags"]["external_harness"] == "mlx-history"
    assert created["tags"]["join_brief_path"] == "README.md#real-overnight-autoresearch-worker"
    assert "join_command" not in created["tags"]
    assert created["tags"]["proof_series"] == "mlx-history-apple-silicon-300"
    assert created["tags"]["proof_version"] == "2"
    assert fake_api.appended_payloads[0]["tags"]["proof_series"] == "mlx-history-apple-silicon-300"
    assert fake_api.appended_payloads[0]["tags"]["proof_status"] == "historical"
