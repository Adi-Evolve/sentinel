from __future__ import annotations

import re

from backend.models.schemas import NormalisedEvent
from backend.parser.base import BaseParser, coerce_int, infer_event_type, normalise_ip, parse_timestamp


APACHE_COMBINED = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" '
    r'(?P<status>\d{3}) (?P<bytes>\d+|-)'
)


class ApacheParser(BaseParser):
    parser_name = "apache"

    def parse_line(self, line: str) -> NormalisedEvent:
        match = APACHE_COMBINED.match(line)
        if not match:
            return self.make_parse_error_event(line)

        timestamp = parse_timestamp(match.group("time"))
        if timestamp is None:
            return self.make_parse_error_event(line)

        status_code = coerce_int(match.group("status"))
        endpoint = match.group("path")
        return NormalisedEvent(
            timestamp=timestamp,
            source_ip=normalise_ip(match.group("ip")),
            event_type=infer_event_type(status_code=status_code, endpoint=endpoint),
            user=None,
            status_code=status_code,
            endpoint=endpoint,
            bytes_sent=coerce_int(match.group("bytes")),
            raw_line=line,
            parse_error=False,
        )
