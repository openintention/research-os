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
    (evidence_dir / "public-ingress-smoke.md").write_text("# smoke", encoding="utf-8")

    client = TestClient(create_site_app(dist_dir))

    index_response = client.get("/")
    assert index_response.status_code == 200
    assert "OpenIntention" in index_response.text

    style_response = client.get("/styles.css")
    assert style_response.status_code == 200

    asset_response = client.get("/assets/favicon.svg")
    assert asset_response.status_code == 200

    evidence_response = client.get("/evidence/public-ingress-smoke.md")
    assert evidence_response.status_code == 200
    assert evidence_response.headers["content-type"].startswith("text/markdown")
    assert "# smoke" in evidence_response.text

    join_response = client.get("/join")
    assert join_response.status_code == 200
    assert "curl -fsSL" not in join_response.text
    assert "OPENINTENTION_REPO_URL" in join_response.text
    assert "scripts/join_openintention.py --no-bootstrap" in join_response.text

    join_sh_response = client.get("/join.sh")
    assert join_sh_response.status_code == 200
    assert join_sh_response.text == join_response.text


def test_site_server_renders_effort_index_from_live_api(monkeypatch, tmp_path):
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    evidence_dir = dist_dir / "evidence"
    assets_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html><body>OpenIntention</body></html>", encoding="utf-8")
    (dist_dir / "styles.css").write_text("body {}", encoding="utf-8")
    (assets_dir / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")

    def fake_fetch_json(api_base_url: str, path: str, *, query=None):
        assert api_base_url == "http://api.internal:8080"
        assert path == "/api/v1/efforts"
        assert query is None
        return [
            {
                "effort_id": "effort-1",
                "name": "Eval Sprint: improve validation loss under fixed budget",
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "workspace_ids": ["workspace-1"],
                "tags": {"effort_type": "eval", "seeded": "true"},
                "successor_effort_id": None,
                "updated_at": "2026-03-11T15:00:00Z",
            },
            {
                "effort_id": "effort-2",
                "name": "MLX History Sprint: improve val_bpb on Apple Silicon",
                "objective": "val_bpb",
                "platform": "Apple-Silicon-MLX",
                "budget_seconds": 300,
                "workspace_ids": ["workspace-2", "workspace-3"],
                "tags": {"external_harness": "mlx-history"},
                "successor_effort_id": None,
                "updated_at": "2026-03-11T16:00:00Z",
            },
        ]

    monkeypatch.setattr("apps.site.server._fetch_json", fake_fetch_json)
    client = TestClient(
        create_site_app(
            dist_dir,
            api_base_url="https://api.example.com",
            api_fetch_base_url="http://api.internal:8080",
        )
    )

    response = client.get("/efforts")
    assert response.status_code == 200
    assert "Live external-harness proof" in response.text
    assert "Hosted shared state, proxy contribution loop" in response.text
    assert "/efforts/effort-1" in response.text
    assert "/efforts/effort-2" in response.text
    assert "https://api.example.com/api/v1/publications/efforts/effort-1" in response.text


def test_site_server_renders_effort_detail_from_live_api(monkeypatch, tmp_path):
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    evidence_dir = dist_dir / "evidence"
    assets_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html><body>OpenIntention</body></html>", encoding="utf-8")
    (dist_dir / "styles.css").write_text("body {}", encoding="utf-8")
    (assets_dir / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")

    def fake_fetch_json(api_base_url: str, path: str, *, query=None):
        assert api_base_url == "http://api.internal:8080"
        if path == "/api/v1/efforts":
            return [
                {
                    "effort_id": "effort-mlx",
                    "name": "MLX History Sprint: improve val_bpb on Apple Silicon",
                    "objective": "val_bpb",
                    "platform": "Apple-Silicon-MLX",
                    "budget_seconds": 300,
                    "workspace_ids": ["workspace-alpha", "workspace-beta"],
                    "tags": {
                        "external_harness": "mlx-history",
                        "join_command": "python3 scripts/run_mlx_history_compounding_smoke.py --repo-path /tmp/mlx-history --base-url https://api.example.com",
                    },
                    "successor_effort_id": None,
                    "updated_at": "2026-03-11T16:00:00Z",
                }
            ]
        if path == "/api/v1/workspaces":
            assert query == {"effort_id": "effort-mlx"}
            return [
                {
                    "workspace_id": "workspace-beta",
                    "name": "mlx-history-beta-5efc7aa",
                    "actor_id": "mlx-beta",
                    "participant_role": "verifier",
                    "run_ids": ["run-beta"],
                    "claim_ids": ["claim-beta"],
                    "reproduction_count": 1,
                    "adoption_count": 1,
                    "objective": "val_bpb",
                    "platform": "Apple-Silicon-MLX",
                    "budget_seconds": 300,
                    "updated_at": "2026-03-11T13:47:23Z",
                },
                {
                    "workspace_id": "workspace-alpha",
                    "name": "mlx-history-alpha-4161af3",
                    "actor_id": "mlx-alpha",
                    "participant_role": "contributor",
                    "run_ids": ["run-alpha"],
                    "claim_ids": ["claim-alpha"],
                    "reproduction_count": 0,
                    "adoption_count": 0,
                    "objective": "val_bpb",
                    "platform": "Apple-Silicon-MLX",
                    "budget_seconds": 300,
                    "updated_at": "2026-03-11T13:47:22Z",
                },
            ]
        if path == "/api/v1/claims":
            assert query == {"objective": "val_bpb", "platform": "Apple-Silicon-MLX"}
            return [
                {
                    "claim_id": "claim-beta",
                    "workspace_id": "workspace-beta",
                    "status": "pending",
                    "statement": "reduce depth from 8 to 4",
                    "claim_type": "improvement",
                    "candidate_snapshot_id": "snap-beta",
                    "objective": "val_bpb",
                    "platform": "Apple-Silicon-MLX",
                    "support_count": 0,
                    "contradiction_count": 0,
                    "updated_at": "2026-03-11T13:47:23Z",
                }
            ]
        if path == "/api/v1/events":
            if query == {"workspace_id": "workspace-beta", "limit": 10_000}:
                return [
                    {
                        "event_id": "event-beta-started",
                        "kind": "workspace.started",
                        "occurred_at": "2026-03-11T13:47:20Z",
                        "workspace_id": "workspace-beta",
                        "aggregate_id": "workspace-beta",
                        "aggregate_kind": "workspace",
                        "actor_id": "mlx-beta",
                        "payload": {},
                        "tags": {},
                    },
                    {
                        "event_id": "event-beta-run",
                        "kind": "run.completed",
                        "occurred_at": "2026-03-11T13:47:21Z",
                        "workspace_id": "workspace-beta",
                        "aggregate_id": "run-beta",
                        "aggregate_kind": "run",
                        "actor_id": "mlx-beta",
                        "payload": {
                            "run_id": "run-beta",
                            "snapshot_id": "snap-beta",
                            "metric_name": "val_bpb",
                            "metric_value": 1.807902,
                            "direction": "min",
                            "status": "success",
                        },
                        "tags": {},
                    },
                    {
                        "event_id": "event-beta-claim",
                        "kind": "claim.asserted",
                        "occurred_at": "2026-03-11T13:47:22Z",
                        "workspace_id": "workspace-beta",
                        "aggregate_id": "claim-beta",
                        "aggregate_kind": "claim",
                        "actor_id": "mlx-beta",
                        "payload": {"claim_id": "claim-beta"},
                        "tags": {},
                    },
                    {
                        "event_id": "event-beta-repro",
                        "kind": "claim.reproduced",
                        "occurred_at": "2026-03-11T13:47:23Z",
                        "workspace_id": "workspace-beta",
                        "aggregate_id": "claim-beta",
                        "aggregate_kind": "claim",
                        "actor_id": "mlx-beta",
                        "payload": {"claim_id": "claim-beta"},
                        "tags": {},
                    },
                    {
                        "event_id": "event-beta-adopt",
                        "kind": "adoption.recorded",
                        "occurred_at": "2026-03-11T13:47:24Z",
                        "workspace_id": "workspace-beta",
                        "aggregate_id": "claim-beta",
                        "aggregate_kind": "claim",
                        "actor_id": "mlx-beta",
                        "payload": {"claim_id": "claim-beta"},
                        "tags": {},
                    },
                ]
            if query == {"workspace_id": "workspace-alpha", "limit": 10_000}:
                return [
                    {
                        "event_id": "event-alpha-started",
                        "kind": "workspace.started",
                        "occurred_at": "2026-03-11T13:47:19Z",
                        "workspace_id": "workspace-alpha",
                        "aggregate_id": "workspace-alpha",
                        "aggregate_kind": "workspace",
                        "actor_id": "mlx-alpha",
                        "payload": {},
                        "tags": {},
                    },
                    {
                        "event_id": "event-alpha-run",
                        "kind": "run.completed",
                        "occurred_at": "2026-03-11T13:47:20Z",
                        "workspace_id": "workspace-alpha",
                        "aggregate_id": "run-alpha",
                        "aggregate_kind": "run",
                        "actor_id": "mlx-alpha",
                        "payload": {
                            "run_id": "run-alpha",
                            "snapshot_id": "snap-alpha",
                            "metric_name": "val_bpb",
                            "metric_value": 1.812345,
                            "direction": "min",
                            "status": "success",
                        },
                        "tags": {},
                    },
                ]
            raise AssertionError(query)
        if path == "/api/v1/frontiers/val_bpb/Apple-Silicon-MLX":
            assert query == {"budget_seconds": 300}
            return {
                "members": [
                    {
                        "snapshot_id": "snap-beta",
                        "workspace_id": "workspace-beta",
                        "run_id": "run-beta",
                        "objective": "val_bpb",
                        "platform": "Apple-Silicon-MLX",
                        "budget_seconds": 300,
                        "metric_name": "val_bpb",
                        "metric_value": 1.807902,
                        "direction": "min",
                        "claim_count": 1,
                        "last_updated_at": "2026-03-11T13:47:23Z",
                    }
                ]
            }
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("apps.site.server._fetch_json", fake_fetch_json)
    client = TestClient(
        create_site_app(
            dist_dir,
            api_base_url="https://api.example.com",
            api_fetch_base_url="http://api.internal:8080",
        )
    )

    response = client.get("/efforts/effort-mlx")
    assert response.status_code == 200
    assert "MLX History Sprint: improve val_bpb on Apple Silicon" in response.text
    assert "Live external-harness proof" in response.text
    assert "README.md#external-mlx-compounding-proof" in response.text
    assert "python3 scripts/run_mlx_history_compounding_smoke.py" in response.text
    assert "Best current result" in response.text
    assert "Latest claim signal" in response.text
    assert "Best next move" in response.text
    assert "Compounding proof" in response.text
    assert "Visible work is stacking up on this effort" in response.text
    assert "2 contributors" in response.text
    assert "2 visible handoffs" in response.text
    assert "2 successful runs" in response.text
    assert "1 claim signal" in response.text
    assert "1 reproduction" in response.text
    assert "1 adoption" in response.text
    assert "Best-so-far progression" in response.text
    assert "Starting point" in response.text
    assert "New best #1" in response.text
    assert "Latest public handoff" in response.text
    assert "Recent handoffs" in response.text
    assert "Work the next person can continue" in response.text
    assert "mlx-beta" in response.text
    assert "Left behind 1 run, 1 claim, 1 reproduction, and 1 adoption" in response.text
    assert "/api/v1/publications/workspaces/workspace-beta/discussion" in response.text
    assert "claim-beta" in response.text
    assert "snap-beta" in response.text


def test_site_server_prefers_private_fetch_base_without_leaking_it(monkeypatch, tmp_path):
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    evidence_dir = dist_dir / "evidence"
    assets_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html><body>OpenIntention</body></html>", encoding="utf-8")
    (dist_dir / "styles.css").write_text("body {}", encoding="utf-8")
    (assets_dir / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")

    calls: list[tuple[str, str, dict[str, object] | None]] = []

    def fake_fetch_json(api_base_url: str, path: str, *, query=None):
        calls.append((api_base_url, path, query))
        if path == "/api/v1/efforts":
            return [
                {
                    "effort_id": "effort-1",
                    "name": "Eval Sprint",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "budget_seconds": 300,
                    "workspace_ids": ["workspace-1"],
                    "tags": {"effort_type": "eval"},
                    "successor_effort_id": None,
                    "updated_at": "2026-03-11T15:00:00Z",
                }
            ]
        if path == "/api/v1/workspaces":
            return []
        if path == "/api/v1/claims":
            return []
        if path == "/api/v1/events":
            return []
        if path == "/api/v1/frontiers/val_bpb/A100":
            return {"members": []}
        raise AssertionError(path)

    monkeypatch.setattr("apps.site.server._fetch_json", fake_fetch_json)
    monkeypatch.setenv("OPENINTENTION_API_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("OPENINTENTION_API_FETCH_BASE_URL", "http://api.internal:8080")

    client = TestClient(create_site_app(dist_dir))

    response = client.get("/efforts/effort-1")
    assert response.status_code == 200
    assert all(base == "http://api.internal:8080" for base, _, _ in calls)
    assert "python3 -m clients.tiny_loop.run --base-url https://api.example.com" in response.text
    assert "api.internal" not in response.text


def test_site_server_splits_current_and_historical_proof_efforts(monkeypatch, tmp_path):
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    evidence_dir = dist_dir / "evidence"
    assets_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text("<html><body>OpenIntention</body></html>", encoding="utf-8")
    (dist_dir / "styles.css").write_text("body {}", encoding="utf-8")
    (assets_dir / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")

    def fake_fetch_json(api_base_url: str, path: str, *, query=None):
        assert api_base_url == "http://api.internal:8080"
        assert path == "/api/v1/efforts"
        return [
            {
                "effort_id": "effort-current",
                "name": "MLX History Sprint: improve val_bpb on Apple Silicon (proof v2)",
                "objective": "val_bpb",
                "platform": "Apple-Silicon-MLX",
                "budget_seconds": 300,
                "workspace_ids": ["workspace-2"],
                "tags": {
                    "external_harness": "mlx-history",
                    "public_proof": "true",
                    "proof_series": "mlx-history-apple-silicon-300",
                    "proof_version": "2",
                },
                "successor_effort_id": None,
                "updated_at": "2026-03-11T16:00:00Z",
            },
            {
                "effort_id": "effort-old",
                "name": "MLX History Sprint: improve val_bpb on Apple Silicon",
                "objective": "val_bpb",
                "platform": "Apple-Silicon-MLX",
                "budget_seconds": 300,
                "workspace_ids": ["workspace-1"],
                "tags": {
                    "external_harness": "mlx-history",
                    "public_proof": "true",
                    "proof_series": "mlx-history-apple-silicon-300",
                    "proof_version": "1",
                    "proof_status": "historical",
                },
                "successor_effort_id": "effort-current",
                "updated_at": "2026-03-11T15:00:00Z",
            },
        ]

    monkeypatch.setattr("apps.site.server._fetch_json", fake_fetch_json)
    client = TestClient(
        create_site_app(
            dist_dir,
            api_base_url="https://api.example.com",
            api_fetch_base_url="http://api.internal:8080",
        )
    )

    response = client.get("/efforts")
    assert response.status_code == 200
    assert "Historical proof runs" in response.text
    assert "Historical proof run" in response.text
    assert "Current successor: <code>effort-current</code>" in response.text
