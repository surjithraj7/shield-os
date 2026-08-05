from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ExperienceTransfer, ShieldParameter
from app.transfer import recommend_for_target, transfer_record

router = APIRouter(prefix="/api/experience", tags=["experience"])


class TransferRequest(BaseModel):
    source_line: str = "Beijing Metro Line 12"
    source_segment: str = "A"
    target_line: str = "Beijing Metro Line 12"
    target_segment: str = "B"
    geology_factor: float = 1.05
    save_history: bool = False


def _shield_rows(db: Session, line: str, limit: int = 80) -> list[dict]:
    rows = (
        db.query(ShieldParameter)
        .filter(ShieldParameter.line == line)
        .order_by(ShieldParameter.ring_no.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "ring_no": r.ring_no,
            "thrust_kn": r.thrust_kn,
            "torque_knm": r.torque_knm,
            "advance_speed_mm_min": r.advance_speed_mm_min,
            "grouting_pressure_mpa": r.grouting_pressure_mpa,
            "grouting_volume_m3": r.grouting_volume_m3,
            "face_pressure_kpa": r.face_pressure_kpa,
        }
        for r in rows
    ]


@router.get("/recommend")
def recommend(
    source_line: str = "Beijing Metro Line 12",
    geology_factor: float = 1.05,
    db: Session = Depends(get_db),
):
    rows = _shield_rows(db, source_line)
    rec = recommend_for_target(rows, geology_factor=geology_factor)
    return {
        "source_line": source_line,
        "recommendation": rec,
        "params": rec["params"],
        "transfer_record": transfer_record(
            source_line, "A", source_line, "B", rec
        ),
    }


@router.post("/recommend")
def recommend_post(req: TransferRequest, db: Session = Depends(get_db)):
    rows = _shield_rows(db, req.source_line)
    rec = recommend_for_target(rows, geology_factor=req.geology_factor)
    record = transfer_record(
        req.source_line,
        req.source_segment,
        req.target_line,
        req.target_segment,
        rec,
    )
    if req.save_history:
        db.add(
            ExperienceTransfer(
                source_line=req.source_line,
                source_segment=req.source_segment,
                target_line=req.target_line,
                target_segment=req.target_segment,
                params_json=json.dumps(rec),
            )
        )
        db.commit()
    return {
        "source_line": req.source_line,
        "source_segment": req.source_segment,
        "target_line": req.target_line,
        "target_segment": req.target_segment,
        "recommendation": rec,
        "params": rec["params"],
        "saved": req.save_history,
    }


@router.get("/history")
def history(db: Session = Depends(get_db)):
    rows = db.query(ExperienceTransfer).order_by(ExperienceTransfer.created_at.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "source_line": r.source_line,
            "source_segment": r.source_segment,
            "target_line": r.target_line,
            "target_segment": r.target_segment,
            "params": json.loads(r.params_json),
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
