from __future__ import annotations

from scripts.run_public_ingress_smoke import (
    DEFAULT_PUBLIC_REPO_URL,
    PublicIngressResult,
    build_public_ingress_report,
    extract_public_repo_url,
)


def test_extract_public_repo_url_prefers_openintention_repo():
    html = """
    <html>
      <body>
        <a href="https://github.com/example/other-repo">other</a>
        <a href="https://github.com/openintention/research-os">repo</a>
      </body>
    </html>
    """

    assert extract_public_repo_url(html) == DEFAULT_PUBLIC_REPO_URL


def test_build_public_ingress_report_includes_public_entry_and_outcome():
    report = build_public_ingress_report(
        PublicIngressResult(
            site_url="https://openintention.io",
            repo_url="https://github.com/openintention/research-os",
            clone_path="/tmp/public-ingress/clone",
            agent_brief_path="/tmp/public-ingress/clone/docs/join-with-ai.md",
            smoke_report_path="/tmp/public-ingress/first-user/first-user-smoke.md",
            commands=[
                "git clone --depth 1 https://github.com/openintention/research-os /tmp/public-ingress/clone",
                "/tmp/public-ingress/clone/.venv-public-ingress/bin/python scripts/run_first_user_smoke.py --output-dir /tmp/public-ingress/first-user",
            ],
            smoke_report_excerpt="# First User Smoke Report\n\n## Base URL",
        )
    )

    assert "Public Ingress Smoke Report" in report
    assert "https://openintention.io" in report
    assert "https://github.com/openintention/research-os" in report
    assert "docs/join-with-ai.md" in report
    assert "A newcomer can arrive from the public site" in report
