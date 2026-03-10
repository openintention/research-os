from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def create_site_app(dist_dir: Path | None = None) -> FastAPI:
    dist_root = dist_dir or Path(__file__).resolve().parent / "dist"
    assets_root = dist_root / "assets"
    evidence_root = dist_root / "evidence"
    assets_root.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="OpenIntention Site", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/assets", StaticFiles(directory=assets_root), name="site-assets")
    app.mount("/evidence", StaticFiles(directory=evidence_root), name="site-evidence")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(dist_root / "index.html")

    @app.get("/styles.css", include_in_schema=False)
    def styles() -> FileResponse:
        return FileResponse(dist_root / "styles.css")

    return app


app = create_site_app()
