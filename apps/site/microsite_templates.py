from __future__ import annotations

from pathlib import Path
from html import escape

from apps.site.context_contracts import (
    MicrositeEffortOverview,
    MicrositeEvidenceContext,
    MicrositeIndexContext,
)

DEFAULT_PUBLIC_REPO_URL = "https://github.com/openintention/research-os"


def build_index_context(
    *,
    participation_excerpt: str,
    eval_effort: MicrositeEffortOverview,
    inference_effort: MicrositeEffortOverview,
    default_join_command: str,
    inference_join_command: str,
    styles_version: str,
    scripts_version: str,
    repo_url: str | None,
    site_css_url: str = "/styles.css",
    site_js_url: str | None = None,
) -> MicrositeIndexContext:
    return MicrositeIndexContext(
        participation_excerpt=participation_excerpt,
        eval_effort=eval_effort,
        inference_effort=inference_effort,
        default_join_command=default_join_command,
        inference_join_command=inference_join_command,
        styles_version=styles_version,
        scripts_version=scripts_version,
        repo_url=repo_url,
        site_css_url=site_css_url,
        site_js_url=site_js_url,
    )


def build_evidence_context(
    *,
    markdown_path: Path,
    title: str,
    styles_version: str,
) -> MicrositeEvidenceContext:
    return MicrositeEvidenceContext(
        markdown_path=markdown_path,
        title=title,
        styles_version=styles_version,
    )


def render_index_page(context: MicrositeIndexContext) -> str:
    return _index_html(
        participation_excerpt=context.participation_excerpt,
        eval_effort=context.eval_effort,
        inference_effort=context.inference_effort,
        repo_url=context.repo_url,
        default_join_command=context.default_join_command,
        inference_join_command=context.inference_join_command,
        styles_version=context.styles_version,
        scripts_version=context.scripts_version,
    )


def render_evidence_page(context: MicrositeEvidenceContext) -> str:
    return _render_evidence_page_html(
        markdown_path=context.markdown_path,
        title=context.title,
        styles_version=context.styles_version,
    )


def _humanize_best_result(value: str) -> str:
    return value.replace("claim signals", "recorded findings").replace("claim signal", "recorded finding")


def _humanize_latest_finding(value: str) -> str:
    import re

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


def _index_html(
    *,
    participation_excerpt: str,
    eval_effort: MicrositeEffortOverview,
    inference_effort: MicrositeEffortOverview,
    repo_url: str | None,
    default_join_command: str,
    inference_join_command: str,
    styles_version: str,
    scripts_version: str,
) -> str:
    manual_path_url = (
        f"{repo_url}#manual-join-path"
        if repo_url
        else "./evidence/join-with-ai.html"
    )
    repo_action = (
        f'<a class="button secondary" href="{escape(repo_url)}">Open the GitHub repo</a>'
        if repo_url
        else '<a class="button secondary" href="#inspect">Inspect what is already public</a>'
    )
    repo_list_item = (
        f'<li><a href="{escape(repo_url)}">GitHub repo for code and docs</a></li>'
        if repo_url
        else "<li>The public repo link will land with the first announcement.</li>"
    )
    site_footer_repo_link = (
        f'<a href="{escape(repo_url)}">GitHub repo</a>' if repo_url else ""
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
            <pre class="command command-secondary">git clone {escape(repo_url or DEFAULT_PUBLIC_REPO_URL)}
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
          <li><a href="/publish">Publish a goal (technical, proxy-only v1)</a></li>
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
        <a href="/evidence/join-with-ai.html">Agent brief</a>
        {site_footer_repo_link}
      </div>
    </footer>
    <script src="./site.js?v={escape(scripts_version)}" defer></script>
  </body>
</html>
"""


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
