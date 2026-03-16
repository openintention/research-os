from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for path in (SRC_ROOT, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from research_os.http import build_request  # noqa: E402
from research_os.http import open_url  # noqa: E402
from scripts.run_public_ingress_smoke import run_public_ingress_smoke  # noqa: E402
from scripts.run_shared_participation_smoke import run_shared_participation_smoke  # noqa: E402


DEFAULT_SITE_URL = "https://openintention.io"
DEFAULT_API_BASE_URL = "https://api.openintention.io"


@dataclass(frozen=True, slots=True)
class ProductionSmokeResult:
    site_url: str
    api_base_url: str
    public_ingress_report: str
    shared_participation_report: str
    effort_names: list[str]
    homepage_url: str
    effort_page_urls: list[str]


def run_production_smoke(
    *,
    site_url: str,
    api_base_url: str,
    output_dir: str,
    python_executable: str = sys.executable,
) -> Path:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    _require_text(f"{api_base_url.rstrip('/')}/healthz", must_include="ok")
    homepage_url = f"{site_url.rstrip('/')}/"
    homepage_html = _require_text(homepage_url, must_include="Hosted effort explorer is live")
    for phrase in ("Snapshot evidence bundled", "Freshness model:", "Open deterministic join proof"):
        if phrase not in homepage_html:
            raise RuntimeError(f"homepage missing freshness phrase `{phrase}`: {homepage_url}")
    public_ingress_report = run_public_ingress_smoke(
        site_url=site_url,
        output_dir=str(output_root / "public-ingress"),
        python_executable=python_executable,
    )
    shared_participation_report = run_shared_participation_smoke(
        base_url=api_base_url,
        output_dir=str(output_root / "shared-participation"),
        artifact_root=str(output_root / "client-artifacts" / "shared-participation"),
    )

    efforts = _get_json(f"{api_base_url.rstrip('/')}/api/v1/efforts")
    if not isinstance(efforts, list) or not efforts:
        raise RuntimeError("production smoke expected at least one hosted effort")

    effort_names = [str(item["name"]) for item in efforts]
    effort_index_url = f"{site_url.rstrip('/')}/efforts"
    effort_index_html = _require_text(effort_index_url, must_include="Shared efforts")
    for effort_name in effort_names:
        if effort_name not in effort_index_html:
            raise RuntimeError(f"effort explorer index missing effort name: {effort_name}")

    effort_page_urls: list[str] = []
    for effort in efforts:
        effort_id = str(effort["effort_id"])
        effort_name = str(effort["name"])
        effort_page_url = f"{site_url.rstrip('/')}/efforts/{effort_id}"
        effort_page_html = _require_text(effort_page_url, must_include=effort_name)
        if (
            "Full live state" not in effort_page_html
            and "Machine-readable frontier and claim state" not in effort_page_html
        ):
            raise RuntimeError(f"effort page missing current-state section: {effort_page_url}")
        effort_page_urls.append(effort_page_url)

    result = ProductionSmokeResult(
        site_url=site_url,
        api_base_url=api_base_url,
        public_ingress_report=str(public_ingress_report),
        shared_participation_report=str(shared_participation_report),
        effort_names=effort_names,
        homepage_url=homepage_url,
        effort_page_urls=effort_page_urls,
    )
    report_path = output_root / "production-smoke.md"
    report_path.write_text(build_production_smoke_report(result), encoding="utf-8")
    return report_path


def build_production_smoke_report(result: ProductionSmokeResult) -> str:
    effort_lines = [f"- `{name}`" for name in result.effort_names]
    page_lines = [f"- `{url}`" for url in result.effort_page_urls]
    return "\n".join(
        [
            "# Production Smoke Report",
            "",
            "## Hosted Surface",
            f"- Site: `{result.site_url}`",
            f"- API: `{result.api_base_url}`",
            "",
            "## Executed Checks",
            f"- Homepage freshness copy: `{result.homepage_url}`",
            f"- Public ingress smoke: `{result.public_ingress_report}`",
            f"- Shared participation smoke: `{result.shared_participation_report}`",
            "- Hosted API healthz returned 200",
            "- Hosted homepage distinguishes live hosted state, bundled snapshot evidence, and deterministic smoke proofs",
            "- Hosted effort explorer index rendered current effort state",
            "- Hosted effort detail pages rendered current state for each effort",
            "",
            "## Hosted Efforts Observed",
            *effort_lines,
            "",
            "## Explorer Pages Observed",
            *page_lines,
            "",
            "## Outcome",
            "- The live public site, hosted API, and shared seeded-effort path are all reachable from the current production deployment.",
            "- A newcomer can still enter through the public surface while separate participants append into one hosted effort state.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the current production smoke floor against the hosted site and API."
    )
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL, help="Public OpenIntention site URL.")
    parser.add_argument(
        "--api-base-url",
        default=DEFAULT_API_BASE_URL,
        help="Hosted OpenIntention API base URL.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/publications/launch/production-smoke",
        help="Directory to write production smoke artifacts into.",
    )
    args = parser.parse_args()

    report_path = run_production_smoke(
        site_url=args.site_url,
        api_base_url=args.api_base_url,
        output_dir=args.output_dir,
    )
    print(report_path)


def _get_json(url: str) -> list[dict[str, object]] | dict[str, object]:
    request = build_request(url, headers={"User-Agent": "OpenIntentionSmoke/0.1"})
    with open_url(request, timeout=20) as response:
        import json

        return json.loads(response.read().decode("utf-8"))


def _require_text(url: str, *, must_include: str) -> str:
    request = build_request(url, headers={"User-Agent": "OpenIntentionSmoke/0.1"})
    with open_url(request, timeout=20) as response:
        text = response.read().decode("utf-8")
    if must_include not in text:
        raise RuntimeError(f"expected `{must_include}` in {url}")
    return text


if __name__ == "__main__":
    main()
