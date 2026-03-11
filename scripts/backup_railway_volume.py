from __future__ import annotations

import argparse
import base64
from pathlib import Path
import subprocess
import tarfile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download the hosted Railway /data volume as a local tar.gz archive."
    )
    parser.add_argument(
        "--service",
        default="openintention-api",
        help="Railway service name or ID for the hosted API.",
    )
    parser.add_argument(
        "--output-path",
        default="data/backups/openintention-production-data.tar.gz",
        help="Local tar.gz file to write.",
    )
    args = parser.parse_args()

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "railway",
        "ssh",
        "--service",
        args.service,
        (
            "sh -lc "
            "\"python scripts/backup_runtime_state.py "
            "--db-path /data/research_os.db "
            "--artifact-root /data/artifacts "
            "--output-path /tmp/openintention-runtime-state.tar.gz >/dev/null "
            "&& python -c "
            "'import base64, pathlib, sys; "
            "sys.stdout.write(base64.b64encode(pathlib.Path"
            "(\\\"/tmp/openintention-runtime-state.tar.gz\\\").read_bytes()).decode())'\""
        ),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    archive_bytes = base64.b64decode("".join(result.stdout.split()), validate=True)
    output_path.write_bytes(archive_bytes)
    with tarfile.open(output_path, "r:gz"):
        pass

    print(output_path)


if __name__ == "__main__":
    main()
