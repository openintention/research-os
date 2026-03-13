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
    assert "Hosted effort explorer is live" in html
    assert "1 command to join" in html
    assert "Snapshot evidence bundled" in html
    assert "For ML engineers, benchmark tinkerers, and agent-native builders" in html
    assert "OpenIntention gives small research loops a shared place to land." in html
    assert "Freshness model:" in html
    assert "See how it works" in html
    assert "What you get back" in html
    assert "A visible workspace" in html
    assert "A visible result" in html
    assert "A handoff" in html
    assert "Open deterministic join proof" in html
    assert "./styles.css?v=" in html
    assert "Pick your first effort and run one command" in html
    assert "The linked briefs below are generated snapshots from the last export." in html
    assert "Best first path" in html
    assert "Alternative path" in html
    assert "Start here if you want the easiest first contribution." in html
    assert "Use this path if you care more about performance work." in html
    assert "Copy this" in html
    assert "Copy command" in html
    assert "Run it yourself or paste the same one-liner into Claude or Codex." in html
    assert "This starts with" in html
    assert "Eval Sprint, the easiest first path." in html
    assert "What your first run leaves behind" in html
    assert "Bundled snapshot evidence" in html
    assert "A successful join should leave behind visible work" in html
    assert "A recent public-surface join" in html
    assert "Each successful join leaves behind a workspace" in html
    assert "Eval Sprint" in html
    assert "Inference Sprint" in html
    assert "4 workspaces" in html
    assert "2 workspaces" in html
    assert "For agents and technical users" in html
    assert "Technical appendix" in html
    assert "Use the live explorer for current hosted state" in html
    assert "https://github.com/example/openintention" in html
    assert "./evidence/join-with-ai.html" in html
    assert "./evidence/public-ingress-smoke.html" in html
    assert 'href="/efforts"' in html
    assert "curl -fsSL https://openintention.io/join | bash" in html
    assert "--profile inference-sprint" in html
    assert "data-copy-eval=" in html
    assert "data-copy-inference=" in html
    assert "Open the agent brief" in html
    assert "These counts come from generated effort briefs packaged with this build." in html
    assert "Both seeded efforts already have visible work" not in html
    assert "Already live now" not in html
    assert "What an effort is" not in html
    assert "What we are trying to prove" not in html
    assert "What we are inviting you into" not in html
    assert "What happens next" not in html
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
    assert "Repo brief" in evidence_html
    assert "../styles.css?v=" in evidence_html
