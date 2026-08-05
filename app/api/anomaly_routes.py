from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.ml.anomaly import scan_series, severity
from app.models import MonitoringData, ShieldParameter

router = APIRouter(prefix="/api/anomaly", tags=["anomaly"])

ANOMALY_SOURCES = {
    "settlement": ("monitoring", "measured_value_mm"),
    "thrust": ("shield", "thrust_kn"),
    "torque": ("shield", "torque_knm"),
    "advance_speed": ("shield", "advance_speed_mm_min"),
    "grouting_pressure": ("shield", "grouting_pressure_mpa"),
}


def _series(db: Session, kind: str, attr: str) -> list[float]:
    if kind == "monitoring":
        rows = db.query(MonitoringData).order_by(MonitoringData.ring_no.asc()).all()
    else:
        rows = db.query(ShieldParameter).order_by(ShieldParameter.ring_no.asc()).all()
    return [float(getattr(r, attr)) for r in rows]


@router.get("/scan")
def scan(
    window: int = 10,
    z_threshold: float = 2.5,
    db: Session = Depends(get_db),
):
    result = {}
    for name, (kind, attr) in ANOMALY_SOURCES.items():
        series = _series(db, kind, attr)
        scan = scan_series(series, window=window, z_threshold=z_threshold)
        flagged = [
            {**p, "severity": severity(p["zscore"]), "source": name}
            for p in scan["flagged"]
        ]
        result[name] = {
            "method": scan["method"],
            "max_zscore": scan["max_zscore"],
            "flagged_count": scan["flagged_count"],
            "total_points": scan["total_points"],
            "flagged": flagged,
        }
    total = sum(v["flagged_count"] for v in result.values())
    return {"sources": result, "total_flagged": total, "window": window, "z_threshold": z_threshold}
