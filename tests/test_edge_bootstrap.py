from __future__ import annotations

from src.research_os.edge_bootstrap import (
    edge_join_command,
    edge_join_command_with_args,
    render_edge_bootstrap_script,
)


def test_edge_join_command_uses_public_join_route() -> None:
    assert edge_join_command("https://openintention.io/") == "curl -fsSL https://openintention.io/join | bash"
    assert (
        edge_join_command_with_args("https://openintention.io", "--profile", "inference-sprint")
        == "curl -fsSL https://openintention.io/join | bash -s -- --profile inference-sprint"
    )


def test_render_edge_bootstrap_script_prefers_python311_and_supports_nightly() -> None:
    script = render_edge_bootstrap_script(
        site_url="https://openintention.io/",
        repo_url="https://github.com/openintention/research-os.git",
        channel="main",
    )

    assert 'OPENINTENTION_SITE_URL="${OPENINTENTION_SITE_URL:-https://openintention.io}"' in script
    assert 'OPENINTENTION_REPO_URL="${OPENINTENTION_REPO_URL:-https://github.com/openintention/research-os.git}"' in script
    assert 'if command -v python3.11 >/dev/null 2>&1; then' in script
    assert 'printf \'%s\\n\' "python3.11"' in script
    assert 'exec "$OPENINTENTION_VENV_DIR/bin/python" scripts/join_openintention.py --no-bootstrap "${pass_args[@]}"' in script
    assert 'exec "$OPENINTENTION_VENV_DIR/bin/python" scripts/run_nightly_contribution_window.py "${pass_args[@]}"' in script
