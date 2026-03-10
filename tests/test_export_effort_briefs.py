from __future__ import annotations

from scripts import export_effort_briefs, seed_demo


def test_export_effort_briefs_writes_seeded_effort_markdown(tmp_path, monkeypatch):
    db_path = tmp_path / "seed.db"
    artifact_root = tmp_path / "artifacts"
    output_dir = tmp_path / "briefs"

    monkeypatch.setenv("RESEARCH_OS_DB_PATH", str(db_path))
    monkeypatch.setenv("RESEARCH_OS_ARTIFACT_ROOT", str(artifact_root))
    monkeypatch.setattr("sys.argv", ["seed_demo.py", "--reset"])
    seed_demo.main()

    written_paths = export_effort_briefs.export_effort_briefs(
        db_path=str(db_path),
        output_dir=str(output_dir),
    )

    names = {path.name for path in written_paths}
    assert names == {
        "eval-sprint-improve-validation-loss-under-fixed-budget.md",
        "inference-sprint-improve-flash-path-throughput-on-h100.md",
    }

    eval_body = (output_dir / "eval-sprint-improve-validation-loss-under-fixed-budget.md").read_text(
        encoding="utf-8"
    )
    inference_body = (
        output_dir / "inference-sprint-improve-flash-path-throughput-on-h100.md"
    ).read_text(encoding="utf-8")

    assert "Effort: Eval Sprint: improve validation loss under fixed budget" in eval_body
    assert "python -m clients.tiny_loop.run" in eval_body
    assert "Effort: Inference Sprint: improve flash-path throughput on H100" in inference_body
    assert "python -m clients.tiny_loop.run --profile inference-sprint" in inference_body
