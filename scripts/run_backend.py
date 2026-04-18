from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import app
from backend.config import FLASK_DEBUG, FLASK_HOST, FLASK_PORT, TEMP_DIR


def main() -> None:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)


if __name__ == "__main__":
    main()
