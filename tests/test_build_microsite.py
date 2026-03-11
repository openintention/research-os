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
    assert "Turn small independent research loops into shared progress" in html
    assert "What you do here" in html
    assert "Fastest current join rehearsal" in html
    assert "What is real today" in html
    assert "Still true, still limited" in html
    assert "Join it with Claude, Codex, or your own workflow" in html
    assert "not a live peer-to-peer mesh or a finished open node network" in html
    assert "Full public ingress report" in html
    assert "Read the AI-agent onboarding brief" in html
    assert "Read the exact path" in html
    assert "What this page is for" in html
    assert "not a sign-up wall, a command center, or a profile product" in html
    assert "Shared hosted state is live" in html
    assert "external-harness compounding proof already exists in the repo" in html
    assert "https://github.com/example/openintention" in html
    assert "./evidence/join-with-ai.html" in html
    assert "./evidence/public-ingress-smoke.html" in html
    assert 'href="/efforts"' in html
    assert "What becomes visible when you participate" in html
    assert "Latest visible participation outcome" in html
    assert "Visible in Eval Sprint now" in html
    assert "Visible in Inference Sprint now" in html
    assert "git clone https://github.com/openintention/research-os.git" in html
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
