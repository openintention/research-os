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

from clients.tiny_loop.api import HttpResearchOSApi  # noqa: E402
from research_os.effort_lifecycle import next_proof_effort_name  # noqa: E402
from research_os.effort_lifecycle import proof_version  # noqa: E402


@dataclass(frozen=True, slots=True)
class ProofEffortRolloverResult:
    source_effort_id: str
    source_name: str
    successor_effort_id: str
    successor_name: str
    series: str
    source_version: int
    successor_version: int


def rollover_proof_effort(
    *,
    base_url: str,
    effort_id: str | None = None,
    effort_name: str | None = None,
    actor_id: str = "openintention-operator",
    reason: str = "start a new proof window",
    successor_name: str | None = None,
    successor_summary: str | None = None,
    successor_tags: dict[str, str] | None = None,
    drop_successor_tags: set[str] | None = None,
    proof_series: str | None = None,
) -> ProofEffortRolloverResult:
    api = HttpResearchOSApi(base_url.rstrip("/"))
    efforts = api.list_efforts()
    source = _select_effort(efforts, effort_id=effort_id, effort_name=effort_name)
    if source.get("successor_effort_id"):
        raise RuntimeError("proof effort already has a successor and is already historical")

    series = proof_series or str(source.get("tags", {}).get("proof_series") or source["effort_id"])
    source_version = _proof_version_from_payload(source)
    successor_version = max(
        [source_version]
        + [
            _proof_version_from_payload(item)
            for item in efforts
            if item.get("tags", {}).get("proof_series") == series
        ]
    ) + 1
    resolved_successor_name = successor_name or next_proof_effort_name(str(source["name"]), successor_version)
    resolved_successor_tags = dict(source.get("tags", {}))
    for key in drop_successor_tags or set():
        resolved_successor_tags.pop(key, None)
    resolved_successor_tags.update(successor_tags or {})
    resolved_successor_tags.update(
        {
            "public_proof": "true",
            "proof_series": series,
            "proof_version": str(successor_version),
        }
    )
    resolved_successor_tags.pop("proof_status", None)

    created = api.create_effort(
        {
            "name": resolved_successor_name,
            "objective": source["objective"],
            "platform": source["platform"],
            "budget_seconds": source["budget_seconds"],
            "summary": source.get("summary") if successor_summary is None else successor_summary,
            "tags": resolved_successor_tags,
            "actor_id": actor_id,
        }
    )
    successor_effort_id = created["effort_id"]
    api.append_event(
        {
            "kind": "effort.rolled_over",
            "aggregate_id": source["effort_id"],
            "aggregate_kind": "effort",
            "actor_id": actor_id,
            "payload": {
                "effort_id": source["effort_id"],
                "successor_effort_id": successor_effort_id,
                "proof_series": series,
                "proof_version": str(source_version),
                "reason": reason,
            },
            "tags": {
                "public_proof": "true",
                "proof_series": series,
                "proof_version": str(source_version),
                "proof_status": "historical",
            },
        }
    )

    return ProofEffortRolloverResult(
        source_effort_id=str(source["effort_id"]),
        source_name=str(source["name"]),
        successor_effort_id=str(successor_effort_id),
        successor_name=resolved_successor_name,
        series=series,
        source_version=source_version,
        successor_version=successor_version,
    )


def build_rollover_report(result: ProofEffortRolloverResult) -> str:
    return "\n".join(
        [
            "# Proof Effort Rollover Report",
            "",
            f"- Source effort: `{result.source_name}` (`{result.source_effort_id}`)",
            f"- Successor effort: `{result.successor_name}` (`{result.successor_effort_id}`)",
            f"- Proof series: `{result.series}`",
            f"- Source version: `{result.source_version}`",
            f"- Successor version: `{result.successor_version}`",
            "",
            "## Outcome",
            "- The previous proof effort remains in the immutable event log.",
            "- The previous effort is now historical and points to its successor.",
            "- New verification and public proof work should continue on the successor effort.",
        ]
    ) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a successor effort and mark the previous proof effort historical."
    )
    parser.add_argument("--base-url", required=True, help="Hosted API base URL.")
    parser.add_argument("--effort-id", help="Existing proof effort to roll over.")
    parser.add_argument("--effort-name", help="Existing proof effort name to roll over.")
    parser.add_argument("--actor-id", default="openintention-operator", help="Operator actor id.")
    parser.add_argument("--reason", default="start a new proof window", help="Human-readable rollover reason.")
    parser.add_argument("--successor-name", help="Override the successor effort display name.")
    parser.add_argument("--successor-summary", help="Override the successor effort summary.")
    parser.add_argument("--proof-series", help="Override the proof-series identifier for source and successor.")
    parser.add_argument(
        "--set-tag",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Set or override a successor effort tag. Repeatable.",
    )
    parser.add_argument(
        "--drop-tag",
        action="append",
        default=[],
        metavar="KEY",
        help="Remove a tag from the successor effort before applying overrides. Repeatable.",
    )
    parser.add_argument(
        "--output-path",
        default="data/publications/launch/proof-effort-rollover/proof-effort-rollover.md",
        help="Where to write the rollover report.",
    )
    args = parser.parse_args()
    if not args.effort_id and not args.effort_name:
        raise SystemExit("one of --effort-id or --effort-name is required")

    result = rollover_proof_effort(
        base_url=args.base_url,
        effort_id=args.effort_id,
        effort_name=args.effort_name,
        actor_id=args.actor_id,
        reason=args.reason,
        successor_name=args.successor_name,
        successor_summary=args.successor_summary,
        successor_tags=_parse_tag_assignments(args.set_tag),
        drop_successor_tags=set(args.drop_tag),
        proof_series=args.proof_series,
    )
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_rollover_report(result), encoding="utf-8")
    print(output_path)


def _select_effort(
    efforts: list[dict[str, object]],
    *,
    effort_id: str | None,
    effort_name: str | None,
) -> dict[str, object]:
    if effort_id is not None:
        for effort in efforts:
            if effort["effort_id"] == effort_id:
                return effort
        raise RuntimeError(f"unknown effort id: {effort_id}")
    if effort_name is not None:
        for effort in efforts:
            if effort["name"] == effort_name:
                return effort
        raise RuntimeError(f"unknown effort name: {effort_name}")
    raise RuntimeError("missing effort selector")


def _proof_version_from_payload(effort: dict[str, object]) -> int:
    from research_os.domain.models import EffortView  # imported lazily to reuse the canonical parser

    model = EffortView.model_validate(effort)
    return proof_version(model)


def _parse_tag_assignments(values: list[str]) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for raw in values:
        key, separator, value = raw.partition("=")
        if not separator or not key:
            raise SystemExit(f"invalid --set-tag value: {raw!r}; expected KEY=VALUE")
        assignments[key] = value
    return assignments


if __name__ == "__main__":
    main()
