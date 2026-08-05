from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ShmReading

router = APIRouter(prefix="/api/shm", tags=["shm"])


class ShmReadingIn(BaseModel):
    line: str = "Beijing Metro Line 12"
    section: str = "TBM-left-line"
    ring_no: int
    chainage_m: float
    sensor_id: str
    sensor_type: str
    measured_value: float
    unit: str = "mm"
    status: str = "normal"


def _row_out(r: ShmReading) -> dict:
    return {
        "id": r.id,
        "line": r.line,
        "section": r.section,
        "ring_no": r.ring_no,
        "chainage_m": r.chainage_m,
        "sensor_id": r.sensor_id,
        "sensor_type": r.sensor_type,
        "measured_value": r.measured_value,
        "unit": r.unit,
        "status": r.status,
        "timestamp": r.timestamp.isoformat(),
    }


@router.post("/readings")
def create_reading(req: ShmReadingIn, db: Session = Depends(get_db)):
    row = ShmReading(**req.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_out(row)


@router.get("/readings")
def list_readings(
    sensor_type: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    query = db.query(ShmReading).order_by(ShmReading.timestamp.desc())
    if sensor_type:
        query = query.filter(ShmReading.sensor_type == sensor_type)
    rows = query.limit(limit).all()
    return [_row_out(r) for r in rows]


@router.get("/summary")
def shm_summary(db: Session = Depends(get_db)):
    rows = db.query(ShmReading).order_by(ShmReading.timestamp.desc()).limit(1000).all()
    grouped: dict[str, list[float]] = {}
    counts = {"seepage": 0, "segment_displacement": 0, "lining_strain": 0}
    statuses: dict[str, int] = {}
    latest_by_type: dict[str, dict] = {}
    for r in rows:
        grouped.setdefault(r.sensor_type, []).append(r.measured_value)
        counts[r.sensor_type] = counts.get(r.sensor_type, 0) + 1
        statuses[r.status] = statuses.get(r.status, 0) + 1
        latest_by_type.setdefault(r.sensor_type, _row_out(r))
    stats = {}
    for k, v in grouped.items():
        n = len(v)
        stats[k] = {
            "count": n,
            "latest": round(v[0], 3),
            "min": round(min(v), 3),
            "max": round(max(v), 3),
            "mean": round(sum(v) / n, 3),
        }
    total_alerts = sum(v for k, v in statuses.items() if k != "normal")
    return {
        "sensor_type_counts": counts,
        "stats": stats,
        "status_counts": statuses,
        "total_alerts": total_alerts,
        "latest_readings": list(latest_by_type.values()),
    }
