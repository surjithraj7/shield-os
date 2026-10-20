# Intelligent Tunneling Management Platform

Digital-twin settlement engine for urban shield tunneling. Predicts ground
deformation during shield excavation with a dual-calculation engine and exposes
it through a REST API backed by a monitoring database.

## Scientific settlement engine

**Immediate settlement — Mindlin's solution.** Surface displacement from a
horizontal point load acting in an elastic half-space (Mindlin 1936) is
superposed over:
- the tunnel face thrust pressure (disc surface integral),
- shield skin friction (cylindrical shell integral),
- tail-void ground loss (volume-loss settlement trough).

Sign convention: settlement (downward) is positive.

**Long-term settlement — excess pore-water-pressure dissipation via Hankel
transforms.** The Terzaghi–Rendulic consolidation equation is solved in
axisymmetric coordinates using a 0th-order Hankel transform in the radial
direction and a Fourier sine series in depth. The Bessel integrals are closed
form, so the pore-pressure field and settlement are cheap to evaluate:

```
p(r,z,t) = sum_n A_n sin(lambda_n z) exp(-c_v lambda_n^2 t)
           * [sigma_r^2 / (2(sigma_r^2/2 + c_h t))] exp(-r^2 / (4(sigma_r^2/2 + c_h t)))

s(r,t) = m_v * integral [ p(r,z,0) - p(r,z,t) ] dz
```

**Validation target.** The model predicts within 5% of monitored settlement
(e.g. Beijing Metro Line 12: predicted 4.2 mm vs monitored 4.4 mm). With the
default calibration the engine returns ~4.40 mm against a 4.4 mm reference,
a 0.08% deviation.

## Database schema (SQLite via SQLAlchemy)

Core PRD tables plus IoT and incident tables:

| Table | Purpose |
| --- | --- |
| `shield_parameters` | Ring-by-ring TBM thrust, advance speed, torque, grouting pressure/volume, face pressure, pitch/yaw |
| `monitoring_data` | Sensor readings: measured settlement per ring/chainage per target type |
| `calculated_results` | Predicted vs monitored values, difference, relative error %, risk level |
| `iot_sensors` | Registered sensors, canonical type/unit, location, source (`simulated`/`real`), enabled flag |
| `sensor_readings` | Validated readings with event ID, sequence, quality flags, out-of-order marker |
| `risk_assessments` | Explainable score, level, evidence, recommended action, linked alert |
| `alerts` | Deduplicated alert lifecycle: open -> acknowledged -> investigating -> resolved |
| `audit_log` | Privileged actions (sensor registration, alert transitions, simulation runs) |

## API

| Endpoint | Description |
| --- | --- |
| `POST /api/engine/immediate` | Mindlin settlement trough at a station |
| `POST /api/engine/consolidation` | Hankel-transform long-term settlement over time + radial profile |
| `POST /api/engine/total` | Immediate + consolidation trough at a station and time |
| `POST /api/engine/evaluate` | Predicted vs monitored, error %, red/yellow/orange/green alarm |
| `GET /api/engine/reference/beijing-line12` | The 4.2 mm / 4.4 mm validation case |
| `POST /api/engine/calibrate` | Derive a calibration factor from a monitored value |
| `POST /api/grout/hydration` | Two-component grout hydration timeseries (viscosity, E(t), hardening, effective tail-void loss) |
| `POST /api/grout/impact` | Settlement reduction from grout-hardening vs static volume loss |
| `GET/POST /api/autodrive/advisory` | Closed-loop predict-then-control: recommended TBM parameter adjustments |
| `POST /api/ringeye/scan` | Optical ring scan -> ovalization ΔD, joint gap, seepage risk (persisted) |
| `POST /api/ringeye/analyze` | Analyze a supplied radial point cloud |
| `GET /api/ringeye/readings` / `summary` | Ring deformation history / risk summary |
| `POST /api/xray/map` | Strain + safety-cone mapping of the settlement trough onto 3D assets |
| `GET /api/xray/summary` | X-RAY alert counts for ALERTS.LOG |
| `GET/POST /api/data/shield-params` | Shield parameter rows |
| `GET/POST /api/data/monitoring` | Monitoring rows |
| `GET /api/data/calculated` | Predicted-vs-monitored results |
| `GET /api/iot/types` | Canonical sensor types and units |
| `GET/POST /api/iot/sensors` | Sensor registry (registration requires operator/admin) |
| `GET /api/iot/sensors/{id}` | Sensor detail and connectivity health |
| `GET /api/iot/readings` | Validated reading history |
| `POST /api/iot/readings` | Ingest a reading (`X-API-Key` or operator/admin bearer token) |
| `GET/POST /api/iot/health` | Fleet health summary / run connectivity check |
| `POST /api/iot/simulate` | Generate clearly labelled simulated readings |
| `POST /api/iot/seed-demo` | Idempotently seed the demo sensor fleet |
| `GET /api/risk/assessments` | Explainable risk assessments |
| `GET /api/alerts` / `summary` | Persisted alert log and counts |
| `POST /api/alerts` | Manual operator alert |
| `POST /api/alerts/{id}/acknowledge` / `resolve` | Alert lifecycle transitions |

Interactive docs at `http://localhost:8000/docs`.

## IoT ingestion and alert lifecycle

The IoT module validates canonical units, numeric range, timestamps, event IDs,
and duplicates before persisting a reading. Each reading is scored by an
explainable rules + statistical engine. Alerts are deduplicated per
sensor/rule/severity, escalate severity, increment occurrence counts, and move
through `open -> acknowledged -> investigating -> resolved` with an audit trail.
Stale or silent sensors raise offline/degraded health alerts.

```bash
curl -X POST http://localhost:8000/api/iot/readings \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $IOT_INGEST_API_KEY" \
  -d '{"sensor_id":"SM-001","value":12.4,"unit":"mm","event_id":"gw-0001"}'
```

Set `IOT_INGEST_API_KEY` to enable device-key ingestion; without it, ingestion
requires an operator/admin bearer token. `RISK_THRESHOLDS_JSON` overrides the
default moderate/high/critical thresholds. Demo and simulator data always carry
`source: "simulated"` and are not field measurements.

Security notes: development/test runs use demo accounts (`admin/admin123`,
`operator/shield123`). Production startup refuses to create them and requires
`SHIELD_ADMIN_PASSWORD` (12+ characters). CORS defaults to localhost in
development and same-origin only in production; login, ingestion, and assistant
endpoints are rate-limited in memory (single-process only).

## AI assistant (NVIDIA NIM / Kimi-k3 / OpenAI / Gemini)

The AI ASSIST copilot is powered by **NVIDIA Cloud API / NIM** (`https://integrate.api.nvidia.com/v1/chat/completions`), Moonshot AI Kimi-k3, OpenAI, or Gemini. It can answer questions, open platform modules, generate 3D designs, run data analytics, and perform multimodal Vision AI inspection of CCTV tunnel images via tool calling.

To enable NVIDIA NIM, create a `.env` file in the project root:

```bash
NVIDIA_API_KEY=nvapi-REPLACE_WITH_YOUR_KEY
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=moonshotai/kimi-k3
TRITON_SERVER_IMAGE=nvcr.io/nvidia/tritonserver:26.07-trtllm-python-py3
```

**NVIDIA Vision AI Endpoint:**
- `POST /api/assistant/nvidia/vision`: Performs multimodal vision QA on CCTV tunnel face or cutterhead images (`prompt`, `image_url`, `model`, `max_tokens`, `temperature`, `reasoning_effort`).

**OpenAI & Relay Support:**
```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=oc/big-pickle
OPENAI_BASE_URL=http://localhost:20128/v1
```

If keys are unconfigured or endpoints are unreachable, the assistant automatically falls back to the built-in offline rule-based copilot, ensuring 100% platform availability.

## Gemini copilot (image + question + QA)

The AI ASSIST copilot can also run on Google Gemini, mirroring the ChatGPT
integration and adding three generative tasks:

| Task | Endpoint | Model |
| --- | --- | --- |
| Chat / tool calling | `POST /api/assistant/gemini/chat` | `gemini-2.5-flash` |
| Image generation | `POST /api/assistant/gemini/image` | `imagen-3.0-generate-002` |
| Question generation | `POST /api/assistant/gemini/questions` | `gemini-2.5-flash` |
| Multimodal QA | `POST /api/assistant/gemini/qa` | `gemini-2.5-flash` |

To enable it, add to your `.env`:

```bash
GEMINI_API_KEY=...        # required - your Google AI Studio / Vertex key
GEMINI_MODEL=gemini-2.5-flash       # optional chat model
GEMINI_IMAGE_MODEL=imagen-3.0-generate-002   # optional image model
```

`/api/assistant/chat` prefers ChatGPT when configured, then Gemini, then the
offline rule-based copilot. Requests:

```bash
# Generate an image -> base64 PNGs
curl -X POST http://localhost:8000/api/assistant/gemini/image \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A futuristic, eco-friendly library filled with floating glowing books","aspect_ratio":"1:1"}'

# Questions from a topic -> JSON with id/question/options/correct_answer
curl -X POST http://localhost:8000/api/assistant/gemini/questions \
  -H "Content-Type: application/json" -d '{"prompt":"Photosynthesis"}'

# Multimodal QA (image_base64 optional)
curl -X POST http://localhost:8000/api/assistant/gemini/qa \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is the primary architectural style shown in this picture?","image_base64":"<base64>"}'
```

## Getting started

```bash
pip install -r requirements.txt
npm --prefix frontend run build    # build the React frontend bundle
python scripts/seed_data.py        # seed 120 rings of Beijing Line 12-style data
python -m uvicorn app.main:app --port 8000  # start server (serves API + UI on :8000)
python -m pytest                   # run the test suite (106 tests)
```

## Deploying

The repository ships a production Dockerfile plus `render.yaml` (Render
Blueprint) and `railway.toml` (Railway). The Docker build compiles the React
frontend and FastAPI serves it from the same origin, so `VITE_API_URL` stays
unset. See [`RENDER_DEPLOYMENT.md`](RENDER_DEPLOYMENT.md) for the full Render
runbook, verification commands, and current deployment status.

**Render requirements**

- Use a paid Web Service plan (`1c-2g` or higher). A persistent disk cannot be
  attached to Render's free plan.
- Mount a 1 GB disk at `/data` and keep
  `TUNNEL_DB_URL=sqlite:////data/tunneling.db`.
- Set `SHIELD_ADMIN_PASSWORD` as a secret before the first deploy. Startup fails
  safely if it is missing rather than creating `admin123`.
- Optionally set `SHIELD_OPERATOR_PASSWORD`, `VITE_GOOGLE_MAPS_API_KEY` (baked at
  build time), AI provider keys, and `IOT_INGEST_API_KEY`.
- Demo telemetry is enabled by `SHIELD_SEED_DEMO=true`; every simulated reading
  remains labelled `source="simulated"`. Set it to `false` for an empty dataset.

**IMPORTANT - AI relay in the cloud.** The assistant's default local
OpenAI-compatible relay (`http://localhost:20128/v1`) only exists on a developer
machine. Render cannot reach it. Set `OPENAI_BASE_URL` to a public endpoint (and
`OPENAI_API_KEY`/`OPENAI_MODEL`) or configure NVIDIA/Gemini. Without a provider,
chat falls back to the offline rule-based copilot and the rest of the platform
works normally.

**Railway**: create a project from the GitHub repo, mount a volume at `/data`,
set `TUNNEL_DB_URL=sqlite:////data/tunneling.db` and `SHIELD_ENV=production`,
then provide the same bootstrap secrets described above.

## Project layout

```
app/
  main.py            FastAPI app + lifespan (table creation)
  db.py              SQLAlchemy engine/session
  models.py          ORM: settlement, SHM, IoT sensors/readings, risk, alert, audit tables
  schemas.py         Pydantic request/response models
  risk.py            legacy red/yellow/orange/green settlement alarm rules
  risk_engine.py     explainable IoT threshold/statistical risk engine
  iot/service.py     sensor registry, validation, dedupe, health, simulation
  security.py        rate limiting and device API-key verification
  audit.py           audit-log helper
  engine/
    mindlin.py       immediate settlement (Mindlin superposition)
    consolidation.py long-term consolidation (Hankel-transform pore-pressure dissipation)
    orchestrator.py  fusion, calibration, error metrics, validation reference
    grout.py         GROUT-SIM: time-dependent two-component grout hydration model
    autodrive.py     AUTODRIVE.AI: closed-loop predict-then-control advisory engine
    ringeye.py       RING-EYE: optical ring ovalization / joint-gap / seepage analysis
    xray.py          X-RAY: settlement-strain mapping onto 3D urban assets
  ml/anomaly.py      rolling-zscore anomaly detection
  api/               REST endpoints (incl. grout, autodrive, ringeye, xray routers)
scripts/seed_data.py sample data generator
tests/               pytest suite
```

## Monitoring and advisory modules (SHIELD-OS 2.0)

These modules extend the platform with analysis and engineering advisories. They
do not command TBM machinery directly.

| Module | What it does |
| --- | --- |
| **AUTODRIVE.AI** | Combines the Mindlin model with available monitoring data. When settlement overshoots the target, it micro-simulates and returns prioritized advisory TBM actions (e.g. "+20 kPa face support pressure", "+0.2 m3 tail-void grout", "-5 mm/min advance speed") with expected recovery. It does not write to machine controls. |
| **GROUT-SIM.EXE** | Time-dependent constitutive model for two-component backfill grout: pumpable-window viscosity, early-age stiffness E(t), and a hardening S-curve. It replaces the static tail-void volume-loss with `effective_volume_loss(t)` so the first 6-24h ground loss is physically resolved. |
| **X-RAY.EXE** | Projects the Mindlin settlement trough onto nearby urban assets in the 3D twin, computes pipe bending strain (microstrain) + stress from trough curvature, classifies safe/warning/critical, and overlays a settlement heatmap + safety cones directly in the Three.js viewport. Results are advisory and do not automatically create persisted IoT alerts. |
| **RING-EYE.EXE** | Optical/LiDAR point-cloud diffing against ideal CAD geometry. Quantifies ring ovalization ΔD, eccentricity, joint-gap opening and predicts seepage risk at ring joints before the TBM moves out of range. Scans are persisted in `ringeye_readings`. |


