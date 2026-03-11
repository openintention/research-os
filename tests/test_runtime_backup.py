from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tarfile

import pytest

from research_os.ops.runtime_backup import BACKUP_MANIFEST_NAME
from research_os.ops.runtime_backup import ARTIFACT_ARCHIVE_ROOT
from research_os.ops.runtime_backup import DB_ARCHIVE_NAME
from research_os.ops.runtime_backup import create_runtime_backup
from research_os.ops.runtime_backup import restore_runtime_backup


def test_create_runtime_backup_archives_db_artifacts_and_manifest(tmp_path: Path) -> None:
    db_path = tmp_path / "runtime" / "research_os.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _write_sqlite_marker(db_path, value="db-bytes")

    artifact_root = tmp_path / "runtime" / "artifacts"
    nested_artifact = artifact_root / "sha256" / "artifact.json"
    nested_artifact.parent.mkdir(parents=True, exist_ok=True)
    nested_artifact.write_text('{"value": 1}', encoding="utf-8")

    archive_path = tmp_path / "backups" / "runtime-state.tar.gz"
    summary = create_runtime_backup(
        db_path=str(db_path),
        artifact_root=str(artifact_root),
        output_path=str(archive_path),
    )

    assert summary.archive_path == str(archive_path)

    with tarfile.open(archive_path, "r:gz") as archive:
        names = archive.getnames()
        assert DB_ARCHIVE_NAME in names
        assert BACKUP_MANIFEST_NAME in names
        assert f"{ARTIFACT_ARCHIVE_ROOT}/sha256/artifact.json" in names

        manifest_bytes = archive.extractfile(BACKUP_MANIFEST_NAME).read()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        assert manifest["db_path"] == str(db_path)
        assert manifest["artifact_root"] == str(artifact_root)


def test_restore_runtime_backup_recreates_runtime_state(tmp_path: Path) -> None:
    source_db = tmp_path / "source" / "research_os.db"
    source_db.parent.mkdir(parents=True, exist_ok=True)
    _write_sqlite_marker(source_db, value="db-bytes")

    source_artifacts = tmp_path / "source" / "artifacts"
    source_file = source_artifacts / "sha256" / "artifact.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("artifact", encoding="utf-8")

    archive_path = tmp_path / "backup" / "runtime-state.tar.gz"
    create_runtime_backup(
        db_path=str(source_db),
        artifact_root=str(source_artifacts),
        output_path=str(archive_path),
    )

    restored_db = tmp_path / "restored" / "research_os.db"
    restored_artifacts = tmp_path / "restored" / "artifacts"
    restore_runtime_backup(
        archive_path=str(archive_path),
        db_path=str(restored_db),
        artifact_root=str(restored_artifacts),
    )

    assert _read_sqlite_marker(restored_db) == "db-bytes"
    assert (restored_artifacts / "sha256" / "artifact.txt").read_text(encoding="utf-8") == "artifact"


def test_restore_runtime_backup_requires_force_when_target_exists(tmp_path: Path) -> None:
    source_db = tmp_path / "source" / "research_os.db"
    source_db.parent.mkdir(parents=True, exist_ok=True)
    _write_sqlite_marker(source_db, value="new-db")

    source_artifacts = tmp_path / "source" / "artifacts"
    source_file = source_artifacts / "sha256" / "artifact.txt"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("new-artifact", encoding="utf-8")

    archive_path = tmp_path / "backup" / "runtime-state.tar.gz"
    create_runtime_backup(
        db_path=str(source_db),
        artifact_root=str(source_artifacts),
        output_path=str(archive_path),
    )

    restored_db = tmp_path / "restored" / "research_os.db"
    restored_db.parent.mkdir(parents=True, exist_ok=True)
    _write_sqlite_marker(restored_db, value="old-db")

    restored_artifacts = tmp_path / "restored" / "artifacts"
    restored_artifacts.mkdir(parents=True, exist_ok=True)
    (restored_artifacts / "stale.txt").write_text("stale", encoding="utf-8")

    with pytest.raises(FileExistsError):
        restore_runtime_backup(
            archive_path=str(archive_path),
            db_path=str(restored_db),
            artifact_root=str(restored_artifacts),
        )

    restore_runtime_backup(
        archive_path=str(archive_path),
        db_path=str(restored_db),
        artifact_root=str(restored_artifacts),
        force=True,
    )

    assert _read_sqlite_marker(restored_db) == "new-db"
    assert (restored_artifacts / "sha256" / "artifact.txt").read_text(encoding="utf-8") == "new-artifact"


def _write_sqlite_marker(path: Path, *, value: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("create table if not exists marker(value text)")
        connection.execute("delete from marker")
        connection.execute("insert into marker(value) values (?)", (value,))
        connection.commit()
    finally:
        connection.close()


def _read_sqlite_marker(path: Path) -> str:
    connection = sqlite3.connect(path)
    try:
        row = connection.execute("select value from marker").fetchone()
    finally:
        connection.close()
    return str(row[0])
