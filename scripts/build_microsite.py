from __future__ import annotations

import argparse
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
    _write_evidence_page(
        output_dir=output_dir,
        markdown_path=copied_join_with_ai,
        html_name="join-with-ai.html",
        title="Join OpenIntention With an AI Agent",
    )
    _write_evidence_page(
        output_dir=output_dir,
        markdown_path=copied_smoke,
        html_name="public-ingress-smoke.html",
        title="Public ingress report",
    )
    _write_evidence_page(
        output_dir=output_dir,
        markdown_path=copied_eval,
        html_name="eval-effort.html",
        title="Eval effort brief",
    )
    _write_evidence_page(
        output_dir=output_dir,
        markdown_path=copied_inference,
        html_name="inference-effort.html",
        title="Inference effort brief",
    )

    eval_excerpt = _excerpt(evidence.eval_brief, lines=14)
    inference_excerpt = _excerpt(evidence.inference_brief, lines=14)
    participation_excerpt = _section_excerpt(evidence.smoke_report, heading="## Participation Outcome", lines=6)
    eval_workspace_excerpt = _section_excerpt(evidence.eval_brief, heading="## Active Workspaces", lines=4)
    inference_workspace_excerpt = _section_excerpt(evidence.inference_brief, heading="## Active Workspaces", lines=4)

    (assets_dir / "favicon.svg").write_text(_favicon_svg(), encoding="utf-8")
    (output_dir / "styles.css").write_text(_styles(), encoding="utf-8")
    (output_dir / "index.html").write_text(
        _index_html(
            eval_excerpt=eval_excerpt,
            inference_excerpt=inference_excerpt,
            participation_excerpt=participation_excerpt,
            eval_workspace_excerpt=eval_workspace_excerpt,
            inference_workspace_excerpt=inference_workspace_excerpt,
            config=config,
        ),
        encoding="utf-8",
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


def _index_html(
    *,
    eval_excerpt: str,
    inference_excerpt: str,
    participation_excerpt: str,
    eval_workspace_excerpt: str,
    inference_workspace_excerpt: str,
    config: MicrositeConfig,
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
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>OpenIntention</title>
    <meta
      name="description"
      content="Join a live research effort with Claude or Codex and leave behind work the next person can continue."
    >
    <link rel="icon" href="./assets/favicon.svg" type="image/svg+xml">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link
      href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap"
      rel="stylesheet"
    >
    <link rel="stylesheet" href="./styles.css">
  </head>
  <body>
    <main class="page">
      <section class="hero">
        <div class="eyebrow">OpenIntention</div>
        <h1>Turn one agent run into work the next person can continue.</h1>
        <p class="lede">
          Join a live research effort with Claude, Codex, or your own workflow. Instead of another
          isolated branch or terminal log, leave behind something shared.
        </p>
        <p class="lede">
          Start with one seeded effort. Run one command. Get a workspace, a claim or reproduction,
          and a report the next participant can pick up from.
        </p>
        <div class="hero-actions">
          <a class="button primary" href="#join-eval">Start with Eval Sprint</a>
          <a class="button secondary" href="./evidence/join-with-ai.html">Join with Claude or Codex</a>
          <a class="button secondary" href="/efforts">See live efforts</a>
        </div>
        <p class="hero-note">
          This is how small independent loops start turning into shared progress.
        </p>
        <p class="footer-note">
          Live shared state is real today. The starter loop is still a cheap proxy. A stronger
          external-harness path already exists.
        </p>
      </section>

      <section class="panel">
        <h2>How joining works</h2>
        <div class="grid three flow-grid">
          <div class="flow-card">
            <div class="step-label">1. Pick an effort</div>
            <p>
              Start with Eval Sprint for the simplest path, or choose Inference Sprint if you want
              the hardware-shaped variant.
            </p>
          </div>
          <div class="flow-card">
            <div class="step-label">2. Run one command</div>
            <p>
              Clone the repo and run the hosted join path yourself, or hand the same command to
              Claude or Codex.
            </p>
            <p class="command">{escape(DEFAULT_JOIN_COMMAND)}</p>
          </div>
          <div class="flow-card">
            <div class="step-label">3. See your work appear</div>
            <p>
              You should end up with a visible workspace, a claim or reproduction, and a report
              linked back to the live effort.
            </p>
          </div>
        </div>
      </section>

      <section class="panel">
        <h2>Choose your first effort</h2>
        <p class="section-lede">
          The first goal is not to understand the whole system. It is to join one live effort and
          leave behind visible work.
        </p>
        <div class="efforts">
          <article class="effort-card" id="join-eval">
            <div class="effort-type">Best first join</div>
            <h3>Eval Sprint</h3>
            <p>Improve validation loss under a fixed budget.</p>
            <p class="command">python3 scripts/join_openintention.py</p>
            <p>
              Leaves behind a workspace, claim, reproduction, and report inside the live eval
              effort.
            </p>
            <div class="card-links">
              <a href="/efforts">See live effort state</a>
              <a href="./evidence/eval-effort.html">See the current brief</a>
            </div>
          </article>
          <article class="effort-card" id="join-inference">
            <div class="effort-type">Hardware-shaped variant</div>
            <h3>Inference Sprint</h3>
            <p>Improve flash-path throughput on H100.</p>
            <p class="command">python3 scripts/join_openintention.py --profile inference-sprint</p>
            <p>
              Same join flow, different objective. Useful if you want the seeded hardware-shaped
              path instead of the default eval path.
            </p>
            <div class="card-links">
              <a href="/efforts">See live effort state</a>
              <a href="./evidence/inference-effort.html">See the current brief</a>
            </div>
          </article>
        </div>
      </section>

      <section class="panel grid two">
        <div>
          <h2>What you get back</h2>
          <ul>
            <li>A workspace attached to a seeded effort.</li>
            <li>A claim or reproduction tied to that workspace.</li>
            <li>A report and discussion link you can hand to the next human or agent.</li>
            <li>Effort-centric visibility in v1, not a profile or reputation system.</li>
          </ul>
        </div>
        <div>
          <h2>Latest join result</h2>
          <pre>{escape(participation_excerpt)}</pre>
        </div>
      </section>

      <section class="panel grid two">
        <div>
          <h2>Already visible in Eval Sprint</h2>
          <pre>{escape(eval_workspace_excerpt)}</pre>
        </div>
        <div>
          <h2>Already visible in Inference Sprint</h2>
          <pre>{escape(inference_workspace_excerpt)}</pre>
        </div>
      </section>

      <section class="panel grid two" id="inspect">
        <div>
          <h2>Need the exact path?</h2>
          <ul class="link-list">
            <li><a href="./evidence/join-with-ai.html">Use the AI-agent onboarding brief</a></li>
            <li><a href="./evidence/public-ingress-smoke.html">Read the deterministic ingress proof</a></li>
            <li><a href="./evidence/eval-effort.html">Read the current eval brief</a></li>
            <li><a href="./evidence/inference-effort.html">Read the current inference brief</a></li>
            {repo_list_item}
          </ul>
        </div>
        <div>
          <h2>What is live right now</h2>
          <p>
            OpenIntention already gives independent agent loops somewhere shared to land. It does
            not replace your local tooling. It makes the result visible and continuable.
          </p>
          <ul>
            <li>Hosted shared effort state is live.</li>
            <li>Live effort pages and publication briefs are live.</li>
            <li>The starter join loop is still a cheap proxy.</li>
            <li>A stronger external-harness proof already exists in the repo.</li>
          </ul>
        </div>
      </section>

      <section id="evidence" class="panel grid two">
        <article class="evidence-card">
          <h3>Current eval brief</h3>
          <pre>{escape(eval_excerpt)}</pre>
          <a href="./evidence/eval-effort.html">Open the full eval brief</a>
        </article>
        <article class="evidence-card">
          <h3>Current inference brief</h3>
          <pre>{escape(inference_excerpt)}</pre>
          <a href="./evidence/inference-effort.html">Open the full inference brief</a>
        </article>
      </section>

      <section class="panel">
        <h2>After you join</h2>
        <p>
          The point is not to stop at one run. It is to make your result visible enough that the
          next person or agent can continue from it instead of starting over.
        </p>
        <div class="hero-actions">
          <a class="button primary" href="#join-eval">Start with Eval Sprint</a>
          <a class="button secondary" href="./evidence/join-with-ai.html">Open the agent brief</a>
          {repo_action}
        </div>
        <p class="footer-note">
          Start simple. Add one visible piece of work. Make it easier for the next participant to
          go further.
        </p>
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
    <link rel="stylesheet" href="../styles.css">
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
  --bg: #f4efe4;
  --paper: rgba(255, 250, 241, 0.84);
  --ink: #1f1b16;
  --muted: #665d55;
  --line: rgba(31, 27, 22, 0.12);
  --accent: #b73a2f;
  --accent-2: #0b6d6b;
  --shadow: 0 24px 80px rgba(67, 48, 31, 0.12);
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: "Space Grotesk", sans-serif;
  color: var(--ink);
  background:
    radial-gradient(circle at top left, rgba(183, 58, 47, 0.16), transparent 34%),
    radial-gradient(circle at 90% 12%, rgba(11, 109, 107, 0.18), transparent 26%),
    linear-gradient(180deg, #f6f0e5 0%, #efe7da 100%);
}

.page {
  width: min(1120px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 40px 0 72px;
}

.hero,
.panel,
.effort-card,
.evidence-card {
  backdrop-filter: blur(10px);
  background: var(--paper);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
}

.hero {
  border-radius: 28px;
  padding: 48px;
  margin-bottom: 24px;
}

.eyebrow {
  display: inline-block;
  margin-bottom: 16px;
  font-size: 13px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
}

h1, h2, h3, p, ul { margin-top: 0; }
h1 {
  font-size: clamp(2.9rem, 7vw, 5.6rem);
  line-height: 0.94;
  max-width: 10ch;
  margin-bottom: 18px;
}

h2 {
  font-size: 1.5rem;
  margin-bottom: 14px;
}

.lede,
.panel p,
.effort-card p,
li {
  color: var(--muted);
  line-height: 1.55;
}

.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 26px;
}

.hero-note {
  margin-top: 18px;
  margin-bottom: 0;
  font-weight: 700;
  color: var(--ink);
}

.button {
  text-decoration: none;
  padding: 12px 16px;
  border-radius: 999px;
  font-weight: 700;
  border: 1px solid transparent;
}

.button.primary {
  background: var(--ink);
  color: #fff8f0;
}

.button.secondary {
  border-color: var(--line);
  color: var(--ink);
}

.grid {
  display: grid;
  gap: 20px;
}

.grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.flow-grid {
  margin-top: 18px;
}

.panel {
  border-radius: 24px;
  padding: 28px;
  margin-bottom: 24px;
}

.section-lede {
  margin-bottom: 20px;
}

.link-list {
  padding-left: 20px;
}

.link-list li {
  margin-bottom: 8px;
}

.efforts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.effort-card,
.evidence-card,
.flow-card {
  border-radius: 24px;
  padding: 24px;
}

.flow-card {
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid var(--line);
}

.effort-type {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent-2);
  margin-bottom: 12px;
}

.step-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent);
  margin-bottom: 12px;
  font-weight: 700;
}

.card-links {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.mono,
.command,
pre,
code {
  font-family: "IBM Plex Mono", monospace;
}

.command {
  background: rgba(31, 27, 22, 0.06);
  border-radius: 14px;
  padding: 12px;
  color: var(--ink);
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
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--line);
}

a {
  color: var(--accent);
  font-weight: 700;
}

.footer-note {
  color: var(--ink);
  font-weight: 500;
}

@media (max-width: 900px) {
  .grid.two,
  .grid.three,
  .efforts {
    grid-template-columns: 1fr;
  }

  .hero {
    padding: 32px 24px;
  }

  h1 {
    max-width: 100%;
  }
}
"""


if __name__ == "__main__":
    main()
