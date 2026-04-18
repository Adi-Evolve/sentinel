from __future__ import annotations

import re

from backend.models.schemas import NormalisedEvent
from backend.parser.base import BaseParser, infer_event_type, normalise_ip, parse_timestamp


SYSLOG_LINE = re.compile(
    r"^<(?P<priority>\d+)>\d+\s+(?P<timestamp>\S+)\s+(?P<host>\S+)\s+"
    r"(?P<app>\S+)\s+(?P<procid>\S+)\s+(?P<msgid>\S+)\s+(?P<structured_data>-|\[[^\]]+\])\s*(?P<message>.*)$"
)
RFC3164_LINE = re.compile(
    r"^(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<app>[^:]+):\s*(?P<message>.*)$"
)
IP_PATTERN = re.compile(
    r"(?P<ip>(?:\d{1,3}(?:\.\d{1,3}){3})|(?:[0-9a-fA-F:]{2,}))"
)


class SyslogParser(BaseParser):
    parser_name = "syslog"

    def parse_line(self, line: str) -> NormalisedEvent:
        match = SYSLOG_LINE.match(line)
        if match:
            timestamp = parse_timestamp(match.group("timestamp"))
            message = match.group("message")
        else:
            legacy = RFC3164_LINE.match(line)
            if not legacy:
                return self.make_parse_error_event(line)
            timestamp = parse_timestamp(
                f"{legacy.group('month')} {legacy.group('day')} {legacy.group('time')}",
                allow_yearless=True,
            )
            message = legacy.group("message")

        if timestamp is None:
            return self.make_parse_error_event(line)

        ip_match = IP_PATTERN.search(message)
        return NormalisedEvent(
            timestamp=timestamp,
            source_ip=normalise_ip(ip_match.group("ip") if ip_match else None),
            event_type=infer_event_type(message=message),
            user=None,
            status_code=None,
            endpoint=None,
            bytes_sent=None,
            raw_line=line,
            parse_error=False,
        )
