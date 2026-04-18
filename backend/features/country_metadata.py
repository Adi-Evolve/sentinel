from __future__ import annotations

import math


COUNTRY_CENTROIDS: dict[str, tuple[float, float]] = {
    "AR": (-38.41, -63.61),
    "AU": (-25.27, 133.77),
    "BD": (23.68, 90.35),
    "BR": (-14.23, -51.92),
    "CA": (56.13, -106.34),
    "CH": (46.82, 8.23),
    "CN": (35.86, 104.20),
    "DE": (51.17, 10.45),
    "ES": (40.46, -3.75),
    "FR": (46.23, 2.21),
    "GB": (55.38, -3.44),
    "HU": (47.16, 19.50),
    "ID": (-0.79, 113.92),
    "IN": (20.59, 78.96),
    "IT": (41.87, 12.57),
    "JP": (36.20, 138.25),
    "KR": (35.91, 127.77),
    "MX": (23.63, -102.55),
    "NG": (9.08, 8.68),
    "NL": (52.13, 5.29),
    "PK": (30.38, 69.35),
    "PL": (51.92, 19.15),
    "RO": (45.94, 24.97),
    "RU": (61.52, 105.32),
    "SE": (60.13, 18.64),
    "SG": (1.35, 103.82),
    "TR": (38.96, 35.24),
    "UA": (48.38, 31.17),
    "US": (37.09, -95.71),
    "ZA": (-30.56, 22.94),
}

COUNTRY_NAMES: dict[str, str] = {
    "AR": "Argentina",
    "AU": "Australia",
    "BD": "Bangladesh",
    "BR": "Brazil",
    "CA": "Canada",
    "CH": "Switzerland",
    "CN": "China",
    "DE": "Germany",
    "ES": "Spain",
    "FR": "France",
    "GB": "United Kingdom",
    "HU": "Hungary",
    "ID": "Indonesia",
    "IN": "India",
    "IT": "Italy",
    "JP": "Japan",
    "KR": "South Korea",
    "MX": "Mexico",
    "NG": "Nigeria",
    "NL": "Netherlands",
    "PK": "Pakistan",
    "PL": "Poland",
    "RO": "Romania",
    "RU": "Russia",
    "SE": "Sweden",
    "SG": "Singapore",
    "TR": "Turkey",
    "UA": "Ukraine",
    "US": "United States",
    "ZA": "South Africa",
}


class CountryMetadataLookup:
    def __init__(self) -> None:
        self._centroids = COUNTRY_CENTROIDS
        self._names = COUNTRY_NAMES

    def get_country_name(self, country_code: str) -> str:
        code = (country_code or "").upper()
        if code not in self._names:
            return country_code or "Unknown"
        return self._names[code]

    def distance_km(self, country_a: str, country_b: str) -> float | None:
        left = self._centroids.get((country_a or "").upper())
        right = self._centroids.get((country_b or "").upper())
        if not left or not right:
            return None
        return _haversine_km(left[0], left[1], right[0], right[1])


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c
