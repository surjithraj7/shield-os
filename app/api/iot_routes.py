from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.auth import get_current_user
from app.db import get_db
from app.iot.service import (
    IngestValidationError,
    SUPPORTED_SENSOR_TYPES,
    get_sensor,
    ingest_reading,
    raise_offline_alerts,
    register_sensor,
    seed_demo_iot,
    sensor_health,
    sensor_to_dict,
    simulate_batch,
)
from app.models import Alert, IotSensor, RiskAssessment, SensorReading, User
from app.security import enforce_rate_limit, verify_ingest_key

router = APIRouter(prefix="/api/iot", tags=["iot"])


class SensorCreate(BaseModel):
    sensor_id: str = Field(..., min_length=1, max_length=96)
    name: str = Field(default="", max_length=160)
    sensor_type: str = Field(..., min_length=1, max_length=48)
    unit: str | None = None
    line: str = "Beijing Metro Line 12"
    section: str = "TBM-left-line"
    ring_no: int = Field(default=0, ge=0)
    chainage_m: float = 0.0
    location_note: str = Field(default="", max_length=256)
    status: str = Field(default="active", pattern="^(active|offline|maintenance)$")
    source: str = Field(default="simulated", pattern="^(real|simulated|manual)$")
    min_value: float | None = None
    max_value: float | None = None
    sampling_interval_s: float = Field(default=60.0, gt=0.0, le=86400.0)


class ReadingCreate(BaseModel):
    model_config = ConfigDict(extra="allow")

    sensor_id: str = Field(..., min_length=1, max_length=96)
    value: float | None = None
    measured_value: float | None = None
    unit: str | None = None
    measured_at: datetime | None = None
    timestamp: datetime | None = None
    event_id: str | None = Field(default=None, max_length=96)
    quality: str = Field(default="good", pattern="^(good|suspect|stale|out_of_order)$")
    source: str | None = Field(default=None, pattern="^(real|simulated|manual)$")
    device_id: str | None = None
    gateway_id: str | None = None


def require_ingest(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    user: User | None = Depends(get_current_user),
) -> User | None:
    enforce_rate_limit(request, "iot-ingest", limit=600, window_s=60.0)
    if verify_ingest_key(x_api_key):
        return user
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Provide X-API-Key or an operator/admin bearer token",
        )
    if user.role not in {"operator", "admin"}:
        raise HTTPException(status_code=403, detail="Operator or admin role required")
    return user


def require_operator(
    request: Request,
    user: User | None = Depends(get_current_user),
) -> User:
    enforce_rate_limit(request, "iot-write", limit=120, window_s=60.0)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if user.role not in {"operator", "admin"}:
        raise HTTPException(status_code=403, detail="Operator or admin role required")
    return user


def _reading_out(row: SensorReading) -> dict[str, Any]:
    return {
        "id": row.id,
        "event_id": row.event_id,
        "sensor_id": row.sensor_id,
        "line": row.line,
        "section": row.section,
        "ring_no": row.ring_no,
        "chainage_m": row.chainage_m,
        "value": row.value,
        "unit": row.unit,
        "measured_at": row.measured_at.isoformat(),
        "received_at": row.received_at.isoformat(),
        "quality": row.quality,
        "source": row.source,
    }


def _assessment_out(row: RiskAssessment) -> dict[str, Any]:
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
    }


@router.get("/types")
def sensor_types():
    return {"types": SUPPORTED_SENSOR_TYPES}


@router.get("/sensors")
def list_sensors(
    sensor_type: str | None = None,
    status: str | None = None,
    include_health: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(IotSensor).order_by(IotSensor.sensor_type, IotSensor.sensor_id)
    if sensor_type:
        query = query.filter(IotSensor.sensor_type == sensor_type)
    if status:
        query = query.filter(IotSensor.status == status)
    rows = query.all()
    output = []
    for row in rows:
        item = sensor_to_dict(row)
        if include_health:
            item["health"] = sensor_health(row)
        output.append(item)
    return output


@router.get("/sensors/{sensor_id}")
def get_sensor_detail(sensor_id: str, db: Session = Depends(get_db)):
    row = get_sensor(db, sensor_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Sensor not found")
    item = sensor_to_dict(row)
    item["health"] = sensor_health(row)
    latest = (
        db.query(SensorReading)
        .filter(SensorReading.sensor_id == sensor_id)
        .order_by(SensorReading.measured_at.desc())
        .first()
    )
    item["latest_reading"] = _reading_out(latest) if latest else None
    return item


@router.post("/sensors", status_code=201)
def create_sensor(
    req: SensorCreate,
    request: Request,
    user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required to register sensors")
    try:
        row = register_sensor(db, req.model_dump())
    except IngestValidationError as exc:
        status = 409 if "already registered" in str(exc) else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    record_audit(
        db,
        actor=user.username,
        action="sensor.register",
        object_type="sensor",
        object_id=row.sensor_id,
        details={"sensor_type": row.sensor_type, "source": row.source},
    )
    db.commit()
    db.refresh(row)
    return sensor_to_dict(row)


@router.get("/sensors/{sensor_id}/readings")
def sensor_readings(
    sensor_id: str,
    limit: int = Query(default=200, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    if get_sensor(db, sensor_id) is None:
        raise HTTPException(status_code=404, detail="Sensor not found")
    rows = (
        db.query(SensorReading)
        .filter(SensorReading.sensor_id == sensor_id)
        .order_by(SensorReading.measured_at.desc())
        .limit(limit)
        .all()
    )
    return [_reading_out(r) for r in rows]


@router.get("/readings")
def list_readings(
    sensor_id: str | None = None,
    sensor_type: str | None = None,
    quality: str | None = None,
    limit: int = Query(default=200, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    query = db.query(SensorReading)
    if sensor_id:
        query = query.filter(SensorReading.sensor_id == sensor_id)
    if sensor_type:
        query = query.join(IotSensor, IotSensor.sensor_id == SensorReading.sensor_id).filter(
            IotSensor.sensor_type == sensor_type
        )
    if quality:
        query = query.filter(SensorReading.quality == quality)
    rows = query.order_by(SensorReading.measured_at.desc()).limit(limit).all()
    return [_reading_out(r) for r in rows]


@router.post("/readings", status_code=201)
def create_reading(
    req: ReadingCreate,
    user: User | None = Depends(require_ingest),
    db: Session = Depends(get_db),
):
    try:
        result = ingest_reading(db, req.model_dump(exclude_none=True))
    except IngestValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not result.get("duplicate"):
        record_audit(
            db,
            actor=user.username if user else "device-api-key",
            action="sensor.reading_ingest",
            object_type="sensor",
            object_id=req.sensor_id,
            details={
                "event_id": result.get("event_id"),
                "source": result.get("source"),
                "quality": result.get("quality"),
                "risk": (result.get("risk") or {}).get("category"),
            },
        )
    db.commit()
    return result


@router.get("/health")
def health_overview(db: Session = Depends(get_db)):
    sensors = db.query(IotSensor).order_by(IotSensor.sensor_id).all()
    rows = [sensor_health(s) for s in sensors]
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["connectivity"]] = counts.get(row["connectivity"], 0) + 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_sensors": len(rows),
        "connectivity_counts": counts,
        "sensors": rows,
    }


@router.post("/health/check")
def check_health(
    request: Request,
    user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    created = raise_offline_alerts(db)
    record_audit(
        db,
        actor=user.username,
        action="sensor.health_check",
        object_type="sensor_health",
        details={"alerts_created": len(created)},
    )
    db.commit()
    return {"alerts_created": len(created), "alert_ids": [a.id for a in created]}


@router.post("/simulate")
def simulate(
    request: Request,
    sensor_type: str | None = None,
    count: int = Query(default=1, ge=1, le=100),
    anomaly: bool = False,
    seed: int = 42,
    user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    existing_alert_ids = {row[0] for row in db.query(Alert.id).all()}
    try:
        results = simulate_batch(
            db,
            sensor_type=sensor_type,
            count=count,
            anomaly=anomaly,
            seed=seed,
        )
    except IngestValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record_audit(
        db,
        actor=user.username,
        action="sensor.simulate",
        object_type="simulation",
        details={"sensor_type": sensor_type, "count": count, "anomaly": anomaly},
    )
    db.commit()
    alert_ids = [r["alert_id"] for r in results if r.get("alert_id")]
    new_alert_ids = {alert_id for alert_id in alert_ids if alert_id not in existing_alert_ids}
    return {
        "status": "simulated",
        "source": "simulated",
        "readings_created": sum(1 for r in results if not r.get("duplicate")),
        "alerts_created": len(new_alert_ids),
        "alerts_triggered": len(set(alert_ids)),
        "results": results,
    }


@router.post("/seed-demo")
def seed_demo(
    user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    created = seed_demo_iot(db)
    record_audit(
        db,
        actor=user.username,
        action="sensor.seed_demo",
        object_type="simulation",
        details=created,
    )
    db.commit()
    return {"status": "seeded", **created, "source": "simulated"}


@router.get("/assessments")
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
