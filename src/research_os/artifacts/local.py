from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


_DIGEST_PREFIX = "sha256:"
_URI_PREFIX = "artifact://sha256/"


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    digest: str
    uri: str
    size_bytes: int


class LocalArtifactRegistry:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, content: bytes) -> ArtifactRecord:
        digest_hex = hashlib.sha256(content).hexdigest()
        path = self._path_for_digest_hex(digest_hex)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return ArtifactRecord(
            digest=f"{_DIGEST_PREFIX}{digest_hex}",
            uri=f"{_URI_PREFIX}{digest_hex}",
            size_bytes=path.stat().st_size,
        )

    def put_file(self, source_path: str | Path) -> ArtifactRecord:
        return self.put_bytes(Path(source_path).read_bytes())

    def exists(self, artifact_ref: str) -> bool:
        return self.resolve(artifact_ref).exists()

    def read_bytes(self, artifact_ref: str) -> bytes:
        return self.resolve(artifact_ref).read_bytes()

    def resolve(self, artifact_ref: str) -> Path:
        digest_hex = self._digest_hex_from_ref(artifact_ref)
        return self._path_for_digest_hex(digest_hex)

    def _path_for_digest_hex(self, digest_hex: str) -> Path:
        return self.root / "sha256" / digest_hex[:2] / digest_hex[2:]

    def _digest_hex_from_ref(self, artifact_ref: str) -> str:
        if artifact_ref.startswith(_URI_PREFIX):
            return artifact_ref.removeprefix(_URI_PREFIX)
        if artifact_ref.startswith(_DIGEST_PREFIX):
            return artifact_ref.removeprefix(_DIGEST_PREFIX)
        raise ValueError(f"unsupported artifact reference: {artifact_ref}")
