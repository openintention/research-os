from __future__ import annotations

from fastapi.testclient import TestClient

from apps.site.server import _build_effort_proof
from apps.site.server import _build_effort_worker_coordination
from apps.site.server import _participant_visibility_summary
from apps.site.server import create_site_app
from research_os.domain.models import LeaseObservation
from research_os.domain.models import WorkspaceView


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
    assert "scripts/run_overnight_autoresearch_worker.py" in join_response.text

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
    assert "Live external-harness goal" in response.text
    assert "Live goal, proxy join path" in response.text
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
                    "tags": {
                        "external_harness": "mlx-history",
                        "worker_mode": "overnight-autoresearch",
                    },
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
                    "tags": {
                        "external_harness": "mlx-history",
                    },
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
        if path == "/api/v1/leases":
            assert query == {"effort_id": "effort-mlx"}
            return [
                {
                    "lease": {
                        "lease_id": "lease-worker-1",
                        "lease_schema": "openintention-lease-v1",
                        "lease_version": 1,
                        "work_item_type": "explore_effort",
                        "participant_role": "contributor",
                        "subject_type": "effort",
                        "subject_id": "effort-mlx",
                        "effort_id": "effort-mlx",
                        "objective": "val_bpb",
                        "platform": "Apple-Silicon-MLX",
                        "budget_seconds": 300,
                        "planner_fingerprint": "sha256:" + "b" * 64,
                        "holder_node_id": "node_mlxworkerproof01",
                        "holder_workspace_id": None,
                        "status": "released",
                        "max_duration_seconds": 120,
                        "renewal_count": 1,
                        "acquired_at": "2026-03-11T13:47:20Z",
                        "renewed_at": "2026-03-11T13:47:28Z",
                        "released_at": "2026-03-11T13:47:31Z",
                        "completed_at": None,
                        "failed_at": None,
                        "failure_reason": None,
                        "observed_run_id": None,
                        "observed_claim_id": None,
                        "stale_completion": False,
                        "expires_at": "2026-03-11T13:47:50Z",
                    },
                    "liveness_status": "not_applicable",
                    "holder_heartbeat": {
                        "heartbeat_schema": "openintention-node-heartbeat-v1",
                        "heartbeat_version": 1,
                        "request_id": "heartbeat-worker-1",
                        "node_id": "node_mlxworkerproof01",
                        "ttl_seconds": 12,
                        "sent_at": "2026-03-11T13:47:29Z",
                        "observed_at": "2026-03-11T13:47:29Z",
                        "expires_at": "2026-03-11T13:47:41Z",
                        "freshness_status": "stale",
                    },
                }
            ]
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
    assert "Live external-harness goal" in response.text
    assert "README.md#real-overnight-autoresearch-worker" in response.text
    assert "python3 scripts/run_overnight_autoresearch_worker.py" in response.text
    assert "&lt;external_harness_command&gt;" in response.text
    assert "working best right now" in response.text
    assert "Latest finding" in response.text
    assert "What to try next" in response.text
    assert "How this goal is moving" in response.text
    assert "How people are moving this goal forward" in response.text
    assert "2 contributors" in response.text
    assert "2 visible handoffs" in response.text
    assert "2 successful runs" in response.text
    assert "1 recorded finding" in response.text
    assert "1 reproduction" in response.text
    assert "1 adoption" in response.text
    assert "Best-so-far progression" in response.text
    assert "Starting point" in response.text
    assert "mlx-history:overnight-autoresearch" in response.text
    assert "New best #1" in response.text
    assert "Latest handoff" in response.text
    assert "Who is involved" in response.text
    assert "People and agents visible on this goal" in response.text
    assert "Worker activity" in response.text
    assert "What background workers are doing on this goal" in response.text
    assert "No worker is active right now" in response.text
    assert "Open lease observation" in response.text
    assert "node_mlxworkerproof01" in response.text
    assert "not applicable" in response.text
    assert "worker import" in response.text
    assert "first visible" in response.text
    assert "Recent handoffs" in response.text
    assert "Work the next person can continue on this goal" in response.text
    assert "mlx-beta" in response.text
    assert "Left behind 1 run, 1 claim, 1 reproduction, and 1 adoption" in response.text
    assert "/api/v1/publications/workspaces/workspace-beta/discussion" in response.text
    assert "claim-beta" in response.text
    assert "snap-beta" in response.text


def test_site_server_highlights_joined_contribution_on_goal_page(monkeypatch, tmp_path):
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
                    "effort_id": "effort-eval",
                    "name": "Eval Sprint: improve validation loss under fixed budget",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "budget_seconds": 300,
                    "workspace_ids": ["workspace-joined"],
                    "tags": {"effort_type": "eval", "seeded": "true"},
                    "successor_effort_id": None,
                    "updated_at": "2026-03-17T11:00:00Z",
                }
            ]
        if path == "/api/v1/workspaces":
            assert query == {"effort_id": "effort-eval"}
            return [
                {
                    "workspace_id": "workspace-joined",
                    "name": "eval-joined",
                    "actor_id": "aliargun",
                    "participant_role": "contributor",
                    "run_ids": ["run-joined"],
                    "claim_ids": ["claim-joined"],
                    "reproduction_count": 1,
                    "adoption_count": 0,
                    "objective": "val_bpb",
                    "platform": "A100",
                    "budget_seconds": 300,
                    "tags": {"simulated_contribution": "true"},
                    "updated_at": "2026-03-17T11:00:00Z",
                }
            ]
        if path == "/api/v1/claims":
            return [
                {
                    "claim_id": "claim-joined",
                    "workspace_id": "workspace-joined",
                    "status": "supported",
                    "statement": "Quadratic features improved the seeded eval objective.",
                    "claim_type": "improvement",
                    "candidate_snapshot_id": "snap-joined",
                    "objective": "val_bpb",
                    "platform": "A100",
                    "support_count": 1,
                    "contradiction_count": 0,
                    "updated_at": "2026-03-17T11:00:00Z",
                }
            ]
        if path == "/api/v1/events":
            return [
                {
                    "event_id": "event-joined-started",
                    "kind": "workspace.started",
                    "occurred_at": "2026-03-17T10:59:59Z",
                    "workspace_id": "workspace-joined",
                    "aggregate_id": "workspace-joined",
                    "aggregate_kind": "workspace",
                    "actor_id": "aliargun",
                    "payload": {},
                    "tags": {},
                },
                {
                    "event_id": "event-joined-run",
                    "kind": "run.completed",
                    "occurred_at": "2026-03-17T11:00:00Z",
                    "workspace_id": "workspace-joined",
                    "aggregate_id": "run-joined",
                    "aggregate_kind": "run",
                    "actor_id": "aliargun",
                    "payload": {
                        "run_id": "run-joined",
                        "snapshot_id": "snap-joined",
                        "metric_name": "val_bpb",
                        "metric_value": 0.9,
                        "direction": "min",
                        "status": "success",
                    },
                    "tags": {},
                },
                {
                    "event_id": "event-joined-claim",
                    "kind": "claim.asserted",
                    "occurred_at": "2026-03-17T11:00:01Z",
                    "workspace_id": "workspace-joined",
                    "aggregate_id": "claim-joined",
                    "aggregate_kind": "claim",
                    "actor_id": "aliargun",
                    "payload": {"claim_id": "claim-joined"},
                    "tags": {},
                },
            ]
        if path == "/api/v1/frontiers/val_bpb/A100":
            return {
                "members": [
                    {
                        "snapshot_id": "snap-joined",
                        "workspace_id": "workspace-joined",
                        "run_id": "run-joined",
                        "objective": "val_bpb",
                        "platform": "A100",
                        "budget_seconds": 300,
                        "metric_name": "val_bpb",
                        "metric_value": 0.9,
                        "direction": "min",
                        "claim_count": 1,
                        "last_updated_at": "2026-03-17T11:00:01Z",
                    }
                ]
            }
        if path == "/api/v1/leases":
            return []
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("apps.site.server._fetch_json", fake_fetch_json)
    client = TestClient(
        create_site_app(
            dist_dir,
            api_base_url="https://api.example.com",
            api_fetch_base_url="http://api.internal:8080",
        )
    )

    response = client.get(
        "/efforts/effort-eval?workspace=workspace-joined&actor=aliargun&claim=claim-joined&reproduction=run-joined&joined=1"
    )
    assert response.status_code == 200
    assert "Your contribution" in response.text
    assert "You joined this goal" in response.text
    assert "aliargun now has visible hosted work on this goal" in response.text
    assert "What the next contributor should do" in response.text
    assert "Jump to this handoff" in response.text
    assert 'id="workspace-workspace-joined"' in response.text
    assert "highlight-card" in response.text


def test_build_effort_proof_tracks_participant_visibility_summary():
    workspaces = [
        WorkspaceView.model_validate(
            {
                "workspace_id": "workspace-current",
                "name": "current",
                "actor_id": "repeat-actor",
                "participant_role": "contributor",
                "run_ids": ["run-current"],
                "claim_ids": ["claim-current"],
                "reproduction_count": 0,
                "adoption_count": 0,
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "tags": {"external_harness": "mlx-history", "worker_mode": "overnight-autoresearch"},
                "updated_at": "2026-03-17T10:00:00Z",
            }
        ),
        WorkspaceView.model_validate(
            {
                "workspace_id": "workspace-carried",
                "name": "carried",
                "actor_id": "repeat-actor",
                "participant_role": "verifier",
                "run_ids": ["run-carried"],
                "claim_ids": [],
                "reproduction_count": 1,
                "adoption_count": 0,
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "tags": {"simulated_contribution": "true"},
                "updated_at": "2026-03-16T10:00:00Z",
            }
        ),
        WorkspaceView.model_validate(
            {
                "workspace_id": "workspace-new",
                "name": "new",
                "actor_id": "new-actor",
                "participant_role": "contributor",
                "run_ids": ["run-new"],
                "claim_ids": [],
                "reproduction_count": 0,
                "adoption_count": 0,
                "objective": "val_bpb",
                "platform": "A100",
                "budget_seconds": 300,
                "tags": {},
                "updated_at": "2026-03-15T10:00:00Z",
            }
        ),
    ]

    proof = _build_effort_proof(
        workspaces,
        workspace_events={},
        current_workspace_ids={"workspace-current", "workspace-new"},
        scope_label="proof series",
    )

    assert proof.contributor_count == 2
    assert proof.current_window_participant_count == 2
    assert proof.repeat_contributor_count == 1
    assert proof.worker_contributor_count == 1
    assert proof.verifier_contributor_count == 1
    assert proof.new_arrival_count == 1
    assert [spotlight.actor for spotlight in proof.participant_spotlights] == [
        "repeat-actor",
        "new-actor",
    ]
    assert proof.participant_spotlights[0].workspace_count == 2
    assert proof.participant_spotlights[0].has_worker_handoff is True
    assert (
        _participant_visibility_summary(proof, scope_label="proof series")
        == "This proof series currently shows 2 visible participants, all visible in the current window, 1 through worker import, 1 acting as verifier, 1 returning contributor, and 1 first-time visible contributor."
    )


def test_build_effort_worker_coordination_summarizes_released_worker_windows():
    coordination = _build_effort_worker_coordination(
        [
            LeaseObservation.model_validate(
                {
                    "lease": {
                        "lease_id": "lease-worker-1",
                        "lease_schema": "openintention-lease-v1",
                        "lease_version": 1,
                        "work_item_type": "explore_effort",
                        "participant_role": "contributor",
                        "subject_type": "effort",
                        "subject_id": "effort-1",
                        "effort_id": "effort-1",
                        "objective": "val_bpb",
                        "platform": "Apple-Silicon-MLX",
                        "budget_seconds": 300,
                        "planner_fingerprint": "sha256:" + "c" * 64,
                        "holder_node_id": "node_workerproofsummary01",
                        "holder_workspace_id": None,
                        "status": "released",
                        "max_duration_seconds": 120,
                        "renewal_count": 1,
                        "acquired_at": "2026-03-17T05:47:34Z",
                        "renewed_at": "2026-03-17T05:47:39Z",
                        "released_at": "2026-03-17T05:47:41Z",
                        "completed_at": None,
                        "failed_at": None,
                        "failure_reason": None,
                        "observed_run_id": None,
                        "observed_claim_id": None,
                        "stale_completion": False,
                        "expires_at": "2026-03-17T05:47:47Z",
                    },
                    "liveness_status": "not_applicable",
                    "holder_heartbeat": {
                        "heartbeat_schema": "openintention-node-heartbeat-v1",
                        "heartbeat_version": 1,
                        "request_id": "heartbeat-worker-1",
                        "node_id": "node_workerproofsummary01",
                        "ttl_seconds": 12,
                        "sent_at": "2026-03-17T05:47:40Z",
                        "observed_at": "2026-03-17T05:47:40Z",
                        "expires_at": "2026-03-17T05:47:52Z",
                        "freshness_status": "stale",
                    },
                }
            )
        ]
    )

    assert coordination.active_count == 0
    assert coordination.released_count == 1
    assert coordination.latest_observation is not None
    assert (
        coordination.summary_line
        == "1 worker lease window has touched this goal. No worker is active right now; node_workerproofsummary01 left its latest lease in status released after 1 renewal. The last observed heartbeat is stale."
    )


def test_site_server_carries_forward_proof_series_context_for_fresh_successor(monkeypatch, tmp_path):
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
                    "effort_id": "effort-current",
                    "name": "MLX History Sprint: improve val_bpb on Apple Silicon (proof v2)",
                    "objective": "val_bpb",
                    "platform": "Apple-Silicon-MLX",
                    "budget_seconds": 300,
                    "workspace_ids": [],
                    "tags": {
                        "external_harness": "mlx-history",
                        "public_proof": "true",
                        "proof_series": "mlx-history-apple-silicon-300",
                        "proof_version": "2",
                    },
                    "successor_effort_id": None,
                    "updated_at": "2026-03-13T07:36:43Z",
                },
                {
                    "effort_id": "effort-old",
                    "name": "Autoresearch MLX Sprint: improve val_bpb on Apple Silicon",
                    "objective": "val_bpb",
                    "platform": "Apple-Silicon-MLX",
                    "budget_seconds": 300,
                    "workspace_ids": ["workspace-alpha", "workspace-beta"],
                    "tags": {
                        "external_harness": "autoresearch-mlx",
                        "public_proof": "true",
                        "proof_series": "mlx-history-apple-silicon-300",
                        "proof_version": "1",
                        "proof_status": "historical",
                    },
                    "successor_effort_id": "effort-current",
                    "updated_at": "2026-03-11T13:47:22Z",
                },
            ]
        if path == "/api/v1/workspaces":
            if query == {"effort_id": "effort-current"}:
                return []
            if query == {"effort_id": "effort-old"}:
                return [
                    {
                        "workspace_id": "workspace-beta",
                        "name": "mlx-history-beta-5efc7aa",
                        "actor_id": "mlx-beta",
                        "participant_role": "contributor",
                        "run_ids": ["run-beta"],
                        "claim_ids": ["claim-beta"],
                        "reproduction_count": 1,
                        "adoption_count": 1,
                        "objective": "val_bpb",
                        "platform": "Apple-Silicon-MLX",
                        "budget_seconds": 300,
                        "tags": {
                            "external_harness": "mlx-history",
                            "worker_mode": "overnight-autoresearch",
                        },
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
                        "tags": {
                            "external_harness": "mlx-history",
                        },
                        "updated_at": "2026-03-11T13:47:22Z",
                    },
                ]
            raise AssertionError(query)
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
                    "support_count": 1,
                    "contradiction_count": 0,
                    "updated_at": "2026-03-11T13:47:23Z",
                }
            ]
        if path == "/api/v1/events":
            if query == {"workspace_id": "workspace-beta", "limit": 10_000}:
                return [
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
                            "metric_value": 2.533728,
                            "direction": "min",
                            "status": "success",
                        },
                        "tags": {},
                    }
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
        if path == "/api/v1/leases":
            assert query == {"effort_id": "effort-current"}
            return []
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("apps.site.server._fetch_json", fake_fetch_json)
    client = TestClient(
        create_site_app(
            dist_dir,
            api_base_url="https://api.example.com",
            api_fetch_base_url="http://api.internal:8080",
        )
    )

    response = client.get("/efforts/effort-current")
    assert response.status_code == 200
    assert "Current contributions</span><code>0</code>" in response.text
    assert "Series history</span><code>2</code>" in response.text
    assert "proof cards below carry forward" in response.text
    assert "This goal series already has 2 contributors" in response.text
    assert "current proof window is fresh" in response.text.lower()
    assert "mlx-beta" in response.text
    assert "from <code>unknown</code>" not in response.text
    assert "Window</span><code>carried</code>" in response.text
    assert "carried forward from an earlier proof window in this series" in response.text
    assert "Goal-series findings" in response.text
    assert "reduce depth from 8 to 4" in response.text


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
        if path == "/api/v1/leases":
            return []
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
    assert "Historical goal windows" in response.text
    assert "Historical goal window" in response.text
    assert "Current successor: <code>effort-current</code>" in response.text
