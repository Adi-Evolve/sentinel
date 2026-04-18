from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from backend.briefing.engine import enrich_anomalies_with_briefings
from backend.detection.isolation_forest import apply_isolation_forest
from backend.detection.rules import apply_rule_engine
from backend.detection.scorer import rank_anomalies
from backend.detection.spike import apply_spike_detector
from backend.features.engineer import build_feature_matrix, compute_impossible_travel_metadata
from backend.features.geoip import GeoIPResolver
from backend.features.known_bad import KnownBadIPLookup
from backend.ingestion.detector import detect_format
from backend.parser import get_parser_for_format

import backend.config as config
import backend.detection.isolation_forest as iforest_module
import backend.detection.rules as rules_module
import backend.detection.scorer as scorer_module


DATA_DIR = ROOT / "data" / "demo_logs"
OUTPUT_FILE = ROOT / "data" / "tuning_recommendations.json"


@dataclass
class Candidate:
    name: str
    values: dict[str, Any]


def set_tunable(candidate: Candidate) -> None:
    for key, value in candidate.values.items():
        setattr(config, key, value)

    # Rules module imports constants at module import time.
    rules_module.BRUTE_FORCE_THRESHOLD = config.BRUTE_FORCE_THRESHOLD
    rules_module.BRUTE_FORCE_WINDOW = config.BRUTE_FORCE_WINDOW
    rules_module.STUFFING_FAIL_THRESHOLD = config.STUFFING_FAIL_THRESHOLD
    rules_module.SCAN_ENDPOINT_THRESHOLD = config.SCAN_ENDPOINT_THRESHOLD
    rules_module.SCAN_RATE_THRESHOLD = config.SCAN_RATE_THRESHOLD
    rules_module.WINDOW_SIZE_MINUTES = config.WINDOW_SIZE_MINUTES

    # Isolation forest module constants.
    iforest_module.IF_CONTAMINATION = config.IF_CONTAMINATION
    iforest_module.IF_THRESHOLD = config.IF_THRESHOLD

    # Scorer constants.
    scorer_module.MIN_SCORE_TO_INCLUDE = config.MIN_SCORE_TO_INCLUDE
    scorer_module.KNOWN_BAD_IP_BONUS = config.KNOWN_BAD_IP_BONUS
    scorer_module.HIGH_CONFIDENCE_RULE_SCORE = config.HIGH_CONFIDENCE_RULE_SCORE


def scan_file(path: Path) -> dict:
    detected = detect_format(path)
    parser = get_parser_for_format(detected)
    events = parser.parse_file(path)

    geoip = GeoIPResolver()
    known_bad = KnownBadIPLookup()
    metadata = compute_impossible_travel_metadata(events, geoip_resolver=geoip)
    matrix = build_feature_matrix(
        events,
        geoip_resolver=geoip,
        known_bad_lookup=known_bad,
        impossible_travel_metadata=metadata,
    )
    matrix = apply_rule_engine(matrix)
    matrix = apply_isolation_forest(matrix)
    matrix = apply_spike_detector(events, matrix)
    anomalies = rank_anomalies(matrix, events, anomaly_metadata=metadata)
    anomalies, _ = enrich_anomalies_with_briefings(anomalies)

    return {
        "format": detected,
        "events": len([e for e in events if not e.parse_error]),
        "feature_rows": len(matrix),
        "anomalies": [a.to_dict() for a in anomalies],
    }


def evaluate(results: dict[str, dict]) -> tuple[float, dict[str, Any]]:
    score = 100.0
    notes: dict[str, Any] = {}

    brute = results["brute_force"]
    brute_top = (brute["anomalies"] or [{}])[0]
    if brute_top.get("rule_triggered") != "credential_stuffing":
        score -= 35
        notes["brute_force_rule_mismatch"] = brute_top.get("rule_triggered")
    if float(brute_top.get("composite_score", 0)) < 85:
        score -= 12
        notes["brute_force_score_low"] = brute_top.get("composite_score")

    travel = results["impossible_travel"]
    travel_top = (travel["anomalies"] or [{}])[0]
    if travel_top.get("rule_triggered") != "impossible_travel":
        score -= 35
        notes["impossible_travel_rule_mismatch"] = travel_top.get("rule_triggered")
    if travel_top.get("user") != "ajay.kumar":
        score -= 8
        notes["impossible_travel_user_mismatch"] = travel_top.get("user")

    noisy = results["noisy_mixed"]
    noisy_count = len(noisy["anomalies"])
    noisy_critical = sum(1 for item in noisy["anomalies"] if item.get("severity_label") == "CRITICAL")

    if noisy_count > 5:
        score -= min(20, (noisy_count - 5) * 4)
        notes["noisy_anomaly_count"] = noisy_count
    if noisy_critical > 1:
        score -= min(20, (noisy_critical - 1) * 8)
        notes["noisy_critical_count"] = noisy_critical

    notes["summary"] = {
        "brute_top_rule": brute_top.get("rule_triggered"),
        "brute_top_score": brute_top.get("composite_score"),
        "travel_top_rule": travel_top.get("rule_triggered"),
        "travel_top_user": travel_top.get("user"),
        "noisy_anomaly_count": noisy_count,
        "noisy_critical_count": noisy_critical,
    }
    return score, notes


def ensure_noisy_log() -> Path:
    path = DATA_DIR / "noisy_mixed.log"
    if path.exists():
        return path

    from scripts.generate_noisy_log import main as generate_noisy_main

    generate_noisy_main()
    return path


def main() -> int:
    brute_file = DATA_DIR / "brute_force.log"
    travel_file = DATA_DIR / "impossible_travel.log"
    noisy_file = ensure_noisy_log()

    for path in (brute_file, travel_file, noisy_file):
        if not path.exists():
            print(f"[FAIL] Missing required log file: {path}")
            return 1

    base_candidate = Candidate(
        name="baseline",
        values={
            "BRUTE_FORCE_THRESHOLD": config.BRUTE_FORCE_THRESHOLD,
            "BRUTE_FORCE_WINDOW": config.BRUTE_FORCE_WINDOW,
            "STUFFING_FAIL_THRESHOLD": config.STUFFING_FAIL_THRESHOLD,
            "IF_CONTAMINATION": config.IF_CONTAMINATION,
            "IF_THRESHOLD": config.IF_THRESHOLD,
            "MIN_SCORE_TO_INCLUDE": config.MIN_SCORE_TO_INCLUDE,
            "KNOWN_BAD_IP_BONUS": config.KNOWN_BAD_IP_BONUS,
        },
    )

    candidates = [
        base_candidate,
        Candidate(
            name="strict-noisy",
            values={
                **base_candidate.values,
                "IF_CONTAMINATION": 0.03,
                "IF_THRESHOLD": 0.65,
                "MIN_SCORE_TO_INCLUDE": 15.0,
                "KNOWN_BAD_IP_BONUS": 6.0,
            },
        ),
        Candidate(
            name="balanced-prod",
            values={
                **base_candidate.values,
                "IF_CONTAMINATION": 0.04,
                "IF_THRESHOLD": 0.62,
                "MIN_SCORE_TO_INCLUDE": 12.0,
                "KNOWN_BAD_IP_BONUS": 7.0,
                "STUFFING_FAIL_THRESHOLD": 6,
            },
        ),
        Candidate(
            name="high-sensitivity",
            values={
                **base_candidate.values,
                "IF_CONTAMINATION": 0.08,
                "IF_THRESHOLD": 0.55,
                "MIN_SCORE_TO_INCLUDE": 8.0,
                "KNOWN_BAD_IP_BONUS": 8.0,
            },
        ),
    ]

    board: list[dict[str, Any]] = []

    for candidate in candidates:
        set_tunable(candidate)
        results = {
            "brute_force": scan_file(brute_file),
            "impossible_travel": scan_file(travel_file),
            "noisy_mixed": scan_file(noisy_file),
        }
        total_score, notes = evaluate(results)
        board.append(
            {
                "name": candidate.name,
                "score": round(total_score, 2),
                "values": candidate.values,
                "notes": notes,
            }
        )

    board.sort(key=lambda item: item["score"], reverse=True)
    best = board[0]

    output = {
        "best_candidate": best,
        "leaderboard": board,
        "env_recommendation": {
            key: value for key, value in best["values"].items()
        },
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=True), encoding="utf-8")

    print("[PASS] Threshold tuning complete")
    print(f"Best candidate: {best['name']} (score {best['score']})")
    for key, value in output["env_recommendation"].items():
        print(f"{key}={value}")
    print(f"\nDetails written to: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
