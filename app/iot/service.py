"""Sensor registry, validation, ingestion, health, and simulation.

Wi-Fi is intentionally treated as transport only. Devices (or a gateway)
submit measurements to the HTTP ingestion API; no Wi-Fi credentials are stored
in the application. Simulated measurements are always labelled
``source="simulated"`` in the database and API responses.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models import Alert, IotSensor, SensorReading
from app.risk_engine import evaluate_reading, threshold_profile

UTC = timezone.utc
MAX_FUTURE_SECONDS = 300.0

SUPPORTED_SENSOR_TYPES: dict[str, dict[str, str]] = {
    "settlement": {"unit": "mm", "description": "Surface or subsurface settlement"},
    "convergence": {"unit": "mm", "description": "Tunnel convergence / segment displacement"},
    "vibration": {"unit": "mm/s", "description": "Ground or structure vibration"},
    "water_pressure": {"unit": "kPa", "description": "Pore water / piezometric pressure"},
    "groundwater_level": {"unit": "m", "description": "Groundwater level above reference"},
    "temperature": {"unit": "C", "description": "Ambient or equipment temperature"},
    "humidity": {"unit": "%", "description": "Relative humidity"},
    "gas_ch4": {"unit": "%LEL", "description": "Methane concentration"},
    "gas_co": {"unit": "ppm", "description": "Carbon monoxide concentration"},
    "crack_width": {"unit": "mm", "description": "Crack or joint width"},
    "seepage": {"unit": "m3/day", "description": "Water ingress flow"},
    "strain": {"unit": "ue", "description": "Lining strain"},
    "tbm_thrust": {"unit": "kN", "description": "TBM total thrust"},
    "tbm_torque": {"unit": "kNm", "description": "Cutterhead torque"},
    "tbm_face_pressure": {"unit": "kPa", "description": "EPB face pressure"},
}

TYPE_ALIASES = {
    "surface_settlement": "settlement",
    "segment_displacement": "convergence",
    "deformation": "convergence",
    "pore_pressure": "water_pressure",
    "water_level": "groundwater_level",
    "gas": "gas_ch4",
    "methane": "gas_ch4",
    "carbon_monoxide": "gas_co",
    "joint_gap": "crack_width",
    "water_ingress": "seepage",
    "lining_strain": "strain",
    "thrust": "tbm_thrust",
    "torque": "tbm_torque",
    "face_pressure": "tbm_face_pressure",
}

UNIT_ALIASES = {
    "millimetre": "mm",
    "millimeter": "mm",
    "millimetres": "mm",
    "millimeters": "mm",
    "centimetre": "cm",
    "centimeter": "cm",
    "metre": "m",
    "meter": "m",
    "metres": "m",
    "meters": "m",
    "m/s": "mm/s",
    "mm/sec": "mm/s",
    "kpa": "kPa",
    "mpa": "MPa",
    "pa": "Pa",
    "bar": "bar",
    "c": "C",
    "degc": "C",
    "°c": "C",
    "percent": "%",
    "pct": "%",
    "%lel": "%LEL",
    "lel": "%LEL",
    "m3/d": "m3/day",
    "m3/day": "m3/day",
    "m³/day": "m3/day",
    "microstrain": "ue",
    "µε": "ue",
    "knm": "kNm",
    "kn": "kN",
}

LENGTH_TO_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0}
PRESSURE_TO_KPA = {"Pa": 0.001, "kPa": 1.0, "MPa": 1000.0, "bar": 100.0}

QUALITY_VALUES = {"good", "suspect", "stale", "out_of_order"}


class IngestValidationError(ValueError):
    """Raised when an ingestion payload cannot be accepted safely."""


def canonical_sensor_type(sensor_type: str) -> str:
    cleaned = sensor_type.strip().lower().replace(" ", "_").replace("-", "_")
    cleaned = TYPE_ALIASES.get(cleaned, cleaned)
    if cleaned not in SUPPORTED_SENSOR_TYPES:
        supported = ", ".join(sorted(SUPPORTED_SENSOR_TYPES))
        raise IngestValidationError(f"Unsupported sensor_type '{sensor_type}'. Supported: {supported}")
    return cleaned


def canonical_unit(unit: str) -> str:
    cleaned = unit.strip()
    return UNIT_ALIASES.get(cleaned.lower(), cleaned)


def convert_value(value: float, from_unit: str, to_unit: str) -> float:
    source = canonical_unit(from_unit)
    target = canonical_unit(to_unit)
    if source == target:
        return float(value)
    if source in LENGTH_TO_MM and target in LENGTH_TO_MM:
        return float(value) * LENGTH_TO_MM[source] / LENGTH_TO_MM[target]
    if source in PRESSURE_TO_KPA and target in PRESSURE_TO_KPA:
        return float(value) * PRESSURE_TO_KPA[source] / PRESSURE_TO_KPA[target]
    raise IngestValidationError(f"Incompatible units '{from_unit}' -> '{to_unit}'")


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def default_event_id(sensor_id: str, measured_at: datetime, value: float, unit: str) -> str:
    material = f"{sensor_id}|{measured_at.isoformat()}|{value:.12g}|{unit}"
    return "auto-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:48]


def register_sensor(db: Session, payload: dict[str, Any]) -> IotSensor:
    sensor_type = canonical_sensor_type(payload["sensor_type"])
    expected_unit = SUPPORTED_SENSOR_TYPES[sensor_type]["unit"]
    unit = canonical_unit(payload.get("unit") or expected_unit)
    if unit != expected_unit:
        raise IngestValidationError(
            f"Sensor type '{sensor_type}' uses unit '{expected_unit}', not '{unit}'"
        )
    sensor_id = payload["sensor_id"].strip()
    if not sensor_id:
        raise IngestValidationError("sensor_id is required")
    if db.query(IotSensor).filter(IotSensor.sensor_id == sensor_id).first():
        raise IngestValidationError(f"Sensor '{sensor_id}' is already registered")
    min_value = payload.get("min_value")
    max_value = payload.get("max_value")
    for label, bound in (("min_value", min_value), ("max_value", max_value)):
        if bound is not None and not math.isfinite(float(bound)):
            raise IngestValidationError(f"{label} must be finite")
    if min_value is not None and max_value is not None and float(min_value) >= float(max_value):
        raise IngestValidationError("min_value must be lower than max_value")
    row = IotSensor(
        sensor_id=sensor_id,
        name=payload.get("name") or sensor_id,
        sensor_type=sensor_type,
        unit=unit,
        line=payload.get("line", "Beijing Metro Line 12"),
        section=payload.get("section", "TBM-left-line"),
        ring_no=int(payload.get("ring_no", 0)),
        chainage_m=float(payload.get("chainage_m", 0.0)),
        location_note=payload.get("location_note", "")[:256],
        status=payload.get("status", "active"),
        source=payload.get("source", "simulated"),
        min_value=float(min_value) if min_value is not None else None,
        max_value=float(max_value) if max_value is not None else None,
        sampling_interval_s=float(payload.get("sampling_interval_s", 60.0)),
    )
    if row.sampling_interval_s <= 0:
        raise IngestValidationError("sampling_interval_s must be positive")
    db.add(row)
    db.flush()
    return row


def get_sensor(db: Session, sensor_id: str) -> IotSensor | None:
    return db.query(IotSensor).filter(IotSensor.sensor_id == sensor_id).first()


def ingest_reading(
    db: Session,
    payload: dict[str, Any],
    *,
    evaluate: bool = True,
) -> dict[str, Any]:
    """Validate, normalize, persist, and optionally risk-assess a reading."""
    sensor_id = str(payload.get("sensor_id", "")).strip()
    sensor = get_sensor(db, sensor_id)
    if sensor is None:
        raise IngestValidationError(f"Unknown sensor '{sensor_id}'")

    value = payload.get("value", payload.get("measured_value"))
    if value is None:
        raise IngestValidationError("value (or measured_value) is required")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise IngestValidationError("value must be numeric") from exc
    if not math.isfinite(numeric):
        raise IngestValidationError("value must be finite")

    unit = canonical_unit(str(payload.get("unit") or sensor.unit))
    numeric = convert_value(numeric, unit, sensor.unit)

    measured_at = payload.get("measured_at") or payload.get("timestamp") or utcnow_naive()
    if isinstance(measured_at, str):
        try:
            measured_at = datetime.fromisoformat(measured_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise IngestValidationError("measured_at must be an ISO-8601 timestamp") from exc
    if not isinstance(measured_at, datetime):
        raise IngestValidationError("measured_at must be a timestamp")
    measured_naive = _naive_utc(measured_at)
    now = utcnow_naive()
    if (measured_naive - now).total_seconds() > MAX_FUTURE_SECONDS:
        raise IngestValidationError("measured_at is too far in the future")

    if sensor.min_value is not None and numeric < sensor.min_value:
        raise IngestValidationError(
            f"value {numeric:g} is below sensor minimum {sensor.min_value:g} {sensor.unit}"
        )
    if sensor.max_value is not None and numeric > sensor.max_value:
        raise IngestValidationError(
            f"value {numeric:g} is above sensor maximum {sensor.max_value:g} {sensor.unit}"
        )

    quality = str(payload.get("quality", "good")).lower()
    if quality not in QUALITY_VALUES:
        raise IngestValidationError(f"quality must be one of {sorted(QUALITY_VALUES)}")

    event_id = str(payload.get("event_id") or "").strip()
    if not event_id:
        event_id = default_event_id(sensor.sensor_id, measured_naive, numeric, sensor.unit)

    existing = db.query(SensorReading).filter(SensorReading.event_id == event_id).first()
    if existing is not None:
        return {
            "status": "duplicate",
            "duplicate": True,
            "event_id": event_id,
            "reading_id": existing.id,
            "sensor_id": existing.sensor_id,
        }

    latest = (
        db.query(SensorReading)
        .filter(SensorReading.sensor_id == sensor.sensor_id)
        .order_by(SensorReading.measured_at.desc())
        .first()
    )
    if latest is not None and measured_naive < _naive_utc(latest.measured_at):
        quality = "out_of_order"

    source = str(payload.get("source") or sensor.source)
    if source not in {"real", "simulated", "manual"}:
        raise IngestValidationError("source must be one of: real, simulated, manual")

    reading = SensorReading(
        event_id=event_id,
        sensor_id=sensor.sensor_id,
        line=sensor.line,
        section=sensor.section,
        ring_no=sensor.ring_no,
        chainage_m=sensor.chainage_m,
        value=numeric,
        unit=sensor.unit,
        measured_at=measured_naive,
        received_at=now,
        quality=quality,
        source=source,
        raw_json=json.dumps(
            {
                "submitted_unit": unit,
                "submitted_value": value,
                "event_id": event_id,
                "device_id": payload.get("device_id"),
                "gateway_id": payload.get("gateway_id"),
                "payload": {k: v for k, v in payload.items() if k not in {"value", "measured_value"}},
            },
            default=str,
        ),
    )
    db.add(reading)
    db.flush()

    if sensor.last_seen_at is None or _naive_utc(sensor.last_seen_at) < measured_naive:
        sensor.last_seen_at = measured_naive
    if sensor.status == "offline":
        sensor.status = "active"

    alert = None
    assessment = None
    if evaluate:
        assessment, alert = evaluate_reading(db, sensor, reading)

    return {
        "status": "accepted",
        "duplicate": False,
        "event_id": event_id,
        "reading_id": reading.id,
        "sensor_id": reading.sensor_id,
        "value": reading.value,
        "unit": reading.unit,
        "quality": reading.quality,
        "source": reading.source,
        "risk": {
            "category": assessment.risk_category,
            "score": assessment.risk_score,
            "trigger": assessment.trigger,
            "recommendation": assessment.recommendation,
            "data_quality": assessment.data_quality,
            "source": assessment.source,
            "confidence": assessment.confidence,
        }
        if assessment
        else None,
        "alert_id": alert.id if alert else None,
    }


def sensor_health(sensor: IotSensor, now: datetime | None = None) -> dict[str, Any]:
    now_naive = _naive_utc(now or datetime.now(UTC))
    timeout = max(60.0, sensor.sampling_interval_s * 3.0)
    last_seen = _naive_utc(sensor.last_seen_at) if sensor.last_seen_at else None
    if last_seen is None:
        state = "never_seen"
        age = None
    else:
        age = max(0.0, (now_naive - last_seen).total_seconds())
        if age <= timeout:
            state = "online"
        elif age <= timeout * 2:
            state = "stale"
        else:
            state = "offline"
    return {
        "sensor_id": sensor.sensor_id,
        "name": sensor.name,
        "sensor_type": sensor.sensor_type,
        "unit": sensor.unit,
        "status": sensor.status,
        "connectivity": state,
        "last_seen_at": last_seen.isoformat() if last_seen else None,
        "age_s": round(age, 1) if age is not None else None,
        "stale_after_s": round(timeout, 1),
        "sampling_interval_s": sensor.sampling_interval_s,
        "source": sensor.source,
        "line": sensor.line,
        "section": sensor.section,
        "ring_no": sensor.ring_no,
        "chainage_m": sensor.chainage_m,
    }


def raise_offline_alerts(db: Session) -> list[Alert]:
    """Open health alerts for sensors that previously reported but are offline."""
    created: list[Alert] = []
    now = utcnow_naive()
    for sensor in db.query(IotSensor).all():
        health = sensor_health(sensor, now)
        if health["connectivity"] not in {"offline", "stale"}:
            continue
        if sensor.last_seen_at is None:
            continue
        dedupe_key = f"{sensor.sensor_id}:{sensor.sensor_type}:sensor_health"
        active = (
            db.query(Alert)
            .filter(Alert.dedupe_key == dedupe_key, Alert.status.in_(("open", "acknowledged", "investigating")))
            .first()
        )
        if active:
            active.last_seen_at = now
            active.occurrence_count += 1
            continue
        severity = "HIGH" if health["connectivity"] == "offline" else "MODERATE"
        alert = Alert(
            dedupe_key=dedupe_key,
            title=f"{severity} sensor connectivity: {sensor.name}",
            message=(
                f"{sensor.sensor_id} has not reported for {health['age_s']} s "
                f"(stale after {health['stale_after_s']} s)."
            ),
            severity=severity,
            status="open",
            trigger=f"sensor connectivity {health['connectivity']}",
            sensor_id=sensor.sensor_id,
            line=sensor.line,
            section=sensor.section,
            ring_no=sensor.ring_no,
            chainage_m=sensor.chainage_m,
            value=0.0,
            unit=sensor.unit,
            source=sensor.source,
            created_at=now,
            last_seen_at=now,
        )
        db.add(alert)
        created.append(alert)
    db.flush()
    return created


DEMO_SENSORS = [
    ("SIM-SETTLE-018", "Settlement point SP-018", "settlement", 18, 121.6, -50.0, 80.0, "Surface settlement array near Building B-01"),
    ("SIM-CONV-024", "Convergence array CV-024", "convergence", 24, 128.8, -20.0, 20.0, "Ring convergence monitoring array"),
    ("SIM-VIB-030", "Vibration monitor VB-030", "vibration", 30, 136.0, 0.0, 30.0, "Ground vibration monitoring point"),
    ("SIM-PIEZO-033", "Piezometer PZ-033", "water_pressure", 33, 139.6, 0.0, 400.0, "Pore pressure monitoring point"),
    ("SIM-GW-019", "Standpipe GW-019", "groundwater_level", 19, 122.8, 0.0, 8.0, "Groundwater level monitoring well"),
    ("SIM-TEMP-001", "Tunnel temperature TH-01", "temperature", 21, 125.2, -20.0, 80.0, "Ambient temperature / humidity station"),
    ("SIM-GAS-001", "Methane detector CH4-01", "gas_ch4", 28, 133.6, 0.0, 100.0, "Gas monitoring station at ring 28"),
]


def seed_demo_iot(db: Session) -> dict[str, int]:
    """Create clearly labelled simulated sensors and a short baseline history."""
    if db.query(IotSensor).count() > 0:
        return {"sensors": 0, "readings": 0}
    rng = random.Random(2026)
    sensors: list[IotSensor] = []
    for sensor_id, name, stype, ring, chainage, min_value, max_value, note in DEMO_SENSORS:
        sensor = IotSensor(
            sensor_id=sensor_id,
            name=name,
            sensor_type=stype,
            unit=SUPPORTED_SENSOR_TYPES[stype]["unit"],
            line="Beijing Metro Line 12",
            section="TBM-left-line",
            ring_no=ring,
            chainage_m=chainage,
            location_note=note,
            status="active",
            source="simulated",
            min_value=min_value,
            max_value=max_value,
            sampling_interval_s=300.0,
        )
        db.add(sensor)
        sensors.append(sensor)
    db.flush()

    baselines = {
        "settlement": 2.2,
        "convergence": 1.1,
        "vibration": 1.4,
        "water_pressure": 95.0,
        "groundwater_level": 0.6,
        "temperature": 24.0,
        "gas_ch4": 1.8,
    }
    now = utcnow_naive()
    reading_count = 0
    for sensor in sensors:
        base = baselines.get(sensor.sensor_type, 1.0)
        for i in range(12):
            measured = now - timedelta(seconds=sensor.sampling_interval_s * (11 - i))
            drift = base * 0.002 * i
            noise = rng.uniform(-0.02, 0.02) * max(abs(base), 1.0)
            value = base + drift + noise
            db.add(
                SensorReading(
                    event_id=f"seed-{sensor.sensor_id}-{i:03d}",
                    sensor_id=sensor.sensor_id,
                    line=sensor.line,
                    section=sensor.section,
                    ring_no=sensor.ring_no,
                    chainage_m=sensor.chainage_m,
                    value=round(value, 4),
                    unit=sensor.unit,
                    measured_at=measured,
                    received_at=now,
                    quality="good",
                    source="simulated",
                    raw_json=json.dumps({"seeded_demo": True}),
                )
            )
            reading_count += 1
        sensor.last_seen_at = now
    db.flush()

    # Assess the newest seeded reading per sensor for traceable demo results.
    for sensor in sensors:
        latest = (
            db.query(SensorReading)
            .filter(SensorReading.sensor_id == sensor.sensor_id)
            .order_by(SensorReading.measured_at.desc())
            .first()
        )
        if latest is not None:
            evaluate_reading(db, sensor, latest)
    db.commit()
    return {"sensors": len(sensors), "readings": reading_count}


SIM_BASELINES = {
    "settlement": (2.4, 0.25),
    "convergence": (1.2, 0.18),
    "vibration": (1.5, 0.22),
    "water_pressure": (95.0, 4.0),
    "groundwater_level": (0.55, 0.05),
    "temperature": (24.0, 0.6),
    "humidity": (64.0, 2.5),
    "gas_ch4": (1.8, 0.25),
    "gas_co": (4.0, 1.0),
    "crack_width": (0.04, 0.01),
    "seepage": (0.25, 0.03),
    "strain": (150.0, 8.0),
    "tbm_thrust": (15000.0, 600.0),
    "tbm_torque": (2500.0, 120.0),
    "tbm_face_pressure": (280.0, 12.0),
}


def simulate_reading(
    db: Session,
    sensor: IotSensor,
    *,
    anomaly: bool = False,
    measured_at: datetime | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    rng = rng or random.Random()
    base, spread = SIM_BASELINES.get(sensor.sensor_type, (1.0, 0.1))
    value = base + rng.gauss(0.0, spread)
    if anomaly:
        profile = threshold_profile(sensor.sensor_type)
        critical = profile.get("critical")
        value = float(critical) * 1.08 if critical else base * 4.0
    return ingest_reading(
        db,
        {
            "sensor_id": sensor.sensor_id,
            "value": value,
            "unit": sensor.unit,
            "measured_at": measured_at or utcnow_naive(),
            "source": "simulated",
            "event_id": f"sim-{sensor.sensor_id}-{uuid.uuid4().hex}",
            "quality": "good",
        },
    )


def simulate_batch(
    db: Session,
    *,
    sensor_type: str | None = None,
    count: int = 1,
    anomaly: bool = False,
    seed: int = 42,
) -> list[dict[str, Any]]:
    query = db.query(IotSensor).filter(IotSensor.status == "active")
    if sensor_type:
        query = query.filter(IotSensor.sensor_type == canonical_sensor_type(sensor_type))
    sensors = query.order_by(IotSensor.sensor_id).all()
    if not sensors:
        raise IngestValidationError("No active sensors match the simulation request")
    rng = random.Random(seed)
    results = []
    now = utcnow_naive()
    for sensor in sensors:
        for i in range(count):
            # Simulated packets are one second apart so a batch is strictly
            # ordered and remains inside the accepted future-time window.
            measured = now + timedelta(seconds=i)
            results.append(
                simulate_reading(
                    db,
                    sensor,
                    anomaly=anomaly and i == count - 1,
                    measured_at=measured,
                    rng=rng,
                )
            )
    db.commit()
    return results


def sensor_to_dict(sensor: IotSensor) -> dict[str, Any]:
    return {
        "sensor_id": sensor.sensor_id,
        "name": sensor.name,
        "sensor_type": sensor.sensor_type,
        "unit": sensor.unit,
        "line": sensor.line,
        "section": sensor.section,
        "ring_no": sensor.ring_no,
        "chainage_m": sensor.chainage_m,
        "location_note": sensor.location_note,
        "status": sensor.status,
        "source": sensor.source,
        "min_value": sensor.min_value,
        "max_value": sensor.max_value,
        "sampling_interval_s": sensor.sampling_interval_s,
        "last_seen_at": sensor.last_seen_at.isoformat() if sensor.last_seen_at else None,
        "created_at": sensor.created_at.isoformat() if sensor.created_at else None,
        "supported_types": sorted(SUPPORTED_SENSOR_TYPES),
    }
