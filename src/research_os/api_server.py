from __future__ import annotations

import os

import uvicorn


def _port_from_env() -> int:
    port = os.getenv("PORT", "8000")
    try:
        return int(port)
    except ValueError:
        return 8000


def main() -> None:
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=_port_from_env())


if __name__ == "__main__":
    main()
