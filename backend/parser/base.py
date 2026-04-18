from __future__ import annotations

import abc
import ipaddress
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from backend.config import DEFAULT_LOG_YEAR
from backend.models.schemas import NormalisedEvent


class BaseParser(abc.ABC):
    parser_name = "base"

    def parse_file(self, file_path: str | Path) -> list[NormalisedEvent]:
        path = Path(file_path)
        events: list[NormalisedEvent] = []
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                line = raw_line.rstrip("\n")
                if not line.strip():
                    continue
                try:
                    events.append(self.parse_line(line))
                except Exception:
                    events.append(self.make_parse_error_event(line))
        return events

    @abc.abstractmethod
    def parse_line(self, line: str) -> NormalisedEvent:
        raise NotImplementedError

    def make_parse_error_event(self, line: str) -> NormalisedEvent:
        return NormalisedEvent(
            timestamp=datetime.now(timezone.utc),
            source_ip="0.0.0.0",
            event_type="unknown",
            user=None,
            status_code=None,
            endpoint=None,
            bytes_sent=None,
            raw_line=line,
            parse_error=True,
        )


def parse_timestamp(value: str | None, *, allow_yearless: bool = False) -> Optional[datetime]:
    if not value:
        return None

    candidate = value.strip()
    if not candidate:
        return None

    iso_candidate = candidate.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(iso_candidate)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    formats = [
        "%d/%b/%Y:%H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(candidate, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue

    if allow_yearless:
        for fmt in ("%Y %b %d %H:%M:%S",):
            try:
                parsed = datetime.strptime(f"{DEFAULT_LOG_YEAR} {candidate}", fmt)
                parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.astimezone(timezone.utc)
            except ValueError:
                continue
    return None


def normalise_ip(value: str | None) -> str:
    if not value:
        return "0.0.0.0"
    stripped = value.strip("[]")
    try:
        return str(ipaddress.ip_address(stripped))
    except ValueError:
        return "0.0.0.0"


def coerce_int(value: str | int | None) -> Optional[int]:
    if value in (None, "", "-"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def infer_event_type(
    *,
    message: str = "",
    status_code: int | None = None,
    endpoint: str | None = None,
) -> str:
    text = message.lower()
    endpoint_lower = (endpoint or "").lower()

    if "failed password" in text or "invalid user" in text:
        return "login_failed"
    if "accepted password" in text or "accepted publickey" in text:
        return "login_success"
    if "connection closed" in text or "disconnected from" in text:
        return "connection_closed"
    if "sudo:" in text:
        return "sudo_attempt"
    if "service started" in text or "systemd" in text:
        return "service_start"

    if status_code in {401, 403}:
        return "login_failed" if "login" in endpoint_lower else "http_request"
    if status_code == 200 and "login" in endpoint_lower:
        return "login_success"
    if status_code is not None:
        return "http_request"
    return "unknown"


def first_non_empty(values: Iterable[Optional[str]]) -> Optional[str]:
    for value in values:
        if value:
            stripped = value.strip()
            if stripped:
                return stripped
    return None
