"""Write the public API's OpenAPI document, which the website's TypeScript types are generated from.

    python -m scripts.export_openapi            # writes ../web/openapi.json
    python -m scripts.export_openapi out.json

Then, in web/:  npm run api:types
A test fails when web/openapi.json is out of date, so the two sides cannot drift apart unnoticed."""
import json
import os
import sys
from pathlib import Path

# Importing the app reads the settings, but nothing here opens a database connection.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://unused:unused@localhost/unused")

from app.main import app  # noqa: E402

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "web" / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    target.write_text(render(), encoding="utf-8", newline="\n")
    print(f"wrote {target}")
