from __future__ import annotations

from sqlalchemy.orm import Session

from app.ml.anomaly import scan_series, severity
from app.models import CalculatedResult, MonitoringData, ShmReading, ShieldParameter, SpatialAsset

WINDOW_IDS = {
    "geo": "win-sensor",
    "camera": "win-camera",
    "risks": "win-alerts",
    "settlement": "win-settlement",
    "twin": "win-twin",
    "dashboard": "win-dashboard",
    "shm": "win-shm",
    "anomaly": "win-anomaly",
    "transfer": "win-transfer",
    "spatial": "win-spatial",
    "report": "win-report",
    "assistant": "win-ai",
}

SOFTWARE_GUIDE = """TUNNELARCHITECT-AI ASSISTANT - PLATFORM GUIDE
I can help you operate every module of the Intelligent Tunneling Management Platform.

DESKTOP ICONS / MODULES:
- GEO DATA (SENSOR.EXE) - live cutterhead metrics: thrust, torque, advance speed, grout pressure.
- CUTTERHEAD (CAMERA.EXE) - CCTV tunnel-face feed with AR overlay markers.
- RISK REPORTS (ALERTS.LOG) - active risk sources from monitored calculations.
- SETTLEMENT (SETTLEMENT.PLT) - predicted vs monitored settlement curve + calibration.
- CYBER TWIN (TWIN.EXE) - 3D digital twin of the shield + ground, live metrics HUD.
- TBM DASHBOARD (TBM-DASH.EXE) - real-time monitoring dashboard: KPI sparklines
  (penetration speed, thrust force, soil volume), interactive 3D TBM model with a glowing
  orange cutter head, personnel count chart and construction cost tracker.
- SHM (SHM.EXE) - structural health monitor: seepage, segment displacement, lining strain.
- ANOMALY AI (ANOMALY.AI) - rolling z-score ML engine flagging abnormal sensor values.
- TRANSFER (TRANSFER.AI) - A/B/C segment experience transfer for parameter tuning.
- SPATIAL (SPATIAL.PLN) - 3D clearance planning against nearby assets.
- REPORT (REPORT.EXE) - auto-generate regulatory compliance report (downloads HTML).
- AI ASSIST (this window) - ask me anything; I can open modules, build 3D designs,
  run analysis and generate reports for you.

HOW TO USE:
1. Click a desktop icon to open that module. Double-click to maximize.
2. Use the taskbar tabs to restore minimized windows; X closes, _ minimizes.
3. Right-click the desktop for quick actions (refresh, export, calibrate, thresholds).

ASK ME, for example:
- "how do I generate a report?"
- "open the cyber twin"
- "create a TBM design with sensors"
- "analyse the settlement data"
- "show me the live status"
- "what is the platform?" """


def _template_tbm() -> list[dict]:
    return [
        {"id": "a1", "type": "tbm", "name": "TBM Shell", "position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1], "color": 0x6a0dad},
        {"id": "a2", "type": "cutter", "name": "Cutterhead", "position": [0, 0, 4.6], "rotation": [0, 0, 0], "scale": [1, 1, 1], "color": 0xff00ff},
        {"id": "a3", "type": "ring", "name": "Ring R-01", "position": [0, 0, -4.5], "rotation": [0, 0, 0], "scale": [1, 1, 1], "color": 0x008080},
        {"id": "a4", "type": "ring", "name": "Ring R-02", "position": [0, 0, -6.2], "rotation": [0, 0, 0], "scale": [1, 1, 1], "color": 0x008080},
        {"id": "a5", "type": "sensor", "name": "Settlement Sensor S-01", "position": [0, 4.6, -6], "rotation": [0, 0, 0], "scale": [1, 1, 1], "color": 0xff8800},
        {"id": "a6", "type": "sensor", "name": "Strain Gauge SG-01", "position": [3.4, 2.4, -5.5], "rotation": [0, 0, 0], "scale": [0.8, 0.8, 0.8], "color": 0xff8800},
        {"id": "a7", "type": "pipe", "name": "Grout Pipe G-01", "position": [3.6, 0, -7], "rotation": [0, 0, 0], "scale": [1, 1, 1], "color": 0xffff00},
        {"id": "a8", "type": "strut", "name": "Steel Strut ST-01", "position": [0, -1.8, -1], "rotation": [0, 0, 0], "scale": [1, 1, 1], "color": 0xc0c0c0},
        {"id": "a9", "type": "beacon", "name": "Survey Beacon B-01", "position": [-3.6, 0.4, -8], "rotation": [0, 0, 0], "scale": [1, 1, 1], "color": 0xff2d6f},
    ]


def _template_sensors(n: int = 8) -> list[dict]:
    parts = []
    for i in range(n):
        parts.append(
            {
                "id": f"s{i:02d}",
                "type": "sensor",
                "name": f"Instrument Sensor S-{i:02d}",
                "position": [i * 2.0 - (n - 1), 0, 0],
                "rotation": [0, 0, 0],
                "scale": [0.6, 0.6, 0.6],
                "color": 0xff8800,
            }
        )
    parts.append(
        {"id": "sm", "type": "beacon", "name": "Master Beacon", "position": [0, 2.2, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1], "color": 0xff2d6f}
    )
    return parts


def _template_tunnel() -> list[dict]:
    parts = []
    for i in range(6):
        parts.append(
            {
                "id": f"r{i:02d}",
                "type": "ring",
                "name": f"Ring R-{i + 1:02d}",
                "position": [0, 0, -i * 1.7],
                "rotation": [0, 0, 0],
                "scale": [1, 1, 1],
                "color": 0x008080,
            }
        )
    for i in range(3):
        parts.append(
            {
                "id": f"p{i:02d}",
                "type": "pipe",
                "name": f"Grout Pipe G-{i + 1:02d}",
                "position": [3.4, 0, -i * 3.4 - 1],
                "rotation": [0, 0, 0],
                "scale": [1, 1, 1],
                "color": 0xffff00,
            }
        )
        parts.append(
            {
                "id": f"b{i:02d}",
                "type": "beacon",
                "name": f"Survey Beacon B-{i + 1:02d}",
                "position": [-3.4, 0.4, -i * 3.4 - 1],
                "rotation": [0, 0, 0],
                "scale": [1, 1, 1],
                "color": 0xff2d6f,
            }
        )
    return parts


def _design(request_text: str) -> list[dict] | None:
    text = request_text.lower()
    if any(k in text for k in ["tbm", "cutter", "shield machine", "machine"]):
        return _template_tbm()
    if any(k in text for k in ["sensor", "instrument", "gauge", "array", "monitoring"]):
        return _template_sensors()
    if any(k in text for k in ["tunnel", "ring", "segment", "section"]):
        return _template_tunnel()
    return _template_tbm()


def _analyse(db: Session) -> str:
    calc_rows = db.query(CalculatedResult).order_by(CalculatedResult.ring_no.asc()).all()
    shield_rows = db.query(ShieldParameter).order_by(ShieldParameter.ring_no.asc()).all()
    mon_rows = db.query(MonitoringData).order_by(MonitoringData.ring_no.asc()).all()
    shm_rows = db.query(ShmReading).all()

    lines = ["ANALYSIS SUMMARY", "-" * 46]

    if calc_rows:
        last = calc_rows[-1]
        mean_err = sum(abs(c.relative_error_pct) for c in calc_rows) / len(calc_rows)
        worst = max(calc_rows, key=lambda c: abs(c.relative_error_pct))
        lines.append(f"RINGS EVALUATED: {len(calc_rows)} (up to ring {last.ring_no})")
        lines.append(f"LATEST: predicted {last.predicted_value_mm:.2f}mm vs monitored {last.monitored_value_mm or 0:.2f}mm -> err {abs(last.relative_error_pct):.2f}%")
        lines.append(f"MEAN |ERR|: {mean_err:.2f}%  |  WORST RING {worst.ring_no}: {abs(worst.relative_error_pct):.2f}%")
        green = sum(1 for c in calc_rows if c.risk_level in ("green", "low"))
        lines.append(f"RISK DISTRIBUTION: {green}/{len(calc_rows)} rings within green band")
    else:
        lines.append("NO CALCULATED RINGS YET.")

    if shield_rows:
        s = shield_rows[-1]
        lines.append(
            f"CUTTERHEAD (ring {s.ring_no}): thrust {s.thrust_kn:.0f}kN, torque {s.torque_knm:.0f}kNm, "
            f"speed {s.advance_speed_mm_min:.1f}mm/min, grout {s.grouting_pressure_mpa:.2f}MPa"
        )

    if mon_rows:
        vals = [float(m.measured_value_mm) for m in mon_rows]
        lines.append(f"MONITORING: {len(vals)} points, max {max(vals):.2f}mm, mean {sum(vals) / len(vals):.2f}mm")

    for name, series in [("settlement", [float(m.measured_value_mm) for m in mon_rows])]:
        scan = scan_series(series)
        if scan["flagged_count"]:
            lines.append(f"ANOMALY ENGINE: {scan['flagged_count']} settlement point(s) flagged (z>=2.5)")
        else:
            lines.append("ANOMALY ENGINE: no settlement outliers flagged.")

    alerts = [r for r in shm_rows if r.status != "normal"]
    lines.append(f"SHM: {len(shm_rows)} readings, {len(alerts)} alert(s).")

    critical = [a for a in db.query(SpatialAsset).all() if a.clearance_limit_m and a.radius_m >= a.clearance_limit_m]
    if critical:
        lines.append(f"SPATIAL: {len(critical)} asset(s) at/beyond clearance limit (see SPATIAL.PLN).")
    else:
        lines.append("SPATIAL: all assets within clearance limits.")

    lines.append("-" * 46)
    lines.append("RECOMMENDATION: open ANOMALY.AI for flagged points, CYBER TWIN for live geometry,")
    lines.append("and REPORT.EXE to generate the regulatory compliance report.")
    return "\n".join(lines)


def _status(db: Session) -> str:
    calc_rows = db.query(CalculatedResult).order_by(CalculatedResult.ring_no.asc()).all()
    shield_rows = db.query(ShieldParameter).order_by(ShieldParameter.ring_no.asc()).all()
    shm_rows = db.query(ShmReading).all()
    assets = db.query(SpatialAsset).all()

    lines = ["LIVE STATUS", "-" * 40]
    last = calc_rows[-1] if calc_rows else None
    s = shield_rows[-1] if shield_rows else None
    lines.append(f"RINGS DRIVEN: {len(calc_rows)}" + (f" (latest ring {last.ring_no})" if last else ""))
    if last and last.monitored_value_mm is not None:
        lines.append(
            f"SETTLEMENT: predicted {last.predicted_value_mm:.2f}mm vs monitored {last.monitored_value_mm:.2f}mm "
            f"(err {abs(last.relative_error_pct):.2f}%)"
        )
    elif last:
        lines.append(f"SETTLEMENT: predicted {last.predicted_value_mm:.2f}mm (monitoring pending)")
    if s:
        lines.append(
            f"CUTTERHEAD: thrust {s.thrust_kn:.0f}kN | torque {s.torque_knm:.0f}kNm | speed {s.advance_speed_mm_min:.1f}mm/min | "
            f"grout {s.grouting_pressure_mpa:.2f}MPa"
        )
    alerts = [r for r in shm_rows if r.status != "normal"]
    lines.append(f"SHM: {len(shm_rows)} readings, {len(alerts)} alert(s)")
    lines.append(f"SPATIAL ASSETS: {len(assets)} monitored")
    lines.append("PLATFORM: ONLINE - all systems nominal.")
    return "\n".join(lines)


def _guide(request_text: str) -> tuple[str, list[str]]:
    text = request_text.lower()
    if any(k in text for k in ["report", "regulatory", "pdf", "compliance", "export"]):
        return (
            "REPORT GENERATION:\n1. Open the REPORT.EXE module (desktop icon 'Report').\n"
            "2. Click GENERATE - the platform builds the regulatory compliance report and downloads\n"
            "   shield_regulatory_report.html automatically.\n"
            "3. You can also just tell me 'generate the report' and I will open it for you.",
            ["report"],
        )
    if any(k in text for k in ["twin", "3d", "digital twin", "cyber"]):
        return (
            "DIGITAL CYBER TWIN:\nOpen the 'Cyber Twin' icon (TWIN.EXE) for a real-time 3D model of the "
            "shield, ground and tunnel rings with a live metrics HUD.\n"
            "Rotate: left-drag. Pan: right-drag. Zoom: scroll. The twin refreshes every 6 seconds.",
            ["twin"],
        )
    if any(k in text for k in ["editor", "design", "dashboard", "monitor"]):
        return (
            "TBM MONITORING DASHBOARD:\nOpen the 'TBM Dash' icon (TBM-DASH.EXE).\n"
            "- Top: live KPI cards with sparklines - Penetration Speed, Thrust Force, Soil Volume.\n"
            "- Right: an interactive 3D TBM model - drag to rotate, scroll to zoom, and use the\n"
            "  sliders (CUTTER RPM, GLOW, ORBIT, GRID, WIREFRAME) to edit the model live.\n"
            "- Bottom left: personnel count line chart. Bottom centre: construction cost tracker.\n"
            "- Ask me to 'create a design' and I will generate it and open it for you.",
            ["dashboard"],
        )
    if any(k in text for k in ["anomaly", "outlier", "ml", "ai engine"]):
        return (
            "ML ANOMALY ENGINE:\nOpen the 'Anomaly AI' icon (ANOMALY.AI). It runs a rolling z-score "
            "scan over settlement, thrust, torque, advance speed and grouting pressure, flagging "
            "outliers with severity. Use it to find abnormal sensor readings quickly.",
            ["anomaly"],
        )
    if any(k in text for k in ["shm", "structural", "health"]):
        return (
            "STRUCTURAL HEALTH MONITOR:\nOpen the 'SHM' icon. It streams seepage, segment "
            "displacement and lining-strain readings with per-sensor status and alert highlights.",
            ["shm"],
        )
    if any(k in text for k in ["spatial", "clearance"]):
        return (
            "SPATIAL CLEARANCE PLANNER:\nOpen the 'Spatial' icon (SPATIAL.PLN). It lists nearby "
            "assets (sewers, water mains, metro tunnels) and computes shield clearance against each.",
            ["spatial"],
        )
    if any(k in text for k in ["transfer", "experience", "abc"]):
        return (
            "EXPERIENCE TRANSFER:\nOpen the 'Transfer' icon (TRANSFER.AI). It recommends cutterhead "
            "parameters for a target segment based on A/B/C source-segment experience and geology.",
            ["transfer"],
        )
    if any(k in text for k in ["login", "password", "log in", "user", "account"]):
        return (
            "AUTHENTICATION:\nAccounts: admin/admin123 (full access) and operator/shield123.\n"
            "GUEST MODE is a read-only simulation for exploring the UI without login.",
            [],
        )
    if any(k in text for k in ["what is", "what can", "about", "software", "platform"]):
        return (
            "THIS PLATFORM\nI am TunnelArchitect-AI, your assistant for the Intelligent Tunneling "
            "Management Platform.\n\n"
            + SOFTWARE_GUIDE,
            [],
        )
    return (
        "I can help you with this platform. Try asking:\n"
        "- 'how do I generate a report?'\n- 'open the cyber twin'\n"
        "- 'create a sensor array design'\n- 'analyse the data'\n- 'live status'",
        [],
    )


def respond(message: str, db: Session) -> dict:
    text = (message or "").strip().lower()
    actions: list[dict] = []

    if not text:
        return {
            "reply": "Hello! I'm TunnelArchitect-AI. Ask me how to use the software, create a 3D design, "
            "analyse the data, or generate a report.",
            "actions": [],
        }

    if any(k in text for k in ["hello", "hi ", "hey", "good morning", "good afternoon"]):
        return {
            "reply": "Hello! I'm TunnelArchitect-AI, your tunneling platform copilot.\n\n"
            "I can: navigate modules, build 3D instrument designs, run data analysis and generate "
            "regulatory reports.\n\nTry:\n- 'open the cyber twin'\n- 'create a TBM design'\n- 'analyse the data'"
            "\n- 'generate the report'\n- 'how do I use the 3D editor?'",
            "actions": [{"type": "navigate", "window": "win-ai"}],
        }

    if any(k in text for k in ["how", "help", "usage", "guide", "what is", "what can", "tutorial", "use the software", "how to"]):
        reply, open_windows = _guide(message)
        for wid in open_windows:
            actions.append({"type": "navigate", "window": WINDOW_IDS.get(wid, wid)})
        return {"reply": reply, "actions": actions}

    if any(k in text for k in ["open ", "show ", "launch", "go to", "navigate", "display"]):
        target = None
        if any(k in text for k in ["twin", "3d", "cyber"]):
            target = "win-twin"
        elif any(k in text for k in ["editor", "design", "dashboard", "monitor"]):
            target = "win-dashboard"
        elif any(k in text for k in ["report"]):
            target = "win-report"
        elif any(k in text for k in ["anomaly", "ai"]):
            target = "win-anomaly"
        elif any(k in text for k in ["shm", "structural"]):
            target = "win-shm"
        elif any(k in text for k in ["spatial", "clearance"]):
            target = "win-spatial"
        elif any(k in text for k in ["transfer", "experience"]):
            target = "win-transfer"
        elif any(k in text for k in ["sensor", "geo", "cutterhead", "metrics"]):
            target = "win-sensor"
        elif any(k in text for k in ["settlement", "chart"]):
            target = "win-settlement"
        elif any(k in text for k in ["risk", "alert", "alerts"]):
            target = "win-alerts"
        elif any(k in text for k in ["camera", "cctv"]):
            target = "win-camera"
        if target:
            return {"reply": f"Opening {target.replace('win-', '').upper()} module.", "actions": [{"type": "navigate", "window": target}]}
        return {"reply": "Which module? I know: GEO DATA, CUTTERHEAD, RISK REPORTS, SETTLEMENT, CYBER TWIN, TBM DASH, SHM, ANOMALY AI, TRANSFER, SPATIAL, REPORT.", "actions": []}

    if any(k in text for k in ["design", "create", "add", "build", "assemble", "make me", "model"]):
        parts = _design(message)
        return {
            "reply": f"Generated a {len(parts)}-part 3D instrument design and opened the TBM DASHBOARD.\n"
            "Use the 3D TBM model editor sliders to tweak the cutter RPM and glow, drag to orbit, "
            "and scroll to zoom.",
            "actions": [{"type": "design", "design": parts}, {"type": "navigate", "window": "win-dashboard"}],
        }

    if any(k in text for k in ["analyz", "analyse", "analysis", "check", "insight", "evaluate"]):
        return {
            "reply": _analyse(db),
            "actions": [{"type": "navigate", "window": "win-anomaly"}],
        }

    if any(k in text for k in ["report", "regulatory", "compliance", "export", "pdf"]):
        return {
            "reply": "Generating the regulatory compliance report...\n\nOpening REPORT.EXE - click GENERATE "
            "to download shield_regulatory_report.html with the full compliance summary.",
            "actions": [{"type": "report"}, {"type": "navigate", "window": "win-report"}],
        }

    if any(k in text for k in ["status", "live", "current", "health", "situation", "overview"]):
        return {"reply": _status(db), "actions": []}

    return {
        "reply": "I didn't fully understand that, but here is what I can do:\n"
        "- guide you through the software ('how do I...')\n"
        "- open modules ('open the cyber twin')\n"
        "- create 3D designs ('create a TBM design with sensors')\n"
        "- analyse data ('analyse the settlement data')\n"
        "- generate reports ('generate the report')\n"
        "- live status ('live status')",
        "actions": [],
    }
