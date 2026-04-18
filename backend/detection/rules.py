from __future__ import annotations

import pandas as pd

from backend.config import (
    BRUTE_FORCE_WINDOW,
    BRUTE_FORCE_THRESHOLD,
    SCAN_ENDPOINT_THRESHOLD,
    SCAN_RATE_THRESHOLD,
    STUFFING_FAIL_THRESHOLD,
    WINDOW_SIZE_MINUTES,
)


RULE_DEFINITIONS = [
    {
        "rule_id": "brute_force",
        "label": "Brute force login attempt",
        "severity": 88,
        "condition": lambda row: row["login_failure_count"] >= BRUTE_FORCE_THRESHOLD
        and WINDOW_SIZE_MINUTES <= BRUTE_FORCE_WINDOW,
    },
    {
        "rule_id": "credential_stuffing",
        "label": "Credential stuffing - failures followed by success",
        "severity": 95,
        "condition": lambda row: row["login_failure_count"] >= STUFFING_FAIL_THRESHOLD
        and row["login_success_count"] >= 1,
    },
    {
        "rule_id": "off_hours_login",
        "label": "Successful login outside business hours",
        "severity": 62,
        "condition": lambda row: row["login_success_count"] >= 1 and bool(row["is_night_hour"]),
    },
    {
        "rule_id": "impossible_travel",
        "label": "Impossible travel",
        "severity": 98,
        "condition": lambda row: bool(row["impossible_travel"]),
    },
    {
        "rule_id": "port_scan",
        "label": "Reconnaissance - high unique endpoint probe count",
        "severity": 74,
        "condition": lambda row: row["unique_endpoints"] >= SCAN_ENDPOINT_THRESHOLD
        and row["requests_per_minute"] >= SCAN_RATE_THRESHOLD,
    },
]


def apply_rule_engine(feature_matrix: pd.DataFrame) -> pd.DataFrame:
    if feature_matrix.empty:
        return _add_empty_rule_columns(feature_matrix.copy())

    enriched = feature_matrix.copy()
    all_rules: list[list[str]] = []
    primary_rules: list[str | None] = []
    rule_scores: list[float] = []
    rule_flags: list[bool] = []

    for row in enriched.to_dict(orient="records"):
        fired = [rule for rule in RULE_DEFINITIONS if rule["condition"](row)]
        fired_ids = [rule["rule_id"] for rule in fired]
        highest = max(fired, key=lambda rule: rule["severity"]) if fired else None
        all_rules.append(fired_ids)
        primary_rules.append(highest["rule_id"] if highest else None)
        rule_scores.append((highest["severity"] / 100.0) if highest else 0.0)
        rule_flags.append(bool(fired))

    enriched["all_rules_fired"] = all_rules
    enriched["rule_triggered"] = primary_rules
    enriched["rule_score"] = rule_scores
    enriched["rule_flagged"] = rule_flags
    return enriched


def _add_empty_rule_columns(feature_matrix: pd.DataFrame) -> pd.DataFrame:
    feature_matrix["all_rules_fired"] = pd.Series(dtype="object")
    feature_matrix["rule_triggered"] = pd.Series(dtype="object")
    feature_matrix["rule_score"] = pd.Series(dtype="float64")
    feature_matrix["rule_flagged"] = pd.Series(dtype="bool")
    return feature_matrix
