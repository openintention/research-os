from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
import json
from pathlib import Path
import shutil
import sqlite3
import tarfile
import tempfile


BACKUP_MANIFEST_NAME = "backup-manifest.json"
DB_ARCHIVE_NAME = "research_os.db"
ARTIFACT_ARCHIVE_ROOT = "artifacts"


@dataclass(frozen=True, slots=True)
class RuntimeBackupSummary:
    archive_path: str
    db_path: str
    artifact_root: str
    created_at: str


def create_runtime_backup(
    *,
    db_path: str,
    artifact_root: str,
    output_path: str,
) -> RuntimeBackupSummary:
    db_file = Path(db_path)
    artifact_dir = Path(artifact_root)
    archive_file = Path(output_path)

    if not db_file.is_file():
        raise FileNotFoundError(f"missing database file at {db_file}")
    if not artifact_dir.is_dir():
        raise FileNotFoundError(f"missing artifact root at {artifact_dir}")

    archive_file.parent.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(UTC).isoformat()

    manifest = {
        "created_at": created_at,
        "db_path": str(db_file),
        "artifact_root": str(artifact_dir),
    }

    with tempfile.TemporaryDirectory(prefix="research-os-backup-") as temp_dir:
        snapshot_path = Path(temp_dir) / DB_ARCHIVE_NAME
        _copy_sqlite_snapshot(source=db_file, destination=snapshot_path)

        with tarfile.open(archive_file, "w:gz") as archive:
            archive.add(snapshot_path, arcname=DB_ARCHIVE_NAME)
            archive.add(artifact_dir, arcname=ARTIFACT_ARCHIVE_ROOT)
            manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
            manifest_info = tarfile.TarInfo(name=BACKUP_MANIFEST_NAME)
            manifest_info.size = len(manifest_bytes)
            archive.addfile(manifest_info, BytesIO(manifest_bytes))

    return RuntimeBackupSummary(
        archive_path=str(archive_file),
        db_path=str(db_file),
        artifact_root=str(artifact_dir),
        created_at=created_at,
    )


def restore_runtime_backup(
    *,
    archive_path: str,
    db_path: str,
    artifact_root: str,
    force: bool = False,
) -> RuntimeBackupSummary:
    archive_file = Path(archive_path)
    if not archive_file.is_file():
        raise FileNotFoundError(f"missing backup archive at {archive_file}")

    db_file = Path(db_path)
    artifact_dir = Path(artifact_root)

    _ensure_restore_targets(db_file=db_file, artifact_dir=artifact_dir, force=force)

    with tempfile.TemporaryDirectory(prefix="research-os-restore-") as temp_dir:
        extract_root = Path(temp_dir)
        created_at = _extract_backup(archive_file=archive_file, extract_root=extract_root)

        extracted_db = extract_root / DB_ARCHIVE_NAME
        extracted_artifacts = extract_root / ARTIFACT_ARCHIVE_ROOT
        if not extracted_db.is_file():
            raise FileNotFoundError(f"backup archive missing {DB_ARCHIVE_NAME}")
        if not extracted_artifacts.is_dir():
            raise FileNotFoundError(f"backup archive missing {ARTIFACT_ARCHIVE_ROOT}/")

        db_file.parent.mkdir(parents=True, exist_ok=True)
        artifact_dir.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(extracted_db), str(db_file))
        shutil.move(str(extracted_artifacts), str(artifact_dir))

    return RuntimeBackupSummary(
        archive_path=str(archive_file),
        db_path=str(db_file),
        artifact_root=str(artifact_dir),
        created_at=created_at,
    )


def _ensure_restore_targets(*, db_file: Path, artifact_dir: Path, force: bool) -> None:
    artifact_exists = artifact_dir.exists() and any(artifact_dir.iterdir())
    if not force and (db_file.exists() or artifact_exists):
        raise FileExistsError(
            "restore target already contains runtime state; pass force=True to replace it"
        )

    if force and db_file.exists():
        db_file.unlink()

    if force and artifact_dir.exists():
        shutil.rmtree(artifact_dir)


def _extract_backup(*, archive_file: Path, extract_root: Path) -> str:
    created_at = ""
    with tarfile.open(archive_file, "r:gz") as archive:
        members = archive.getmembers()
        _validate_members(members)
        archive.extractall(extract_root, members=members)

    manifest_path = extract_root / BACKUP_MANIFEST_NAME
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        created_at = str(manifest.get("created_at", ""))
    return created_at


def _validate_members(members: list[tarfile.TarInfo]) -> None:
    for member in members:
        path = Path(member.name)
        if path.is_absolute():
            raise ValueError(f"backup archive contains absolute path: {member.name}")
        if ".." in path.parts:
            raise ValueError(f"backup archive contains unsafe path: {member.name}")


def _copy_sqlite_snapshot(*, source: Path, destination: Path) -> None:
    source_connection = sqlite3.connect(source)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()
