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

Three tables per the PRD:

| Table | Purpose |
| --- | --- |
| `shield_parameters` | Ring-by-ring TBM thrust, advance speed, torque, grouting pressure/volume, face pressure, pitch/yaw |
| `monitoring_data` | Sensor readings: measured settlement per ring/chainage per target type |
| `calculated_results` | Predicted vs monitored values, difference, relative error %, risk level |

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

Interactive docs at `http://localhost:8000/docs`.

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
python -m pytest                   # run the test suite (79 tests)
```

## Deploying

The repo ships a `Dockerfile`, `render.yaml` (Render blueprint) and
`railway.toml` (Railway) for full-stack deploys. The Docker build compiles the
React frontend and serves it from FastAPI (same origin), so `VITE_API_URL`
stays unset.

**Deploy to Render** (recommended):

1. Push this repo to GitHub.
2. In Render → New → Blueprint, point at the repo. `render.yaml` defines the
   service, health check, env vars and a 1 GB persistent disk at `/data`.
3. Set the secret env vars (`sync: false` ones): `OPENAI_API_KEY`,
   `OPENAI_BASE_URL`, `OPENAI_MODEL`, `GEMINI_API_KEY`.

**Deploy to Railway**:

1. Push this repo to GitHub.
2. In Railway → New Project → Deploy from GitHub repo.
3. `railway.toml` sets the start command and health check. Mount a volume at
   `/data` and set `TUNNEL_DB_URL=sqlite:////data/tunneling.db` so the SQLite DB
   survives restarts.

**IMPORTANT — AI relay in the cloud.** The assistant's OpenAI-compatible relay
(`http://localhost:20128/v1`) only exists on this machine. Render/Railway cannot
reach it, so for the AI copilot to work you must set `OPENAI_BASE_URL` to a
public OpenAI-compatible endpoint (and set `OPENAI_API_KEY`/`OPENAI_MODEL`).
Without one, chat falls back to the offline rule-based copilot and the rest of
the platform works normally.

## Project layout

```
app/
  main.py            FastAPI app + lifespan (table creation)
  db.py              SQLAlchemy engine/session
  models.py          ORM: ShieldParameter, MonitoringData, CalculatedResult, RingEyeReading, ...
  schemas.py         Pydantic request/response models
  risk.py            red/yellow/orange/green alarm rules
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

## AI-driven control modules (SHIELD-OS 2.0)

Four new modules move the platform from monitoring to active mitigation:

| Module | What it does |
| --- | --- |
| **AUTODRIVE.AI** | Combines the Mindlin model with the live SENSOR.EXE feed. When settlement overshoots the target, it micro-simulates and returns prioritized TBM actions (e.g. "+20 kPa face support pressure", "+0.2 m3 tail-void grout", "-5 mm/min advance speed") with expected recovery. |
| **GROUT-SIM.EXE** | Time-dependent constitutive model for two-component backfill grout: pumpable-window viscosity, early-age stiffness E(t), and a hardening S-curve. It replaces the static tail-void volume-loss with `effective_volume_loss(t)` so the first 6-24h ground loss is physically resolved. |
| **X-RAY.EXE** | Projects the Mindlin settlement trough onto nearby urban assets in the 3D twin, computes pipe bending strain (microstrain) + stress from trough curvature, classifies safe/warning/critical, and overlays a settlement heatmap + safety cones directly in the Three.js viewport. Critical assets are pushed into ALERTS.LOG. |
| **RING-EYE.EXE** | Optical/LiDAR point-cloud diffing against ideal CAD geometry. Quantifies ring ovalization ΔD, eccentricity, joint-gap opening and predicts seepage risk at ring joints before the TBM moves out of range. Scans are persisted in `ringeye_readings`. |


