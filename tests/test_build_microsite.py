from __future__ import annotations

from scripts.build_microsite import MicrositeConfig, MicrositeEvidence, build_microsite


def test_build_microsite_generates_index_and_copies_evidence(tmp_path):
    repo_root = tmp_path
    smoke_report = repo_root / "smoke.md"
    eval_brief = repo_root / "eval.md"
    inference_brief = repo_root / "inference.md"
    join_with_ai = repo_root / "join-with-ai.md"
    smoke_report.write_text("# First User Smoke Report\nline\n", encoding="utf-8")
    eval_brief.write_text("# Effort: Eval Sprint\nline\n", encoding="utf-8")
    inference_brief.write_text("# Effort: Inference Sprint\nline\n", encoding="utf-8")
    join_with_ai.write_text("# Join With an AI Agent\nline\n", encoding="utf-8")

    output_dir = repo_root / "dist"
    index_path = build_microsite(
        repo_root=repo_root,
        output_dir=output_dir,
        evidence=MicrositeEvidence(
            smoke_report=smoke_report,
            eval_brief=eval_brief,
            inference_brief=inference_brief,
            join_with_ai=join_with_ai,
        ),
        config=MicrositeConfig(repo_url="https://github.com/example/openintention"),
    )

    html = index_path.read_text(encoding="utf-8")
    assert "OpenIntention" in html
    assert "Machine-native coordination for shared research efforts." in html
    assert "not presented as affiliated" in html
    assert "Claude, Codex, or another agent" in html
    assert "What OpenIntention is" in html
    assert "What OpenIntention is not" in html
    assert "Not a local agent IDE or tmux replacement." in html
    assert "Not a live peer-to-peer mesh today." in html
    assert "Full smoke report" in html
    assert "Read the AI-agent onboarding brief" in html
    assert "Inspect this yourself" in html
    assert "There is no sign-up flow yet." in html
    assert "not a local command-center or agent pane manager" in html
    assert "https://github.com/example/openintention" in html
    assert (output_dir / "styles.css").exists()
    assert (output_dir / "assets" / "favicon.svg").exists()
    assert (output_dir / "evidence" / "first-user-smoke.md").read_text(encoding="utf-8").startswith(
        "# First User Smoke Report"
    )
    assert (output_dir / "evidence" / "join-with-ai.md").read_text(encoding="utf-8").startswith(
        "# Join With an AI Agent"
    )
