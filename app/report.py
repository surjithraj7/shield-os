from __future__ import annotations

from datetime import datetime, timezone

from app.api.anomaly_routes import _series
from app.ml.anomaly import scan_series
from app.models import (
    Alert,
    CalculatedResult,
    IotSensor,
    MonitoringData,
    RiskAssessment,
    SensorReading,
    ShmReading,
    ShieldParameter,
    SpatialAsset,
)
from app.spatial import evaluate_clearances

SEVERITY_COLOR = {"low": "#00cc66", "notice": "#ff8800", "warning": "#ffff00", "high": "#ff2d6f"}


def _html_escape(value) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _table(headers: list[str], rows: list[list]) -> str:
    if not rows:
        return "<p class='muted'>No data</p>"
    head = "".join(f"<th>{_html_escape(h)}</th>" for h in headers)
    body = ""
    for r in rows:
        cells = "".join(f"<td>{_html_escape(c)}</td>" for c in r)
        body += f"<tr>{cells}</tr>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def build_regulatory_report(db, start_x: float = 100.0, end_x: float = 244.0) -> str:
    shield_rows = db.query(ShieldParameter).order_by(ShieldParameter.ring_no.asc()).all()
    monitoring_rows = db.query(MonitoringData).order_by(MonitoringData.ring_no.asc()).all()
    calc_rows = db.query(CalculatedResult).order_by(CalculatedResult.ring_no.asc()).all()
    shm_rows = db.query(ShmReading).order_by(ShmReading.timestamp.desc()).limit(300).all()
    assets = db.query(SpatialAsset).all()
    iot_sensors = db.query(IotSensor).order_by(IotSensor.sensor_id.asc()).all()
    iot_readings = db.query(SensorReading).order_by(SensorReading.measured_at.desc()).limit(200).all()
    risk_rows = db.query(RiskAssessment).order_by(RiskAssessment.created_at.desc()).limit(100).all()
    alert_rows = db.query(Alert).order_by(Alert.created_at.desc()).limit(100).all()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    risk_counts: dict[str, int] = {}
    for r in calc_rows:
        risk_counts[r.risk_level] = risk_counts.get(r.risk_level, 0) + 1

    shm_types = {}
    for r in shm_rows:
        shm_types[r.sensor_type] = shm_types.get(r.sensor_type, 0) + 1

    anomalies = {}
    for name, (kind, attr) in {
        "Settlement": ("monitoring", "measured_value_mm"),
        "Thrust": ("shield", "thrust_kn"),
        "Advance Speed": ("shield", "advance_speed_mm_min"),
    }.items():
        scan = scan_series(_series(db, kind, attr))
        anomalies[name] = scan["flagged_count"]

    simulated_readings = sum(1 for r in iot_readings if r.source == "simulated")
    active_alerts = [a for a in alert_rows if a.status != "resolved"]
    critical_alerts = sum(1 for a in alert_rows if a.severity == "CRITICAL")

    clearance = evaluate_clearances(
        [
            {
                "id": a.id,
                "name": a.name,
                "asset_type": a.asset_type,
                "x_enu": a.x_enu,
                "y_enu": a.y_enu,
                "z_enu": a.z_enu,
                "radius_m": a.radius_m,
                "clearance_limit_m": a.clearance_limit_m,
                "note": a.note,
            }
            for a in assets
        ],
        start_x=start_x,
        end_x=end_x,
    )

    recent = calc_rows[-20:]
    recent_table = _table(
        ["Ring", "Chainage (m)", "Predicted (mm)", "Monitored (mm)", "Diff (mm)", "Err %", "Risk"],
        [
            [r.ring_no, round(r.chainage_m, 2), round(r.predicted_value_mm, 2),
             round(r.monitored_value_mm, 2), round(r.difference_mm, 2),
             round(r.relative_error_pct, 2), r.risk_level]
            for r in recent
        ],
    )

    shm_table = _table(
        ["Sensor", "Type", "Value", "Unit", "Status", "Time"],
        [
            [r.sensor_id, r.sensor_type, r.measured_value, r.unit, r.status, r.timestamp.isoformat()]
            for r in shm_rows[:20]
        ],
    )

    clearance_table = _table(
        ["Asset", "Type", "Distance (m)", "Clearance (m)", "Limit (m)", "Level"],
        [
            [c["name"], c["asset_type"], c["distance_m"], c["clearance_m"], c["clearance_limit_m"], c["level"]]
            for c in clearance["results"]
        ],
    )

    iot_table = _table(
        ["Sensor", "Type", "Unit", "Source", "Registered"],
        [
            [s.sensor_id, s.sensor_type, s.unit, s.source, s.created_at.isoformat()]
            for s in iot_sensors[:30]
        ],
    )

    risk_table = _table(
        ["Time", "Sensor", "Score", "Level", "Action", "Evidence"],
        [
            [r.created_at.isoformat(), r.sensor_id or "-", round(r.risk_score, 1),
             r.risk_category, r.recommendation, r.trigger]
            for r in risk_rows[:20]
        ],
    )

    alert_table = _table(
        ["Time", "Severity", "Title", "Status", "Sensor", "Occurrences"],
        [
            [a.created_at.isoformat(), a.severity, a.title, a.status,
             a.sensor_id or "-", a.occurrence_count]
            for a in alert_rows[:20]
        ],
    )

    worst_risk = max(calc_rows, key=lambda r: {"low": 0, "notice": 1, "warning": 2, "high": 3}.get(r.risk_level, 0)) if calc_rows else None

    if worst_risk is not None:
        settlement_cards = f"""<div class="grid">
    <div class="card"><b>{worst_risk.predicted_value_mm:.2f} mm</b><span>Worst-Risk Predicted</span></div>
    <div class="card"><b>{worst_risk.monitored_value_mm:.2f} mm</b><span>Worst-Risk Monitored</span></div>
    <div class="card"><b>{worst_risk.relative_error_pct:.2f}%</b><span>Relative Error (&lt;5% target)</span></div>
    <div class="card"><b>{'PASS' if worst_risk.relative_error_pct < 5.0 else 'FAIL'}</b><span>5% Threshold</span></div>
  </div>"""
    else:
        settlement_cards = "<p class='muted'>No calculated settlement results are available.</p>"

    total_err = sum(r.relative_error_pct for r in calc_rows) / len(calc_rows) if calc_rows else 0.0
    if calc_rows:
        validation_sentence = (
            "Settlement predictions were validated against monitored ground movement with a mean "
            f"relative error of <b>{total_err:.2f}%</b> (target &lt; 5%) on the available dataset."
        )
    else:
        validation_sentence = (
            "No calculated settlement results were available for validation in this reporting window."
        )

    def bar(label, value):
        return (
            f"<div class='bar-row'><span class='bar-label'>{label}</span>"
            f"<span class='bar-track'><span class='bar-fill' style='width:{value}%'></span></span>"
            f"<span class='bar-val'>{value}</span></div>"
        )

    max_risk = max(risk_counts.values(), default=1)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Engineering Monitoring Report - Intelligent Tunneling Management Platform</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e; margin: 0; padding: 32px; background: #f4f4f8; }}
  h1 {{ margin: 0; font-size: 22px; }}
  h2 {{ border-bottom: 3px solid #6a0dad; padding-bottom: 4px; margin-top: 28px; font-size: 16px; }}
  .head {{ background: linear-gradient(90deg, #6a0dad, #ff00ff); color: #fff; padding: 18px 22px; border-radius: 6px; }}
  .meta {{ color: #555; font-size: 12px; margin-top: 6px; }}
  .grid {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px; }}
  .card {{ background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 12px 16px; flex: 1 1 180px; }}
  .card b {{ display: block; font-size: 22px; }}
  .card span {{ font-size: 11px; color: #666; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 11px; margin-top: 8px; background: #fff; }}
  th, td {{ border: 1px solid #ccc; padding: 4px 8px; text-align: left; }}
  th {{ background: #eee; }}
  .muted {{ color: #888; }}
  .bar-row {{ display: flex; align-items: center; gap: 10px; margin: 4px 0; font-size: 12px; }}
  .bar-label {{ width: 130px; }}
  .bar-track {{ flex: 1; background: #eee; height: 12px; border-radius: 3px; }}
  .bar-fill {{ display: block; height: 12px; background: #6a0dad; border-radius: 3px; }}
  .bar-val {{ width: 36px; text-align: right; }}
  .foot {{ margin-top: 30px; font-size: 11px; color: #777; border-top: 1px solid #ccc; padding-top: 10px; }}
  .warn {{ color: #ff2d6f; font-weight: bold; }}
</style>
</head>
<body>
  <div class="head">
    <h1>Engineering Monitoring Report</h1>
    <div>Intelligent Tunneling Management Platform - Digital Twin Settlement &amp; SHM System</div>
    <div class="meta">Generated {now} &nbsp;|&nbsp; {_html_escape(shield_rows[0].line if shield_rows else 'Beijing Metro Line 12')} &nbsp;|&nbsp; {_html_escape(shield_rows[0].section if shield_rows else 'TBM-left-line')}</div>
  </div>

  <h2>1. Executive Summary</h2>
  <div class="grid">
    <div class="card"><b>{len(shield_rows)}</b><span>Rings Driven</span></div>
    <div class="card"><b>{len(calc_rows)}</b><span>Calculated Results</span></div>
    <div class="card"><b>{len(shm_rows)}</b><span>SHM Readings</span></div>
    <div class="card"><b>{total_err:.2f}%</b><span>Mean Relative Error</span></div>
    <div class="card"><b>{clearance['critical_count']}</b><span>Critical Clearances</span></div>
    <div class="card"><b>{sum(anomalies.values())}</b><span>ML Anomalies</span></div>
    <div class="card"><b>{len(iot_sensors)}</b><span>IoT Sensors Registered</span></div>
    <div class="card"><b>{len(active_alerts)}</b><span>Active Alerts</span></div>
  </div>

  <h2>2. Settlement Validation</h2>
  {settlement_cards}
  {recent_table}

  <h2>3. Alarm Distribution</h2>
  {''.join(bar(risk.capitalize(), round(risk_counts.get(risk, 0) / max_risk * 100, 1)) for risk in ('low', 'notice', 'warning', 'high'))}

  <h2>4. Structural Health Monitoring (SHM)</h2>
  <div class="grid">
    <div class="card"><b>{shm_types.get('seepage', 0)}</b><span>Seepage</span></div>
    <div class="card"><b>{shm_types.get('segment_displacement', 0)}</b><span>Segment Displacement</span></div>
    <div class="card"><b>{shm_types.get('lining_strain', 0)}</b><span>Lining Strain</span></div>
  </div>
  {shm_table}

  <h2>5. Spatial Clearance Analysis</h2>
  <div class="grid">
    <div class="card"><b>{clearance['critical_count']}</b><span>Critical (&le;60% limit)</span></div>
    <div class="card"><b>{clearance['warning_count']}</b><span>Warning (&le;limit)</span></div>
    <div class="card"><b>{clearance['safe_count']}</b><span>Safe</span></div>
  </div>
  {clearance_table}

  <h2>6. ML Anomaly Scan</h2>
  {''.join(f"<div class='bar-row'><span class='bar-label'>{name}</span><span class='bar-track'><span class='bar-fill' style='width:{min(100, (count / max(1, max(anomalies.values()))) * 100):.1f}%'></span></span><span class='bar-val'>{count}</span></div>" for name, count in anomalies.items())}

  <h2>7. IoT Risk Engine and Alert Lifecycle</h2>
  <div class="grid">
    <div class="card"><b>{len(iot_sensors)}</b><span>Registered Sensors</span></div>
    <div class="card"><b>{len(iot_readings)}</b><span>Recent Readings</span></div>
    <div class="card"><b>{simulated_readings}</b><span>Simulated Readings (Labelled)</span></div>
    <div class="card"><b>{len(risk_rows)}</b><span>Recent Risk Assessments</span></div>
    <div class="card"><b>{len(active_alerts)}</b><span>Active Alerts</span></div>
    <div class="card"><b>{critical_alerts}</b><span>Critical Alerts in Record</span></div>
  </div>
  <p class="muted">Simulated values are explicitly tagged with source "simulated" and must not be
  interpreted as field measurements.</p>
  <h3>Sensor Registry</h3>
  {iot_table}
  <h3>Risk Assessments</h3>
  {risk_table}
  <h3>Alert Records</h3>
  {alert_table}

  <h2>8. Compliance Declaration</h2>
  <p>{validation_sentence} The Beijing Metro Line 12 reference case (predicted 4.2 mm vs
  monitored 4.4 mm) is a benchmark, not a guarantee for other sites. Alarm thresholds,
  structural health monitoring, spatial clearance envelopes, IoT risk scores and ML anomaly
  screening are engineering decision-support outputs. They do not constitute a statutory
  certification and require review by a qualified tunnel engineer before field action.</p>

  <div class="foot">
    SHIELD-OS Digital Twin &nbsp;|&nbsp; Engineering Reporting Engine &nbsp;|&nbsp; Generated {now}
  </div>
</body>
</html>"""
    return html
