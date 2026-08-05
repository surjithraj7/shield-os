from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.engine.autodrive import AutodriveConfig, AutodriveState, compute_advisory
from app.models import CalculatedResult, ShieldParameter
from app.schemas import AutodriveRequest

router = APIRouter(prefix="/api/autodrive", tags=["autodrive"])


def _live_state(db: Session) -> tuple[AutodriveState, dict]:
    row = db.query(ShieldParameter).order_by(ShieldParameter.timestamp.desc()).first()
    calc = db.query(CalculatedResult).order_by(CalculatedResult.timestamp.desc()).first()
    if row:
        state = AutodriveState(
            face_pressure_kpa=row.face_pressure_kpa,
            grouting_volume_m3=row.grouting_volume_m3,
            grouting_pressure_mpa=row.grouting_pressure_mpa,
            advance_speed_mm_min=row.advance_speed_mm_min,
            thrust_kn=row.thrust_kn,
            torque_knm=row.torque_knm,
        )
    else:
        state = AutodriveState()
    context = {
        "ring_no": row.ring_no if row else None,
        "chainage_m": row.chainage_m if row else None,
        "predicted_mm": calc.predicted_value_mm if calc else None,
        "monitored_mm": calc.monitored_value_mm if calc else None,
        "risk_level": calc.risk_level if calc else "green",
    }
    return state, context


@router.get("/advisory")
def advisory(db: Session = Depends(get_db)):
    state, context = _live_state(db)
    predicted = context["predicted_mm"] if context["predicted_mm"] is not None else 6.5
    monitored = context["monitored_mm"]
    result = compute_advisory(state, predicted, monitored)
    return {"context": context, **result}


@router.post("/advisory")
def advisory_post(req: AutodriveRequest):
    state = AutodriveState(
        face_pressure_kpa=req.face_pressure_kpa,
        grouting_volume_m3=req.grouting_volume_m3,
        grouting_pressure_mpa=req.grouting_pressure_mpa,
        advance_speed_mm_min=req.advance_speed_mm_min,
    )
    cfg = AutodriveConfig(target_settlement_mm=req.target_mm)
    result = compute_advisory(state, req.predicted_mm, req.monitored_mm, cfg)
    return result
