from __future__ import annotations

import re
from pathlib import Path

from backend.config import SAMPLE_LINES


APACHE_PATTERN = re.compile(r"^\d+\.\d+\.\d+\.\d+ \S+ \S+ \[")
AUTH_PATTERN = re.compile(r"(sshd\[|Failed password|Accepted password|Invalid user)")
SYSLOG_PATTERN = re.compile(r"^<\d+>")


def detect_format(file_path: str | Path) -> str:
    path = Path(file_path)
    sample: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for _ in range(SAMPLE_LINES):
            line = handle.readline()
            if not line:
                break
            stripped = line.strip()
            if stripped:
                sample.append(stripped)

    if not sample:
        return "generic"

    joined = "\n".join(sample)
    first_line = sample[0]

    if APACHE_PATTERN.search(joined):
        return "apache"
    if AUTH_PATTERN.search(joined):
        return "auth"
    if SYSLOG_PATTERN.search(first_line):
        return "syslog"
    if first_line.startswith("[") or first_line.startswith("{"):
        return "generic"
    if "," in first_line and any(token.lower() in first_line.lower() for token in ("timestamp", "ip", "user")):
        return "generic"
    return "generic"
