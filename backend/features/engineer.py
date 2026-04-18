from __future__ import annotations

from datetime import timedelta

import pandas as pd

from backend.config import (
    IMPOSSIBLE_TRAVEL_WINDOW_MIN,
    IMPOSSIBLE_TRAVEL_MIN_DIST_KM,
    MIN_REQUESTS_PER_WINDOW,
    NIGHT_HOUR_END,
    NIGHT_HOUR_START,
    RATIO_CLAMP_MAX,
    WINDOW_SIZE_MINUTES,
)
from backend.features.country_metadata import CountryMetadataLookup
from backend.features.geoip import GeoIPResolver
from backend.features.known_bad import KnownBadIPLookup
from backend.models.schemas import NormalisedEvent


FEATURE_COLUMNS = [
    "source_ip",
    "window_start",
    "total_events",
    "login_failure_count",
    "login_success_count",
    "failure_success_ratio",
    "requests_per_minute",
    "unique_endpoints",
    "unique_users",
    "hour_of_day",
    "is_night_hour",
    "country_code",
    "is_known_bad_ip",
    "status_4xx_count",
    "status_5xx_count",
    "bytes_per_request",
    "impossible_travel",
]


def build_feature_matrix(
    events: list[NormalisedEvent],
    *,
    geoip_resolver: GeoIPResolver | None = None,
    known_bad_lookup: KnownBadIPLookup | None = None,
    impossible_travel_metadata: dict[tuple[str, pd.Timestamp], dict[str, object]] | None = None,
) -> pd.DataFrame:
    if not events:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    geoip_resolver = geoip_resolver or GeoIPResolver()
    known_bad_lookup = known_bad_lookup or KnownBadIPLookup()

    df = pd.DataFrame(
        [
            {
                "timestamp": event.timestamp,
                "source_ip": event.source_ip,
                "event_type": event.event_type,
                "user": event.user,
                "status_code": event.status_code,
                "endpoint": event.endpoint,
                "bytes_sent": event.bytes_sent,
                "parse_error": event.parse_error,
            }
            for event in events
            if not event.parse_error
        ]
    )

    if df.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["window_start"] = df["timestamp"].dt.floor(f"{WINDOW_SIZE_MINUTES}min")
    df["endpoint"] = df["endpoint"].fillna("")
    df["user"] = df["user"].fillna("")
    df["status_code"] = pd.to_numeric(df["status_code"], errors="coerce")
    df["bytes_sent"] = pd.to_numeric(df["bytes_sent"], errors="coerce").fillna(0)
    if impossible_travel_metadata is None:
        impossible_travel_metadata = compute_impossible_travel_metadata(events, geoip_resolver=geoip_resolver)
    impossible_travel_keys = set(impossible_travel_metadata)

    grouped = (
        df.groupby(["source_ip", "window_start"], dropna=False)
        .agg(
            total_events=("event_type", "size"),
            login_failure_count=("event_type", lambda series: int((series == "login_failed").sum())),
            login_success_count=("event_type", lambda series: int((series == "login_success").sum())),
            unique_endpoints=("endpoint", lambda series: int(series[series != ""].nunique())),
            unique_users=("user", lambda series: int(series[series != ""].nunique())),
            status_4xx_count=("status_code", lambda series: int(series.fillna(0).between(400, 499).sum())),
            status_5xx_count=("status_code", lambda series: int(series.fillna(0).between(500, 599).sum())),
            bytes_per_request=("bytes_sent", "mean"),
        )
        .reset_index()
    )

    grouped = grouped[
        grouped.apply(
            lambda row: row["total_events"] >= MIN_REQUESTS_PER_WINDOW
            or (row["source_ip"], row["window_start"]) in impossible_travel_keys,
            axis=1,
        )
    ].copy()
    if grouped.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    grouped["failure_success_ratio"] = (
        grouped["login_failure_count"] / grouped["login_success_count"].clip(lower=1)
    ).clip(upper=RATIO_CLAMP_MAX)
    grouped["requests_per_minute"] = grouped["total_events"] / float(WINDOW_SIZE_MINUTES)
    grouped["hour_of_day"] = grouped["window_start"].dt.hour
    grouped["is_night_hour"] = grouped["hour_of_day"].apply(_is_night_hour)
    grouped["country_code"] = grouped["source_ip"].map(geoip_resolver.get_country)
    grouped["is_known_bad_ip"] = grouped["source_ip"].map(known_bad_lookup.is_bad)
    grouped["impossible_travel"] = False

    if impossible_travel_keys:
        grouped["impossible_travel"] = grouped.apply(
            lambda row: (row["source_ip"], row["window_start"]) in impossible_travel_keys,
            axis=1,
        )

    grouped["bytes_per_request"] = grouped["bytes_per_request"].fillna(0).round(2)
    grouped["is_night_hour"] = grouped["is_night_hour"].astype(bool)
    grouped["is_known_bad_ip"] = grouped["is_known_bad_ip"].astype(bool)
    grouped["impossible_travel"] = grouped["impossible_travel"].astype(bool)

    return grouped[FEATURE_COLUMNS].sort_values(["window_start", "source_ip"]).reset_index(drop=True)


def _is_night_hour(hour_of_day: int) -> bool:
    return hour_of_day < NIGHT_HOUR_END or hour_of_day >= NIGHT_HOUR_START


def compute_impossible_travel_metadata(
    events: list[NormalisedEvent],
    *,
    geoip_resolver: GeoIPResolver | None = None,
    country_lookup: CountryMetadataLookup | None = None,
) -> dict[tuple[str, pd.Timestamp], dict[str, object]]:
    geoip_resolver = geoip_resolver or GeoIPResolver()
    country_lookup = country_lookup or CountryMetadataLookup()

    rows = [
        {
            "timestamp": event.timestamp,
            "source_ip": event.source_ip,
            "user": event.user,
        }
        for event in events
        if not event.parse_error and event.event_type == "login_success" and event.user
    ]
    if not rows:
        return {}

    login_df = pd.DataFrame(rows)
    login_df["timestamp"] = pd.to_datetime(login_df["timestamp"], utc=True)
    login_df["window_start"] = login_df["timestamp"].dt.floor(f"{WINDOW_SIZE_MINUTES}min")
    login_df["country_code"] = login_df["source_ip"].map(geoip_resolver.get_country)
    login_df = login_df[login_df["country_code"] != "XX"].sort_values(["user", "timestamp"])
    if login_df.empty:
        return {}

    max_gap = timedelta(minutes=IMPOSSIBLE_TRAVEL_WINDOW_MIN)
    metadata_map: dict[tuple[str, pd.Timestamp], dict[str, object]] = {}
    for _, user_rows in login_df.groupby("user"):
        previous = None
        for row in user_rows.itertuples(index=False):
            if previous is not None:
                country_changed = row.country_code != previous.country_code
                timestamp_gap = row.timestamp - previous.timestamp
                if country_changed and timestamp_gap <= max_gap:
                    distance_km = country_lookup.distance_km(previous.country_code, row.country_code)
                    if distance_km is None or distance_km < IMPOSSIBLE_TRAVEL_MIN_DIST_KM:
                        previous = row
                        continue
                    details = {
                        "impossible_travel": {
                            "country_1": country_lookup.get_country_name(previous.country_code),
                            "country_2": country_lookup.get_country_name(row.country_code),
                            "country_code_1": previous.country_code,
                            "country_code_2": row.country_code,
                            "time_1": previous.timestamp.to_pydatetime(),
                            "time_2": row.timestamp.to_pydatetime(),
                            "gap_minutes": timestamp_gap.total_seconds() / 60.0,
                            "distance_km": round(distance_km, 1),
                        }
                    }
                    metadata_map[(row.source_ip, row.window_start)] = details
                    metadata_map[(previous.source_ip, previous.window_start)] = details
            previous = row
    return metadata_map
