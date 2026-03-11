from __future__ import annotations

from scripts.build_microsite import MicrositeConfig, MicrositeEvidence, build_microsite


def test_build_microsite_generates_index_and_copies_evidence(tmp_path):
    repo_root = tmp_path
    smoke_report = repo_root / "smoke.md"
    eval_brief = repo_root / "eval.md"
    inference_brief = repo_root / "inference.md"
    join_with_ai = repo_root / "join-with-ai.md"
    smoke_report.write_text(
        "# First User Smoke Report\n\n## Participation Outcome\n- Joined (Eval): workspace-1\n- Participated (Eval): claim-1\n",
        encoding="utf-8",
    )
    eval_brief.write_text(
        "# Effort: Eval Sprint\n\n## Objective\n- Objective: `val_bpb`\n- Platform: `A100`\n- Budget seconds: `300`\n- Summary: Seeded eval effort.\n\n## Current State\n- Attached workspaces: 4\n- Claims in effort scope: 3\n- Frontier members: 5\n\n## Active Workspaces\n- `eval-workspace`\n",
        encoding="utf-8",
    )
    inference_brief.write_text(
        "# Effort: Inference Sprint\n\n## Objective\n- Objective: `tokens_per_second`\n- Platform: `H100`\n- Budget seconds: `300`\n- Summary: Seeded inference effort.\n\n## Current State\n- Attached workspaces: 2\n- Claims in effort scope: 1\n- Frontier members: 3\n\n## Active Workspaces\n- `inference-workspace`\n",
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
    assert "2 live seeded efforts" in html
    assert "1 command to join" in html
    assert "Visible effort pages" in html
    assert "For ML engineers, benchmark tinkerers, and agent-native builders" in html
    assert "Live today on openintention.io" in html
    assert "See how it works" in html
    assert "What “live effort” means here" in html
    assert "One shared objective" in html
    assert "Visible contributions" in html
    assert "Continuable work" in html
    assert "Read the full join report" in html
    assert "./styles.css?v=" in html
    assert "What happens when you join" in html
    assert "The first run should feel simple" in html
    assert "1. Pick a starting effort" in html
    assert "2. Run one command" in html
    assert "3. Your work appears" in html
    assert "Use this command yourself or hand it directly to Claude or Codex." in html
    assert "What an effort is" in html
    assert "An effort is one shared research objective" in html
    assert "The easiest first path." in html
    assert "You do not need an H100 to try the current starter flow." in html
    assert "Choose your first effort" in html
    assert "Pick the path that matches what you want to contribute first." in html
    assert "What you get after one run" in html
    assert "Already live now" in html
    assert "A visible result on a live effort page" in html
    assert "Shared effort pages are live on" in html
    assert "Eval Sprint" in html
    assert "Inference Sprint" in html
    assert "4 workspaces" in html
    assert "2 workspaces" in html
    assert "Why this matters" in html
    assert "For agents and technical users" in html
    assert "Most agent work still disappears into local branches" in html
    assert "The big picture is not just better logging." in html
    assert "The goal is cumulative progress, not one more isolated run." in html
    assert "What success looks like" in html
    assert "People join" in html
    assert "10 participants" in html
    assert "Work compounds" in html
    assert "100 follow-on steps" in html
    assert "Builders help build it" in html
    assert "Outside developers" in html
    assert "These are proof goals, not vanity metrics." in html
    assert "What we are inviting you into" in html
    assert "Join one live effort, leave behind work someone else can continue" in html
    assert "What happens next" in html
    assert "https://github.com/example/openintention" in html
    assert "./evidence/join-with-ai.html" in html
    assert "./evidence/public-ingress-smoke.html" in html
    assert 'href="/efforts"' in html
    assert "git clone https://github.com/openintention/research-os.git" in html
    assert "python3 scripts/join_openintention.py" in html
    assert "python3 scripts/join_openintention.py --profile inference-sprint" in html
    assert "Check the live effort page, inspect the report your run produced" in html
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
    assert "../styles.css?v=" in evidence_html
