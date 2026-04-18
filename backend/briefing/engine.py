from __future__ import annotations

from collections import Counter

from backend.briefing.templates import render_rule_based_briefing
from backend.models.schemas import Anomaly


def get_briefing(anomaly: Anomaly) -> tuple[str, str]:
    rule_based = render_rule_based_briefing(anomaly)
    if rule_based:
        return rule_based, "rule-based"

    model_reason = ""
    model_explanation = (anomaly.metadata or {}).get("model_explanation", {})
    if isinstance(model_explanation, dict):
        readable = str(model_explanation.get("human_readable") or "").strip()
        if readable:
            model_reason = f" {readable}"

    return (
        f"Anomaly detected from {anomaly.source_ip} ({anomaly.country_code}) with risk score "
        f"{anomaly.composite_score:.0f}/100. Manual review of activity between "
        f"{anomaly.window_start:%Y-%m-%d %H:%M} and {anomaly.window_end:%H:%M} UTC is advised."
        f"{model_reason}",
        "fallback",
    )


def enrich_anomalies_with_briefings(anomalies: list[Anomaly]) -> tuple[list[Anomaly], dict[str, int]]:
    briefing_sources: Counter[str] = Counter()
    for anomaly in anomalies:
        briefing, source = get_briefing(anomaly)
        anomaly.briefing = briefing
        anomaly.briefing_source = source
        briefing_sources[source] += 1

    return anomalies, {
        "rule-based": briefing_sources.get("rule-based", 0),
        "fallback": briefing_sources.get("fallback", 0),
    }
