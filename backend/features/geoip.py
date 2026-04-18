from __future__ import annotations

import csv
import ipaddress
import json
from bisect import bisect_right
from pathlib import Path

from backend.config import DBIP_COUNTRY_PATH, GEOIP_OVERRIDE_PATH


class GeoIPResolver:
    def __init__(
        self,
        db_path: str | Path | None = None,
        override_path: str | Path | None = None,
    ) -> None:
        self.db_path = Path(db_path) if db_path else DBIP_COUNTRY_PATH
        self.override_path = Path(override_path) if override_path else GEOIP_OVERRIDE_PATH
        self._overrides = self._load_overrides()
        self._ranges: list[tuple[int, int, str]] = []
        self._starts: list[int] = []
        self._load_dbip_ranges()

    @property
    def db_loaded(self) -> bool:
        return bool(self._ranges)

    @property
    def override_count(self) -> int:
        return len(self._overrides)

    def get_country(self, ip_value: str) -> str:
        if ip_value in self._overrides:
            return self._overrides[ip_value]

        try:
            ip_obj = ipaddress.ip_address(ip_value)
        except ValueError:
            return "XX"

        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_unspecified:
            return "XX"

        if not self._ranges:
            return "XX"

        try:
            ip_int = int(ip_obj)
            idx = bisect_right(self._starts, ip_int) - 1
            if idx < 0:
                return "XX"
            start, end, code = self._ranges[idx]
            if start <= ip_int <= end:
                return code
            return "XX"
        except Exception:
            return "XX"

    def close(self) -> None:
        return None

    def _load_dbip_ranges(self) -> None:
        if not self.db_path.exists():
            return

        ranges: list[tuple[int, int, str]] = []
        with self.db_path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            for row in reader:
                if len(row) < 3:
                    continue
                try:
                    start = int(ipaddress.ip_address(row[0].strip()))
                    end = int(ipaddress.ip_address(row[1].strip()))
                except ValueError:
                    continue
                country_code = row[2].strip().upper()
                if len(country_code) != 2:
                    continue
                if start > end:
                    start, end = end, start
                ranges.append((start, end, country_code))

        ranges.sort(key=lambda item: item[0])
        self._ranges = ranges
        self._starts = [item[0] for item in ranges]

    def _load_overrides(self) -> dict[str, str]:
        if not self.override_path.exists():
            return {}
        try:
            data = json.loads(self.override_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        overrides: dict[str, str] = {}
        for ip_value, country_code in data.items():
            try:
                ipaddress.ip_address(ip_value)
            except ValueError:
                continue
            code = str(country_code).strip().upper()
            if len(code) == 2:
                overrides[ip_value] = code
        return overrides
