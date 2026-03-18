from __future__ import annotations

from pathlib import Path

from apps.site import microsite_templates
from scripts.build_microsite import (
    _section_excerpt,
    _parse_effort_overview,
)


def test_microsite_index_rendered_output_matches_internal_renderer(tmp_path: Path):
    eval_brief = tmp_path / "eval.md"
    inference_brief = tmp_path / "inference.md"
    smoke = tmp_path / "smoke.md"
    eval_brief.write_text(
        "# Effort: Eval Sprint\n\n- Objective: `val_bpb`\n- Platform: `A100`\n- Budget seconds: `300`\n- Summary: Seeded eval effort.\n## Proof Context\n- Best current result: `val_bpb` = `0.447392` from `participant-alpha` with `1` claim signal.\n- Latest claim signal: `participant-alpha` left a `supported` claim: Quadratic features improved the seeded eval objective.\n- Latest visible handoff: Left behind 3 runs, 1 claim, and 1 reproduction that the next person can inspect and continue.\n## Current State\n- Attached workspaces: 4\n- Claims in effort scope: 3\n- Frontier members: 5\n- Updated at: `2026-03-17T11:00:00Z`\n",
        encoding="utf-8",
    )
    inference_brief.write_text(
        "# Effort: Inference Sprint\n\n- Objective: `tokens_per_second`\n- Platform: `H100`\n- Budget seconds: `300`\n- Summary: Seeded inference effort.\n## Proof Context\n- Best current result: `tokens_per_second` = `1284.0` from `seed` with `0` claim signals.\n- Latest claim signal: `participant-beta` left a `supported` claim: Candidate path improved the seeded inference objective.\n- Latest visible handoff: Left behind 3 runs, 1 claim, and 1 reproduction that the next person can inspect and continue.\n## Current State\n- Attached workspaces: 2\n- Claims in effort scope: 1\n- Frontier members: 3\n- Updated at: `2026-03-17T11:00:00Z`\n",
        encoding="utf-8",
    )
    smoke.write_text(
        "# Public ingress smoke report\n## Participation Outcome\n- Joined (Eval): workspace-1\n- Participated (Eval): claim-1\n",
        encoding="utf-8",
    )

    participation_excerpt = _section_excerpt(smoke, heading="## Participation Outcome", lines=6)
    index_context = microsite_templates.build_index_context(
        participation_excerpt=participation_excerpt,
        eval_effort=_parse_effort_overview(eval_brief),
        inference_effort=_parse_effort_overview(inference_brief),
        generated_at="2026-03-19 00:00:00",
        default_join_command="curl -fsSL https://openintention.io/join | bash",
        inference_join_command="curl -fsSL https://openintention.io/join | bash -- --profile inference-sprint",
        styles_version="abcdef1234",
        scripts_version="1234abcdef",
        repo_url="https://github.com/example/openintention",
    )
    eval_effort = _parse_effort_overview(eval_brief)
    inference_effort = _parse_effort_overview(inference_brief)
    rendered = microsite_templates.render_index_page(index_context)
    assert "Make ML work compound instead of disappear." in rendered
    assert "OpenIntention · be early" in rendered
    assert "Join Eval in 1 command" in rendered
    assert "See a real contribution" in rendered
    assert "gives you a live goal URL that points back to your contribution" in rendered
    assert "Homepage is a generated snapshot from 2026-03-19 00:00:00 UTC." in rendered
    assert "Prefer not to use <code>curl | bash</code>?" in rendered
    assert "https://github.com/example/openintention" in rendered
    assert "Open the GitHub repo" in rendered
    assert "./site.js?v=1234abcdef" in rendered
    assert "./styles.css?v=abcdef1234" in rendered
    assert eval_effort.visible_participants in rendered
    assert eval_effort.attached_workspaces in rendered
    expected_eval_best = eval_effort.best_current_result.replace("claim signals", "recorded findings").replace(
        "claim signal", "recorded finding"
    )
    expected_inference_best = inference_effort.best_current_result.replace(
        "claim signals", "recorded findings"
    ).replace("claim signal", "recorded finding")
    assert expected_eval_best in rendered
    assert expected_inference_best in rendered
    assert "curl -fsSL https://openintention.io/join | bash" in rendered
    assert "--profile inference-sprint" in rendered


def test_microsite_evidence_rendered_output_matches_internal_renderer(tmp_path: Path):
    doc = tmp_path / "join-with-ai.md"
    doc.write_text("# Join With an AI Agent\nline\n", encoding="utf-8")

    evidence_context = microsite_templates.build_evidence_context(
        markdown_path=doc,
        title="Join OpenIntention With an AI Agent",
        styles_version="abcdef1234",
    )
    rendered = microsite_templates.render_evidence_page(evidence_context)
    assert "Join OpenIntention With an AI Agent" in rendered
    assert "Repo brief" in rendered
    assert (
        "This brief is copied from the repo at build time so agents can follow the current public join path."
        in rendered
    )
    assert "line" in rendered
