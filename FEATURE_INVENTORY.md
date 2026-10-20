# Feature Inventory

Status legend: **Verified** = exercised by automated tests or build; **Partial** =
implemented but only partly integrated/validated; **Demo** = simulated or
static visual; **Missing** = not implemented.

| Area | Feature | Status | Evidence / location | Notes |
| --- | --- | --- | --- | --- |
| Settlement | Mindlin immediate settlement engine | Verified | `app/engine.py`, `tests/test_engine.py` | Elastic half-space demonstrator; validate per geology |
| Settlement | Hankel-transform consolidation | Verified | `app/engine.py`, `tests/test_engine.py` | Axisymmetric demonstrator |
| Settlement | Predicted-vs-monitored evaluation | Verified | `/api/engine/evaluate`, `calculated_results` | 5% target is a benchmark, not certification |
| Data | Shield, monitoring, calculated CRUD/data routes | Verified | `app/api/routes.py`, `tests/test_api.py` | SQLite persistence |
| SHM | Structural health readings and summary | Verified | `app/api/shm_routes.py` | Simulated/seed data unless populated externally |
| Anomaly | ML anomaly scan | Verified | `app/ml/anomaly.py`, `/api/anomaly/scan` | Z-score/IQR-style screening, not failure prediction |
| Spatial | Clearance envelope analysis | Verified | `app/spatial.py`, `/api/spatial/*` | Asset table seeded |
| Ring-Eye | Optical ring scan/analysis | Partial | `app/api/ringeye_routes.py` | Algorithmic demonstrator; no live camera pipeline |
| X-RAY | Strain/safety mapping | Partial | `app/api/xray_routes.py` | Derived from existing mesh/assets |
| Autodrive | TBM parameter advisory | Partial | `app/api/autodrive_routes.py` | Advisory only; no machine control write-back |
| Grout | Hydration/impact model | Verified | `app/api/grout_routes.py`, tests | Physics demonstrator |
| Cutter | Cutter wear model | Verified | `app/ml/cutter_wear.py`, tests | Requires real cutter data for calibration |
| Experience | Experience transfer module | Partial | `app/api/experience_routes.py` | Demonstrator |
| Twin | Digital-twin/timeline endpoints | Partial | `app/api/twin_routes.py`, WebSocket routes | Visual/telemetry demo; not a full physics twin |
| Geology/GIS | Geology and GIS views | Partial | `app/api/geology_routes.py`, `gis_routes.py` | GIS map requires `VITE_GOOGLE_MAPS_API_KEY`; some layers static |
| AI | NVIDIA/OpenAI/Gemini assistant | Partial | `app/api/assistant_routes.py`, tests | Mocks verified; live provider calls need keys/quotas |
| AI | PINN surrogate | Verified | `tests/test_pinn_surrogate.py` | Research surrogate; not certified |
| Reports | HTML/PDF regulatory report | Verified | `app/report.py`, `app/api/report_routes.py`, `pdf_routes.py`, tests | Now includes IoT/risk/alerts; wording is decision-support |
| Auth | Login/session/RBAC | Verified | `app/auth.py`, `app/api/auth_routes.py`, tests | Demo credentials; no MFA/password reset |
| Security | Rate limiting | Verified | `app/security.py`, tests | In-memory, per-process only |
| Security | CORS and security headers | Verified | `app/main.py` | Configure `CORS_ORIGINS` for deployment |
| Security | Device ingestion API key | Verified | `app/security.py`, `tests/test_iot_risk.py` | Single static key; no rotation/provisioning |
| IoT | Sensor type/unit registry | Verified | `/api/iot/types`, `app/iot/service.py` | 15 canonical types |
| IoT | Sensor registration | Verified | `POST /api/iot/sensors`, tests | Admin only; simulator by default |
| IoT | Reading validation/dedupe/out-of-order | Verified | `app/iot/service.py`, tests | Event ID idempotency; flagged out-of-order |
| IoT | Health/offline alerts | Verified | `/api/iot/health*`, tests | Request-triggered; no scheduler |
| IoT | Demo data and simulator | Verified | `/api/iot/seed-demo`, `/api/iot/simulate`, tests | Always labelled `simulated` |
| Risk | Threshold + anomaly scoring | Verified | `app/risk_engine.py`, 21 IoT/risk tests | Thresholds are demo defaults |
| Risk | Per-site threshold overrides | Verified | `RISK_THRESHOLDS_JSON`, unit test | JSON env var; invalid JSON silently ignored |
| Alerts | Persisted alert log/summary | Verified | `/api/alerts*`, tests | SQL aggregates |
| Alerts | Acknowledge/resolve lifecycle | Verified | `/api/alerts/{id}/*`, tests | Audit trail; no auto-resolve |
| Alerts | Push/SMS/email delivery | Missing | - | In-app polling only |
| Alerts | Alert log UI | Verified | `frontend/src/components/AlertsLog.jsx` | Live API, 10 s polling, role-gated actions |
| IoT UI | Sensor network and simulator window | Verified | `frontend/src/components/IotMonitor.jsx` | Build verified; browser E2E not automated |
| UI | Desktop/window shell | Verified | `frontend/src/App.jsx`, `Window.jsx` | Build verified |
| UI | TBM dashboards/3D/CCTV/AR | Demo/Partial | multiple components | Several feeds are static/deterministic; not live plant data |
| Deployment | FastAPI serves built frontend | Verified | `app/main.py`, build output | Single instance |
| Deployment | Database migrations | Missing | - | `create_all` only; no Alembic |
| Deployment | Real sensor gateway adapters | Missing | - | HTTP ingestion only; no MQTT/Modbus/OPC-UA |
| Testing | Backend automated tests | Verified | `tests/` | 106 passed on 2026-10-20 |
| Testing | Frontend production build | Verified | `frontend/` | 688 modules; chunk-size warning |
| Testing | Browser E2E/load/multi-user tests | Missing | - | Not covered |
