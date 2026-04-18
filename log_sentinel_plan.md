# Log-Sentinel Implementation Plan (Free-Only)

## 1. Objective

Deliver a complete cybersecurity log triage product that is:
- fully offline-capable
- free to run after setup
- deterministic and explainable
- demo-ready for RESONANCE 2K26

## 2. Final Pipeline

```text
Log file upload
  -> auto format detection
  -> parser normalization
  -> feature engineering
  -> detection (rules + IF + spike)
  -> weighted severity scoring
  -> top anomaly selection
  -> deterministic briefing generation
  -> dashboard + exports + history persistence
```

## 3. Free-Only Design Commitments

- No Anthropic/Claude API
- No Ollama/local LLM runtime requirement
- No MaxMind account-gated GeoLite setup
- GeoIP from DB-IP CSV input file
- Country centroid data embedded in code

## 4. Required Local Assets

- `data/known_bad_ips.csv`
- `data/dbip-country-lite.csv` (DB-IP country-lite CSV)
- `data/geoip_overrides.json` (optional fallback map)
- demo logs under `data/demo_logs`

## 5. Feature and API Scope

Implemented API endpoints:
- `GET /api/health`
- `POST /api/scan`
- `GET /api/report/<scan_id>`
- `GET /api/export/<scan_id>/json`
- `GET /api/export/<scan_id>/pdf`
- `GET /api/scans`
- `DELETE /api/scans/<scan_id>`

UX scope:
- upload and scan flow
- timeline and risk charts
- anomaly cards with briefing source
- scan history open/delete with search
- export actions

## 6. Briefing Logic

Decision order:
1. rule template briefing (`rule-based`)
2. deterministic generic fallback (`fallback`)

No external model calls are made.

## 7. GeoIP Strategy

- Parse DB-IP CSV ranges on startup.
- Convert IP range strings to integers.
- Use binary search for lookup speed.
- Fall back to override map for key IPs.
- Return `XX` for unresolved/private addresses.

## 8. Detection and Scoring

- Rule detector for explicit attack patterns.
- Isolation Forest for statistical outliers.
- Spike detector for sudden traffic bursts.
- Composite weighted score to rank anomalies.

## 9. Testing and Verification

Mandatory checks:
- unit + acceptance tests (`python -m unittest discover -s tests`)
- frontend build (`npm run build`)
- pre-demo flow (`python scripts/pre_demo_check.py`)
- release gate (`python scripts/release_readiness.py`)

## 10. Delivery Checklist

- [x] LLM dependencies removed from runtime path
- [x] MaxMind/geoip2 removed from runtime path
- [x] DB-IP lookup implemented
- [x] Country centroid CSV dependency removed
- [x] docs updated to free-only model
- [x] run final verification after Docker Desktop installation

## 11. Post-Docker Validation Plan

After Docker Desktop is available:
1. run `python scripts/docker_smoke_test.py`
2. run `python scripts/docker_smoke_test.py --full`
3. run `python scripts/release_readiness.py --strict-docker --strict-briefing`
4. verify report generation and scan history persistence from containers
