from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.config import (
    IF_BOOTSTRAP,
    IF_CONTAMINATION,
    IF_MAX_FEATURES,
    IF_N_ESTIMATORS,
    IF_RANDOM_STATE,
    WINDOW_SIZE_MINUTES,
)
from backend.detection.isolation_forest import ISOLATION_FOREST_FEATURES
from backend.models.schemas import Anomaly


@dataclass(slots=True)
class FeatureContribution:
    feature: str
    weight: float


class IsolationForestLimeExplainer:
    """Offline explainability wrapper for Isolation Forest using LIME.

    This class keeps a local Isolation Forest model and provides per-sample
    explanation payloads with both raw feature contributions and a readable summary.
    """

    def __init__(self, training_data: pd.DataFrame, feature_names: list[str] | None = None):
        self.feature_names = feature_names or list(ISOLATION_FOREST_FEATURES)
        self.training_data = self._prepare_matrix(training_data)
        self.model: IsolationForest | None = None
        self.score_min: float = 0.0
        self.score_max: float = 1.0
        self._lime_explainer = None

    def fit(self) -> None:
        self.model = IsolationForest(
            n_estimators=IF_N_ESTIMATORS,
            contamination=IF_CONTAMINATION,
            max_features=IF_MAX_FEATURES,
            bootstrap=IF_BOOTSTRAP,
            random_state=IF_RANDOM_STATE,
        )
        self.model.fit(self.training_data)
        train_scores = -self.model.decision_function(self.training_data)
        self.score_min = float(np.min(train_scores))
        self.score_max = float(np.max(train_scores))

        # Lazy import keeps runtime resilient when lime is not installed yet.
        try:
            from lime.lime_tabular import LimeTabularExplainer

            self._lime_explainer = LimeTabularExplainer(
                self.training_data,
                feature_names=self.feature_names,
                class_names=["normal", "anomaly"],
                mode="classification",
                discretize_continuous=True,
                random_state=IF_RANDOM_STATE,
            )
        except Exception:
            self._lime_explainer = None

    def explain_anomaly(self, sample_input: dict[str, Any] | pd.Series | np.ndarray, *, num_features: int = 6) -> dict[str, Any]:
        if self.model is None:
            self.fit()

        sample = self._prepare_sample(sample_input)
        proba = self.predict_proba(sample.reshape(1, -1))[0]

        if self._lime_explainer is not None:
            explanation = self._lime_explainer.explain_instance(
                sample,
                self.predict_proba,
                num_features=min(num_features, len(self.feature_names)),
            )
            lime_pairs = explanation.as_list(label=1)
            contributions = [
                FeatureContribution(feature=str(name), weight=float(weight))
                for name, weight in lime_pairs
            ]
        else:
            contributions = self._fallback_contributions(sample, num_features=num_features)

        readable = self._human_readable_summary(contributions, anomaly_probability=float(proba[1]))
        return {
            "feature_contributions": [
                {"feature": item.feature, "weight": round(item.weight, 6)} for item in contributions
            ],
            "human_readable": readable,
            "anomaly_probability": round(float(proba[1]), 6),
            "normal_probability": round(float(proba[0]), 6),
            "method": "lime" if self._lime_explainer is not None else "fallback-zscore",
        }

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model not fitted.")

        scores = -self.model.decision_function(x)
        if self.score_max == self.score_min:
            anomaly_prob = np.full(shape=scores.shape, fill_value=0.5, dtype=float)
        else:
            anomaly_prob = (scores - self.score_min) / (self.score_max - self.score_min)
            anomaly_prob = np.clip(anomaly_prob, 0.0, 1.0)

        normal_prob = 1.0 - anomaly_prob
        return np.column_stack([normal_prob, anomaly_prob])

    def _prepare_matrix(self, frame: pd.DataFrame) -> np.ndarray:
        prepared = frame.copy()
        for column in self.feature_names:
            if column not in prepared.columns:
                prepared[column] = 0
        prepared = prepared[self.feature_names].copy()
        for bool_column in ("is_night_hour", "is_known_bad_ip"):
            if bool_column in prepared.columns:
                prepared[bool_column] = prepared[bool_column].astype(int)
        prepared = prepared.fillna(0)
        return prepared.to_numpy(dtype=float)

    def _prepare_sample(self, sample_input: dict[str, Any] | pd.Series | np.ndarray) -> np.ndarray:
        if isinstance(sample_input, np.ndarray):
            values = sample_input.astype(float)
            if values.ndim > 1:
                values = values.reshape(-1)
            if values.shape[0] != len(self.feature_names):
                raise ValueError("Sample array size does not match feature list length.")
            return values

        if isinstance(sample_input, pd.Series):
            sample_dict = sample_input.to_dict()
        else:
            sample_dict = dict(sample_input)

        ordered = []
        for feature in self.feature_names:
            value = sample_dict.get(feature, 0)
            if feature in {"is_night_hour", "is_known_bad_ip"}:
                ordered.append(float(int(bool(value))))
            else:
                ordered.append(float(value))
        return np.asarray(ordered, dtype=float)

    def _fallback_contributions(self, sample: np.ndarray, *, num_features: int) -> list[FeatureContribution]:
        baseline = self.training_data.mean(axis=0)
        spread = self.training_data.std(axis=0)
        spread[spread == 0] = 1.0
        z_scores = (sample - baseline) / spread

        indexed = [
            FeatureContribution(feature=self.feature_names[i], weight=float(z_scores[i]))
            for i in range(len(self.feature_names))
        ]
        indexed.sort(key=lambda item: abs(item.weight), reverse=True)
        return indexed[: min(num_features, len(indexed))]

    def _human_readable_summary(self, contributions: list[FeatureContribution], *, anomaly_probability: float) -> str:
        if not contributions:
            return "Model did not identify strong feature-level contributors for this sample."

        positive = [c for c in contributions if c.weight > 0]
        negative = [c for c in contributions if c.weight < 0]

        lead = (
            f"Isolation Forest estimates anomaly likelihood at {anomaly_probability * 100:.1f}% for this window. "
        )
        if positive:
            lead += "Main drivers increasing anomaly risk: "
            lead += ", ".join(f"{item.feature} ({item.weight:+.3f})" for item in positive[:3])
            lead += ". "
        if negative:
            lead += "Factors reducing anomaly risk: "
            lead += ", ".join(f"{item.feature} ({item.weight:+.3f})" for item in negative[:2])
            lead += "."
        return lead.strip()


def attach_lime_explanations(feature_matrix: pd.DataFrame, anomalies: list[Anomaly]) -> list[Anomaly]:
    if feature_matrix.empty or not anomalies:
        return anomalies

    if len(feature_matrix) < 8:
        # Too few rows for stable IF + LIME; still return deterministic fallback explanations.
        explainer = IsolationForestLimeExplainer(feature_matrix)
    else:
        explainer = IsolationForestLimeExplainer(feature_matrix)

    explainer.fit()

    lookup = {
        (row.source_ip, row.window_start): row._asdict()
        for row in feature_matrix[list(feature_matrix.columns)].itertuples(index=False)
    }

    for anomaly in anomalies:
        key = (anomaly.source_ip, pd.Timestamp(anomaly.window_start).floor(f"{WINDOW_SIZE_MINUTES}min"))
        row = lookup.get(key)
        if not row:
            continue

        lime_payload = explainer.explain_anomaly(row)
        anomaly.metadata = anomaly.metadata or {}
        anomaly.metadata["model_explanation"] = lime_payload
        anomaly.metadata["detection_flags"] = _detection_flags(anomaly)

    return anomalies


def _detection_flags(anomaly: Anomaly) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []

    if anomaly.rule_triggered:
        flags.append(
            {
                "flag": "rule_triggered",
                "why": f"Rule engine matched '{anomaly.rule_triggered}' pattern in this time window.",
            }
        )

    if anomaly.iso_score > 0:
        flags.append(
            {
                "flag": "ml_outlier",
                "why": f"Isolation Forest marked this row as outlier-like (normalized score {anomaly.iso_score:.3f}).",
            }
        )

    if anomaly.spike_score > 0:
        flags.append(
            {
                "flag": "traffic_spike",
                "why": f"Spike detector observed rate abnormality (score {anomaly.spike_score:.3f}).",
            }
        )

    if anomaly.is_known_bad_ip:
        flags.append(
            {
                "flag": "known_bad_ip",
                "why": "Source IP matched known bad CIDR intelligence list.",
            }
        )

    if anomaly.login_failure_count >= 1 and anomaly.login_success_count >= 1:
        flags.append(
            {
                "flag": "fail_then_success",
                "why": "Failed logins followed by successful login in same window increased compromise likelihood.",
            }
        )

    return flags
