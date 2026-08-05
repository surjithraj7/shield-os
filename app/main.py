from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.anomaly_routes import router as anomaly_router
from app.api.assistant_routes import router as assistant_router
from app.api.auth_routes import router as auth_router
from app.api.autodrive_routes import router as autodrive_router
from app.api.experience_routes import router as experience_router
from app.api.grout_routes import router as grout_router
from app.api.model_routes import router as model_router
from app.api.report_routes import router as report_router
from app.api.ringeye_routes import router as ringeye_router
from app.api.routes import router
from app.api.shm_routes import router as shm_router
from app.api.spatial_routes import router as spatial_router
from app.api.twin_routes import router as twin_router
from app.api.xray_routes import router as xray_router
from app.auth import seed_users
from app.db import SessionLocal, init_db
from app.seed_advanced import seed_advanced

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STATIC_CANDIDATES = [
    os.path.join(_REPO_ROOT, "frontend", "dist"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
]
STATIC_DIR = next((d for d in _STATIC_CANDIDATES if os.path.isdir(d)), _STATIC_CANDIDATES[0])


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_users(db)
        seed_advanced(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Intelligent Tunneling Management Platform",
    version="0.1.0",
    description=(
        "Digital-twin settlement engine for urban shield tunneling. "
        "Immediate settlement via Mindlin's solution + long-term consolidation "
        "via excess-pore-pressure dissipation using Hankel transforms."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router)
app.include_router(twin_router)
app.include_router(model_router)
app.include_router(shm_router)
app.include_router(anomaly_router)
app.include_router(experience_router)
app.include_router(spatial_router)
app.include_router(report_router)
app.include_router(assistant_router)
app.include_router(grout_router)
app.include_router(autodrive_router)
app.include_router(ringeye_router)
app.include_router(xray_router)


@app.get("/api/info")
def info():
    return {
        "name": "Intelligent Tunneling Management Platform",
        "engine": "Mindlin + Hankel-transform consolidation",
        "docs": "/docs",
        "endpoints": [
            "POST /api/engine/immediate",
            "POST /api/engine/consolidation",
            "POST /api/engine/total",
            "POST /api/engine/evaluate",
            "GET /api/engine/reference/beijing-line12",
            "POST /api/engine/calibrate",
            "GET|POST /api/data/shield-params",
            "GET|POST /api/data/monitoring",
            "GET /api/data/calculated",
            "POST /api/grout/hydration|impact",
            "GET|POST /api/autodrive/advisory",
            "POST /api/ringeye/scan|analyze",
            "POST /api/xray/map",
        ],
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "engine": "ready"}


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
