# Log-Sentinel Architecture (Free-Only Edition)

## 1. Project Summary

Log-Sentinel is an offline cybersecurity log analysis system for RESONANCE 2K26. It ingests raw server logs, detects suspicious behavior using deterministic analytics, and produces ranked anomaly briefings with JSON/PDF export.

Design goals:
- zero ongoing cost
- no cloud AI APIs
- no account-gated dependencies in core setup
- explainable outputs for judges and operators

## 2. Core Pipeline

```text
Upload log
  -> format detection
  -> parser and event normalization
  -> feature engineering
  -> detection (rules + isolation forest + spike)
  -> weighted severity scoring
  -> top anomalies
  -> deterministic briefing engine
  -> dashboard + JSON/PDF exports
```

## 3. Technology Stack

- Backend: Python 3.11, Flask
- Data/ML: pandas, numpy, scikit-learn
- Export: ReportLab (with minimal fallback writer)
- Frontend: React + Vite + Chart.js
- GeoIP: DB-IP country CSV (offline file), optional override map

## 4. Detection Architecture

Three detectors run per windowed feature row:
- Rule engine: high-confidence signature conditions (brute-force, impossible travel, off-hours, recon patterns)
- Isolation Forest: unsupervised outlier score from numeric behavior features
- Spike detector: rolling-rate anomaly attribution

Composite score:

$$
S = 0.50 * R + 0.35 * I + 0.15 * P
$$

Where:
- R = normalized rule score
- I = normalized Isolation Forest anomaly score
- P = normalized spike score

Rows are sorted by S descending and surfaced as top anomalies.

## 5. Briefing Engine (Deterministic)

The briefing engine is now strictly free and deterministic:
- Tier 1: rule-based template generation
- Tier 2: deterministic fallback summary when no template applies

`briefing_source` values:
- `rule-based`
- `fallback`

There are no LLM providers, no model services, and no API keys required.

## 6. GeoIP and Country Metadata

GeoIP behavior:
- primary lookup from DB-IP CSV range file (`data/dbip-country-lite.csv`)
- binary search over preloaded IP ranges for fast offline lookups
- override map fallback (`data/geoip_overrides.json`)
- unresolved/private values map to `XX`

Country distance behavior:
- in-code country centroid dictionary (no external centroid CSV dependency)
- haversine distance for impossible-travel heuristics

## 7. API Surface (Implemented)

- `GET /api/health`
- `POST /api/scan`
- `GET /api/report/<scan_id>`
- `GET /api/export/<scan_id>/json`
- `GET /api/export/<scan_id>/pdf`
- `GET /api/scans`
- `DELETE /api/scans/<scan_id>`

Optional API protection:
- set `API_AUTH_TOKEN` to require header auth (`X-Api-Key` or `Authorization: Bearer ...`).

## 8. Data Contracts (High Level)

Normalized event includes:
- timestamp
- source_ip
- event_type
- user
- endpoint
- status_code
- raw_line

Anomaly includes:
- source_ip
- severity score
- detector flags and rule trigger
- explanation fields
- briefing and `briefing_source`

Scan result includes:
- summary metrics
- top anomalies
- timeline series
- briefing source counts

## 9. Runtime and Persistence

- scan results persisted under `data/scan_results`
- report/export endpoints can reload persisted results after restart
- history list and delete supported through scan lifecycle APIs

## 10. Deployment Notes

- local Python + Node workflows supported
- Docker compose supported for backend/frontend bring-up
- project can run fully offline once dependencies and local data files are present

## 11. Environment Variables (Current)

- `FLASK_HOST`, `FLASK_PORT`, `FLASK_DEBUG`
- `MIN_LINES_TO_PROCESS`
- `SCAN_RESULTS_DIR`
- `KNOWN_BAD_IPS_PATH`
- `DBIP_COUNTRY_PATH`
- `GEOIP_OVERRIDE_PATH`
- `API_AUTH_TOKEN` (optional)

## 12. Architectural Rationale

Why this version is hackathon-strong:
- deterministic and reproducible behavior for demos
- no paid vendor lock-in
- no fragile dependency on external LLM/network uptime
- still explainable and operator-friendly through rule templates + structured fallback
