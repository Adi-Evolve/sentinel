from __future__ import annotations

from collections import defaultdict

import pandas as pd

from backend.config import (
    SPIKE_MIN_BASELINE_EVENTS,
    SPIKE_ROLLING_WINDOW,
    SPIKE_SEVERITY_BASE,
    SPIKE_Z_THRESHOLD,
    WINDOW_SIZE_MINUTES,
)
from backend.models.schemas import NormalisedEvent


def apply_spike_detector(events: list[NormalisedEvent], feature_matrix: pd.DataFrame) -> pd.DataFrame:
    enriched = feature_matrix.copy()
    if enriched.empty:
        return _add_empty_spike_columns(enriched)

    enriched["spike_flagged"] = False
    enriched["spike_score"] = 0.0
    enriched["spike_excess_ratio"] = 0.0
    enriched["spike_peak_rate"] = 0.0
    enriched["spike_baseline_mean"] = 0.0

    valid_events = [event for event in events if not event.parse_error]
    if len(valid_events) < SPIKE_MIN_BASELINE_EVENTS:
        return enriched

    events_df = pd.DataFrame(
        [{"timestamp": event.timestamp, "source_ip": event.source_ip} for event in valid_events]
    )
    events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], utc=True)
    events_df["minute_bucket"] = events_df["timestamp"].dt.floor("1min")
    series = events_df.set_index("timestamp").resample("1min")["source_ip"].count()
    rolling_mean = series.rolling(window=SPIKE_ROLLING_WINDOW, min_periods=3).mean()
    rolling_std = series.rolling(window=SPIKE_ROLLING_WINDOW, min_periods=3).std().fillna(0)
    upper_bound = rolling_mean + (SPIKE_Z_THRESHOLD * rolling_std)

    flagged_minutes = [
        bucket_time
        for bucket_time, actual_rate in series.items()
        if not pd.isna(upper_bound.loc[bucket_time])
        and not pd.isna(rolling_mean.loc[bucket_time])
        and rolling_mean.loc[bucket_time] >= SPIKE_MIN_BASELINE_EVENTS
        and upper_bound.loc[bucket_time] > 0
        and actual_rate > upper_bound.loc[bucket_time]
    ]
    if not flagged_minutes:
        return enriched

    minute_ip_counts = events_df.groupby(["minute_bucket", "source_ip"], dropna=False).size().reset_index(name="count")
    top_ips_by_minute: dict[pd.Timestamp, list[str]] = {}
    for minute_bucket, group in minute_ip_counts.groupby("minute_bucket"):
        max_count = int(group["count"].max())
        top_ips_by_minute[minute_bucket] = group[group["count"] == max_count]["source_ip"].tolist()

    row_lookup: dict[tuple[str, pd.Timestamp], list[int]] = defaultdict(list)
    for index, row in enriched.iterrows():
        row_lookup[(row["source_ip"], row["window_start"])].append(index)

    for bucket_time in flagged_minutes:
        actual_rate = int(series.loc[bucket_time])
        threshold = float(upper_bound.loc[bucket_time])
        baseline = float(rolling_mean.loc[bucket_time])
        top_ips = top_ips_by_minute.get(bucket_time, [])
        if not top_ips:
            continue

        window_start = bucket_time.floor(f"{WINDOW_SIZE_MINUTES}min")
        excess_ratio = float(actual_rate / threshold)
        spike_score = min((SPIKE_SEVERITY_BASE * excess_ratio) / 100.0, 1.0)

        for ip_value in top_ips:
            indices = row_lookup.get((ip_value, window_start), [])
            if not indices:
                continue
            for index in indices:
                enriched.at[index, "spike_flagged"] = True
                enriched.at[index, "spike_score"] = max(float(enriched.at[index, "spike_score"]), spike_score)
                enriched.at[index, "spike_excess_ratio"] = max(
                    float(enriched.at[index, "spike_excess_ratio"]),
                    excess_ratio,
                )
                enriched.at[index, "spike_peak_rate"] = max(float(enriched.at[index, "spike_peak_rate"]), actual_rate)
                enriched.at[index, "spike_baseline_mean"] = max(
                    float(enriched.at[index, "spike_baseline_mean"]),
                    baseline,
                )

    return enriched


def _add_empty_spike_columns(feature_matrix: pd.DataFrame) -> pd.DataFrame:
    feature_matrix["spike_flagged"] = pd.Series(dtype="bool")
    feature_matrix["spike_score"] = pd.Series(dtype="float64")
    feature_matrix["spike_excess_ratio"] = pd.Series(dtype="float64")
    feature_matrix["spike_peak_rate"] = pd.Series(dtype="float64")
    feature_matrix["spike_baseline_mean"] = pd.Series(dtype="float64")
    return feature_matrix
