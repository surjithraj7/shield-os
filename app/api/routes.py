from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CalculatedResult, MonitoringData, ShieldParameter
from app.schemas import (
    AlarmEvaluation,
    ConsolidationRequest,
    EvaluateRequest,
    ImmediateRequest,
    MonitoringCreate,
    ShieldParamCreate,
    TotalRequest,
)
from app.engine.consolidation import (
    ConsolidationParams,
    consolidation_settlement,
    consolidation_timeseries,
)
from app.engine.mindlin import (
    SoilParams,
    ShieldParams,
    immediate_settlement_trough,
)
from app.engine.orchestrator import (
    EngineConfig,
    beijing_line12_reference,
    calibrate_against_monitored,
    error_metrics,
    predict_at_point,
    total_settlement_trough,
)
from app.risk import assess_risk

router = APIRouter(prefix="/api")


def _shield(shield):
    return ShieldParams(
        depth_m=shield.depth_m,
        radius_m=shield.radius_m,
        y_center_m=shield.y_center_m,
        length_m=shield.length_m,
        face_pressure_kpa=shield.face_pressure_kpa,
        skin_friction_kpa=shield.skin_friction_kpa,
        volume_loss_pct=shield.volume_loss_pct,
        trough_width_coef=shield.trough_width_coef,
    )


def _soil(soil):
    return SoilParams(es_mpa=soil.es_mpa, poisson=soil.poisson, gamma_kn_m3=soil.gamma_kn_m3)


def _consolidation(consolidation):
    return ConsolidationParams(
        depth_m=consolidation.depth_m,
        tunnel_radius_m=consolidation.tunnel_radius_m,
        base_depth_m=consolidation.base_depth_m,
        mv_per_mpa=consolidation.mv_per_mpa,
        cv_m2_per_day=consolidation.cv_m2_per_day,
        ch_m2_per_day=consolidation.ch_m2_per_day,
        p0_kpa=consolidation.p0_kpa,
        sigma_r_m=consolidation.sigma_r_m,
        sigma_z_m=consolidation.sigma_z_m,
        n_modes=consolidation.n_modes,
    )


def _engine(engine):
    return EngineConfig(
        calibration_immediate=engine.calibration_immediate,
        calibration_consolidation=engine.calibration_consolidation,
    )


@router.post("/engine/immediate")
def compute_immediate(req: ImmediateRequest):
    import numpy as np

    y = np.linspace(-req.y_max, req.y_max, req.n_y)
    result = immediate_settlement_trough(
        np.array([req.station]),
        y,
        _shield(req.shield),
        _soil(req.soil),
        calibration=req.calibration,
    )
    return {
        "station": req.station,
        "y_m": y.tolist(),
        "thrust_mm": (result["thrust"][0] * 1000.0).tolist(),
        "friction_mm": (result["friction"][0] * 1000.0).tolist(),
        "ground_loss_mm": (result["ground_loss"][0] * 1000.0).tolist(),
        "total_mm": (result["total"][0] * 1000.0).tolist(),
    }


@router.post("/engine/consolidation")
def compute_consolidation(req: ConsolidationRequest):
    import numpy as np

    t = np.array(req.t_days)
    params = _consolidation(req.consolidation)
    r = np.linspace(0.0, req.r_max, req.n_r)
    series = consolidation_timeseries(t, params)
    profile = consolidation_settlement(r, float(t[-1]), params) * 1000.0
    final_center = consolidation_settlement(np.array([0.0]), 1e9, params)[0] * 1000.0
    return {
        "t_days": series["t_days"].tolist(),
        "center_settlement_mm": (series["settlement_m"] * 1000.0).tolist(),
        "final_center_settlement_mm": float(final_center),
        "radial_profile_r_m": r.tolist(),
        "radial_profile_mm": profile.tolist(),
        "at_t_days": float(t[-1]),
    }


@router.post("/engine/total")
def compute_total(req: TotalRequest):
    import numpy as np

    y = np.linspace(-req.y_max, req.y_max, req.n_y)
    result = total_settlement_trough(
        req.station,
        req.t_days,
        _shield(req.shield),
        _soil(req.soil),
        _consolidation(req.consolidation),
        _engine(req.engine),
        y,
    )
    return {
        "station": req.station,
        "t_days": req.t_days,
        "y_m": result["y"].tolist(),
        "immediate_mm": result["immediate_mm"].tolist(),
        "consolidation_mm": result["consolidation_mm"].tolist(),
        "total_mm": result["total_mm"].tolist(),
    }


@router.post("/engine/evaluate", response_model=AlarmEvaluation)
def evaluate(req: EvaluateRequest):
    predicted = predict_at_point(
        req.station,
        req.t_days,
        _shield(req.shield),
        _soil(req.soil),
        _consolidation(req.consolidation),
        _engine(req.engine),
    )["total_predicted_mm"]
    metrics = error_metrics(predicted, req.monitored_mm)
    risk = assess_risk(req.monitored_mm)
    return AlarmEvaluation(
        predicted_value_mm=predicted,
        monitored_value_mm=req.monitored_mm,
        difference_mm=metrics["difference_mm"],
        relative_error_pct=metrics["relative_error_pct"],
        passes_5pct_threshold=metrics["passes_5pct_threshold"],
        risk_level=risk["risk_level"],
        alert_color=risk["alert_color"],
    )


@router.get("/engine/reference/beijing-line12")
def reference_case():
    return beijing_line12_reference()


@router.post("/engine/calibrate")
def calibrate(req: EvaluateRequest):
    config = calibrate_against_monitored(
        req.monitored_mm,
        req.station,
        req.t_days,
        _shield(req.shield),
        _soil(req.soil),
        _consolidation(req.consolidation),
    )
    return {
        "calibration_immediate": config.calibration_immediate,
        "calibration_consolidation": config.calibration_consolidation,
        "message": "Re-run /engine/evaluate with this engine config to hit the monitored value",
    }


@router.post("/data/shield-params")
def create_shield_param(req: ShieldParamCreate, db: Session = Depends(get_db)):
    row = ShieldParameter(**req.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "ring_no": row.ring_no, "chainage_m": row.chainage_m}


@router.get("/data/shield-params")
def list_shield_params(
    line: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(ShieldParameter).order_by(ShieldParameter.timestamp.desc())
    if line:
        query = query.filter(ShieldParameter.line == line)
    rows = query.limit(limit).all()
    return [
        {
            "id": r.id,
            "line": r.line,
            "section": r.section,
            "ring_no": r.ring_no,
            "chainage_m": r.chainage_m,
            "timestamp": r.timestamp.isoformat(),
            "thrust_kn": r.thrust_kn,
            "advance_speed_mm_min": r.advance_speed_mm_min,
            "torque_knm": r.torque_knm,
            "grouting_pressure_mpa": r.grouting_pressure_mpa,
            "grouting_volume_m3": r.grouting_volume_m3,
            "face_pressure_kpa": r.face_pressure_kpa,
            "pitch_deg": r.pitch_deg,
            "yaw_deg": r.yaw_deg,
        }
        for r in rows
    ]


@router.post("/data/monitoring")
def create_monitoring(req: MonitoringCreate, db: Session = Depends(get_db)):
    row = MonitoringData(**req.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "sensor_id": row.sensor_id, "measured_value_mm": row.measured_value_mm}


@router.get("/data/monitoring")
def list_monitoring(
    line: str | None = None,
    target_type: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(MonitoringData).order_by(MonitoringData.timestamp.desc())
    if line:
        query = query.filter(MonitoringData.line == line)
    if target_type:
        query = query.filter(MonitoringData.target_type == target_type)
    rows = query.limit(limit).all()
    return [
        {
            "id": r.id,
            "line": r.line,
            "section": r.section,
            "ring_no": r.ring_no,
            "chainage_m": r.chainage_m,
            "sensor_id": r.sensor_id,
            "target_type": r.target_type,
            "measured_value_mm": r.measured_value_mm,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in rows
    ]


@router.get("/data/calculated")
def list_calculated(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.query(CalculatedResult).order_by(CalculatedResult.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "line": r.line,
            "section": r.section,
            "ring_no": r.ring_no,
            "chainage_m": r.chainage_m,
            "timestamp": r.timestamp.isoformat(),
            "model_name": r.model_name,
            "immediate_mm": r.immediate_mm,
            "consolidation_mm": r.consolidation_mm,
            "predicted_value_mm": r.predicted_value_mm,
            "monitored_value_mm": r.monitored_value_mm,
            "difference_mm": r.difference_mm,
            "relative_error_pct": r.relative_error_pct,
            "risk_level": r.risk_level,
        }
        for r in rows
    ]
