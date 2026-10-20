# Render Deployment Runbook

**Last updated:** 2026-10-20  
**Target:** Render Web Service running the repository Dockerfile  
**Status:** configuration prepared and locally smoke-tested; **not deployed** because
this environment has no Render account credentials or Render CLI.

## 1. Deployment decision

Use **one Render Docker Web Service** with a **persistent disk**:

| Item | Value |
| --- | --- |
| Service type | Web Service (Docker) |
| Blueprint | `render.yaml` |
| Plan | `1c-2g` or higher (a free service cannot mount a disk) |
| Disk | 1 GB mounted at `/data` |
| Database | SQLite at `/data/tunneling.db` |
| Frontend | React build served by FastAPI from the same origin |
| Health check | `/api/health` |
| Instances | Exactly one (SQLite and in-memory rate limits are single-instance) |

A separate Render Static Site is not used. The frontend is compiled inside the
Docker build and served by FastAPI, which avoids cross-origin API configuration.
Render terminates HTTPS at its proxy.

## 2. Required configuration

`render.yaml` defines the service. Secrets are marked `sync: false` and must be
entered in the Render dashboard; they are never stored in the repository.

| Variable | Required | Purpose |
| --- | --- | --- |
| `SHIELD_ENV` | Yes (blueprint) | Set to `production`. |
| `TUNNEL_DB_URL` | Yes (blueprint) | `sqlite:////data/tunneling.db`. |
| `SHIELD_ADMIN_PASSWORD` | Yes on first empty DB | 12+ character bootstrap administrator password. Startup fails safely if absent. |
| `SHIELD_ADMIN_USERNAME` | Yes (blueprint) | Bootstrap administrator username. |
| `SHIELD_OPERATOR_PASSWORD` | Optional | 12+ character operator password. If omitted, no operator is seeded. |
| `SHIELD_OPERATOR_USERNAME` | Yes (blueprint) | Operator username. |
| `SHIELD_SEED_DEMO` | Yes (blueprint) | `true` seeds clearly labelled simulated demo telemetry; set `false` for an empty dataset. |
| `IOT_INGEST_API_KEY` | Generated | Device API key for `X-API-Key` ingestion; reveal/copy it after deployment. |
| `VITE_GOOGLE_MAPS_API_KEY` | Optional | Build-time Google Maps browser key. Missing key can break the GIS map. |
| `NVIDIA_API_KEY` / `NVIDIA_BASE_URL` / `NVIDIA_MODEL` | Optional | NVIDIA NIM assistant provider. |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | Optional | Public OpenAI-compatible provider. Do **not** use `localhost` on Render. |
| `OPENROUTER_API_KEY` | Optional | OpenRouter fallback provider. |
| `GEMINI_API_KEY` | Optional | Gemini provider. |
| `CORS_ORIGINS` | Optional | Usually unnecessary; same-origin plus `RENDER_EXTERNAL_URL` is automatic. Add only for a custom/separate frontend origin. |

Do not add `.env` to Git. Do not paste secrets into source files, logs, issues, or
the deployment report.

## 3. Build and start behavior

Render builds the repository `Dockerfile`:

1. `node:20-alpine` runs `npm ci` and `npm run build` in `frontend/`;
   `VITE_GOOGLE_MAPS_API_KEY` is injected as a Docker build argument.
2. `python:3.12-slim` installs `requirements.txt` into `/opt/venv`.
3. The runtime image copies `app/`, `scripts/`, and `frontend/dist`.
4. The start command is:

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Render injects `PORT`; the image exposes port 10000. Do not hardcode `PORT` in
`render.yaml`.

Startup runs `create_all`, creates initial accounts, and optionally seeds demo
data. A database or bootstrap failure stops startup rather than serving a
partially initialized application. Health checks execute `SELECT 1` and return
HTTP 503 when the database is unavailable.

## 4. Exact deployment steps

### 4.1 Commit and push the prepared changes

The current working tree contains uncommitted deployment hardening. Review and
push it before creating the Render Blueprint:

```powershell
git status
git diff
git add Dockerfile render.yaml .env.example README.md RENDER_DEPLOYMENT.md `
  app/config.py app/auth.py app/db.py app/main.py app/assistant.py `
  app/api/assistant_routes.py tests/test_deployment.py `
  PROJECT_STATUS.md FEATURE_INVENTORY.md IMPLEMENTATION_ROADMAP.md TEST_REPORT.md
git commit -m "Harden production deployment configuration"
git push origin master
```

Never add `.env`, database files, or secrets to the commit.

### 4.2 Create the Render Blueprint

1. Sign in to the Render Dashboard.
2. Choose **New → Blueprint**.
3. Connect the GitHub repository
   `surjithraj7/shield-os`.
4. Confirm the branch `master`.
5. Review the service `shield-os`, keep the paid `1c-2g` plan (2 GB RAM is
   appropriate for the SciPy/NumPy backend), and confirm the 1 GB disk at `/data`.
6. Render prompts for every `sync: false` value:
   - Generate and enter `SHIELD_ADMIN_PASSWORD` (at least 12 characters).
   - Enter `SHIELD_OPERATOR_PASSWORD` if an operator account is needed.
   - Enter the Maps key and AI provider keys only if those features are required.
   - Leave unused AI keys empty.
7. Apply the Blueprint and watch the first deploy.

Alternative: import the repository as a Web Service manually, select Docker,
use the repository root and `Dockerfile`, add the variables from section 2, and
add the disk. The Blueprint path is preferred because it preserves the intended
configuration.

### 4.3 Verify the deployment

Replace the placeholder with the actual service URL shown by Render. Do not
invent or publish a URL before Render provides it.

```powershell
$RENDER_URL = "https://<actual-service>.onrender.com"
Invoke-RestMethod "$RENDER_URL/api/health"
Invoke-WebRequest "$RENDER_URL/" -UseBasicParsing
```

Expected health response:

```json
{
  "status": "ok",
  "database": "ok",
  "engine": "ready",
  "environment": "production",
  "demo_seed": true
}
```

Then verify:

1. The UI loads at `/`.
2. Login with the configured administrator account succeeds.
3. `admin/admin123` is rejected with HTTP 401.
4. The IoT monitor lists seeded sensors; readings are marked `source: "simulated"`.
5. The regulatory report and alert log render.
6. Restart the service from Render and confirm the same data remains. This proves
   the disk is mounted and `TUNNEL_DB_URL` is correct.
7. Check Render logs for `Startup complete` and absence of tracebacks or secrets.

## 5. Database and persistence notes

- `create_all` creates tables; it does not migrate existing tables. A later schema
  change needs Alembic or an explicit migration plan.
- SQLite is configured with WAL, a 30-second busy timeout, foreign-key checks,
  and `pool_pre_ping`.
- Use exactly one service instance. Multiple instances sharing one SQLite disk are
  unsupported; in-memory rate limiting would also be inconsistent.
- Local `tunneling.db` data is not in Git and is not transferred by deployment.
  The Render disk starts empty and is bootstrapped from environment variables.
- Render takes an encrypted disk snapshot at least every 24 hours and retains
  snapshots for at least seven days. However, Render explicitly warns against
  restoring a disk snapshot as the recovery method for a custom database. Take
  application-level SQLite backups before schema changes and on a schedule.
- A disk-backed service cannot scale beyond one instance and loses zero-downtime
  deploys: Render briefly stops the old instance before starting the new one.
- Disk snapshots are not accessible during builds or pre-deploy commands and are
  not a substitute for a tested database backup/restore procedure.
- From the paid service Shell, an application-level SQLite backup can be created
  with Python, then copied off the service with SCP:

```bash
python -c "import sqlite3; s=sqlite3.connect('/data/tunneling.db'); d=sqlite3.connect('/data/tunneling-backup.db'); s.backup(d); d.close(); s.close()"
```


## 6. Current verification status

| Check | Status |
| --- | --- |
| `render.yaml` validated against Render's JSON schema; paid Docker plan, `/data` disk, health check | Passed locally |
| Dockerfile inspected for multi-stage build, build args, port, and start command | Verified locally |
| Production startup with a fresh SQLite database | Passed locally |
| Production health endpoint with database check | Passed locally |
| Production rejection of `admin/admin123` | Passed locally |
| Production startup without `SHIELD_ADMIN_PASSWORD` | Correctly refused |
| FastAPI serving built frontend and hashed asset | Passed locally |
| Production Uvicorn start command on a local port | Passed locally |
| Backend tests | 106 passed |
| Frontend production build | Passed, 688 modules |
| Docker image build | **Not run**; Docker is not installed |
| Render deploy, logs, disk persistence, public URL | **Not verified**; no Render credentials |

## 7. Known deployment limitations

- Render's free plan cannot attach the persistent disk; deploying with `plan:
  free` will fail.
- The service is single-instance and SQLite-backed. This is a demonstrator /
  department deployment, not an HA production database architecture.
- `SHIELD_SEED_DEMO=true` creates synthetic readings for UI demonstration. All
  such readings are labelled `source="simulated"`; they are not field data.
- Real sensors still require an HTTPS gateway, stable `event_id` values, device
  provisioning, and calibration. No MQTT/Modbus/OPC-UA adapter is included.
- AI provider calls may incur cost. Endpoints are rate-limited (30 requests per
  minute per client) but not authenticated; do not expose high-value provider keys
  without additional access control.
- The Maps browser key is baked into the public browser bundle at build time;
  restrict it by HTTP referrer in Google Cloud and expect to rebuild when it
  changes. Never place a server secret in a `VITE_*` variable.
- No password reset, MFA, account lockout, or external secret manager is
  implemented.
- This document is a prepared runbook, not evidence that Render has deployed the
  application. A public URL and Render logs must be captured after an authorized
  deployment.
