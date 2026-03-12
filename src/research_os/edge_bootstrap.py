from __future__ import annotations

DEFAULT_EDGE_REPO_URL = "https://github.com/openintention/research-os.git"
DEFAULT_EDGE_CHANNEL = "main"
DEFAULT_EDGE_HOME = "$HOME/.openintention"


def edge_join_command(site_url: str) -> str:
    return f"curl -fsSL {site_url.rstrip('/')}/join | bash"


def edge_join_command_with_args(site_url: str, *args: str) -> str:
    suffix = ""
    if args:
        suffix = " -s -- " + " ".join(args)
    return f"{edge_join_command(site_url)}{suffix}"


def render_edge_bootstrap_script(
    *,
    site_url: str,
    repo_url: str = DEFAULT_EDGE_REPO_URL,
    channel: str = DEFAULT_EDGE_CHANNEL,
) -> str:
    normalized_site_url = site_url.rstrip("/")
    return f"""#!/usr/bin/env bash
set -euo pipefail

OPENINTENTION_SITE_URL="${{OPENINTENTION_SITE_URL:-{normalized_site_url}}}"
OPENINTENTION_REPO_URL="${{OPENINTENTION_REPO_URL:-{repo_url}}}"
OPENINTENTION_CHANNEL="${{OPENINTENTION_CHANNEL:-{channel}}}"
OPENINTENTION_HOME="${{OPENINTENTION_HOME:-{DEFAULT_EDGE_HOME}}}"
OPENINTENTION_REPO_DIR="${{OPENINTENTION_REPO_DIR:-$OPENINTENTION_HOME/research-os}}"
OPENINTENTION_VENV_DIR="${{OPENINTENTION_VENV_DIR:-$OPENINTENTION_HOME/.venv}}"
export PIP_DISABLE_PIP_VERSION_CHECK=1

log() {{
  printf '[openintention] %s\\n' "$1"
}}

require_command() {{
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '[openintention] required command not found: %s\\n' "$1" >&2
    exit 1
  fi
}}

resolve_python() {{
  if [ -n "${{OPENINTENTION_PYTHON:-}}" ]; then
    printf '%s\\n' "$OPENINTENTION_PYTHON"
    return 0
  fi

  if command -v python3.11 >/dev/null 2>&1; then
    printf '%s\\n' "python3.11"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    printf '%s\\n' "python3"
    return 0
  fi

  printf '[openintention] required command not found: python3.11 or python3\\n' >&2
  exit 1
}}

main() {{
  require_command git
  OPENINTENTION_PYTHON="$(resolve_python)"

  local mode="join"
  local pass_args=()
  while (($#)); do
    case "$1" in
      --nightly)
        mode="nightly"
        shift
        ;;
      *)
        pass_args+=("$1")
        shift
        ;;
    esac
  done

  mkdir -p "$OPENINTENTION_HOME"

  if [ ! -d "$OPENINTENTION_REPO_DIR/.git" ]; then
    log "cloning $OPENINTENTION_REPO_URL"
    git clone "$OPENINTENTION_REPO_URL" "$OPENINTENTION_REPO_DIR"
  fi

  cd "$OPENINTENTION_REPO_DIR"

  if [ -n "$(git status --porcelain)" ]; then
    printf '[openintention] refusing to update because %s has local changes\\n' "$OPENINTENTION_REPO_DIR" >&2
    printf '[openintention] use a dedicated edge checkout or clean the worktree before retrying\\n' >&2
    exit 1
  fi

  log "syncing edge checkout"
  git fetch --all --prune
  git checkout "$OPENINTENTION_CHANNEL"
  git pull --ff-only origin "$OPENINTENTION_CHANNEL"

  if [ ! -x "$OPENINTENTION_VENV_DIR/bin/python" ]; then
    log "creating local virtualenv"
    "$OPENINTENTION_PYTHON" -m venv "$OPENINTENTION_VENV_DIR"
  fi

  log "updating local edge environment"
  "$OPENINTENTION_VENV_DIR/bin/python" -m pip install -e .

  if [ "$mode" = "nightly" ]; then
    log "starting nightly contribution window"
    exec "$OPENINTENTION_VENV_DIR/bin/python" scripts/run_nightly_contribution_window.py "${{pass_args[@]}}"
  fi

  log "joining the hosted effort"
  exec "$OPENINTENTION_VENV_DIR/bin/python" scripts/join_openintention.py --no-bootstrap "${{pass_args[@]}}"
}}

main "$@"
"""
