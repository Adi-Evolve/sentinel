from __future__ import annotations

from backend.parser.apache import ApacheParser
from backend.parser.auth import AuthLogParser
from backend.parser.generic import GenericParser
from backend.parser.syslog import SyslogParser
from backend.parser.universal import UniversalParser


PARSER_REGISTRY = {
    "apache": ApacheParser,
    "auth": AuthLogParser,
    "syslog": SyslogParser,
    "generic": GenericParser,
    "universal": UniversalParser,
}


def get_parser_for_format(format_name: str):
    parser_cls = PARSER_REGISTRY.get(format_name, GenericParser)
    return parser_cls()


def register_parser(name: str, parser_cls):
    """Register a new parser class."""
    PARSER_REGISTRY[name] = parser_cls


# Auto-register UniversalParser
register_parser("universal", UniversalParser)
