from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from html import escape
import os
import sys
from pathlib import Path
import shutil

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))


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
            default_join_command=default_join_command,
            inference_join_command=inference_join_command,
            styles_version=styles_version,
        ),
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
    default_join_command: str,
    inference_join_command: str,
    styles_version: str,
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
      content="Turn an ML goal into visible shared progress for humans and agents."
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
          <h1>Turn an ML goal into shared progress for humans and agents.</h1>
          <p class="lede">
            Most ML experiments disappear into local runs, branches, and chat logs. OpenIntention
            turns a seeded ML goal into a live page where people and agents can leave progress
            behind instead of starting over from scratch.
          </p>
          <p class="sublede">
            Start with the seeded Eval goal. It takes about five minutes, needs no special
            hardware, and gives you a live result page, a recorded finding or reproduction, and a
            handoff the next contributor can continue.
          </p>
          <div class="hero-actions">
            <a class="button primary" href="#join-eval">Join Eval in 1 command</a>
            <a class="button secondary" href="/efforts">Watch live goals</a>
          </div>
          <div class="hero-trust">
            <span>5 minutes</span>
            <span>No special hardware</span>
            <span>Your result shows up live</span>
          </div>
          <p class="hero-note">
            Run one command, leave visible work behind, and hand the same goal page to the next
            person or agent.
          </p>
        </div>
        <aside class="hero-proof">
          <div class="proof-card shell-card">
            <div class="shell-bar">
              <div class="shell-dots" aria-hidden="true">
                <span></span><span></span><span></span>
              </div>
              <div class="shell-title">default goal · already live</div>
            </div>
            <div class="proof-label">What happens when you join</div>
            <ul class="proof-list">
              <li>
                <strong>Your experiment shows up on a live goal page.</strong>
                <span>Your work lands in shared hosted state instead of staying trapped in a local loop.</span>
              </li>
              <li>
                <strong>Your finding stays attached to the goal.</strong>
                <span>The next person can inspect your claim or reproduction instead of repeating your first step.</span>
              </li>
              <li>
                <strong>The next contributor gets a clear handoff.</strong>
                <span>The goal page and discussion mirror make it obvious what happened and what to try next.</span>
              </li>
            </ul>
            <div class="proof-divider"></div>
            <div class="proof-label">Already happening on Eval</div>
            <p class="proof-summary">
              {escape(_humanize_best_result(eval_effort.best_current_result) or "The default goal already has visible record-setting work.")}
            </p>
            <p class="footer-note">{escape(_humanize_handoff(eval_effort.latest_visible_handoff) or "A newcomer can join the default goal and continue from a real handoff.")}</p>
            <div class="card-links">
              <a href="/efforts">Open live goals</a>
              <a href="./evidence/eval-effort.html">Read the Eval brief</a>
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
    <script>
      document.querySelectorAll(".copy-button[data-copy-text]").forEach((button) => {{
        button.addEventListener("click", async () => {{
          const defaultLabel = button.dataset.copyDefault || "Copy command";
          const command = button.dataset.copyText;
          if (!command) {{
            return;
          }}
          try {{
            await navigator.clipboard.writeText(command);
            button.textContent = "Copied";
          }} catch {{
            button.textContent = "Copy manually";
          }}
          window.setTimeout(() => {{
            button.textContent = defaultLabel;
          }}, 1600);
        }});
      }});
    </script>
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
    eyebrow, lede = _evidence_page_intro(markdown_path)
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
    (output_dir / "evidence" / html_name).write_text(page, encoding="utf-8")


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
  padding: 18px 20px;
  line-height: 1.56;
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
  margin: 0;
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
.result-summary-card,
.selected-effort {
  border-radius: 24px;
  padding: var(--space-5);
}

.flow-card,
.result-summary-card,
.selected-effort,
.summary-card {
  background: var(--panel-2);
  border: 1px solid var(--line);
}

.summary-card {
  display: grid;
  gap: var(--space-2);
}

.join-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.62fr) minmax(0, 1.38fr);
  gap: var(--space-4);
  align-items: start;
}

.join-path-card {
  min-height: 100%;
}

.secondary-join-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  margin-top: var(--space-3);
}

.secondary-path-card {
  min-height: 100%;
}

.join-selector-stack {
  display: grid;
  gap: var(--space-3);
  align-content: start;
}

.effort-toggle {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.effort-selector {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.effort-pill {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid var(--line);
  background: rgba(10, 18, 28, 0.76);
  cursor: pointer;
  transition: border-color 140ms ease, background 140ms ease, transform 140ms ease;
}

.effort-pill-kicker {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent-2);
  font-family: "IBM Plex Mono", monospace;
}

.effort-pill-title {
  color: var(--ink);
  font-weight: 700;
  font-size: 1rem;
}

#effort-eval:checked ~ .join-layout .effort-pill-eval,
#effort-inference:checked ~ .join-layout .effort-pill-inference {
  border-color: var(--line-strong);
  background: rgba(15, 28, 42, 0.92);
  box-shadow: inset 0 1px 0 rgba(126, 247, 184, 0.08);
}

.selected-effort {
  display: none;
  gap: var(--space-3);
}

.selected-effort h3,
.selected-effort p {
  margin: 0;
}

.selected-effort h3 {
  font-size: 1.35rem;
}

.selected-effort-meta {
  color: #d5e1f1;
}

#effort-eval:checked ~ .join-layout .detail-eval,
#effort-inference:checked ~ .join-layout .detail-inference {
  display: grid;
}

.join-command-stack {
  display: grid;
  gap: var(--space-3);
  padding: 24px;
  border-radius: 22px;
  align-content: start;
  align-self: start;
  box-shadow:
    inset 0 1px 0 rgba(126, 247, 184, 0.1),
    0 20px 52px rgba(0, 0, 0, 0.28);
}

.command-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.copy-button {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--line-strong);
  background: rgba(9, 16, 24, 0.72);
  color: var(--ink);
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
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

.command-pills {
  margin-top: 0;
}

.command-secondary {
  margin: 0;
  font-size: 0.92rem;
  line-height: 1.6;
  padding: 16px;
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

.card-links .copy-button {
  min-height: 38px;
}

.proof-result-section {
  display: grid;
  gap: var(--space-3);
}

.proof-result-header {
  display: grid;
  gap: var(--space-2);
  align-items: start;
}

.proof-result-copy {
  display: grid;
  gap: 8px;
  max-width: 58rem;
}

.proof-result-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(320px, 0.92fr);
  gap: var(--space-3);
  align-items: start;
}

.proof-surface-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.14fr) minmax(320px, 0.86fr);
  gap: var(--space-4);
  align-items: start;
}

.proof-stat-pills {
  margin-bottom: var(--space-4);
}

.progress-ladder {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: var(--space-3);
}

.progress-step,
.progress-step-empty {
  border-radius: 18px;
  border: 1px solid var(--line);
  background: rgba(7, 13, 20, 0.68);
  padding: 16px 18px;
}

.progress-step {
  display: grid;
  gap: 6px;
}

.progress-step strong {
  color: #ffffff;
  font-size: 1rem;
  line-height: 1.45;
}

.progress-step span,
.progress-step-empty {
  color: var(--muted);
  line-height: 1.5;
}

.progress-step-kicker {
  color: var(--accent-2);
  font-size: 12px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-family: "IBM Plex Mono", monospace;
}

.result-card,
.result-summary-card {
  min-height: 100%;
}

.result-card {
  display: grid;
  gap: 14px;
  padding: 16px 16px 18px;
}

.result-card .shell-bar {
  padding-bottom: 10px;
}

.result-card .proof-label {
  margin-top: 2px;
}

.counts-list {
  list-style: none;
  padding-left: 0;
  display: grid;
  gap: 0;
  margin: 0;
}

.counts-list li {
  display: grid;
  gap: 6px;
  padding: 14px 0;
  border-bottom: 1px solid var(--line);
}

.counts-list li:first-child {
  padding-top: 6px;
}

.counts-list li:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.counts-list strong {
  color: #ffffff;
}

.counts-list span {
  color: var(--muted);
}

.result-summary-card {
  display: grid;
  gap: 18px;
  align-content: start;
  padding: 22px 22px 24px;
  border-radius: 24px;
  border: 1px solid var(--line);
  background: rgba(18, 27, 41, 0.76);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
}

.success-panel {
  border-color: rgba(126, 247, 184, 0.34);
  background:
    linear-gradient(180deg, rgba(16, 29, 32, 0.9), rgba(10, 18, 24, 0.94));
}

.highlight-card {
  border-color: rgba(126, 247, 184, 0.34);
  box-shadow:
    inset 0 1px 0 rgba(126, 247, 184, 0.08),
    0 0 0 1px rgba(126, 247, 184, 0.12);
}

.effort-summary-grid {
  align-items: start;
}

.summary-stack {
  display: grid;
  gap: var(--space-3);
}

.summary-headline {
  margin: 0;
  color: #eef6ff;
  font-size: 1.04rem;
  line-height: 1.45;
}

.join-summary-card h2 {
  margin-bottom: 0;
}

.state-pills {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.state-pills li {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(9, 16, 24, 0.56);
  line-height: 1.2;
}

.state-pills span {
  color: var(--muted);
  font-size: 0.9rem;
}

.state-pills code {
  color: #edf7ff;
}

.state-pills.compact li {
  padding: 8px 10px;
}

.handoff-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

.handoff-card h3 {
  margin-bottom: 0;
}

.handoff-meta {
  margin: 0;
  color: var(--muted);
  font-size: 0.92rem;
}

.machine-state-panel {
  background:
    linear-gradient(180deg, rgba(13, 21, 31, 0.82), rgba(10, 16, 24, 0.88));
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

.site-footer {
  width: min(1160px, calc(100vw - 32px));
  margin: 0 auto 48px;
  padding: 20px 0 0;
  border-top: 1px solid var(--line);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.site-footer-copy {
  margin: 0;
  color: #9bb0c8;
  font-size: 0.95rem;
}

.site-footer-links {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
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
  margin: 0;
  color: #d2dded;
  font-weight: 500;
  font-size: 0.98rem;
  line-height: 1.52;
}

.result-card .footer-note {
  padding-top: 12px;
  border-top: 1px solid var(--line);
  max-width: 42ch;
}

@media (max-width: 900px) {
  .grid.two,
  .grid.three,
  .join-layout,
  .proof-result-header,
  .proof-result-grid,
  .proof-surface-grid,
  .handoff-grid,
  .technical-footer-copy,
  .secondary-join-grid {
    grid-template-columns: 1fr;
  }

  .site-footer {
    flex-direction: column;
    align-items: flex-start;
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

  .result-card,
  .result-summary-card {
    padding: 18px;
  }

  .effort-selector {
    grid-template-columns: 1fr;
  }

  .card-links a {
    width: 100%;
    justify-content: center;
  }

  .state-pills {
    gap: 8px;
  }

  .state-pills li {
    width: 100%;
    justify-content: space-between;
  }
}
"""


if __name__ == "__main__":
    main()
