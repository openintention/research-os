from __future__ import annotations

from research_os.ledger.sqlite import SQLiteEventStore
from research_os.service import ResearchOSService
from scripts import seed_demo


def test_seed_demo_creates_canonical_eval_and_inference_efforts(tmp_path, monkeypatch):
    db_path = tmp_path / "seed.db"
    artifact_root = tmp_path / "artifacts"

    monkeypatch.setenv("RESEARCH_OS_DB_PATH", str(db_path))
    monkeypatch.setenv("RESEARCH_OS_ARTIFACT_ROOT", str(artifact_root))
    monkeypatch.setattr("sys.argv", ["seed_demo.py", "--reset"])

    seed_demo.main()

    service = ResearchOSService(SQLiteEventStore(str(db_path)))
    efforts = {effort.name: effort for effort in service.list_efforts()}

    assert set(efforts) == {
        "Eval Sprint: improve validation loss under fixed budget",
        "Inference Sprint: improve flash-path throughput on H100",
    }

    eval_effort = efforts["Eval Sprint: improve validation loss under fixed budget"]
    inference_effort = efforts["Inference Sprint: improve flash-path throughput on H100"]

    assert eval_effort.objective == "val_bpb"
    assert eval_effort.platform == "A100"
    assert eval_effort.tags["effort_type"] == "eval"

    assert inference_effort.objective == "tokens_per_second"
    assert inference_effort.platform == "H100"
    assert inference_effort.tags["effort_type"] == "inference"

    workspaces = service.list_workspaces()
    eval_workspaces = {workspace.name for workspace in workspaces if workspace.effort_id == eval_effort.effort_id}
    inference_workspaces = {
        workspace.name for workspace in workspaces if workspace.effort_id == inference_effort.effort_id
    }

    assert eval_workspaces == {
        "attention-sweep-a100",
        "optimizer-schedule-a100",
        "novel-arch-a100",
    }
    assert inference_workspaces == {"flash-path-h100"}
