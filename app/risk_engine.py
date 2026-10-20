"""Explainable, configurable tunnel monitoring risk engine.

The engine deliberately separates three evidence sources:

1. Engineering threshold rules (configured per sensor type).
2. Statistical anomaly detection against the recent history of the same sensor.
3. Data-quality penalties (stale / out-of-order / suspect readings).

Threshold values shipped in ``DEFAULT_PROFILES`` are demonstrator defaults only.
They are **not** certified structural safety limits. Override them for a project
with the ``RISK_THRESHOLDS_JSON`` environment variable, for example::

    RISK_THRESHOLDS_JSON={"settlement":{"moderate":5,"high":10,"critical":20}}
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import numpy as np
from sqlalchemy.orm import Session

from app.models import Alert, RiskAssessment, SensorReading

CATEGORY_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}
CATEGORY_SCORE = {"LOW": 10.0, "MODERATE": 40.0, "HIGH": 70.0, "CRITICAL": 95.0}
ACTIVE_ALERT_STATUSES = ("open", "acknowledged", "investigating")

DEFAULT_PROFILES: dict[str, dict[str, Any]] = {
    "settlement": {"moderate": 5.0, "high": 10.0, "critical": 20.0, "unit": "mm"},
    "convergence": {"moderate": 3.0, "high": 6.0, "critical": 12.0, "unit": "mm"},
    "vibration": {"moderate": 2.5, "high": 5.0, "critical": 8.0, "unit": "mm/s"},
    "water_pressure": {"moderate": 100.0, "high": 200.0, "critical": 300.0, "unit": "kPa"},
    "groundwater_level": {"moderate": 1.0, "high": 2.0, "critical": 3.0, "unit": "m"},
    "temperature": {"moderate": 35.0, "high": 45.0, "critical": 55.0, "unit": "C"},
    "humidity": {"moderate": 80.0, "high": 90.0, "critical": 95.0, "unit": "%"},
    "gas_ch4": {"moderate": 10.0, "high": 20.0, "critical": 25.0, "unit": "%LEL"},
    "gas_co": {"moderate": 25.0, "high": 50.0, "critical": 100.0, "unit": "ppm"},
    "crack_width": {"moderate": 0.2, "high": 0.5, "critical": 1.0, "unit": "mm"},
    "seepage": {"moderate": 1.0, "high": 2.0, "critical": 4.0, "unit": "m3/day"},
    "strain": {"moderate": 250.0, "high": 400.0, "critical": 600.0, "unit": "ue"},
    "tbm_thrust": {"moderate": 30000.0, "high": 40000.0, "critical": 50000.0, "unit": "kN"},
    "tbm_torque": {"moderate": 4000.0, "high": 5000.0, "critical": 6000.0, "unit": "kNm"},
    "tbm_face_pressure": {"moderate": 400.0, "high": 500.0, "critical": 600.0, "unit": "kPa"},
}

RECOMMENDATIONS = {
    "settlement": "Verify the surface monitoring point and compare with adjacent points; review tail-void grouting and TBM face pressure.",
    "convergence": "Re-scan the ring with Ring-Eye, inspect segment joints, and check temporary support before continuing.",
    "vibration": "Inspect cutterhead and bearing condition, reduce advance rate if vibration continues, and review the vibration trend.",
    "water_pressure": "Check piezometer calibration and local drainage; inspect the face and tail seal for water ingress.",
    "groundwater_level": "Verify the piezometer and compare with nearby wells; check for unexpected water inflow.",
    "temperature": "Inspect sensor placement and ventilation; confirm whether the reading reflects equipment or ambient conditions.",
    "humidity": "Check ventilation and seal condition; verify the sensor is not saturated or fouled.",
    "gas_ch4": "Stop hot work, increase ventilation, evacuate if configured limits require it, and verify with a calibrated gas detector.",
    "gas_co": "Increase ventilation, remove personnel if required by site procedure, and verify with a calibrated detector.",
    "crack_width": "Inspect and document the crack, compare with previous readings, and request an engineering assessment.",
    "seepage": "Inspect the lining joint and drainage path, verify the flow measurement, and review grout records.",
    "strain": "Re-scan and inspect the instrumented ring; compare with the structural monitoring baseline.",
    "tbm_thrust": "Check thrust cylinders and the TBM control log; do not adjust setpoints without the shift engineer.",
    "tbm_torque": "Inspect cutterhead conditions and torque trend; coordinate any parameter change with the TBM operator.",
    "tbm_face_pressure": "Verify face pressure with the TBM control system and review EPB chamber conditions.",
    "default": "Verify the sensor, compare with nearby instruments, and escalate to the responsible engineer.",
}

STALE_FACTOR = 3.0
MAX_FUTURE_SECONDS = 300.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _load_overrides() -> dict[str, dict[str, Any]]:
    raw = os.environ.get("RISK_THRESHOLDS_JSON", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {k: v for k, v in parsed.items() if isinstance(v, dict)}


def threshold_profile(sensor_type: str) -> dict[str, Any]:
    """Return the effective threshold profile for a sensor type.

    Unknown sensor types intentionally return no numeric thresholds and are
    evaluated by statistical anomaly detection and data-quality rules only.
    """
    profile = dict(DEFAULT_PROFILES.get(sensor_type, {}))
    overrides = _load_overrides().get(sensor_type, {})
    profile.update(overrides)
    profile["threshold_source"] = (
        "environment_override" if overrides else ("builtin_demo" if sensor_type in DEFAULT_PROFILES else "none")
    )
    return profile


def _threshold_category(value: float, profile: dict[str, Any]) -> tuple[str, str | None]:
    if not {"moderate", "high", "critical"} <= profile.keys():
        return "LOW", None
    if value >= float(profile["critical"]):
        return "CRITICAL", f"value {value:g} >= critical threshold {float(profile['critical']):g}"
    if value >= float(profile["high"]):
        return "HIGH", f"value {value:g} >= high threshold {float(profile['high']):g}"
    if value >= float(profile["moderate"]):
        return "MODERATE", f"value {value:g} >= moderate threshold {float(profile['moderate']):g}"
    return "LOW", None


def _anomaly(
    value: float, history: Iterable[float], min_points: int = 5
) -> tuple[str, float, str | None]:
    values = [float(v) for v in history if math.isfinite(float(v))]
    if len(values) < min_points:
        return "LOW", 0.0, None
    arr = np.asarray(values, dtype=float)
    mean = float(arr.mean())
    std = float(arr.std())
    if std < 1e-12:
        delta = abs(value - mean)
        if delta > max(1e-9, abs(mean) * 0.02):
            return (
                "HIGH",
                0.0,
                f"statistical anomaly: step change of {delta:g} from constant baseline {mean:g}",
            )
        return "LOW", 0.0, None
    z = (value - mean) / std
    if abs(z) >= 4.0:
        return "HIGH", float(z), f"statistical anomaly z={z:.2f} against {len(values)} prior readings"
    if abs(z) >= 3.0:
        return "MODERATE", float(z), f"statistical anomaly z={z:.2f} against {len(values)} prior readings"
    return "LOW", float(z), None


def _trend(history: Iterable[float]) -> tuple[float, str | None]:
    values = [float(v) for v in history]
    if len(values) < 5:
        return 0.0, None
    recent = values[-5:]
    slope = float(np.polyfit(np.arange(len(recent)), np.asarray(recent), 1)[0])
    scale = max(abs(float(np.mean(recent))), 1e-9)
    if abs(slope) / scale < 0.05:
        return slope, None
    direction = "rising" if slope > 0 else "falling"
    return slope, f"{direction} trend over the last 5 readings ({slope:+.3g} per sample)"


def _max_category(a: str, b: str) -> str:
    return a if CATEGORY_ORDER[a] >= CATEGORY_ORDER[b] else b


def evaluate_value(
    sensor_type: str,
    value: float,
    unit: str,
    history: Iterable[float] = (),
    data_quality: str = "good",
    sensor_source: str = "simulated",
    measured_at: datetime | None = None,
    sampling_interval_s: float = 60.0,
) -> dict[str, Any]:
    """Evaluate one reading without touching the database.

    The returned dictionary is JSON-serializable and contains the evidence used
    for the classification so the dashboard and reports can explain it.
    """
    profile = threshold_profile(sensor_type)
    history_list = [float(v) for v in history]
    rule_category, rule_trigger = _threshold_category(value, profile)
    anomaly_category, zscore, anomaly_trigger = _anomaly(value, history_list)
    slope, trend_trigger = _trend(history_list)

    category = _max_category(rule_category, anomaly_category)
    triggers = [t for t in (rule_trigger, anomaly_trigger) if t]
    if trend_trigger:
        triggers.append(trend_trigger)

    quality = data_quality or "good"
    confidence = 0.85
    if sensor_source == "simulated":
        confidence = 0.55
    if quality in {"stale", "out_of_order", "suspect"}:
        confidence = min(confidence, 0.45)
        triggers.append(f"data quality: {quality}")
    if measured_at is not None:
        age_s = (_naive(_now()) - _naive(measured_at)).total_seconds()
        if age_s > max(60.0, sampling_interval_s * STALE_FACTOR):
            quality = "stale" if quality == "good" else quality
            confidence = min(confidence, 0.4)
            triggers.append(f"reading age {age_s:.0f}s exceeds freshness window")

    if category == "LOW" and not triggers:
        trigger = "within configured thresholds; no statistical anomaly"
    else:
        trigger = "; ".join(triggers) if triggers else "within configured thresholds"
    if category == "LOW" and trend_trigger:
        # A trend alone is not an alarm; expose it as an observation.
        trigger = trend_trigger

    score = CATEGORY_SCORE[category]
    if anomaly_category != "LOW" and category == anomaly_category:
        score = min(100.0, score + min(10.0, abs(zscore) * 1.5))
    if quality in {"stale", "out_of_order", "suspect"}:
        score = max(0.0, score - 5.0)

    return {
        "sensor_type": sensor_type,
        "value": float(value),
        "unit": unit,
        "risk_category": category,
        "risk_score": round(score, 2),
        "trigger": trigger,
        "recommendation": RECOMMENDATIONS.get(sensor_type, RECOMMENDATIONS["default"]),
        "data_quality": quality,
        "source": sensor_source,
        "confidence": round(confidence, 3),
        "zscore": round(zscore, 3),
        "trend_slope": round(slope, 6),
        "thresholds": {k: profile.get(k) for k in ("moderate", "high", "critical")},
        "threshold_source": profile.get("threshold_source", "none"),
        "evaluated_at": _now().isoformat(),
    }


def evaluate_reading(
    db: Session,
    sensor,
    reading: SensorReading,
    history_limit: int = 30,
    create_alert: bool = True,
) -> tuple[RiskAssessment, Alert | None]:
    """Persist a risk assessment for a reading and open/escalate an alert.

    The caller owns the transaction. This function flushes but does not commit.
    Duplicate alerts are prevented per ``sensor_id + rule trigger``; an existing
    active alert is escalated and its occurrence counter is incremented.
    """
    rows = (
        db.query(SensorReading)
        .filter(SensorReading.sensor_id == reading.sensor_id, SensorReading.id != reading.id)
        .order_by(SensorReading.measured_at.desc())
        .limit(history_limit)
        .all()
    )
    history = [r.value for r in reversed(rows)]
    result = evaluate_value(
        sensor_type=sensor.sensor_type,
        value=reading.value,
        unit=reading.unit,
        history=history,
        data_quality=reading.quality,
        sensor_source=reading.source,
        measured_at=reading.measured_at,
        sampling_interval_s=sensor.sampling_interval_s,
    )

    assessment = RiskAssessment(
        line=reading.line,
        section=reading.section,
        ring_no=reading.ring_no,
        chainage_m=reading.chainage_m,
        sensor_id=reading.sensor_id,
        sensor_type=sensor.sensor_type,
        value=reading.value,
        unit=reading.unit,
        risk_category=result["risk_category"],
        risk_score=result["risk_score"],
        trigger=result["trigger"][:256],
        recommendation=result["recommendation"][:512],
        data_quality=result["data_quality"],
        source=result["source"],
        confidence=result["confidence"],
        details_json=json.dumps({**result, "history_points": len(history)}),
    )
    db.add(assessment)
    db.flush()

    alert = None
    if create_alert and result["risk_category"] in {"MODERATE", "HIGH", "CRITICAL"}:
        alert = _upsert_alert(db, sensor, reading, assessment, result)
        assessment.alert_id = alert.id
        db.flush()
    return assessment, alert


def _upsert_alert(
    db: Session,
    sensor,
    reading: SensorReading,
    assessment: RiskAssessment,
    result: dict[str, Any],
) -> Alert:
    rule_key = "threshold" if "threshold" in result["trigger"] else "anomaly"
    dedupe_key = f"{sensor.sensor_id}:{sensor.sensor_type}:{rule_key}"
    alert = (
        db.query(Alert)
        .filter(Alert.dedupe_key == dedupe_key, Alert.status.in_(ACTIVE_ALERT_STATUSES))
        .order_by(Alert.created_at.desc())
        .first()
    )
    now = _now()
    severity = result["risk_category"]
    if alert:
        if CATEGORY_ORDER[severity] > CATEGORY_ORDER[alert.severity]:
            alert.severity = severity
            alert.title = f"{severity} {sensor.name}"
        alert.message = (
            f"{sensor.sensor_id} ({sensor.sensor_type}) reading {reading.value:g} {reading.unit}: "
            f"{result['trigger']}"
        )
        alert.trigger = result["trigger"][:256]
        alert.value = reading.value
        alert.assessment_id = assessment.id
        alert.last_seen_at = now
        alert.occurrence_count += 1
        alert.source = reading.source
        db.flush()
        return alert

    alert = Alert(
        dedupe_key=dedupe_key,
        title=f"{severity} {sensor.name}",
        message=(
            f"{sensor.sensor_id} ({sensor.sensor_type}) reading {reading.value:g} {reading.unit}: "
            f"{result['trigger']}"
        ),
        severity=severity,
        status="open",
        trigger=result["trigger"][:256],
        sensor_id=sensor.sensor_id,
        assessment_id=assessment.id,
        line=reading.line,
        section=reading.section,
        ring_no=reading.ring_no,
        chainage_m=reading.chainage_m,
        value=reading.value,
        unit=reading.unit,
        source=reading.source,
        created_at=now,
        last_seen_at=now,
    )
    db.add(alert)
    db.flush()
    return alert
