from __future__ import annotations

import ipaddress
from pathlib import Path

from backend.config import KNOWN_BAD_PATH


class KnownBadIPLookup:
    def __init__(self, source_path: str | Path | None = None) -> None:
        self.source_path = Path(source_path) if source_path else KNOWN_BAD_PATH
        self._networks = self._load_networks()

    def _load_networks(self) -> list[object]:
        if not self.source_path.exists():
            return []

        networks: list[object] = []
        with self.source_path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw_line in handle:
                candidate = raw_line.strip()
                if not candidate or candidate.startswith("#"):
                    continue
                try:
                    networks.append(ipaddress.ip_network(candidate, strict=False))
                except ValueError:
                    continue
        return networks

    def is_bad(self, ip_value: str) -> bool:
        try:
            ip_obj = ipaddress.ip_address(ip_value)
        except ValueError:
            return False
        return any(ip_obj in network for network in self._networks)

    @property
    def total_networks(self) -> int:
        return len(self._networks)
