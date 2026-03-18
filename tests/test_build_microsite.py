from __future__ import annotations

from scripts.build_microsite import MicrositeConfig, MicrositeEvidence, build_microsite


def test_build_microsite_generates_index_and_copies_evidence(tmp_path):
    repo_root = tmp_path
    smoke_report = repo_root / "smoke.md"
    eval_brief = repo_root / "eval.md"
    inference_brief = repo_root / "inference.md"
    join_with_ai = repo_root / "join-with-ai.md"
    repeated_participation = repo_root / "repeated-external-participation.md"
    smoke_report.write_text(
        "# First User Smoke Report\n\n## Participation Outcome\n- Joined (Eval): workspace-1\n- Participated (Eval): claim-1\n",
        encoding="utf-8",
    )
    eval_brief.write_text(
        "# Effort: Eval Sprint\n\n## Objective\n- Objective: `val_bpb`\n- Platform: `A100`\n- Budget seconds: `300`\n- Summary: Seeded eval effort.\n\n## Proof Context\n- Best current result: `val_bpb` = `0.447392` from `participant-alpha` with `1` claim signal.\n- Latest claim signal: `participant-alpha` left a `supported` claim: Quadratic features improved the seeded eval objective.\n- Latest visible handoff: Left behind 3 runs, 1 claim, and 1 reproduction that the next participant can inspect and continue.\n\n## Current State\n- Attached workspaces: 4\n- Claims in effort scope: 3\n- Frontier members: 5\n- Updated at: `2026-03-17T11:00:00Z`\n\n## Active Workspaces\n- `eval-workspace` actor=participant-alpha, role=contributor, window=current, path=proxy, runs=3, claims=1, reproductions=1, updated=2026-03-17T11:00:00Z\n",
        encoding="utf-8",
    )
    inference_brief.write_text(
        "# Effort: Inference Sprint\n\n## Objective\n- Objective: `tokens_per_second`\n- Platform: `H100`\n- Budget seconds: `300`\n- Summary: Seeded inference effort.\n\n## Proof Context\n- Best current result: `tokens_per_second` = `1284.0` from `seed` with `0` claim signals.\n- Latest claim signal: `participant-beta` left a `supported` claim: Candidate path improved the seeded inference objective.\n- Latest visible handoff: Left behind 3 runs, 1 claim, and 1 reproduction that the next participant can inspect and continue.\n\n## Current State\n- Attached workspaces: 2\n- Claims in effort scope: 1\n- Frontier members: 3\n- Updated at: `2026-03-17T11:00:00Z`\n\n## Active Workspaces\n- `inference-workspace` actor=participant-beta, role=contributor, window=current, path=proxy, runs=3, claims=1, reproductions=1, updated=2026-03-17T11:00:00Z\n",
        encoding="utf-8",
    )
    join_with_ai.write_text("# Join With an AI Agent\nline\n", encoding="utf-8")
    repeated_participation.write_text("# Repeated External Participation Proof\n\nline\n", encoding="utf-8")

    output_dir = repo_root / "dist"
    index_path = build_microsite(
        repo_root=repo_root,
        output_dir=output_dir,
        evidence=MicrositeEvidence(
            smoke_report=smoke_report,
            eval_brief=eval_brief,
            inference_brief=inference_brief,
            join_with_ai=join_with_ai,
            repeated_participation_report=repeated_participation,
        ),
        config=MicrositeConfig(repo_url="https://github.com/example/openintention"),
    )

    html = index_path.read_text(encoding="utf-8")
    assert "OpenIntention" in html
    assert "Turn an ML goal into shared progress for humans and agents." in html
    assert "Join Eval in 1 command" in html
    assert "Your result shows up live" in html
    assert "Most ML experiments disappear into local runs, branches, and chat logs." in html
    assert "Run one command, leave visible work behind" in html
    assert "What happens when you join" in html
    assert "Your experiment shows up on a live goal page." in html
    assert "Your finding stays attached to the goal." in html
    assert "The next contributor gets a clear handoff." in html
    assert "./styles.css?v=" in html
    assert "Run one command, get a live goal page back" in html
    assert "Start with Eval." in html
    assert "Prefer performance work?" in html
    assert "Prefer not to use <code>curl | bash</code>?" in html
    assert "Copy this" in html
    assert "Copy command" in html
    assert "gives you a live goal URL that points back to your contribution" in html
    assert "What people are already moving on Eval" in html
    assert "Why this is worth joining now" in html
    assert "Best result so far" in html
    assert "Eval Sprint" in html
    assert "Inference Sprint" in html
    assert "4 visible contributions" in html
    assert "For agents and technical users" in html
    assert "Technical appendix" in html
    assert "View install script" in html
    assert "Manual join path" in html
    assert "Live goal pages are current hosted state." in html
    assert "https://github.com/example/openintention" in html
    assert "./evidence/join-with-ai.html" in html
    assert "./evidence/public-ingress-smoke.html" in html
    assert "./evidence/repeated-external-participation.html" in html
    assert 'href="/efforts"' in html
    assert "curl -fsSL https://openintention.io/join | bash" in html
    assert "--profile inference-sprint" in html
    assert "data-copy-text=" in html
    assert "Open the agent brief" in html
    assert "The live goal page is the current hosted source of truth." in html
    assert "Both seeded efforts already have visible work" not in html
    assert "Already live now" not in html
    assert "What an effort is" not in html
    assert "What we are trying to prove" not in html
    assert "What we are inviting you into" not in html
    assert "What happens next" not in html
    assert "Visible proof bundled" not in html
    assert (output_dir / "styles.css").exists()
    assert (output_dir / "assets" / "favicon.svg").exists()
    assert (output_dir / "evidence" / "public-ingress-smoke.md").read_text(encoding="utf-8").startswith(
        "# First User Smoke Report"
    )
    assert (output_dir / "evidence" / "join-with-ai.md").read_text(encoding="utf-8").startswith(
        "# Join With an AI Agent"
    )
    assert (
        output_dir / "evidence" / "repeated-external-participation.md"
    ).read_text(encoding="utf-8").startswith("# Repeated External Participation Proof")
    assert (output_dir / "evidence" / "join-with-ai.html").exists()
    assert (output_dir / "evidence" / "repeated-external-participation.html").exists()
    evidence_html = (output_dir / "evidence" / "join-with-ai.html").read_text(encoding="utf-8")
    assert "Open raw markdown" in evidence_html
    assert "Back to OpenIntention" in evidence_html
    assert "Repo brief" in evidence_html
    assert "../styles.css?v=" in evidence_html
    repeated_html = (output_dir / "evidence" / "repeated-external-participation.html").read_text(encoding="utf-8")
    assert "Hosted network proof" in repeated_html
