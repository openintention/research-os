from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(slots=True)
class Settings:
    app_name: str = "research-os"
    db_path: str = "./data/research_os.db"
    artifact_root: str = "./data/artifacts"
    default_frontier_size: int = 10

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("RESEARCH_OS_APP_NAME", "research-os"),
            db_path=os.getenv("RESEARCH_OS_DB_PATH", "./data/research_os.db"),
            artifact_root=os.getenv("RESEARCH_OS_ARTIFACT_ROOT", "./data/artifacts"),
            default_frontier_size=int(os.getenv("RESEARCH_OS_DEFAULT_FRONTIER_SIZE", "10")),
        )

    def ensure_directories(self) -> None:
        path = Path(self.db_path)
        if path != Path(":memory:"):
            path.parent.mkdir(parents=True, exist_ok=True)
        Path(self.artifact_root).mkdir(parents=True, exist_ok=True)
