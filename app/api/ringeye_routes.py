from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.engine.ringeye import RingEyeParams, analyze_ring, simulate_scan
from app.models import RingEyeReading
from app.schemas import RingEyeRequest, RingEyeScanRequest

router = APIRouter(prefix="/api/ringeye", tags=["ringeye"])

LINE = "Beijing Metro Line 12"
SECTION = "TBM-left-line"


def _row_out(r: RingEyeReading) -> dict:
    return {
        "id": r.id,
        "line": r.line,
        "section": r.section,
        "ring_no": r.ring_no,
        "chainage_m": r.chainage_m,
        "nominal_diameter_mm": r.nominal_diameter_mm,
        "delta_d_mm": r.delta_d_mm,
        "ovalization_pct": r.ovalization_pct,
        "eccentricity_mm": r.eccentricity_mm,
        "joint_gap_mm": r.joint_gap_mm,
        "seepage_risk": r.seepage_risk,
        "status": r.status,
        "timestamp": r.timestamp.isoformat(),
    }


@router.post("/scan")
def scan_ring(req: RingEyeScanRequest, db: Session = Depends(get_db)):
    cloud = simulate_scan(req.ovalization_mm, req.n_points)
    analysis = analyze_ring(
        req.ring_no,
        req.chainage_m,
        cloud["radial_devs_mm"],
        cloud["angles_deg"],
        RingEyeParams(),
    )
    row = RingEyeReading(
        line=LINE,
        section=SECTION,
        ring_no=req.ring_no,
        chainage_m=req.chainage_m,
        nominal_diameter_mm=analysis["nominal_diameter_mm"],
        delta_d_mm=analysis["delta_d_mm"],
        ovalization_pct=analysis["ovalization_pct"],
        eccentricity_mm=analysis["eccentricity_mm"],
        joint_gap_mm=analysis["joint_gap_mm"],
        seepage_risk=analysis["seepage_risk"],
        status=analysis["status"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"analysis": analysis, "point_cloud": cloud, "stored": _row_out(row)}


@router.post("/analyze")
def analyze(req: RingEyeRequest):
    analysis = analyze_ring(
        req.ring_no,
        req.chainage_m,
        req.radial_devs_mm,
        None,
        RingEyeParams(
            nominal_diameter_mm=req.nominal_diameter_mm,
            segment_count=req.segment_count,
        ),
    )
    return analysis


@router.get("/readings")
def list_readings(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.query(RingEyeReading).order_by(RingEyeReading.timestamp.desc()).limit(limit).all()
    return [_row_out(r) for r in rows]


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    rows = db.query(RingEyeReading).order_by(RingEyeReading.timestamp.desc()).limit(1000).all()
    latest = _row_out(rows[0]) if rows else None
    counts = {"normal": 0, "warning": 0, "critical": 0}
    for r in rows:
        counts[r.seepage_risk] = counts.get(r.seepage_risk, 0) + 1
    return {
        "latest": latest,
        "risk_counts": counts,
        "total_scans": len(rows),
        "total_alerts": sum(v for k, v in counts.items() if k != "normal"),
    }
