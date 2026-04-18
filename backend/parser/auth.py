from __future__ import annotations

import re

from backend.models.schemas import NormalisedEvent
from backend.parser.base import BaseParser, infer_event_type, normalise_ip, parse_timestamp


AUTH_LINE = re.compile(
    r"(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\d+:\d+:\d+)\s+"
    r"(?P<host>\S+)\s+(?P<service>\S+)\[(?P<pid>\d+)\]:\s+(?P<message>.+)"
)
FAILED_PW = re.compile(r"Failed password for (?:invalid user )?(?P<user>\S+) from (?P<ip>\S+)")
ACCEPTED_PW = re.compile(r"Accepted (?:password|publickey) for (?P<user>\S+) from (?P<ip>\S+)")
INVALID_USER = re.compile(r"Invalid user (?P<user>\S+) from (?P<ip>\S+)")
CONNECTION_CLOSED = re.compile(r"Connection closed by (?P<ip>\S+)")


class AuthLogParser(BaseParser):
    parser_name = "auth"

    def parse_line(self, line: str) -> NormalisedEvent:
        match = AUTH_LINE.match(line)
        if not match:
            return self.make_parse_error_event(line)

        timestamp = parse_timestamp(
            f"{match.group('month')} {match.group('day')} {match.group('time')}",
            allow_yearless=True,
        )
        message = match.group("message")
        if timestamp is None:
            return self.make_parse_error_event(line)

        user = None
        source_ip = "0.0.0.0"

        for pattern in (FAILED_PW, ACCEPTED_PW, INVALID_USER, CONNECTION_CLOSED):
            detail_match = pattern.search(message)
            if detail_match:
                user = detail_match.groupdict().get("user")
                source_ip = normalise_ip(detail_match.groupdict().get("ip"))
                break

        return NormalisedEvent(
            timestamp=timestamp,
            source_ip=source_ip,
            event_type=infer_event_type(message=message),
            user=user,
            status_code=None,
            endpoint=None,
            bytes_sent=None,
            raw_line=line,
            parse_error=False,
        )
