from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from html import escape
import os
from pathlib import Path
import shutil


@dataclass(frozen=True, slots=True)
class MicrositeEvidence:
    smoke_report: Path
    eval_brief: Path
    inference_brief: Path
    join_with_ai: Path


@dataclass(frozen=True, slots=True)
class MicrositeConfig:
    repo_url: str | None = None


@dataclass(frozen=True, slots=True)
class EffortOverview:
    title: str
    objective: str
    platform: str
    budget_seconds: str
    summary: str
    attached_workspaces: str
    claims_in_scope: str
    frontier_members: str


DEFAULT_PUBLIC_REPO_URL = "https://github.com/openintention/research-os"
DEFAULT_JOIN_COMMAND = (
    "git clone https://github.com/openintention/research-os.git && "
    "cd research-os && "
    "python3 scripts/join_openintention.py"
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
    shutil.copyfile(evidence.smoke_report, copied_smoke)
    shutil.copyfile(evidence.eval_brief, copied_eval)
    shutil.copyfile(evidence.inference_brief, copied_inference)
    shutil.copyfile(evidence.join_with_ai, copied_join_with_ai)

    participation_excerpt = _section_excerpt(evidence.smoke_report, heading="## Participation Outcome", lines=6)
    eval_effort = _parse_effort_overview(evidence.eval_brief)
    inference_effort = _parse_effort_overview(evidence.inference_brief)

    styles = _styles()
    styles_version = hashlib.sha256(styles.encode("utf-8")).hexdigest()[:10]
    (assets_dir / "favicon.svg").write_text(_favicon_svg(), encoding="utf-8")
    (output_dir / "styles.css").write_text(styles, encoding="utf-8")
    (output_dir / "index.html").write_text(
        _index_html(
            participation_excerpt=participation_excerpt,
            eval_effort=eval_effort,
            inference_effort=inference_effort,
            config=config,
            styles_version=styles_version,
        ),
        encoding="utf-8",
    )
    for html_name, markdown_path, title in (
        ("join-with-ai.html", copied_join_with_ai, "Join OpenIntention With an AI Agent"),
        ("public-ingress-smoke.html", copied_smoke, "Public ingress report"),
        ("eval-effort.html", copied_eval, "Eval effort brief"),
        ("inference-effort.html", copied_inference, "Inference effort brief"),
    ):
        _write_evidence_page(
            output_dir=output_dir,
            markdown_path=markdown_path,
            html_name=html_name,
            title=title,
            styles_version=styles_version,
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
    return EffortOverview(
        title=title,
        objective=capture(r"^- Objective: `([^`]+)`$"),
        platform=capture(r"^- Platform: `([^`]+)`$"),
        budget_seconds=capture(r"^- Budget seconds: `([^`]+)`$"),
        summary=capture(r"^- Summary: (.+)$"),
        attached_workspaces=capture(r"^- Attached workspaces: (\d+)$", "0"),
        claims_in_scope=capture(r"^- Claims in effort scope: (\d+)$", "0"),
        frontier_members=capture(r"^- Frontier members: (\d+)$", "0"),
    )


def _human_join_summary(participation_excerpt: str) -> str:
    effort_name_map = {
        "Eval": "Eval Sprint",
        "Inference": "Inference Sprint",
    }
    joined_efforts: list[str] = []
    participated_efforts: list[str] = []
    for line in participation_excerpt.splitlines():
        joined_match = re.match(r"- Joined \(([^)]+)\):", line)
        if joined_match:
            joined_efforts.append(effort_name_map.get(joined_match.group(1), joined_match.group(1)))
        participated_match = re.match(r"- Participated \(([^)]+)\):", line)
        if participated_match:
            participated_efforts.append(
                effort_name_map.get(participated_match.group(1), participated_match.group(1))
            )

    bullets: list[str] = []
    if joined_efforts:
        bullets.append(
            f"Recent newcomers joined {', '.join(joined_efforts)} directly from the public surface."
        )
    if participated_efforts:
        bullets.append(
            f"Those runs left behind visible results in {', '.join(participated_efforts)} that the next person can inspect."
        )
    bullets.append("Each successful join creates a workspace, a visible result, and a report you can hand forward.")
    return "\n".join(f"- {bullet}" for bullet in bullets)


def _index_html(
    *,
    participation_excerpt: str,
    eval_effort: EffortOverview,
    inference_effort: EffortOverview,
    config: MicrositeConfig,
    styles_version: str,
) -> str:
    repo_action = (
        f'<a class="button secondary" href="{escape(config.repo_url)}">Inspect the repo</a>'
        if config.repo_url
        else '<a class="button secondary" href="#inspect">Inspect what is already public</a>'
    )
    repo_list_item = (
        f'<li><a href="{escape(config.repo_url)}">Public technical repo</a></li>'
        if config.repo_url
        else "<li>The public repo link will land with the first announcement.</li>"
    )
    hero_participation_excerpt = _human_join_summary(participation_excerpt)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>OpenIntention</title>
    <meta
      name="description"
      content="Join a live AI research effort with your agent and leave behind work the next person can continue."
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
          <div class="eyebrow">OpenIntention</div>
          <h1>Join a live AI research effort with your agent.</h1>
          <p class="lede">
            For ML engineers, benchmark tinkerers, and agent-native builders who want one run to
            become shared progress instead of another private result.
          </p>
          <p class="sublede">
            Live today on openintention.io: two seeded efforts, visible results, and one simple
            join path that leaves behind work the next person can continue.
          </p>
          <div class="hero-actions">
            <a class="button primary" href="#join-eval">Start with Eval Sprint</a>
            <a class="button secondary" href="#how-it-works">See how it works</a>
          </div>
          <div class="hero-trust">
            <span>2 live seeded efforts</span>
            <span>1 command to join</span>
            <span>Visible effort pages</span>
          </div>
          <p class="hero-note">
            OpenIntention gives small research loops somewhere shared to land.
          </p>
          <p class="footer-note">
            Shared effort state is live today. The starter loop is still a cheap proxy. A stronger
            external-harness path already exists in the repo.
          </p>
        </div>
        <aside class="hero-proof">
          <div class="proof-card shell-card">
            <div class="shell-bar">
              <div class="shell-dots" aria-hidden="true">
                <span></span><span></span><span></span>
              </div>
              <div class="shell-title">live effort · proof</div>
            </div>
            <div class="proof-label">What you get back</div>
            <ul class="proof-list">
              <li>
                <strong>A visible workspace</strong>
                <span>Your run lands on a live effort page instead of staying trapped in a local loop.</span>
              </li>
              <li>
                <strong>A visible result</strong>
                <span>You leave behind a claim or reproduction the next person can inspect.</span>
              </li>
              <li>
                <strong>A handoff</strong>
                <span>Your run produces a short report the next person or agent can continue from.</span>
              </li>
            </ul>
            <div class="proof-divider"></div>
            <div class="proof-label">Already happening now</div>
            <p class="proof-summary">
              People are already joining the seeded efforts from the public surface and leaving
              behind visible work.
            </p>
            <div class="card-links">
              <a href="/efforts">See live effort state</a>
              <a href="./evidence/public-ingress-smoke.html">Read the full join report</a>
            </div>
          </div>
        </aside>
      </section>

      <section class="panel join-panel" id="how-it-works">
        <h2>Pick your first effort and run one command</h2>
        <p class="section-lede">
          Start with Eval Sprint if you want the easiest first path. Choose Inference Sprint if
          you care more about performance work. You do not need special hardware for the starter
          flow.
        </p>
        <div class="join-layout">
          <div class="join-choices">
            <article class="choice-card is-primary" id="join-eval">
              <div class="effort-type">Best first path</div>
              <h3>Eval Sprint</h3>
              <p>
                The easiest first contribution. Join a live quality-focused effort and leave
                behind a result the next person can continue from.
              </p>
              <div class="card-links">
                <a href="./evidence/eval-effort.html">See the current brief</a>
                <a href="/efforts">See live effort state</a>
              </div>
            </article>
            <article class="choice-card">
              <div class="effort-type">Alternative path</div>
              <h3>Inference Sprint</h3>
              <p>
                The performance path. The starter flow is still a proxy here, but you do not need
                an H100 to try it.
              </p>
              <div class="card-links">
                <a href="./evidence/inference-effort.html">See the current brief</a>
                <a href="/efforts">See live effort state</a>
              </div>
            </article>
          </div>
          <div class="join-command-stack shell-card">
            <div class="shell-bar">
              <div class="shell-dots" aria-hidden="true">
                <span></span><span></span><span></span>
              </div>
              <div class="shell-title">join command · session</div>
            </div>
            <div class="proof-label">Copy this</div>
            <p class="command command-hero">{escape(DEFAULT_JOIN_COMMAND)}</p>
            <p class="command-note">
              Paste the same command into Claude or Codex if you want your agent to do the join
              for you. Add <code>--profile inference-sprint</code> for the performance path.
            </p>
          </div>
        </div>
      </section>

      <section class="panel proof-result-section">
        <div class="proof-result-header">
          <div>
            <div class="proof-label">Proof and result</div>
            <h2>What your first run leaves behind</h2>
          </div>
          <p class="section-lede">
            A successful join should leave behind visible work, not another local-only result.
          </p>
        </div>
        <div class="proof-result-grid">
          <div class="shell-card result-card">
            <div class="shell-bar">
              <div class="shell-dots" aria-hidden="true">
                <span></span><span></span><span></span>
              </div>
              <div class="shell-title">recent join · result</div>
            </div>
            <div class="proof-label">A recent public-surface join</div>
            <pre class="proof-pre">{escape(hero_participation_excerpt)}</pre>
            <p class="footer-note">
              Each successful join leaves behind a workspace, a visible result, and a report linked
              back to the effort.
            </p>
          </div>
          <div class="result-summary-card">
            <div class="proof-label">Already live now</div>
            <p>
              Both seeded efforts already have visible work and shared history that the next person
              can continue from.
            </p>
            <ul class="counts-list">
              <li>
                <strong>{escape(eval_effort.title)}</strong>
                <span>{escape(eval_effort.attached_workspaces)} workspaces · {escape(eval_effort.claims_in_scope)} claim signals · {escape(eval_effort.frontier_members)} frontier entries</span>
              </li>
              <li>
                <strong>{escape(inference_effort.title)}</strong>
                <span>{escape(inference_effort.attached_workspaces)} workspaces · {escape(inference_effort.claims_in_scope)} claim signals · {escape(inference_effort.frontier_members)} frontier entries</span>
              </li>
            </ul>
            <div class="card-links">
              <a href="/efforts">See live effort state</a>
              <a href="./evidence/public-ingress-smoke.html">Read the full join report</a>
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
              Use the agent brief, inspect the live effort state, or read the repo and public
              evidence directly.
            </p>
          </div>
          <div class="hero-actions">
            <a class="button primary" href="./evidence/join-with-ai.html">Open the agent brief</a>
            {repo_action}
          </div>
        </div>
        <ul class="link-list">
          <li><a href="./evidence/public-ingress-smoke.html">Read the deterministic ingress proof</a></li>
          <li><a href="./evidence/eval-effort.html">Read the current eval brief</a></li>
          <li><a href="./evidence/inference-effort.html">Read the current inference brief</a></li>
          {repo_list_item}
        </ul>
      </section>
    </main>
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
    markdown_path: Path,
    html_name: str,
    title: str,
    styles_version: str,
) -> None:
    markdown_text = markdown_path.read_text(encoding="utf-8")
    page = f"""<!doctype html>
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
        <div class="eyebrow">OpenIntention evidence</div>
        <h1>{escape(title)}</h1>
        <p class="lede">
          This is a public evidence artifact from the current narrow contribution path. It is
          rendered for humans here, with the raw markdown kept alongside it for agents and scripts.
        </p>
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
    (output_dir / "evidence" / html_name).write_text(page, encoding="utf-8")


def _styles() -> str:
    return """
:root {
  --bg: #071018;
  --bg-2: #0c1623;
  --panel: rgba(15, 23, 36, 0.9);
  --panel-2: rgba(19, 29, 45, 0.88);
  --shell: rgba(9, 16, 24, 0.96);
  --ink: #edf3fb;
  --muted: #9cadc2;
  --line: rgba(144, 173, 209, 0.16);
  --line-strong: rgba(144, 173, 209, 0.28);
  --accent: #7ef7b8;
  --accent-2: #63c7ff;
  --accent-3: #ffb454;
  --shadow: 0 28px 80px rgba(0, 0, 0, 0.42);
  --space-1: 8px;
  --space-2: 12px;
  --space-3: 16px;
  --space-4: 20px;
  --space-5: 24px;
  --space-6: 32px;
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: "Space Grotesk", sans-serif;
  color: var(--ink);
  background:
    radial-gradient(circle at 10% 0%, rgba(126, 247, 184, 0.12), transparent 28%),
    radial-gradient(circle at 88% 12%, rgba(99, 199, 255, 0.14), transparent 24%),
    radial-gradient(circle at 50% 100%, rgba(255, 180, 84, 0.08), transparent 30%),
    linear-gradient(180deg, #071018 0%, #0b121b 52%, #09111a 100%);
}

.page {
  width: min(1140px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 40px 0 72px;
}

.hero,
.panel,
.effort-card,
.evidence-card {
  backdrop-filter: blur(10px);
  background: var(--panel);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
}

.hero {
  border-radius: 28px;
  padding: 44px;
  margin-bottom: var(--space-5);
  background:
    linear-gradient(180deg, rgba(20, 31, 47, 0.92), rgba(11, 18, 27, 0.94)),
    linear-gradient(90deg, rgba(126, 247, 184, 0.04), transparent 40%),
    linear-gradient(transparent 95%, rgba(144, 173, 209, 0.03) 95%);
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: var(--space-6);
  align-items: stretch;
}

.hero-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.eyebrow {
  display: inline-block;
  margin-bottom: 16px;
  font-size: 13px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  font-family: "IBM Plex Mono", monospace;
}

h1, h2, h3, p, ul { margin-top: 0; }
h1 {
  font-size: clamp(2.9rem, 7vw, 5.6rem);
  line-height: 0.94;
  max-width: 10ch;
  margin-bottom: var(--space-3);
  color: var(--ink);
}

h2 {
  font-size: 1.5rem;
  margin-bottom: var(--space-2);
  color: var(--ink);
}

h3 {
  color: var(--ink);
}

.lede,
.panel p,
.effort-card p,
li {
  color: var(--muted);
  line-height: 1.55;
}

.lede {
  color: #dce8f6;
  font-size: 1.08rem;
  max-width: 34rem;
}

.sublede {
  color: var(--muted);
  max-width: 36rem;
}

.hero-actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-top: var(--space-5);
}

.hero-note {
  margin-top: var(--space-4);
  margin-bottom: var(--space-1);
  font-weight: 700;
  color: var(--accent-2);
}

.hero-trust {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-top: var(--space-4);
}

.hero-trust span {
  border: 1px solid var(--line);
  background: rgba(9, 16, 24, 0.72);
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 0.9rem;
  color: var(--ink);
  font-family: "IBM Plex Mono", monospace;
}

.hero-proof {
  display: flex;
}

.proof-card {
  width: 100%;
  border-radius: 24px;
  padding: var(--space-5);
  background:
    linear-gradient(180deg, rgba(18, 28, 42, 0.96), rgba(10, 17, 26, 0.98));
  border: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.shell-card {
  background:
    linear-gradient(180deg, rgba(16, 25, 38, 0.98), rgba(9, 15, 22, 0.98));
  border: 1px solid var(--line-strong);
}

.shell-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--line);
}

.shell-dots {
  display: inline-flex;
  gap: 8px;
}

.shell-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: block;
}

.shell-dots span:nth-child(1) { background: #ff7b72; }
.shell-dots span:nth-child(2) { background: var(--accent-3); }
.shell-dots span:nth-child(3) { background: var(--accent); }

.shell-title {
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-family: "IBM Plex Mono", monospace;
}

.eyebrow,
.proof-label,
.effort-type {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 700;
  font-family: "IBM Plex Mono", monospace;
}

.eyebrow,
.proof-label {
  color: var(--accent-2);
}

.proof-list {
  display: grid;
  gap: var(--space-3);
  padding-left: 0;
  list-style: none;
  margin-bottom: 0;
}

.proof-list li {
  display: grid;
  gap: 4px;
}

.proof-list strong {
  color: #ffffff;
}

.proof-list span {
  color: var(--muted);
  line-height: 1.45;
}

.proof-summary {
  margin: 0;
  color: #d5e1f1;
  max-width: 30ch;
}

.proof-divider {
  height: 1px;
  background: var(--line);
}

.proof-pre {
  margin: 0;
  max-height: none;
  color: #d7e8ff;
}

.button {
  text-decoration: none;
  padding: 12px 18px;
  border-radius: 14px;
  font-weight: 700;
  border: 1px solid transparent;
  transition: transform 140ms ease, border-color 140ms ease, background 140ms ease;
}

.button.primary {
  background: var(--accent);
  color: #071018;
}

.button.secondary {
  border-color: var(--line-strong);
  background: rgba(9, 16, 24, 0.72);
  color: var(--ink);
}

.grid {
  display: grid;
  gap: var(--space-4);
}

.grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.panel {
  border-radius: 24px;
  padding: var(--space-5);
  margin-bottom: var(--space-5);
  background:
    linear-gradient(180deg, rgba(16, 25, 38, 0.88), rgba(12, 18, 27, 0.92));
}

.section-lede {
  margin-bottom: var(--space-4);
  color: #d5e1f1;
  max-width: 44rem;
}

.link-list {
  padding-left: 20px;
}

.link-list li {
  margin-bottom: var(--space-2);
}

.effort-card,
.evidence-card,
.flow-card,
.choice-card,
.result-summary-card {
  border-radius: 24px;
  padding: var(--space-5);
}

.flow-card,
.choice-card,
.result-summary-card {
  background: var(--panel-2);
  border: 1px solid var(--line);
}

.join-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.72fr) minmax(0, 1.28fr);
  gap: var(--space-5);
  align-items: stretch;
}

.join-choices {
  display: grid;
  gap: var(--space-3);
  align-content: start;
}

.choice-card.is-primary {
  border-color: var(--line-strong);
  box-shadow: inset 0 1px 0 rgba(126, 247, 184, 0.08);
}

.join-command-stack {
  display: grid;
  gap: var(--space-3);
  padding: 26px;
  border-radius: 22px;
  align-content: start;
  box-shadow:
    inset 0 1px 0 rgba(126, 247, 184, 0.1),
    0 20px 52px rgba(0, 0, 0, 0.28);
}

.command-hero {
  margin: 0;
  font-size: 1rem;
  line-height: 1.7;
  padding: 20px;
  border-radius: 18px;
  background: rgba(5, 11, 18, 0.82);
  border: 1px solid var(--line);
  color: #ecfff5;
}

.command-note {
  margin: 0;
  color: #d5e1f1;
}

.effort-type {
  color: var(--accent-2);
  margin-bottom: var(--space-2);
}

.card-links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: var(--space-3);
}

.card-links a {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  background: rgba(9, 16, 24, 0.56);
  color: var(--ink);
  font-size: 0.95rem;
  font-weight: 600;
  text-decoration: none;
}

.proof-result-section {
  display: grid;
  gap: var(--space-4);
}

.proof-result-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 0.92fr);
  gap: var(--space-5);
  align-items: start;
}

.proof-result-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(320px, 0.92fr);
  gap: var(--space-5);
}

.result-card,
.result-summary-card {
  min-height: 100%;
}

.result-card {
  display: grid;
  gap: var(--space-3);
}

.counts-list {
  list-style: none;
  padding-left: 0;
  display: grid;
  gap: var(--space-4);
  margin-bottom: 0;
}

.counts-list li {
  display: grid;
  gap: 4px;
}

.counts-list strong {
  color: #ffffff;
}

.counts-list span {
  color: var(--muted);
}

.result-summary-card {
  display: grid;
  gap: var(--space-3);
  align-content: start;
}

.result-summary-card .card-links {
  margin-top: auto;
  padding-top: var(--space-2);
}

.technical-footer {
  display: grid;
  gap: var(--space-3);
}

.technical-footer-copy {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-4);
  align-items: start;
}

.mono,
.command,
pre,
code {
  font-family: "IBM Plex Mono", monospace;
}

.command {
  background: rgba(9, 16, 24, 0.9);
  border-radius: 14px;
  padding: 12px;
  color: #edfff6;
  border: 1px solid var(--line);
}

pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.5;
  max-height: 320px;
  overflow: auto;
  padding: 16px;
  border-radius: 18px;
  background: rgba(6, 12, 18, 0.88);
  border: 1px solid var(--line);
}

a {
  color: var(--accent-2);
  font-weight: 700;
}

.footer-note {
  color: #d2dded;
  font-weight: 500;
}

@media (max-width: 900px) {
  .grid.two,
  .grid.three,
  .join-layout,
  .proof-result-header,
  .proof-result-grid,
  .technical-footer-copy {
    grid-template-columns: 1fr;
  }

  .hero-grid {
    grid-template-columns: 1fr;
  }

  .hero {
    padding: 32px 24px;
  }

  h1 {
    max-width: 100%;
  }

  .panel {
    padding: 24px 20px;
  }

  .join-command-stack {
    padding: 20px;
  }

  .card-links a {
    width: 100%;
    justify-content: center;
  }
}
"""


if __name__ == "__main__":
    main()
