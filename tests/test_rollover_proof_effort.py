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
