from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
TEMP_DIR = ROOT_DIR / "tmp" / "log_sentinel"
load_dotenv(ROOT_DIR / ".env")


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


SCAN_RESULTS_DIR = Path(_env_str("SCAN_RESULTS_DIR", str(DATA_DIR / "scan_results")))


# --- Ingestion ---
SAMPLE_LINES = _env_int("SAMPLE_LINES", 10)
ALLOWED_EXTENSIONS = {".log", ".txt", ".csv", ".json"}
MIN_LINES_TO_PROCESS = _env_int("MIN_LINES_TO_PROCESS", 10)
PARSE_ERROR_THRESHOLD = _env_float("PARSE_ERROR_THRESHOLD", 0.20)
SUPPORTED_FORMATS = ("apache", "auth", "syslog", "generic")

# --- Time parsing ---
DEFAULT_LOG_YEAR = datetime.now(timezone.utc).year

# --- Feature Engineering ---
WINDOW_SIZE_MINUTES = _env_int("WINDOW_SIZE_MINUTES", 5)
DBIP_COUNTRY_PATH = Path(_env_str("DBIP_COUNTRY_PATH", str(DATA_DIR / "dbip-country-lite.csv")))
GEOIP_OVERRIDE_PATH = Path(_env_str("GEOIP_OVERRIDE_PATH", str(DATA_DIR / "geoip_overrides.json")))
KNOWN_BAD_PATH = Path(_env_str("KNOWN_BAD_PATH", str(DATA_DIR / "known_bad_ips.csv")))
MIN_REQUESTS_PER_WINDOW = _env_int("MIN_REQUESTS_PER_WINDOW", 2)
RATIO_CLAMP_MAX = _env_float("RATIO_CLAMP_MAX", 100.0)
IMPOSSIBLE_TRAVEL_WINDOW_MIN = _env_int("IMPOSSIBLE_TRAVEL_WINDOW_MIN", 45)
IMPOSSIBLE_TRAVEL_MIN_DIST_KM = _env_float("IMPOSSIBLE_TRAVEL_MIN_DIST_KM", 500.0)
NIGHT_HOUR_START = _env_int("NIGHT_HOUR_START", 22)
NIGHT_HOUR_END = _env_int("NIGHT_HOUR_END", 6)

# --- Isolation Forest ---
IF_N_ESTIMATORS = _env_int("IF_N_ESTIMATORS", 100)
IF_CONTAMINATION = _env_float("IF_CONTAMINATION", 0.05)
IF_MAX_FEATURES = _env_float("IF_MAX_FEATURES", 1.0)
IF_BOOTSTRAP = _env_bool("IF_BOOTSTRAP", False)
IF_RANDOM_STATE = _env_int("IF_RANDOM_STATE", 42)
IF_THRESHOLD = _env_float("IF_THRESHOLD", 0.6)

# --- Rule Engine ---
BRUTE_FORCE_THRESHOLD = _env_int("BRUTE_FORCE_THRESHOLD", 10)
BRUTE_FORCE_WINDOW = _env_int("BRUTE_FORCE_WINDOW", 5)
STUFFING_FAIL_THRESHOLD = _env_int("STUFFING_FAIL_THRESHOLD", 5)
SCAN_ENDPOINT_THRESHOLD = _env_int("SCAN_ENDPOINT_THRESHOLD", 40)
SCAN_RATE_THRESHOLD = _env_float("SCAN_RATE_THRESHOLD", 20.0)

# --- Spike Detector ---
SPIKE_ROLLING_WINDOW = _env_int("SPIKE_ROLLING_WINDOW", 15)
SPIKE_Z_THRESHOLD = _env_float("SPIKE_Z_THRESHOLD", 3.0)
SPIKE_MIN_BASELINE_EVENTS = _env_int("SPIKE_MIN_BASELINE_EVENTS", 5)
SPIKE_SEVERITY_BASE = _env_float("SPIKE_SEVERITY_BASE", 65.0)

# --- Scoring ---
RULE_WEIGHT = _env_float("RULE_WEIGHT", 0.50)
IF_WEIGHT = _env_float("IF_WEIGHT", 0.35)
SPIKE_WEIGHT = _env_float("SPIKE_WEIGHT", 0.15)
KNOWN_BAD_IP_BONUS = _env_float("KNOWN_BAD_IP_BONUS", 8.0)
CRITICAL_THRESHOLD = _env_float("CRITICAL_THRESHOLD", 75.0)
WARNING_THRESHOLD = _env_float("WARNING_THRESHOLD", 50.0)
TOP_N_ANOMALIES = _env_int("TOP_N_ANOMALIES", 5)
MIN_SCORE_TO_INCLUDE = _env_float("MIN_SCORE_TO_INCLUDE", 10.0)
HIGH_CONFIDENCE_RULE_SCORE = _env_float("HIGH_CONFIDENCE_RULE_SCORE", 0.85)

# --- API ---
FLASK_HOST = _env_str("FLASK_HOST", "0.0.0.0")
FLASK_PORT = _env_int("FLASK_PORT", 5000)
FLASK_DEBUG = _env_bool("FLASK_DEBUG", False)
API_AUTH_TOKEN = _env_str("API_AUTH_TOKEN", "").strip()

# --- Async jobs ---
JOB_RETENTION_SECONDS = _env_int("JOB_RETENTION_SECONDS", 86400)
JOB_MAX_HISTORY = _env_int("JOB_MAX_HISTORY", 2000)

# --- Optional webhook notifier ---
WEBHOOK_NOTIFY_URL = _env_str("WEBHOOK_NOTIFY_URL", "").strip()
WEBHOOK_NOTIFY_TOKEN = _env_str("WEBHOOK_NOTIFY_TOKEN", "").strip()
WEBHOOK_NOTIFY_TIMEOUT_SECONDS = _env_int("WEBHOOK_NOTIFY_TIMEOUT_SECONDS", 3)
WEBHOOK_NOTIFY_MIN_SCORE = _env_float("WEBHOOK_NOTIFY_MIN_SCORE", 75.0)
