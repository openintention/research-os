from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AutoresearchResult:
    commit: str
    val_bpb: float
    memory_gb: float
    status: str
    description: str


def load_results_tsv(path: str | Path) -> list[AutoresearchResult]:
    results_path = Path(path)
    with results_path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        return [
            AutoresearchResult(
                commit=row["commit"],
                val_bpb=float(row["val_bpb"]),
                memory_gb=float(row["memory_gb"]),
                status=row["status"],
                description=row["description"],
            )
            for row in rows
        ]


def commit_url(repo_url: str, commit: str) -> str:
    normalized = repo_url.rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return f"{normalized}/commit/{commit}"
