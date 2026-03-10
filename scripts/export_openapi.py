from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def main() -> None:
    from apps.api.main import create_app
    from research_os.settings import Settings

    settings = Settings.from_env()
    app = create_app(settings)
    spec = app.openapi()
    output = Path("spec/openapi.generated.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
