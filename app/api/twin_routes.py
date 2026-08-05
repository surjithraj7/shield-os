from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CalculatedResult, MonitoringData, ShieldParameter
from app.risk import assess_risk

router = APIRouter(prefix="/api/twin", tags=["twin"])

RISK_ORDER = {"low": 0, "notice": 1, "warning": 2, "high": 3}


def _risk_label(mm: float | None) -> str:
    if mm is None:
        return "low"
    return assess_risk(mm)["risk_level"]


@router.get("/snapshot")
def twin_snapshot(db: Session = Depends(get_db)):
    shield = db.query(ShieldParameter).order_by(ShieldParameter.timestamp.desc()).first()
    monitoring = db.query(MonitoringData).order_by(MonitoringData.timestamp.desc()).first()
    calc_rows = (
        db.query(CalculatedResult)
        .order_by(CalculatedResult.timestamp.desc())
        .limit(240)
        .all()
    )

    tunnel = [
        {
            "ring_no": r.ring_no,
            "chainage_m": r.chainage_m,
            "predicted_mm": r.predicted_value_mm,
            "monitored_mm": r.monitored_value_mm,
            "risk": r.risk_level,
        }
        for r in calc_rows
    ]

    worst = max(
        tunnel,
        key=lambda t: RISK_ORDER.get(t["risk"], 0),
        default=None,
    )

    latest_calc = calc_rows[0] if calc_rows else None

    metrics = {}
    if shield:
        metrics = {
            "thrust_kn": shield.thrust_kn,
            "torque_knm": shield.torque_knm,
            "advance_speed_mm_min": shield.advance_speed_mm_min,
            "grouting_pressure_mpa": shield.grouting_pressure_mpa,
            "grouting_volume_m3": shield.grouting_volume_m3,
            "face_pressure_kpa": shield.face_pressure_kpa,
            "screw_rpm": 8.5,
        }

    settlement = None
    if latest_calc:
        settlement = {
            "ring_no": latest_calc.ring_no,
            "chainage_m": latest_calc.chainage_m,
            "predicted_mm": latest_calc.predicted_value_mm,
            "monitored_mm": latest_calc.monitored_value_mm,
            "difference_mm": latest_calc.difference_mm,
            "relative_error_pct": latest_calc.relative_error_pct,
            "risk": latest_calc.risk_level,
        }

    return {
        "twin": "SHIELD-OS DIGITAL CYBER TWIN",
        "status": "SYNC",
        "timestamp": (shield.timestamp if shield else latest_calc.timestamp).isoformat()
        if (shield or latest_calc)
        else None,
        "current_ring": shield.ring_no if shield else (latest_calc.ring_no if latest_calc else None),
        "chainage_m": shield.chainage_m if shield else (latest_calc.chainage_m if latest_calc else None),
        "section": shield.section if shield else (latest_calc.section if latest_calc else "TBM-left-line"),
        "metrics": metrics,
        "settlement": settlement,
        "worst_risk": worst,
        "tunnel": tunnel,
    }
