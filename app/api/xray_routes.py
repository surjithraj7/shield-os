from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.engine.consolidation import ConsolidationParams
from app.engine.mindlin import ShieldParams, SoilParams
from app.engine.orchestrator import EngineConfig
from app.engine.xray import XrayConfig, analyze_assets
from app.models import SpatialAsset
from app.schemas import XRayRequest

router = APIRouter(prefix="/api/xray", tags=["xray"])


def _asset_out(r: SpatialAsset) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "asset_type": r.asset_type,
        "x_enu": r.x_enu,
        "y_enu": r.y_enu,
        "z_enu": r.z_enu,
        "radius_m": r.radius_m,
        "clearance_limit_m": r.clearance_limit_m,
        "note": r.note,
    }


def _shield(s) -> ShieldParams:
    return ShieldParams(
        depth_m=s.depth_m,
        radius_m=s.radius_m,
        y_center_m=s.y_center_m,
        length_m=s.length_m,
        face_pressure_kpa=s.face_pressure_kpa,
        skin_friction_kpa=s.skin_friction_kpa,
        volume_loss_pct=s.volume_loss_pct,
        trough_width_coef=s.trough_width_coef,
    )


def _soil(soil) -> SoilParams:
    return SoilParams(es_mpa=soil.es_mpa, poisson=soil.poisson, gamma_kn_m3=soil.gamma_kn_m3)


def _consolidation(c) -> ConsolidationParams:
    return ConsolidationParams(
        depth_m=c.depth_m,
        tunnel_radius_m=c.tunnel_radius_m,
        base_depth_m=c.base_depth_m,
        mv_per_mpa=c.mv_per_mpa,
        cv_m2_per_day=c.cv_m2_per_day,
        ch_m2_per_day=c.ch_m2_per_day,
        p0_kpa=c.p0_kpa,
        sigma_r_m=c.sigma_r_m,
        sigma_z_m=c.sigma_z_m,
        n_modes=c.n_modes,
    )


def _engine(e) -> EngineConfig:
    return EngineConfig(
        calibration_immediate=e.calibration_immediate,
        calibration_consolidation=e.calibration_consolidation,
    )


@router.post("/map")
def xray_map(req: XRayRequest, db: Session = Depends(get_db)):
    assets = db.query(SpatialAsset).all()
    return analyze_assets(
        [_asset_out(r) for r in assets],
        start_x=req.start_x,
        end_x=req.end_x,
        t_days=req.t_days,
        depth_m=req.depth_m,
        shield=_shield(req.shield),
        soil=_soil(req.soil),
        consolidation=_consolidation(req.consolidation),
        engine=_engine(req.engine),
    )


@router.get("/summary")
def xray_summary(db: Session = Depends(get_db)):
    assets = db.query(SpatialAsset).all()
    return analyze_assets(
        [_asset_out(r) for r in assets],
        start_x=100.0,
        end_x=244.0,
        t_days=60.0,
        depth_m=20.0,
        shield=ShieldParams(),
        soil=SoilParams(),
        consolidation=ConsolidationParams(),
        engine=EngineConfig(),
        cfg=XrayConfig(),
    )
