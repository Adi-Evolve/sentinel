from __future__ import annotations

import json


def build_json_report(payload: dict) -> bytes:
    return json.dumps(payload, indent=2, ensure_ascii=True).encode("utf-8")
