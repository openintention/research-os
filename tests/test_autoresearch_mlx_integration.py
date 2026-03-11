from __future__ import annotations

from research_os.integrations.autoresearch_mlx import commit_url, load_results_tsv


def test_load_results_tsv_parses_autoresearch_history(tmp_path) -> None:
    results_path = tmp_path / "results.tsv"
    results_path.write_text(
        "\n".join(
            [
                "commit\tval_bpb\tmemory_gb\tstatus\tdescription",
                "383abb4\t2.667000\t26.9\tkeep\tbaseline",
                "4161af3\t2.533728\t26.9\tkeep\tincrease matrix LR to 0.04",
            ]
        ),
        encoding="utf-8",
    )

    results = load_results_tsv(results_path)

    assert [result.commit for result in results] == ["383abb4", "4161af3"]
    assert results[1].val_bpb == 2.533728
    assert results[1].description == "increase matrix LR to 0.04"


def test_commit_url_normalizes_git_suffix() -> None:
    assert (
        commit_url("https://github.com/trevin-creator/autoresearch-mlx.git", "4161af3")
        == "https://github.com/trevin-creator/autoresearch-mlx/commit/4161af3"
    )
