from __future__ import annotations

from research_os.artifacts.local import LocalArtifactRegistry


def test_local_artifact_registry_deduplicates_by_digest(tmp_path):
    registry = LocalArtifactRegistry(tmp_path / "artifacts")

    first = registry.put_bytes(b"same artifact payload")
    second = registry.put_bytes(b"same artifact payload")

    assert first.digest == second.digest
    assert first.uri == second.uri
    assert first.size_bytes == second.size_bytes
    assert registry.exists(first.digest)
    assert registry.exists(first.uri)
    assert registry.read_bytes(first.digest) == b"same artifact payload"


def test_local_artifact_registry_resolves_content_addressed_path(tmp_path):
    registry = LocalArtifactRegistry(tmp_path / "artifacts")
    artifact = registry.put_bytes(b"snapshot bundle")

    resolved = registry.resolve(artifact.uri)

    assert resolved.exists()
    assert "sha256" in resolved.parts
    assert resolved.read_bytes() == b"snapshot bundle"
