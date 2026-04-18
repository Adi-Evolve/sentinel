from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.config import (
    IF_BOOTSTRAP,
    IF_CONTAMINATION,
    IF_MAX_FEATURES,
    IF_N_ESTIMATORS,
    IF_RANDOM_STATE,
    IF_THRESHOLD,
)


ISOLATION_FOREST_FEATURES = [
    "total_events",
    "login_failure_count",
    "login_success_count",
    "failure_success_ratio",
    "requests_per_minute",
    "unique_endpoints",
    "unique_users",
    "hour_of_day",
    "is_night_hour",
    "is_known_bad_ip",
    "status_4xx_count",
    "status_5xx_count",
    "bytes_per_request",
]


def apply_isolation_forest(feature_matrix: pd.DataFrame) -> pd.DataFrame:
    enriched = feature_matrix.copy()
    if enriched.empty:
        return _add_empty_if_columns(enriched)

    for column in ISOLATION_FOREST_FEATURES:
        if column not in enriched.columns:
            enriched[column] = 0

    if len(enriched) < 2:
        enriched["iso_score_raw"] = 0.0
        enriched["iso_score"] = 0.0
        enriched["iso_flagged"] = False
        return enriched

    X = enriched[ISOLATION_FOREST_FEATURES].copy()
    bool_columns = ["is_night_hour", "is_known_bad_ip"]
    for column in bool_columns:
        X[column] = X[column].astype(int)

    if len(enriched) < 8:
        # Isolation Forest is unstable on very small samples, so use a
        # deterministic deviation ranking until we have enough windows.
        scaled_columns = []
        for column in X.columns:
            min_value = X[column].min()
            max_value = X[column].max()
            if max_value == min_value:
                scaled_columns.append(pd.Series(0.0, index=X.index))
            else:
                scaled_columns.append((X[column] - min_value) / (max_value - min_value))
        raw_scores = pd.concat(scaled_columns, axis=1).sum(axis=1).to_numpy()
        min_score = raw_scores.min()
        max_score = raw_scores.max()
        if max_score == min_score:
            normalised = np.zeros(len(raw_scores))
        else:
            normalised = (raw_scores - min_score) / (max_score - min_score)

        enriched["iso_score_raw"] = raw_scores
        enriched["iso_score"] = normalised
        enriched["iso_flagged"] = enriched["iso_score"] > IF_THRESHOLD
        return enriched

    model = IsolationForest(
        n_estimators=IF_N_ESTIMATORS,
        contamination=IF_CONTAMINATION,
        max_features=IF_MAX_FEATURES,
        bootstrap=IF_BOOTSTRAP,
        random_state=IF_RANDOM_STATE,
    )
    model.fit(X)

    raw_scores = model.decision_function(X)
    min_score = raw_scores.min()
    max_score = raw_scores.max()
    if max_score == min_score:
        normalised = np.zeros(len(raw_scores))
    else:
        normalised = (max_score - raw_scores) / (max_score - min_score)

    enriched["iso_score_raw"] = raw_scores
    enriched["iso_score"] = normalised
    enriched["iso_flagged"] = enriched["iso_score"] > IF_THRESHOLD
    return enriched


def _add_empty_if_columns(feature_matrix: pd.DataFrame) -> pd.DataFrame:
    feature_matrix["iso_score_raw"] = pd.Series(dtype="float64")
    feature_matrix["iso_score"] = pd.Series(dtype="float64")
    feature_matrix["iso_flagged"] = pd.Series(dtype="bool")
    return feature_matrix
