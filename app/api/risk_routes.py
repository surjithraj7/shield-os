from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.auth import get_current_user
from app.db import get_db
from app.models import Alert, RiskAssessment, User
from app.security import enforce_rate_limit

router = APIRouter(prefix="/api", tags=["risk-alerts"])

ACK_FROM = {"open", "acknowledged", "investigating"}


class AlertActionRequest(BaseModel):
    note: str = Field(default="", max_length=1000)


class AlertCreateRequest(BaseModel):
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=1024)
    severity: str = Field(..., pattern="^(LOW|MODERATE|HIGH|CRITICAL)$")
    sensor_id: str = Field(default="", max_length=96)
    trigger: str = Field(default="", max_length=256)
    line: str = Field(default="Beijing Metro Line 12", max_length=64)
    section: str = Field(default="TBM-left-line", max_length=64)
    ring_no: int = Field(default=0, ge=0)
    chainage_m: float = 0.0
    value: float = 0.0
    unit: str = Field(default="", max_length=24)
    source: str = Field(default="manual", pattern="^(real|simulated|manual)$")


def _alert_out(row: Alert) -> dict[str, Any]:
    return {
        "id": row.id,
        "dedupe_key": row.dedupe_key,
        "title": row.title,
        "message": row.message,
        "severity": row.severity,
        "status": row.status,
        "trigger": row.trigger,
        "sensor_id": row.sensor_id,
        "assessment_id": row.assessment_id,
        "line": row.line,
        "section": row.section,
        "ring_no": row.ring_no,
        "chainage_m": row.chainage_m,
        "value": row.value,
        "unit": row.unit,
        "source": row.source,
        "created_at": row.created_at.isoformat(),
        "last_seen_at": row.last_seen_at.isoformat(),
        "occurrence_count": row.occurrence_count,
        "acknowledged_at": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        "acknowledged_by": row.acknowledged_by,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "resolved_by": row.resolved_by,
        "resolution_note": row.resolution_note,
    }


def _assessment_out(row: RiskAssessment) -> dict[str, Any]:
    details = {}
    try:
        details = json.loads(row.details_json)
    except json.JSONDecodeError:
        details = {}
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat(),
        "line": row.line,
        "section": row.section,
        "ring_no": row.ring_no,
        "chainage_m": row.chainage_m,
        "sensor_id": row.sensor_id,
        "sensor_type": row.sensor_type,
        "value": row.value,
        "unit": row.unit,
        "risk_category": row.risk_category,
        "risk_score": row.risk_score,
        "trigger": row.trigger,
        "recommendation": row.recommendation,
        "data_quality": row.data_quality,
        "source": row.source,
        "confidence": row.confidence,
        "alert_id": row.alert_id,
        "details": details,
    }


def _operator(
    request: Request,
    user: User | None = Depends(get_current_user),
) -> User:
    enforce_rate_limit(request, "alert-action", limit=120, window_s=60.0)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if user.role not in {"operator", "admin"}:
        raise HTTPException(status_code=403, detail="Operator or admin role required")
    return user


@router.get("/risk/assessments")
def list_assessments(
    sensor_id: str | None = None,
    risk_category: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(RiskAssessment)
    if sensor_id:
        query = query.filter(RiskAssessment.sensor_id == sensor_id)
    if risk_category:
        query = query.filter(RiskAssessment.risk_category == risk_category.upper())
    rows = query.order_by(RiskAssessment.created_at.desc()).limit(limit).all()
    return [_assessment_out(r) for r in rows]


@router.get("/risk/assessments/{assessment_id}")
def get_assessment(assessment_id: int, db: Session = Depends(get_db)):
    row = db.query(RiskAssessment).filter(RiskAssessment.id == assessment_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return _assessment_out(row)


@router.get("/alerts")
def list_alerts(
    status: str | None = None,
    severity: str | None = None,
    sensor_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity.upper())
    if sensor_id:
        query = query.filter(Alert.sensor_id == sensor_id)
    rows = query.order_by(Alert.created_at.desc()).limit(limit).all()
    return [_alert_out(r) for r in rows]


@router.get("/alerts/summary")
def alerts_summary(db: Session = Depends(get_db)):
    by_status = {
        status: count
        for status, count in db.query(Alert.status, func.count(Alert.id))
        .group_by(Alert.status)
        .all()
    }
    by_severity = {
        severity: count
        for severity, count in db.query(Alert.severity, func.count(Alert.id))
        .group_by(Alert.severity)
        .all()
    }
    total = sum(by_status.values())
    active = sum(by_status.get(status, 0) for status in ACK_FROM)
    latest = db.query(Alert).order_by(Alert.created_at.desc()).first()
    return {
        "total": total,
        "active": active,
        "by_status": by_status,
        "by_severity": by_severity,
        "latest": _alert_out(latest) if latest else None,
    }


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    row = db.query(Alert).filter(Alert.id == alert_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _alert_out(row)


@router.post("/alerts", status_code=201)
def create_manual_alert(
    req: AlertCreateRequest,
    request: Request,
    user: User = Depends(_operator),
    db: Session = Depends(get_db),
):
    row = Alert(
        dedupe_key=f"manual:{user.username}:{req.title}",
        title=req.title,
        message=req.message,
        severity=req.severity,
        status="open",
        trigger=req.trigger or "manual alert",
        sensor_id=req.sensor_id,
        line=req.line,
        section=req.section,
        ring_no=req.ring_no,
        chainage_m=req.chainage_m,
        value=req.value,
        unit=req.unit,
        source=req.source,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        actor=user.username,
        action="alert.create_manual",
        object_type="alert",
        object_id=row.id,
        details={"severity": row.severity, "title": row.title},
    )
    db.commit()
    db.refresh(row)
    return _alert_out(row)


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    req: AlertActionRequest,
    request: Request,
    user: User = Depends(_operator),
    db: Session = Depends(get_db),
):
    row = db.query(Alert).filter(Alert.id == alert_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if row.status == "resolved":
        raise HTTPException(status_code=409, detail="Resolved alerts cannot be acknowledged")
    if row.status == "open":
        row.status = "acknowledged"
        row.acknowledged_at = datetime.now(timezone.utc).replace(tzinfo=None)
        row.acknowledged_by = user.username
    if req.note:
        row.resolution_note = (row.resolution_note + "\n" + req.note).strip()[:1000]
    record_audit(
        db,
        actor=user.username,
        action="alert.acknowledge",
        object_type="alert",
        object_id=row.id,
        details={"note": req.note},
    )
    db.commit()
    db.refresh(row)
    return _alert_out(row)


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    req: AlertActionRequest,
    request: Request,
    user: User = Depends(_operator),
    db: Session = Depends(get_db),
):
    row = db.query(Alert).filter(Alert.id == alert_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if row.status == "resolved":
        return _alert_out(row)
    previous_status = row.status
    row.status = "resolved"
    row.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    row.resolved_by = user.username
    row.resolution_note = req.note[:1000]
    record_audit(
        db,
        actor=user.username,
        action="alert.resolve",
        object_type="alert",
        object_id=row.id,
        details={"note": req.note, "previous_status": previous_status},
    )
    db.commit()
    db.refresh(row)
    return _alert_out(row)
