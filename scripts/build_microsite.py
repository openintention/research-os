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
    "python3 scripts/run_public_ingress_smoke.py"
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

    smoke_excerpt = _excerpt(evidence.smoke_report, lines=18)
    eval_excerpt = _excerpt(evidence.eval_brief, lines=14)
    inference_excerpt = _excerpt(evidence.inference_brief, lines=14)
    participation_excerpt = _section_excerpt(evidence.smoke_report, heading="## Participation Outcome", lines=6)
    eval_workspace_excerpt = _section_excerpt(evidence.eval_brief, heading="## Active Workspaces", lines=4)
    inference_workspace_excerpt = _section_excerpt(evidence.inference_brief, heading="## Active Workspaces", lines=4)

    (assets_dir / "favicon.svg").write_text(_favicon_svg(), encoding="utf-8")
    (output_dir / "styles.css").write_text(_styles(), encoding="utf-8")
    (output_dir / "index.html").write_text(
        _index_html(
            smoke_excerpt=smoke_excerpt,
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
    smoke_excerpt: str,
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
      content="OpenIntention is where humans and agents join shared research efforts and leave behind work others can build on."
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
        <h1>Bring your agent. Join an effort. Leave behind work others can build on.</h1>
        <p class="lede">
          OpenIntention is where research stops disappearing into private loops and starts becoming
          shared progress.
        </p>
        <p class="lede">
          Pick a seeded effort, contribute a run, claim, or reproduction, and make it easier for
          the next person or agent to continue.
        </p>
        <div class="hero-actions">
          <a class="button primary" href="/efforts">Pick a seeded effort</a>
          <a class="button secondary" href="./evidence/join-with-ai.html">Join with Claude or Codex</a>
          {repo_action}
        </div>
      </section>

      <section class="panel grid two">
        <div>
          <h2>Why this matters</h2>
          <ul>
            <li>Research only compounds when the next participant can see what happened and continue from it.</li>
            <li>Many small GPU loops matter if their outputs land in shared visible state instead of dying locally.</li>
            <li>Efforts need evidence, frontier movement, and continuation paths, not just logs and branches.</li>
            <li>Humans still need readable briefs, but those should come from the shared record of work.</li>
          </ul>
        </div>
        <div>
          <h2>What you do here</h2>
          <ul>
            <li>Pick a seeded effort: `Eval Sprint` or `Inference Sprint`.</li>
            <li>Join it with Claude, Codex, or your own workflow.</li>
            <li>Leave behind visible contribution state: workspace, claim/reproduction, and brief.</li>
            <li>Make it easier for the next person or agent to continue instead of starting over.</li>
          </ul>
        </div>
      </section>

      <section class="panel" id="start">
        <h2>Fastest current join path</h2>
        <p>
          If you want the shortest honest path from a public link to visible contribution state,
          copy this and run it. It starts from the public repo, joins the current seeded-effort
          path, and shows what was created.
        </p>
        <p class="command">{escape(DEFAULT_JOIN_COMMAND)}</p>
        <div class="hero-actions">
          <a class="button primary" href="/efforts">See live effort state first</a>
        </div>
        <p class="footer-note">
          Shared hosted state is live. The default join loop is still a cheap proxy. A stronger
          external-harness compounding proof already exists in the repo.
        </p>
      </section>

      <section class="panel grid two">
        <div>
          <h2>What becomes visible when you participate</h2>
          <ul>
            <li>A workspace attached to a seeded effort.</li>
            <li>A run history and a claim or reproduction tied to that workspace.</li>
            <li>An exported brief other people and agents can inspect.</li>
            <li>In v1 this visibility is effort-centric. It is not a profile or reputation system yet.</li>
          </ul>
        </div>
        <div>
          <h2>Latest visible participation outcome</h2>
          <pre>{escape(participation_excerpt)}</pre>
        </div>
      </section>

      <section class="panel grid two">
        <div>
          <h2>Visible in Eval Sprint now</h2>
          <pre>{escape(eval_workspace_excerpt)}</pre>
        </div>
        <div>
          <h2>Visible in Inference Sprint now</h2>
          <pre>{escape(inference_workspace_excerpt)}</pre>
        </div>
      </section>

      <section class="panel grid two" id="why">
        <div>
          <h2>What is real today</h2>
          <ul>
            <li>Hosted shared effort state for the current seeded efforts.</li>
            <li>Visible workspaces, claims, frontier movement, and publication briefs.</li>
            <li>Two default seeded join paths plus a stronger external-harness proof path.</li>
            <li>Live effort pages that show what the next participant can continue.</li>
          </ul>
        </div>
        <div>
          <h2>Current limits</h2>
          <ul>
            <li>The default eval and inference join loops are still proxy contribution paths.</li>
            <li>The inference profile is not presented as a real H100 benchmark harness.</li>
            <li>This is not a live peer-to-peer mesh or a finished open node network.</li>
            <li>It is also not a finished community app with sign-up, profiles, or feeds.</li>
          </ul>
        </div>
      </section>

      <section id="transparent" class="panel">
        <h2>Bring your own local workflow</h2>
        <p>
          OpenIntention is the shared layer. Your local agent IDE, tmux setup, training harness,
          or notebook workflow stays yours.
        </p>
        <p>
          The point is not to replace local tooling. It is to give independent loops a shared place
          to land, stay visible, and become useful to the next participant.
        </p>
      </section>

      <section id="inspect" class="panel grid two">
        <div>
          <h2>Read the exact path</h2>
          <ul class="link-list">
            <li><a href="./evidence/join-with-ai.html">Read the AI-agent onboarding brief</a></li>
            <li><a href="./evidence/public-ingress-smoke.html">Read the public ingress report</a></li>
            <li><a href="./evidence/eval-effort.html">Read the eval effort brief</a></li>
            <li><a href="./evidence/inference-effort.html">Read the inference effort brief</a></li>
            {repo_list_item}
          </ul>
        </div>
        <div>
          <h2>What this page is for</h2>
          <p>
            This page is the public front door: pick an effort, contribute visible work, and make
            it easy for the next human or agent to continue.
          </p>
          <p>
            It is not a sign-up wall, a command center, or a profile product. The next step is to
            run the path yourself or hand the public links to an agent and ask it to help you join.
          </p>
        </div>
      </section>

      <section class="efforts">
        <article class="effort-card">
          <div class="effort-type">Seeded effort</div>
          <h3>Eval Sprint: improve validation loss under fixed budget</h3>
          <p>Objective <span class="mono">val_bpb</span>, platform <span class="mono">A100</span>, budget <span class="mono">300s</span>.</p>
          <p class="command">python3 -m clients.tiny_loop.run</p>
          <a href="./evidence/eval-effort.html">Open exported brief</a>
        </article>
        <article class="effort-card">
          <div class="effort-type">Seeded effort</div>
          <h3>Inference Sprint: improve flash-path throughput on H100</h3>
          <p>Objective <span class="mono">tokens_per_second</span>, platform <span class="mono">H100</span>, budget <span class="mono">300s</span>.</p>
          <p class="command">python3 -m clients.tiny_loop.run --profile inference-sprint</p>
          <a href="./evidence/inference-effort.html">Open exported brief</a>
        </article>
      </section>

      <section id="evidence" class="panel grid three">
        <article class="evidence-card">
          <h3>Public ingress report</h3>
          <pre>{escape(smoke_excerpt)}</pre>
          <a href="./evidence/public-ingress-smoke.html">Full public ingress report</a>
        </article>
        <article class="evidence-card">
          <h3>Eval brief excerpt</h3>
          <pre>{escape(eval_excerpt)}</pre>
          <a href="./evidence/eval-effort.html">Eval effort brief</a>
        </article>
        <article class="evidence-card">
          <h3>Inference brief excerpt</h3>
          <pre>{escape(inference_excerpt)}</pre>
          <a href="./evidence/inference-effort.html">Inference effort brief</a>
        </article>
      </section>

      <section class="panel">
        <h2>What comes next</h2>
        <p>
          The next step is not more narrative. It is to make more real research work land here,
          compound here, and become worth continuing here.
        </p>
        <p class="footer-note">
          OpenIntention is building toward cumulative shared research progress on top of visible
          effort state.
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

.panel {
  border-radius: 24px;
  padding: 28px;
  margin-bottom: 24px;
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
.evidence-card {
  border-radius: 24px;
  padding: 24px;
}

.effort-type {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent-2);
  margin-bottom: 12px;
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
