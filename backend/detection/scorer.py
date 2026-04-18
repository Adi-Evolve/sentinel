from __future__ import annotations

from collections import Counter
from datetime import timedelta

import pandas as pd

from backend.config import (
    CRITICAL_THRESHOLD,
    HIGH_CONFIDENCE_RULE_SCORE,
    IF_WEIGHT,
    KNOWN_BAD_IP_BONUS,
    MIN_SCORE_TO_INCLUDE,
    RULE_WEIGHT,
    SPIKE_WEIGHT,
    TOP_N_ANOMALIES,
    WARNING_THRESHOLD,
    WINDOW_SIZE_MINUTES,
)
from backend.models.schemas import Anomaly, NormalisedEvent


def rank_anomalies(
    feature_matrix: pd.DataFrame,
    events: list[NormalisedEvent],
    *,
    anomaly_metadata: dict[tuple[str, pd.Timestamp], dict[str, object]] | None = None,
) -> list[Anomaly]:
    if feature_matrix.empty:
        return []

    enriched = feature_matrix.copy()
    for column in ("rule_score", "iso_score", "spike_score"):
        if column not in enriched.columns:
            enriched[column] = 0.0

    enriched["composite_score"] = (
        enriched["rule_score"] * RULE_WEIGHT
        + enriched["iso_score"] * IF_WEIGHT
        + enriched["spike_score"] * SPIKE_WEIGHT
    ) * 100.0
    high_confidence_mask = enriched["rule_score"] >= HIGH_CONFIDENCE_RULE_SCORE
    if high_confidence_mask.any():
        enriched.loc[high_confidence_mask, "composite_score"] = enriched.loc[
            high_confidence_mask,
            "composite_score",
        ].combine(
            enriched.loc[high_confidence_mask, "rule_score"] * 100.0,
            max,
        )
    enriched.loc[enriched["is_known_bad_ip"], "composite_score"] = (
        enriched.loc[enriched["is_known_bad_ip"], "composite_score"] + KNOWN_BAD_IP_BONUS
    ).clip(upper=100.0)

    enriched = enriched[enriched["composite_score"] >= MIN_SCORE_TO_INCLUDE].copy()
    if enriched.empty:
        return []

    enriched["severity_label"] = enriched["composite_score"].apply(_severity_label_for_score)
    user_map = _build_primary_user_map(events)
    anomaly_metadata = anomaly_metadata or {}

    ranked = enriched.sort_values("composite_score", ascending=False).head(TOP_N_ANOMALIES).reset_index(drop=True)
    anomalies: list[Anomaly] = []
    for rank, row in enumerate(ranked.itertuples(index=False), start=1):
        key = (row.source_ip, row.window_start)
        anomalies.append(
            Anomaly(
                rank=rank,
                composite_score=round(float(row.composite_score), 2),
                severity_label=row.severity_label,
                source_ip=row.source_ip,
                country_code=row.country_code,
                window_start=row.window_start.to_pydatetime(),
                window_end=(row.window_start + timedelta(minutes=WINDOW_SIZE_MINUTES)).to_pydatetime(),
                rule_triggered=row.rule_triggered,
                all_rules_fired=list(row.all_rules_fired) if isinstance(row.all_rules_fired, list) else [],
                iso_score=round(float(getattr(row, "iso_score", 0.0)), 4),
                spike_score=round(float(getattr(row, "spike_score", 0.0)), 4),
                rule_score=round(float(getattr(row, "rule_score", 0.0)), 4),
                is_known_bad_ip=bool(row.is_known_bad_ip),
                login_failure_count=int(row.login_failure_count),
                login_success_count=int(row.login_success_count),
                requests_per_minute=round(float(row.requests_per_minute), 2),
                unique_endpoints=int(row.unique_endpoints),
                user=user_map.get(key),
                metadata=anomaly_metadata.get(key, {}),
            )
        )
    return anomalies


def _build_primary_user_map(events: list[NormalisedEvent]) -> dict[tuple[str, pd.Timestamp], str | None]:
    rows = [
        {
            "source_ip": event.source_ip,
            "window_start": pd.Timestamp(event.timestamp).floor(f"{WINDOW_SIZE_MINUTES}min"),
            "user": event.user,
        }
        for event in events
        if not event.parse_error and event.user
    ]
    if not rows:
        return {}

    df = pd.DataFrame(rows)
    mapping: dict[tuple[str, pd.Timestamp], str | None] = {}
    for key, group in df.groupby(["source_ip", "window_start"]):
        user_counts = Counter(group["user"])
        mapping[key] = user_counts.most_common(1)[0][0]
    return mapping


def _severity_label_for_score(score: float) -> str:
    if score >= CRITICAL_THRESHOLD:
        return "CRITICAL"
    if score >= WARNING_THRESHOLD:
        return "WARNING"
    return "LOW"
