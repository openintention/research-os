from __future__ import annotations

from fastapi.testclient import TestClient

from apps.site.server import create_site_app


def test_site_server_serves_generated_index_and_evidence(tmp_path):
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    evidence_dir = dist_dir / "evidence"
    assets_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html><body>OpenIntention</body></html>", encoding="utf-8")
    (dist_dir / "styles.css").write_text("body {}", encoding="utf-8")
    (assets_dir / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    (evidence_dir / "first-user-smoke.md").write_text("# smoke", encoding="utf-8")

    client = TestClient(create_site_app(dist_dir))

    index_response = client.get("/")
    assert index_response.status_code == 200
    assert "OpenIntention" in index_response.text

    style_response = client.get("/styles.css")
    assert style_response.status_code == 200

    asset_response = client.get("/assets/favicon.svg")
    assert asset_response.status_code == 200

    evidence_response = client.get("/evidence/first-user-smoke.md")
    assert evidence_response.status_code == 200
    assert "# smoke" in evidence_response.text
