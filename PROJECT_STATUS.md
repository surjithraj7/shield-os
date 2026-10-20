# Project Status

**Project:** Intelligent Tunneling Management Platform (SHIELD-OS)
**Repository:** `C:\Users\SURJITH RAJ\tunneling-platform`
**Status date:** 2026-10-20
**Last committed baseline:** `da07e3e` (new IoT/risk work described here is uncommitted)
**Overall state:** Working engineering demonstrator with a verified IoT ingestion,
risk-assessment, and alert-lifecycle slice. Not a certified safety system.

## 1. What the platform is

A FastAPI + SQLite backend and React/Vite desktop-style frontend for shield-tunnel
settlement prediction, monitoring, structural health, spatial clearance, TBM
advisory, AI assistance, and reporting. The UI uses a digital-twin metaphor with
draggable windows, 3D views, charts, and simulated operational feeds.

## 2. Current architecture

- Backend: Python FastAPI, SQLAlchemy 2, SQLite (`TUNNEL_DB_URL`, default
  `sqlite:///./tunneling.db`).
- Frontend: React 18, Vite 6, Three.js, Recharts; built into `frontend/dist` and
  served by FastAPI when present.
- Data: core settlement/monitoring tables plus `iot_sensors`, `sensor_readings`,
  `risk_assessments`, `alerts`, and `audit_log`.
- Auth: PBKDF2 password hashes, opaque session tokens in `auth_sessions`, bearer
  header, role checks (`admin`, `operator`, plus existing roles).
- Real-time: existing WebSocket routes for platform telemetry; IoT/alerts UI
  currently polls every 10 seconds.
- AI: optional NVIDIA NIM / OpenAI-compatible / Gemini providers; external calls
  require operator-supplied credentials.

## 3. Completed and verified in this work

1. **Explainable risk engine** (`app/risk_engine.py`)
   - Per-sensor-type threshold profiles for 15 canonical types.
   - `RISK_THRESHOLDS_JSON` environment overrides.
   - Statistical z-score anomaly detection, constant-baseline step-change
     detection, short-term trend evidence, and data-quality penalties.
   - Confidence is explicitly lower for simulated data and suspect/stale data.
   - Persists assessment evidence and recommendation; links to an alert.

2. **IoT ingestion pipeline** (`app/iot/service.py`, `app/api/iot_routes.py`)
   - Sensor registration with canonical type/unit enforcement.
   - Unit conversion for length and pressure families.
   - Numeric, finite, range, timestamp, future-time, quality, and source
     validation.
   - Idempotent ingestion by `event_id`, per-sensor duplicate protection.
   - Out-of-order readings are accepted and flagged, not silently reordered.
   - Sensor health states: `online`, `stale`, `offline`, `never_seen`.
   - Offline/stale health alerts; no background scheduler, health checks run on
     request.
   - Demo fleet of seven explicitly `source="simulated"` sensors and a simulator.

3. **Alert lifecycle** (`app/models.py`, `app/api/risk_routes.py`)
   - Persisted alerts with severity, trigger, evidence, occurrence count, source,
     line/section/ring/chainage, and timestamps.
   - Deduplication per sensor/type/rule with severity escalation.
   - `open -> acknowledged -> resolved` transitions with actor, note, audit log.
   - Summary counts are SQL aggregates, not capped client-side counts.

4. **Security controls**
   - Login rate limiting (20 requests/minute/IP).
   - Ingestion rate limiting (600/minute/IP) and write rate limiting
     (120/minute/IP).
   - `X-API-Key` device ingestion via `IOT_INGEST_API_KEY` with constant-time
     comparison; operator/admin bearer token fallback.
   - Sensor registration and demo seeding require admin.
   - CORS restricted to localhost defaults or `CORS_ORIGINS`; security headers
     added; unhandled exceptions return a generic 500 and are logged server-side.
   - Audit records for sensor registration, ingestion, simulation, seeding,
     health checks, and alert transitions.

5. **Frontend integration**
   - New `IoT Alerts` desktop window (`frontend/src/components/IotMonitor.jsx`).
   - `AlertsLog.jsx` now reads persisted alerts, shows summary counts, and
     supports acknowledge/resolve for operator/admin users.
   - New API endpoints added to `frontend/src/api.js`.
   - Static hardcoded alert sources removed from the active alert log.
   - Production build verified.

6. **Reporting**
   - HTML regulatory report now includes sensor registry, risk assessments,
     alerts, active/critical counts, and a simulated-reading count.
   - Compliance wording changed from certification claims to
     decision-support language requiring qualified-engineer review.

7. **Tests and documentation**
   - `tests/test_iot_risk.py` adds 21 unit/API tests.
   - Full backend suite: **106 passed** in 82.10 s.
   - Frontend build: **passed**, 688 modules, 1,468.78 kB JS (chunk-size warning).
   - Status, inventory, roadmap, test report, and limitations documents added.

## 4. Partially implemented or demonstrator-only

- **Real sensor hardware:** no gateway, MQTT/Modbus/OPC-UA adapter, device
  provisioning, certificate rotation, or field calibration is implemented.
  Ingestion is HTTP-only and the demo fleet is simulated.
- **Risk thresholds:** built-in profiles are demonstrator defaults, not
  project-approved control limits. They must be replaced per site.
- **Offline detection:** computed on health requests; no scheduled background
  job raises alerts when nobody calls the API.
- **Alert delivery:** in-app polling only; no SMS, email, webhook, or push.
- **TBM/3D/AI modules:** several visuals and feeds are deterministic or simulated
  demonstrations rather than live machine telemetry. See
  `FEATURE_INVENTORY.md`.
- **AI providers:** code paths exist and are tested with mocks; live provider
  quality requires API keys and is not verified by this test run.
- **Persistence:** `create_all` only; no Alembic migrations. SQLite is suitable
  for a single-instance demo, not high-availability production.
- **Auth lifecycle:** no password-change/reset endpoint, MFA, account lockout, or
  session revocation UI.

## 5. How to run

```powershell
# From the repository root
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# Frontend development
npm --prefix frontend install
npm --prefix frontend run dev

# Production frontend bundle (served by FastAPI)
npm --prefix frontend run build
python -m uvicorn app.main:app --port 8000
```

Open `http://localhost:8000/docs` for the API. Development/test startup seeds
`admin/admin123` and `operator/shield123`. Production startup refuses those
defaults and requires `SHIELD_ADMIN_PASSWORD` (12+ characters).

## 6. Recommended next milestone

Before calling this production-ready: add forced credential rotation and thresholds,
add Alembic migrations, move rate limiting to Redis, add real gateway adapters,
run site acceptance tests for each sensor type, add browser end-to-end tests, and
have a qualified tunnel engineer sign off on alarm logic. Details are in
`IMPLEMENTATION_ROADMAP.md` and `KNOWN_LIMITATIONS.md`; deployment steps and
current blockers are in `RENDER_DEPLOYMENT.md`.
