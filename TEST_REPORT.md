# Test Report

**Date:** 2026-10-20
**Environment:** Windows (`win32`), Python 3.14, pytest; Node.js with Vite 6.4.3
**Backend command:** `python -m pytest -o addopts="" -q -p no:warnings`
**Frontend command:** `npm run build` in `frontend/`

## 1. Summary

| Check | Result |
| --- | --- |
| Backend test suite | **106 passed**, 0 failed, 0 skipped, 82.10 s |
| New IoT/risk test module | **21 passed** |
| Deployment/config tests | **3 passed** |
| Frontend production build | **Passed**, 688 modules transformed in 8.32 s |
| Startup/import smoke | Covered by TestClient tests and lifespan usage |
| Real hardware integration | Not tested (no hardware connected) |
| Browser end-to-end | Not automated |
| Load/soak testing | Not performed |
| Coverage measurement | Not run |

## 2. New test coverage (`tests/test_iot_risk.py`)

Risk engine unit tests:

- `test_low_reading`
- `test_threshold_categories`
- `test_statistical_anomaly_detected` (includes constant-baseline step change)
- `test_unknown_sensor_type_uses_anomaly_only`
- `test_simulated_data_has_lower_confidence`
- `test_threshold_override_from_environment`

API tests:

- `test_sensor_registration_requires_admin`
- `test_unauthorized_ingest_rejected`
- `test_valid_ingest_creates_assessment_and_alert`
- `test_duplicate_event_returns_duplicate`
- `test_alert_dedupe_and_escalation`
- `test_invalid_unit_rejected`
- `test_out_of_range_rejected`
- `test_out_of_order_is_accepted_and_flagged`
- `test_alert_acknowledge_and_resolve`
- `test_alert_action_requires_authentication`
- `test_sensor_list_and_health`
- `test_simulator_is_labelled_and_creates_data`
- `test_api_key_ingestion_path`
- `test_offline_sensor_health_alert`
- `test_regulatory_report_includes_iot_risk_section`

These tests exercise registration authorization, unauth ingestion, unit/range
validation, idempotent duplicates, out-of-order flagging, alert dedupe/escalation,
lifecycle transitions, health states, offline alerts, simulator provenance, and
device API-key ingestion.

## 3. Full suite result

```text
........................................................................ [ 67%]
..................................                                       [100%]
106 passed in 82.10s (0:01:22)
```

The pre-existing suites (`test_api.py`, `test_engine.py`, `test_gemini.py`,
`test_new_api.py`, `test_new_modules.py`, `test_nvidia.py`,
`test_pinn_surrogate.py`) continued to pass after the IoT/risk additions,
report changes, and deployment hardening. Three deployment configuration tests
(`tests/test_deployment.py`) verify production credential bootstrapping and
rejection of known demo credentials.

## 4. Frontend build result

```text
vite v6.4.3 building for production...
✓ 688 modules transformed.
dist/index.html                 0.72 kB │ gzip:   0.42 kB
dist/assets/index-*.css        61.67 kB │ gzip:  14.86 kB
dist/assets/index-*.js      1,468.78 kB │ gzip: 402.38 kB
✓ built in 8.32s
```

Outcome: pass. Warning: the main JS chunk exceeds Vite's 500 kB advisory limit.
No frontend unit or browser E2E tests are configured.

## 5. Warnings observed

- FastAPI deprecation warnings for `@router.on_event("startup"/"shutdown")` in
  `app/api/websocket_routes.py`; existing code, not changed in this work.
- Google Gen AI library union-type deprecation warning in `tests/test_gemini.py`;
  dependency-level warning.
- Vite chunk-size warning described above.

No test failures or unhandled exceptions were observed.

## 6. What is not proven by this report

- Correctness of built-in risk thresholds for a real project.
- Real sensor accuracy, calibration, connectivity, or gateway behavior.
- Live AI provider responses (external calls are mocked/optional in tests).
- Multi-worker behavior, HA, backup/restore, or complete production security.
- Browser rendering, accessibility, or responsive behavior beyond a successful
  build.
- Regulatory acceptance or engineer sign-off.
- A Render deployment, public URL, or Docker image build: Docker is not installed
  locally and no Render credentials are available in this environment.

## 7. Deployment smoke checks

A production-mode (`SHIELD_ENV=production`) TestClient run against a fresh
temporary SQLite database verified:

- `/api/health` returned HTTP 200 with `database: ok`.
- `admin/admin123` login was rejected with HTTP 401.
- The configured bootstrap administrator logged in successfully.
- Seven seeded sensors were listed and the regulatory report rendered.
- FastAPI served the built frontend (`/`) and hashed JS asset successfully.
- A real Uvicorn process started in production mode on port 8765, returned
  `/api/health` with `database: ok`, and served `/` with HTTP 200.
- A fresh production database with no `SHIELD_ADMIN_PASSWORD` refused startup
  with an explicit error instead of creating a default account.

These are local process checks, not a Render runtime verification.
