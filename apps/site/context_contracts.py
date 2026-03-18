from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class AssetContext:
    """Typed assets context shared by server and microsite renderers."""

    site_css_url: str
    site_js_url: str | None


@dataclass(frozen=True, slots=True)
class EffortIndexContext(AssetContext):
    public_api_base_url: str
    efforts: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class PublishGoalContext(AssetContext):
    pass


@dataclass(frozen=True, slots=True)
class EffortDetailContext(AssetContext):
    public_api_base_url: str
    effort: Any
    proof_surface: Any
    frontier: dict[str, object]
    lease_observations: list[Any]
    highlighted_workspace_id: str | None
    highlighted_actor_id: str | None
    highlighted_claim_id: str | None
    highlighted_reproduction_run_id: str | None
    joined: bool


class MicrositeEffortOverview(Protocol):
    title: str
    visible_participants: str
    attached_workspaces: str
    best_current_result: str
    latest_claim_signal: str
    latest_visible_handoff: str


@dataclass(frozen=True, slots=True)
class MicrositeIndexContext(AssetContext):
    participation_excerpt: str
    eval_effort: MicrositeEffortOverview
    inference_effort: MicrositeEffortOverview
    default_join_command: str
    inference_join_command: str
    styles_version: str
    scripts_version: str
    repo_url: str | None


@dataclass(frozen=True, slots=True)
class MicrositeEvidenceContext:
    markdown_path: Path
    title: str
    styles_version: str
