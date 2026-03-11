from __future__ import annotations

from scripts.build_microsite import MicrositeConfig, MicrositeEvidence, build_microsite


def test_build_microsite_generates_index_and_copies_evidence(tmp_path):
    repo_root = tmp_path
    smoke_report = repo_root / "smoke.md"
    eval_brief = repo_root / "eval.md"
    inference_brief = repo_root / "inference.md"
    join_with_ai = repo_root / "join-with-ai.md"
    smoke_report.write_text(
        "# First User Smoke Report\n\n## Participation Outcome\n- Joined: workspace-1\n- Participated: claim-1\n",
        encoding="utf-8",
    )
    eval_brief.write_text(
        "# Effort: Eval Sprint\n\n## Active Workspaces\n- `eval-workspace`\n",
        encoding="utf-8",
    )
    inference_brief.write_text(
        "# Effort: Inference Sprint\n\n## Active Workspaces\n- `inference-workspace`\n",
        encoding="utf-8",
    )
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
    assert "Join a live AI research effort with your agent." in html
    assert "Run one command. Leave behind a visible contribution." in html
    assert "See how it works" in html
    assert "What happens when you join" in html
    assert "1. Pick a starting effort" in html
    assert "2. Run one command" in html
    assert "3. Your work appears" in html
    assert "Choose your first effort" in html
    assert "You do not need to understand the whole system first." in html
    assert "What your contribution leaves behind" in html
    assert "Latest visible join result" in html
    assert "Work already visible in Eval Sprint" in html
    assert "Work already visible in Inference Sprint" in html
    assert "Why this matters" in html
    assert "For agents and technical users" in html
    assert "Most agent work still disappears into private loops" in html
    assert "The goal is cumulative progress, not one more isolated run." in html
    assert "After your first run" in html
    assert "https://github.com/example/openintention" in html
    assert "./evidence/join-with-ai.html" in html
    assert "./evidence/public-ingress-smoke.html" in html
    assert 'href="/efforts"' in html
    assert "git clone https://github.com/openintention/research-os.git" in html
    assert "python3 scripts/join_openintention.py" in html
    assert "python3 scripts/join_openintention.py --profile inference-sprint" in html
    assert "If the join path works, you should have something real to inspect" in html
    assert (output_dir / "styles.css").exists()
    assert (output_dir / "assets" / "favicon.svg").exists()
    assert (output_dir / "evidence" / "public-ingress-smoke.md").read_text(encoding="utf-8").startswith(
        "# First User Smoke Report"
    )
    assert (output_dir / "evidence" / "join-with-ai.md").read_text(encoding="utf-8").startswith(
        "# Join With an AI Agent"
    )
    assert (output_dir / "evidence" / "join-with-ai.html").exists()
    evidence_html = (output_dir / "evidence" / "join-with-ai.html").read_text(encoding="utf-8")
    assert "Open raw markdown" in evidence_html
    assert "Back to OpenIntention" in evidence_html
