from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from html import escape
import os
from datetime import UTC, datetime
import sys
from pathlib import Path
import shutil

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_SITE_STATIC_DIR = _REPO_ROOT / "apps" / "site" / "static"


@dataclass(frozen=True, slots=True)
class MicrositeEvidence:
    smoke_report: Path
    eval_brief: Path
    inference_brief: Path
    join_with_ai: Path
    repeated_participation_report: Path


@dataclass(frozen=True, slots=True)
class MicrositeConfig:
    repo_url: str | None = None
    default_join_command: str = ""
    inference_join_command: str = ""


@dataclass(frozen=True, slots=True)
class EffortOverview:
    title: str
    objective: str
    platform: str
    budget_seconds: str
    summary: str
    best_current_result: str
    latest_claim_signal: str
    latest_visible_handoff: str
    attached_workspaces: str
    claims_in_scope: str
    frontier_members: str
    visible_participants: str
    updated_at: str


DEFAULT_PUBLIC_REPO_URL = "https://github.com/openintention/research-os"
DEFAULT_PUBLIC_SITE_URL = "https://openintention.io"


def _load_edge_join_commands() -> tuple[str, str]:
    from research_os.edge_bootstrap import edge_join_command
    from research_os.edge_bootstrap import edge_join_command_with_args

    return (
        edge_join_command(DEFAULT_PUBLIC_SITE_URL),
        edge_join_command_with_args(DEFAULT_PUBLIC_SITE_URL, "--profile", "inference-sprint"),
    )


def build_microsite(
    *,
    repo_root: Path,
    output_dir: Path,
    evidence: MicrositeEvidence,
    config: MicrositeConfig | None = None,
) -> Path:
    config = config or MicrositeConfig()
    output_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = output_dir / "assets"
    evidence_dir = output_dir / "evidence"
    assets_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    copied_smoke = evidence_dir / "public-ingress-smoke.md"
    copied_eval = evidence_dir / "eval-effort.md"
    copied_inference = evidence_dir / "inference-effort.md"
    copied_join_with_ai = evidence_dir / "join-with-ai.md"
    copied_repeated_participation = evidence_dir / "repeated-external-participation.md"
    shutil.copyfile(evidence.smoke_report, copied_smoke)
    shutil.copyfile(evidence.eval_brief, copied_eval)
    shutil.copyfile(evidence.inference_brief, copied_inference)
    shutil.copyfile(evidence.join_with_ai, copied_join_with_ai)
    shutil.copyfile(evidence.repeated_participation_report, copied_repeated_participation)

    participation_excerpt = _section_excerpt(evidence.smoke_report, heading="## Participation Outcome", lines=6)
    eval_effort = _parse_effort_overview(evidence.eval_brief)
    inference_effort = _parse_effort_overview(evidence.inference_brief)
    default_join_command, inference_join_command = _load_edge_join_commands()
    default_join_command = config.default_join_command or default_join_command
    inference_join_command = config.inference_join_command or inference_join_command

    styles = _load_stylesheet()
    site_script = _load_site_script()
    styles_version = _asset_version(styles)
    scripts_version = _asset_version(site_script)
    from apps.site import microsite_templates

    (assets_dir / "favicon.svg").write_text(_favicon_svg(), encoding="utf-8")
    (output_dir / "styles.css").write_text(styles, encoding="utf-8")
    (output_dir / "site.js").write_text(site_script, encoding="utf-8")
    index_context = microsite_templates.build_index_context(
        participation_excerpt=participation_excerpt,
        eval_effort=eval_effort,
        inference_effort=inference_effort,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        default_join_command=default_join_command,
        inference_join_command=inference_join_command,
        styles_version=styles_version,
        scripts_version=scripts_version,
        repo_url=config.repo_url,
    )
    (output_dir / "index.html").write_text(
        microsite_templates.render_index_page(index_context),
        encoding="utf-8",
    )
    for html_name, markdown_path, title in (
        ("join-with-ai.html", copied_join_with_ai, "Join OpenIntention With an AI Agent"),
        ("public-ingress-smoke.html", copied_smoke, "Public ingress report"),
        (
            "repeated-external-participation.html",
            copied_repeated_participation,
            "Repeated hosted participation proof",
        ),
        ("eval-effort.html", copied_eval, "Eval effort brief"),
        ("inference-effort.html", copied_inference, "Inference effort brief"),
    ):
        evidence_context = microsite_templates.build_evidence_context(
            markdown_path=markdown_path,
            title=title,
            styles_version=styles_version,
        )
        _write_evidence_page(
            output_dir=output_dir,
            html_name=html_name,
            evidence_html=microsite_templates.render_evidence_page(evidence_context),
        )
    return output_dir / "index.html"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the OpenIntention microsite.")
    parser.add_argument(
        "--output-dir",
        default="apps/site/dist",
        help="Directory to write the generated microsite into.",
    )
    parser.add_argument(
        "--repo-url",
        default=os.environ.get("OPENINTENTION_REPO_URL", DEFAULT_PUBLIC_REPO_URL),
        help="Optional public repo URL to surface on the microsite.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    build_microsite(
        repo_root=repo_root,
        output_dir=repo_root / args.output_dir,
        evidence=MicrositeEvidence(
            smoke_report=repo_root / "data/publications/launch/public-ingress/public-ingress-smoke.md",
            eval_brief=repo_root / "data/publications/efforts/eval-sprint-improve-validation-loss-under-fixed-budget.md",
            inference_brief=repo_root / "data/publications/efforts/inference-sprint-improve-flash-path-throughput-on-h100.md",
            join_with_ai=repo_root / "docs" / "join-with-ai.md",
            repeated_participation_report=repo_root
            / "data/publications/launch/repeated-external-participation/repeated-external-participation.md",
        ),
        config=MicrositeConfig(repo_url=args.repo_url),
    )


def _excerpt(path: Path, *, lines: int) -> str:
    content = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(content[:lines]).strip()


def _section_excerpt(path: Path, *, heading: str, lines: int) -> str:
    content = path.read_text(encoding="utf-8").splitlines()
    try:
        start_index = content.index(heading) + 1
    except ValueError:
        return ""
    section_lines: list[str] = []
    for line in content[start_index:]:
        if line.startswith("## "):
            break
        if line.strip():
            section_lines.append(line)
        if len(section_lines) >= lines:
            break
    return "\n".join(section_lines).strip()


def _parse_effort_overview(path: Path) -> EffortOverview:
    text = path.read_text(encoding="utf-8")

    def capture(pattern: str, default: str = "") -> str:
        match = re.search(pattern, text, flags=re.MULTILINE)
        return match.group(1).strip() if match else default

    title = capture(r"^# Effort: (.+)$")
    visible_participants = len({match.strip() for match in re.findall(r"actor=([^,\n]+)", text)})
    return EffortOverview(
        title=title,
        objective=capture(r"^- Objective: `([^`]+)`$"),
        platform=capture(r"^- Platform: `([^`]+)`$"),
        budget_seconds=capture(r"^- Budget seconds: `([^`]+)`$"),
        summary=capture(r"^- Summary: (.+)$"),
        best_current_result=_clean_display_text(capture(r"^- Best current result: (.+)$")),
        latest_claim_signal=_clean_display_text(capture(r"^- Latest claim signal: (.+)$")),
        latest_visible_handoff=_clean_display_text(capture(r"^- Latest visible handoff: (.+)$")),
        attached_workspaces=capture(r"^- Attached workspaces: (\d+)$", "0"),
        claims_in_scope=capture(r"^- Claims in effort scope: (\d+)$", "0"),
        frontier_members=capture(r"^- Frontier members: (\d+)$", "0"),
        visible_participants=str(visible_participants),
        updated_at=capture(r"^- Updated at: `([^`]+)`$"),
    )


def _clean_display_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("`", "")).strip()


def _humanize_best_result(value: str) -> str:
    cleaned = value.replace("claim signals", "recorded findings").replace(
        "claim signal", "recorded finding"
    )
    return cleaned


def _humanize_latest_finding(value: str) -> str:
    match = re.match(r"^(?P<actor>.+?) left a [^:]+ claim: (?P<statement>.+)$", value)
    if match:
        actor = match.group("actor").strip()
        statement = match.group("statement").strip()
        return f"{actor} reported: {statement}"
    return value.replace("claim", "finding")


def _humanize_handoff(value: str) -> str:
    humanized = value.replace(" claims,", " findings,")
    humanized = humanized.replace(" claim,", " finding,")
    humanized = humanized.replace(" claims ", " findings ")
    humanized = humanized.replace(" claim ", " finding ")
    return humanized


def _index_html(
    *,
    participation_excerpt: str,
    eval_effort: EffortOverview,
    inference_effort: EffortOverview,
    config: MicrositeConfig,
    default_join_command: str,
    inference_join_command: str,
    styles_version: str,
    scripts_version: str,
) -> str:
    manual_path_url = (
        f"{config.repo_url}#manual-join-path"
        if config.repo_url
        else "./evidence/join-with-ai.html"
    )
    repo_action = (
        f'<a class="button secondary" href="{escape(config.repo_url)}">Open the GitHub repo</a>'
        if config.repo_url
        else '<a class="button secondary" href="#inspect">Inspect what is already public</a>'
    )
    repo_list_item = (
        f'<li><a href="{escape(config.repo_url)}">GitHub repo for code and docs</a></li>'
        if config.repo_url
        else "<li>The public repo link will land with the first announcement.</li>"
    )
    site_footer_repo_link = (
        f'<a href="{escape(config.repo_url)}">GitHub repo</a>' if config.repo_url else ""
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>OpenIntention</title>
    <meta
      name="description"
      content="Make ML work compound instead of disappear."
    >
    <link rel="icon" href="./assets/favicon.svg" type="image/svg+xml">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link
      href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap"
      rel="stylesheet"
    >
    <link rel="stylesheet" href="./styles.css?v={escape(styles_version)}">
  </head>
  <body>
    <main class="page">
      <section class="hero hero-grid">
        <div class="hero-copy">
          <div class="eyebrow">OpenIntention · be early</div>
          <h1>Make ML work compound instead of disappear.</h1>
          <p class="lede">
            Join a live ML goal in one command. Your result shows up on the goal page so the next
            person or agent can continue from it.
          </p>
          <p class="sublede">
            Start with Eval: about five minutes, no special hardware, and a visible result or
            reproduction you can hand off.
          </p>
          <div class="hero-actions">
            <a class="button primary" href="#join-eval">Join Eval in 1 command</a>
            <a class="button secondary" href="/efforts">See the live Eval goal</a>
          </div>
          <div class="hero-trust">
            <span>5 minutes</span>
            <span>No special hardware</span>
            <span>Your result shows up live</span>
          </div>
          <p class="hero-note">
            Run one command. Leave visible work behind. Hand the same goal page to the next
            contributor.
          </p>
        </div>
        <aside class="hero-proof">
          <div class="proof-card shell-card">
            <div class="shell-bar">
              <div class="shell-dots" aria-hidden="true">
                <span></span><span></span><span></span>
              </div>
              <div class="shell-title">eval goal · already live</div>
            </div>
            <div class="proof-label">Already happening on Eval</div>
            <p class="proof-summary">
              {escape(_humanize_best_result(eval_effort.best_current_result) or "Eval already has visible progress to build on.")}
            </p>
            <ul class="proof-list">
              <li>
                <strong>{escape(eval_effort.visible_participants)} people are already here.</strong>
                <span>{escape(eval_effort.attached_workspaces)} visible contributions are already attached to this goal.</span>
              </li>
              <li>
                <strong>Latest handoff.</strong>
                <span>{escape(_humanize_handoff(eval_effort.latest_visible_handoff) or "A newcomer can join the goal and continue from a real handoff.")}</span>
              </li>
            </ul>
            <div class="card-links">
              <a href="/efforts">See the live Eval goal</a>
              <a href="./evidence/repeated-external-participation.html">See a real contribution</a>
            </div>
          </div>
        </aside>
      </section>

      <section class="panel join-panel" id="join-eval">
        <h2>Join Eval in 1 command</h2>
        <p class="section-lede">
          Run one command, get a live goal page back, and hand that page to the next person
          instead of restarting from a blank local loop.
        </p>
        <div class="join-layout">
          <article class="result-summary-card join-path-card">
            <div class="effort-type">Default first path</div>
            <h3>Start with Eval.</h3>
            <p>
              It is the lowest-friction way to join OpenIntention today: short runtime, no
              special hardware, a visible result on the live goal page, and a concrete handoff
              when it finishes.
            </p>
            <ul class="state-pills compact">
              <li><span>Time</span><code>~5m</code></li>
              <li><span>Hardware</span><code>standard</code></li>
              <li><span>People already here</span><code>{escape(eval_effort.visible_participants)}</code></li>
              <li><span>Visible contributions</span><code>{escape(eval_effort.attached_workspaces)}</code></li>
            </ul>
            <div class="card-links">
              <a href="/efforts">Open live goals</a>
              <a href="./evidence/eval-effort.html">Read the Eval brief</a>
            </div>
          </article>
          <div class="join-command-stack shell-card">
            <div class="shell-bar">
              <div class="shell-dots" aria-hidden="true">
                <span></span><span></span><span></span>
              </div>
              <div class="shell-title">join command · session</div>
            </div>
            <div class="command-head">
              <div class="proof-label">Copy this</div>
              <button
                class="copy-button"
                type="button"
                data-copy-default="Copy command"
                data-copy-text="{escape(default_join_command)}"
              >
                Copy command
              </button>
            </div>
            <pre class="command command-hero">{escape(default_join_command)}</pre>
            <p class="command-note">
              Run it yourself, or paste the same one-liner into Claude or Codex. The join flow
              gives you a live goal URL that points back to your contribution.
            </p>
            <div class="hero-trust command-pills">
              <span>Live result page</span>
              <span>Finding or reproduction</span>
              <span>Live handoff URL</span>
            </div>
            <div class="card-links">
              <a href="/join.sh">View install script</a>
              <a href="./evidence/join-with-ai.html">Use with Claude or Codex</a>
            </div>
          </div>
        </div>
        <div class="secondary-join-grid">
          <article class="result-summary-card secondary-path-card">
            <div class="effort-type">Secondary path</div>
            <h3>Prefer performance work?</h3>
            <p>
              The Inference goal stays available as the secondary join path. The starter loop is
              still a proxy there, but the live goal page and handoff surface are real.
            </p>
            <pre class="command command-secondary">{escape(inference_join_command)}</pre>
            <div class="card-links">
              <button
                class="copy-button secondary-copy"
                type="button"
                data-copy-default="Copy inference command"
                data-copy-text="{escape(inference_join_command)}"
              >
                Copy inference command
              </button>
              <a href="./evidence/inference-effort.html">Read the inference brief</a>
            </div>
          </article>
          <article class="result-summary-card secondary-path-card">
            <div class="effort-type">Inspect or run manually</div>
            <h3>Prefer not to use <code>curl | bash</code>?</h3>
            <p>
              Inspect the install script first, or take the manual repo path. Both routes land on
              the same live goal page in the end.
            </p>
            <pre class="command command-secondary">git clone {escape(config.repo_url or DEFAULT_PUBLIC_REPO_URL)}
cd research-os
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python3 scripts/join_openintention.py --no-bootstrap</pre>
            <div class="card-links">
              <a href="/join.sh">View install script</a>
              <a href="{escape(manual_path_url)}">Manual path</a>
            </div>
          </article>
        </div>
      </section>

      <section class="panel proof-result-section">
        <div class="proof-result-header">
          <div class="proof-result-copy">
            <div class="proof-label">Already happening</div>
            <h2>What people are already moving on Eval</h2>
            <p class="section-lede">
              Start with Eval because people are already contributing there, the best visible
              result is clear, and there is a live handoff to continue from.
            </p>
          </div>
        </div>
        <div class="proof-result-grid">
          <div class="shell-card result-card">
            <div class="shell-bar">
              <div class="shell-dots" aria-hidden="true">
                <span></span><span></span><span></span>
              </div>
              <div class="shell-title">eval goal · live momentum</div>
            </div>
            <div class="proof-label">Best result so far</div>
            <p class="summary-headline">{escape(_humanize_best_result(eval_effort.best_current_result))}</p>
            <pre class="proof-pre">{escape(_humanize_latest_finding(eval_effort.latest_claim_signal))}</pre>
            <p class="footer-note">{escape(_humanize_handoff(eval_effort.latest_visible_handoff))}</p>
          </div>
          <div class="result-summary-card">
            <div class="proof-label">Why this is worth joining now</div>
            <p>
              People have already left work here that you can pick up right now. Use the live goal
              page for the current hosted view.
            </p>
            <ul class="counts-list">
              <li>
                <strong>{escape(eval_effort.visible_participants)} people are already contributing on Eval</strong>
                <span>{escape(eval_effort.attached_workspaces)} visible contributions and {escape(eval_effort.claims_in_scope)} recorded findings are already attached to the default goal.</span>
              </li>
              <li>
                <strong>Latest handoff stays inspectable</strong>
                <span>{escape(_humanize_handoff(eval_effort.latest_visible_handoff))}</span>
              </li>
              <li>
                <strong>Inference is there when you want the performance path</strong>
                <span>{escape(_humanize_best_result(inference_effort.best_current_result))}</span>
              </li>
            </ul>
            <p class="footer-note">
              The live goal page is the current hosted source of truth. The packaged evidence
              pages stay available when you want a snapshot.
            </p>
            <div class="card-links">
              <a href="/efforts">Open live goals</a>
              <a href="./evidence/inference-effort.html">See the inference path</a>
            </div>
          </div>
        </div>
      </section>

      <section class="panel technical-footer" id="inspect">
        <div class="technical-footer-copy">
          <div>
            <div class="proof-label">Technical appendix</div>
            <h2>For agents and technical users</h2>
            <p>
              Live goal pages are current hosted state. The bundled evidence pages here are
              packaged snapshots. Verification artifacts stay below when you want to inspect the
              system more deeply.
            </p>
          </div>
          <div class="hero-actions">
            <a class="button primary" href="./evidence/join-with-ai.html">Open the agent brief</a>
            {repo_action}
          </div>
        </div>
        <ul class="link-list">
          <li><a href="/efforts">Live hosted explorer</a></li>
          <li><a href="/publish">Publish a goal in v1</a></li>
          <li><a href="/join.sh">View install script</a></li>
          <li><a href="{escape(manual_path_url)}">Manual join path</a></li>
          <li><a href="./evidence/public-ingress-smoke.html">Deterministic ingress proof</a></li>
          <li><a href="./evidence/repeated-external-participation.html">Repeated hosted participation proof</a></li>
          <li><a href="./evidence/eval-effort.html">Snapshot brief: Eval Sprint</a></li>
          <li><a href="./evidence/inference-effort.html">Snapshot brief: Inference Sprint</a></li>
          {repo_list_item}
        </ul>
      </section>
    </main>
    <footer class="site-footer">
      <p class="site-footer-copy">OpenIntention keeps goals, evidence, and handoffs public enough to compound.</p>
      <div class="site-footer-links">
        <a href="/efforts">Live goals</a>
        <a href="/publish">Publish a goal</a>
        <a href="/evidence/join-with-ai.html">Agent brief</a>
        {site_footer_repo_link}
      </div>
    </footer>
    <script src="./site.js?v={escape(scripts_version)}" defer></script>
  </body>
</html>
"""


def _favicon_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-label="OpenIntention">
  <rect width="96" height="96" rx="24" fill="#1f1b16"/>
  <circle cx="48" cy="48" r="28" fill="none" stroke="#f4efe4" stroke-width="8"/>
  <path d="M48 20c11 0 20 9 20 20 0 10-7 18-16 20v16h-8V40h8c4 0 8-4 8-8 0-7-5-12-12-12s-12 5-12 12h-8c0-11 9-20 20-20Z" fill="#b73a2f"/>
</svg>
"""


def _write_evidence_page(
    *,
    output_dir: Path,
    html_name: str,
    evidence_html: str,
) -> None:
    (output_dir / "evidence" / html_name).write_text(evidence_html, encoding="utf-8")


def _render_evidence_page_html(
    *,
    markdown_path: Path,
    title: str,
    styles_version: str,
) -> str:
    markdown_text = markdown_path.read_text(encoding="utf-8")
    eyebrow, lede = _evidence_page_intro(markdown_path)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} · OpenIntention</title>
    <link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link
      href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap"
      rel="stylesheet"
    >
    <link rel="stylesheet" href="../styles.css?v={escape(styles_version)}">
  </head>
  <body>
    <main class="page evidence-page">
      <section class="hero">
        <div class="eyebrow">{escape(eyebrow)}</div>
        <h1>{escape(title)}</h1>
        <p class="lede">{escape(lede)}</p>
        <div class="hero-actions">
          <a class="button primary" href="../">Back to OpenIntention</a>
          <a class="button secondary" href="./{escape(markdown_path.name)}">Open raw markdown</a>
        </div>
      </section>
      <section class="panel">
        <pre>{escape(markdown_text)}</pre>
      </section>
    </main>
  </body>
</html>
"""


def _evidence_page_intro(markdown_path: Path) -> tuple[str, str]:
    if markdown_path.name == "public-ingress-smoke.md":
        return (
            "Deterministic smoke report",
            "This report proves the public join path end to end. It is a verification artifact, not a live goal counter.",
        )
    if markdown_path.name.endswith("-effort.md"):
        return (
            "Generated snapshot",
            "This brief is a generated snapshot from the last repo export bundled into this site. Use /efforts for live goal state.",
        )
    if markdown_path.name == "repeated-external-participation.md":
        return (
            "Hosted network proof",
            "This report shows multiple distinct participants landing visible work through the canonical hosted network.",
        )
    if markdown_path.name == "join-with-ai.md":
        return (
            "Repo brief",
            "This brief is copied from the repo at build time so agents can follow the current public join path.",
        )
    return (
        "OpenIntention evidence",
        "This is a public evidence artifact rendered for humans, with raw markdown kept alongside it for agents and scripts.",
    )


def _asset_version(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]


def _load_stylesheet() -> str:
    return (_SITE_STATIC_DIR / "site.css").read_text(encoding="utf-8")


def _load_site_script() -> str:
    return (_SITE_STATIC_DIR / "site.js").read_text(encoding="utf-8")



if __name__ == "__main__":
    main()
