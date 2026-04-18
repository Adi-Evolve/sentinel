from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from typing import Any, Optional


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {key: _serialize(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


@dataclass(slots=True)
class NormalisedEvent:
    timestamp: datetime
    source_ip: str
    event_type: str
    user: Optional[str]
    status_code: Optional[int]
    endpoint: Optional[str]
    bytes_sent: Optional[int]
    raw_line: str
    parse_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class Anomaly:
    rank: int
    composite_score: float
    severity_label: str
    source_ip: str
    country_code: str
    window_start: datetime
    window_end: datetime
    rule_triggered: Optional[str]
    all_rules_fired: list[str]
    iso_score: float
    spike_score: float
    rule_score: float
    is_known_bad_ip: bool
    login_failure_count: int
    login_success_count: int
    requests_per_minute: float
    unique_endpoints: int
    user: Optional[str]
    briefing: str = ""
    briefing_source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)


@dataclass(slots=True)
class ScanResult:
    scan_id: str
    scan_timestamp: datetime
    filename: str
    detected_format: str
    total_lines: int
    parse_errors: int
    total_events: int
    unique_ips: int
    time_range_start: Optional[datetime]
    time_range_end: Optional[datetime]
    anomalies: list[Anomaly] = field(default_factory=list)
    briefing_sources: dict[str, int] = field(
        default_factory=lambda: {
            "rule-based": 0,
            "fallback": 0,
        }
    )
    processing_time_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        payload = _serialize(self)
        payload["time_range"] = {
            "start": payload.pop("time_range_start"),
            "end": payload.pop("time_range_end"),
        }
        return payload
