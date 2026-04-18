from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.models.schemas import NormalisedEvent
from backend.parser.base import (
    BaseParser,
    coerce_int,
    first_non_empty,
    infer_event_type,
    normalise_ip,
    parse_timestamp,
)


class GenericParser(BaseParser):
    parser_name = "generic"

    def parse_file(self, file_path: str | Path) -> list[NormalisedEvent]:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="replace").strip()
        if not content:
            return []

        if content.startswith("[") or content.startswith("{"):
            return self._parse_json(content)

        first_line = content.splitlines()[0]
        if "," in first_line:
            return self._parse_csv(path)

        return super().parse_file(path)

    def parse_line(self, line: str) -> NormalisedEvent:
        try:
            record = json.loads(line)
            if not isinstance(record, dict):
                return self.make_parse_error_event(line)
            return self._record_to_event(record, raw_line=line)
        except json.JSONDecodeError:
            return self.make_parse_error_event(line)

    def _parse_json(self, content: str) -> list[NormalisedEvent]:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return [self.make_parse_error_event(line) for line in content.splitlines() if line.strip()]

        if isinstance(payload, dict):
            return [self._record_to_event(payload, raw_line=json.dumps(payload))]
        if isinstance(payload, list):
            events: list[NormalisedEvent] = []
            for item in payload:
                if isinstance(item, dict):
                    events.append(self._record_to_event(item, raw_line=json.dumps(item)))
                else:
                    events.append(self.make_parse_error_event(str(item)))
            return events
        return [self.make_parse_error_event(content)]

    def _parse_csv(self, path: Path) -> list[NormalisedEvent]:
        events: list[NormalisedEvent] = []
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                events.append(self._record_to_event(row, raw_line=json.dumps(row)))
        return events

    def _record_to_event(self, record: dict[str, Any], *, raw_line: str) -> NormalisedEvent:
        timestamp_value = first_non_empty(
            [
                _stringify(record.get("timestamp")),
                _stringify(record.get("time")),
                _stringify(record.get("date")),
            ]
        )
        timestamp = parse_timestamp(timestamp_value)
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            parse_error = True
        else:
            parse_error = False

        endpoint = first_non_empty(
            [
                _stringify(record.get("endpoint")),
                _stringify(record.get("path")),
                _stringify(record.get("url")),
            ]
        )
        status_code = coerce_int(
            first_non_empty(
                [
                    _stringify(record.get("status_code")),
                    _stringify(record.get("status")),
                ]
            )
        )
        message = _stringify(record.get("message")) or ""

        event_type = first_non_empty([_stringify(record.get("event_type"))]) or infer_event_type(
            message=message,
            status_code=status_code,
            endpoint=endpoint,
        )

        return NormalisedEvent(
            timestamp=timestamp,
            source_ip=normalise_ip(
                first_non_empty(
                    [
                        _stringify(record.get("source_ip")),
                        _stringify(record.get("ip")),
                        _stringify(record.get("client_ip")),
                        _stringify(record.get("remote_addr")),
                    ]
                )
            ),
            event_type=event_type,
            user=first_non_empty([_stringify(record.get("user")), _stringify(record.get("username"))]),
            status_code=status_code,
            endpoint=endpoint,
            bytes_sent=coerce_int(
                first_non_empty(
                    [
                        _stringify(record.get("bytes_sent")),
                        _stringify(record.get("bytes")),
                        _stringify(record.get("response_bytes")),
                    ]
                )
            ),
            raw_line=raw_line,
            parse_error=parse_error,
        )


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)
