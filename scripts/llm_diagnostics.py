from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.briefing.engine import get_briefing
from backend.models.schemas import Anomaly


def build_sample_anomaly() -> Anomaly:
    return Anomaly(
        rank=1,
        composite_score=93.2,
        severity_label="CRITICAL",
        source_ip="185.220.101.47",
        country_code="NL",
        window_start=datetime(2026, 4, 13, 2, 31, tzinfo=timezone.utc),
        window_end=datetime(2026, 4, 13, 2, 36, tzinfo=timezone.utc),
        rule_triggered="credential_stuffing",
        all_rules_fired=["brute_force", "credential_stuffing", "off_hours_login"],
        iso_score=0.97,
        spike_score=0.4,
        rule_score=0.95,
        is_known_bad_ip=True,
        login_failure_count=47,
        login_success_count=1,
        requests_per_minute=9.4,
        unique_endpoints=2,
        user="root",
    )


def main() -> int:
    anomaly = build_sample_anomaly()
    briefing, source = get_briefing(anomaly)
    result = {
        "mode": "free-deterministic",
        "briefing_source": source,
        "ok": bool(briefing),
        "preview": briefing[:280],
    }

    print(json.dumps(result, indent=2, ensure_ascii=True))
    if result["ok"] and source in {"rule-based", "fallback"}:
        print("\n[PASS] Briefing diagnostics passed with no LLM dependencies.")
        return 0
    print("\n[FAIL] Briefing diagnostics failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
