from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.anomaly_routes import router as anomaly_router
from app.api.iot_routes import router as iot_router
from app.api.risk_routes import router as risk_router
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
from app.api.websocket_routes import router as ws_router
from app.api.geology_routes import router as geology_router
from app.api.cutter_routes import router as cutter_router
from app.api.gis_routes import router as gis_router
from app.api.pdf_routes import router as pdf_router
from app.auth import seed_users
from app.config import env_bool, environment, is_production, render_external_url
from app.db import SessionLocal, get_db, init_db
from app.iot.service import seed_demo_iot
from app.seed_advanced import seed_advanced

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_users(db)
        if env_bool("SHIELD_SEED_DEMO", default=not is_production()):
            try:
                seed_advanced(db)
                seed_demo_iot(db)
            except Exception:
                db.rollback()
                logger.exception("Optional demo seeding failed; starting with existing data")
        logger.info("Startup complete (environment=%s, demo_seed=%s)", environment(), env_bool("SHIELD_SEED_DEMO", default=not is_production()))
    except Exception:
        logger.exception("Startup failed; refusing to serve an uninitialized application")
        raise
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

_default_origins = (
    ""
    if is_production()
    else (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:8000,http://127.0.0.1:8000"
    )
)
_cors_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", _default_origins).split(",")
    if origin.strip()
]
for _public_url in (render_external_url(), (os.environ.get("PUBLIC_APP_URL") or "").strip().rstrip("/")):
    if _public_url and _public_url not in _cors_origins:
        _cors_origins.append(_public_url)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        # Log server-side, but never leak tracebacks or secrets to the client.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


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
app.include_router(ws_router)
app.include_router(geology_router)
app.include_router(cutter_router)
app.include_router(gis_router)
app.include_router(pdf_router)
app.include_router(iot_router)
app.include_router(risk_router)


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database health check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "unavailable", "engine": "ready"},
        )
    return {
        "status": "ok",
        "database": "ok",
        "engine": "ready",
        "environment": environment(),
        "demo_seed": env_bool("SHIELD_SEED_DEMO", default=not is_production()),
    }


@app.get("/api/info")
def info():
    return {
        "name": "Intelligent Tunneling Management Platform",
        "engine": "Mindlin + Hankel-transform consolidation",
        "docs": "/docs",
    }


_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STATIC_CANDIDATES = [
    os.path.join(_REPO_ROOT, "frontend", "dist"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
]
STATIC_DIR = next((d for d in _STATIC_CANDIDATES if os.path.isdir(d)), _STATIC_CANDIDATES[0])

if os.path.isdir(STATIC_DIR):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    @app.get("/")
    def serve_ui():
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return {"status": "ok", "message": "API backend ready"}

    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")