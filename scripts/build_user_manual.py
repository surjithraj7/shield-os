from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS_DIR = os.path.join(ROOT, "scripts", "manual_shots")
OUT_PDF = os.path.join(ROOT, "shield_user_manual.pdf")
BASE_URL = os.environ.get("MANUAL_BASE_URL", "http://localhost:8000")

os.makedirs(SHOTS_DIR, exist_ok=True)

# icon label -> (window title, screenshot filename)
MODULES = [
    ("Geo Data", "SENSOR.EXE - Real-Time Cutterhead Metrics", "mod_geo.png", 1200),
    ("Cutterhead", "CAMERA.EXE - CCTV: Tunnel Face (AR)", "mod_camera.png", 1200),
    ("Risk Reports", "ALERTS.LOG - Active Risk Sources", "mod_risks.png", 1200),
    ("Settlement", "SETTLEMENT.PLT - Predicted vs Monitored", "mod_settlement.png", 1200),
    ("Cyber Twin", "TWIN.EXE - Digital Cyber Twin 3D", "mod_twin.png", 3200),
    ("3D Editor", "INSTRUMENT-3D.EXE - System Instrument Design Editor", "mod_editor.png", 3200),
    ("SHM", "SHM.EXE - Structural Health Monitor", "mod_shm.png", 1200),
    ("Anomaly AI", "ANOMALY.AI - ML Anomaly Engine", "mod_anomaly.png", 1400),
    ("Transfer", "TRANSFER.AI - A/B/C Experience Transfer", "mod_transfer.png", 1400),
    ("Spatial", "SPATIAL.PLN - 3D Clearance Planner", "mod_spatial.png", 1400),
    ("Report", "REPORT.EXE - Auto-Regulatory Reporting", "mod_report.png", 1200),
    ("AI Assist", "AI-ASSIST.EXE - TunnelArchitect-AI Chat", "mod_ai.png", 1600),
]

SEARCH_TITLE = "SEARCH.EXE - Query Results"


def _ensure_server() -> None:
    try:
        urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=3)
        return
    except Exception:
        pass
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    for _ in range(40):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=2)
            return
        except Exception:
            continue
    raise SystemExit("Server did not start.")


def _close_all_windows(page) -> None:
    for _ in range(3):
        close_btns = page.locator("section.window button.tbtn[title='Close']")
        if close_btns.count() == 0:
            return
        for btn in close_btns.all():
            try:
                btn.click()
            except Exception:
                pass
        page.wait_for_timeout(150)


def capture() -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 950}, device_scale_factor=1)
        page.goto(BASE_URL, wait_until="networkidle")

        # Login screen
        page.locator(".login-box").wait_for(timeout=15000)
        page.wait_for_timeout(800)
        page.locator(".login-box").screenshot(path=os.path.join(SHOTS_DIR, "login.png"))
        page.fill("#login-user", "admin")
        page.fill("#login-pass", "admin123")
        page.locator(".login-btn").click()

        # Desktop
        page.locator(".desktop").wait_for(timeout=15000)
        page.wait_for_timeout(5000)  # let toasts + initial loads settle
        page.screenshot(path=os.path.join(SHOTS_DIR, "desktop.png"))

        # Context menu
        page.mouse.click(420, 300, button="right")
        page.locator(".ctx-menu").wait_for(timeout=3000)
        page.wait_for_timeout(300)
        page.locator(".ctx-menu").screenshot(path=os.path.join(SHOTS_DIR, "context.png"))
        page.keyboard.press("Escape")
        page.mouse.click(20, 500)

        # Search
        page.fill("#search-input", "12")
        page.locator("#search-btn").click()
        page.wait_for_timeout(1200)
        page.locator(".searchdock").screenshot(path=os.path.join(SHOTS_DIR, "search_dock.png"))
        page.locator("section.window").filter(
            has=page.locator(".titlebar-text", has_text=SEARCH_TITLE)
        ).first.screenshot(path=os.path.join(SHOTS_DIR, "search_results.png"))
        _close_all_windows(page)

        # Module windows
        for label, title, fname, wait_ms in MODULES:
            _close_all_windows(page)
            page.wait_for_timeout(200)
            clicked = False
            for ic in page.locator("button.icon").all():
                try:
                    if ic.locator("span").inner_text().strip() == label:
                        ic.click()
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                print(f"  ! no icon for {label}, skipping")
                continue
            page.wait_for_timeout(wait_ms)
            win = page.locator("section.window").filter(
                has=page.locator(".titlebar-text", has_text=title)
            ).first
            try:
                win.wait_for(state="visible", timeout=8000)
            except Exception:
                print(f"  ! window not visible: {label}")
                continue
            page.wait_for_timeout(400)
            win.screenshot(path=os.path.join(SHOTS_DIR, fname))

        browser.close()


def _image_dims(path: str) -> tuple[float, float]:
    from PIL import Image

    with Image.open(path) as im:
        return im.size


def _img_flow(path: str, max_w: float) -> "object":
    from reportlab.platypus import Image

    w, h = _image_dims(path)
    scale = min(1.0, max_w / w)
    return Image(path, width=w * scale, height=h * scale)


def build_pdf() -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    PURPLE = colors.HexColor("#6a0dad")
    PINK = colors.HexColor("#ff00ff")
    DARK = colors.HexColor("#1a1a2e")

    doc = SimpleDocTemplate(
        OUT_PDF,
        pagesize=A4,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title="SHIELD-OS User Manual",
        author="Intelligent Tunneling Management Platform",
    )

    styles = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=styles["Normal"], fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=DARK)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16, textColor=PURPLE, spaceAfter=8, spaceBefore=4)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, textColor=PINK, spaceAfter=5, spaceBefore=12)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, textColor=PURPLE, spaceAfter=4, spaceBefore=8)
    cover = ParagraphStyle("Cover", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=26, textColor=PURPLE, alignment=TA_CENTER)
    sub = ParagraphStyle("Sub", parent=body, fontSize=11, textColor=colors.HexColor("#444"), alignment=TA_CENTER)
    small = ParagraphStyle("Small", parent=body, fontSize=8, textColor=colors.HexColor("#666"))
    bullet = ParagraphStyle("Bullet", parent=body, leftIndent=14, bulletIndent=4, spaceAfter=2)

    class ManualDocTemplate(SimpleDocTemplate):
        def afterFlowable(self, flowable):
            if isinstance(flowable, Paragraph):
                style = flowable.style.name
                text = flowable.getPlainText()
                if style == "H1":
                    self.notify("TOCEntry", (0, text, self.page))
                elif style == "H2":
                    self.notify("TOCEntry", (1, text, self.page))

    story: list = []

    def para(txt: str) -> Paragraph:
        return Paragraph(txt, body)

    def bullets(items: list[str]) -> list:
        return [Paragraph(f"<bullet>&bull;</bullet>{t}", bullet) for t in items]

    def toc() -> None:
        from reportlab.platypus.tableofcontents import TableOfContents

        t = TableOfContents()
        t.levelStyles = [
            ParagraphStyle("TOC0", parent=body, fontName="Helvetica-Bold", fontSize=10, textColor=DARK, leftIndent=0),
            ParagraphStyle("TOC1", parent=body, fontSize=9, textColor=colors.HexColor("#444"), leftIndent=14),
        ]
        story.append(Paragraph("Contents", h1))
        story.append(t)
        story.append(PageBreak())

    def cover_page() -> None:
        story.append(Spacer(1, 60 * mm))
        story.append(Paragraph("SHIELD-OS", cover))
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("INTELLIGENT TUNNELING MANAGEMENT PLATFORM", sub))
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Digital-Twin Settlement Engine - User Manual", sub))
        story.append(Spacer(1, 30 * mm))
        story.append(Paragraph("Version 1.0  |  " + time.strftime("%Y-%m-%d"), sub))
        story.append(PageBreak())

    def section(num: str, title: str) -> None:
        story.append(Paragraph(f"{num}. {title}", h1))

    def module_section(idx: int, title: str, desc: list[str], img: str | None, note: str | None = None) -> None:
        story.append(Paragraph(f"4.{idx}  {title}", h2))
        story.extend([para(t) for t in desc])
        if note:
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph(f"<b>Tip:</b> {note}", small))
        if img and os.path.exists(os.path.join(SHOTS_DIR, img)):
            story.append(Spacer(1, 3 * mm))
            story.append(_img_flow(os.path.join(SHOTS_DIR, img), 170 * mm))
        story.append(Spacer(1, 4 * mm))

    def api_table() -> None:
        rows = [
            ["Method", "Endpoint", "Purpose"],
            ["POST", "/api/engine/immediate", "Immediate Mindlin settlement trough at a station"],
            ["POST", "/api/engine/consolidation", "Hankel-transform long-term settlement over time"],
            ["POST", "/api/engine/total", "Immediate + consolidation trough"],
            ["POST", "/api/engine/evaluate", "Predicted vs monitored + risk alarm"],
            ["GET", "/api/engine/reference/beijing-line12", "4.2 mm / 4.4 mm validation reference"],
            ["POST", "/api/engine/calibrate", "Derive a calibration factor from a monitored value"],
            ["GET|POST", "/api/data/shield-params", "Shield parameter rows"],
            ["GET|POST", "/api/data/monitoring", "Monitoring rows"],
            ["GET", "/api/data/calculated", "Predicted-vs-monitored results"],
            ["POST", "/api/assistant/chat", "AI assistant chat (GPT / Gemini / rule-based)"],
            ["POST", "/api/assistant/gemini/image", "Imagen image generation"],
            ["POST", "/api/assistant/gemini/questions", "Quiz / question generation (JSON)"],
            ["POST", "/api/assistant/gemini/qa", "Multimodal question answering"],
            ["POST", "/api/auth/login", "Login, returns bearer token"],
            ["POST", "/api/auth/logout", "Revoke session"],
            ["GET", "/api/auth/me", "Current user profile"],
            ["GET", "/api/report/regulatory", "Download HTML compliance report"],
        ]
        tbl = Table(rows, colWidths=[28 * mm, 62 * mm, 80 * mm], repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PURPLE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbb")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f0f8")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(tbl)

    def simple_table(headers: list[str], data: list[list]) -> None:
        rows = [headers] + data
        tbl = Table(rows, colWidths=[30 * mm, 60 * mm, 80 * mm], repeatRows=1)
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PURPLE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbb")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f0f8")]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(tbl)

    def footer(canvas, doc_) -> None:
        canvas.saveState()
        canvas.setStrokeColor(PURPLE)
        canvas.setLineWidth(0.6)
        canvas.line(18 * mm, 13 * mm, 192 * mm, 13 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#666"))
        canvas.drawString(18 * mm, 9 * mm, "SHIELD-OS - Intelligent Tunneling Management Platform - User Manual")
        canvas.drawRightString(192 * mm, 9 * mm, f"Page {doc_.page}")
        canvas.restoreState()

    builder = ManualDocTemplate(
        OUT_PDF,
        pagesize=A4,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title="SHIELD-OS User Manual",
        author="Intelligent Tunneling Management Platform",
    )

    # ---- CONTENT ----
    cover_page()
    toc()

    section("1", "Overview")
    story.append(para(
        "SHIELD-OS is a digital-twin settlement engine for urban shield tunneling. During excavation the "
        "TBM advances ring by ring while ground deformation is predicted in real time and compared against "
        "monitored sensors. The platform fuses a dual-calculation scientific engine, a monitoring database "
        "and an AI assistant into a single desktop-style mission-control interface."
    ))
    story.append(para("<b>Scientific settlement engine</b>"))
    story.extend(bullets([
        "<b>Immediate settlement (Mindlin):</b> surface displacement from a horizontal point load in an elastic "
        "half-space is superposed over tunnel face thrust, shield skin friction and tail-void ground loss.",
        "<b>Long-term settlement (consolidation):</b> Terzaghi-Rendulic excess pore-pressure dissipation is solved "
        "with a 0th-order Hankel transform in the radial direction and a Fourier sine series in depth.",
        "<b>Validation target:</b> the engine predicts within 5% of monitored settlement. Beijing Metro Line 12 "
        "benchmark: predicted 4.2 mm vs monitored 4.4 mm (0.08% deviation with default calibration).",
    ]))
    story.append(para("<b>Architecture</b>"))
    story.extend(bullets([
        "<b>Backend:</b> FastAPI (Python) exposing a REST API over a SQLite database (SQLAlchemy ORM).",
        "<b>Frontend:</b> React desktop-style shell (windows, taskbar, icons) with Three.js 3D views.",
        "<b>AI:</b> optional ChatGPT or Google Gemini copilot with an offline rule-based fallback.",
    ]))

    section("2", "Getting Started")
    story.append(para("<b>Install and run</b>"))
    story.extend(bullets([
        "Install dependencies: <font face='Courier' size='8'>pip install -r requirements.txt</font>",
        "Seed the database: <font face='Courier' size='8'>python scripts/seed_data.py</font>",
        "Start the server: <font face='Courier' size='8'>python -m uvicorn app.main:app --port 8000</font>",
        "Open the platform in your browser: <font face='Courier' size='8'>http://localhost:8000</font>",
    ]))
    story.append(para("<b>Login</b>"))
    story.extend(bullets([
        "<b>admin / admin123</b> - administrator (full access)",
        "<b>operator / shield123</b> - operator account",
        "<b>Guest mode</b> - read-only simulation, no account needed",
    ]))
    story.append(_img_flow(os.path.join(SHOTS_DIR, "login.png"), 140 * mm))

    section("3", "Desktop Environment")
    story.append(_img_flow(os.path.join(SHOTS_DIR, "desktop.png"), 175 * mm))
    story.append(para("<b>Desktop icons</b> - click an icon to open its module window, double-click to maximize."))
    simple_table(
        ["Icon", "Module", "Purpose"],
        [
            ["Geo Data", "SENSOR.EXE", "Live cutterhead metrics"],
            ["Cutterhead", "CAMERA.EXE", "CCTV tunnel-face feed with AR overlay"],
            ["Risk Reports", "ALERTS.LOG", "Active risk sources"],
            ["Settlement", "SETTLEMENT.PLT", "Predicted vs monitored curve + calibration"],
            ["Cyber Twin", "TWIN.EXE", "3D digital twin with live HUD"],
            ["3D Editor", "INSTRUMENT-3D.EXE", "Design / assemble instruments in 3D"],
            ["SHM", "SHM.EXE", "Structural health monitor"],
            ["Anomaly AI", "ANOMALY.AI", "ML outlier engine"],
            ["Transfer", "TRANSFER.AI", "A/B/C experience transfer"],
            ["Spatial", "SPATIAL.PLN", "3D clearance planning"],
            ["Report", "REPORT.EXE", "Auto-regulatory reporting"],
            ["AI Assist", "AI-ASSIST.EXE", "AI copilot chat"],
        ],
    )
    story.append(para("<b>Window controls</b> - drag the title bar to move a window. Use <b>_</b> to minimize, "
                      "<b>maximize</b> to fill the screen and <b>X</b> to close. The taskbar shows every open "
                      "window; click a tab to restore a minimized window. The status bar shows the live data link "
                      "state (CONNECTING, DATA LINK OK, or API OFFLINE - SIM MODE)."))
    story.append(para("<b>Right-click the desktop</b> for the quick-action menu."))
    story.append(_img_flow(os.path.join(SHOTS_DIR, "context.png"), 90 * mm))
    story.extend(bullets([
        "<b>Export Data...</b> - download all loaded records as JSON.",
        "<b>Calibrate Sensors...</b> - enter a monitored settlement to derive a calibration factor.",
        "<b>Set Alert Thresholds...</b> - set orange / yellow / red alarm levels (mm).",
        "<b>Refresh Feed</b> - reload data from the API.",
    ]))
    story.append(para("<b>Search dock</b> - type a ring number, chainage (e.g. 102.4) or sensor id and press "
                      "FIND to query the loaded dataset. Results open in the SEARCH.EXE window."))
    story.append(_img_flow(os.path.join(SHOTS_DIR, "search_dock.png"), 150 * mm))
    story.append(_img_flow(os.path.join(SHOTS_DIR, "search_results.png"), 150 * mm))

    section("4", "Module Guide")

    module_section(
        1, "Geo Data - SENSOR.EXE",
        [
            "Live cutterhead and ground metrics: thrust (kN), torque (kNm), advance speed (mm/min), grout "
            "pressure (MPa), face pressure and screw RPM.",
            "Values update automatically. The equalizer bars animate while the feed is playing. Current station "
            "and ring are shown on the HUD.",
            "Open it with the <b>Geo Data</b> desktop icon.",
        ],
        "mod_geo.png",
    )

    module_section(
        2, "Cutterhead CCTV - CAMERA.EXE",
        [
            "Simulated tunnel-face CCTV feed with AR overlay markers for cutting tools and intake.",
            "Use it for a visual check of the cutterhead state during excavation.",
        ],
        "mod_camera.png",
    )

    module_section(
        3, "Risk Reports - ALERTS.LOG",
        [
            "Lists active risk sources with a severity level (safe, notice, warning, critical).",
            "Calculated rings are classified against the configured alarm thresholds.",
        ],
        "mod_risks.png",
    )

    module_section(
        4, "Parameter Controls - ADVANCE.CTL",
        [
            "Adjust live excavation parameters (advance speed, grout volume, face pressure and related control "
            "sliders). Changes are recorded to the shield parameter feed.",
            "Note: this module is opened from within other workflows rather than a standalone desktop icon.",
        ],
        None,
    )

    module_section(
        5, "Settlement - SETTLEMENT.PLT",
        [
            "Plots predicted vs monitored settlement over the tunnel chainage.",
            "Review the mean relative error and the worst ring. The platform targets a <b>&lt; 5%</b> prediction "
            "error against the Beijing Metro Line 12 benchmark.",
            "Use right-click <b>Calibrate Sensors...</b> when the monitored baseline changes.",
        ],
        "mod_settlement.png",
    )

    module_section(
        6, "Cyber Twin - TWIN.EXE",
        [
            "Real-time 3D digital twin of the shield, ground and tunnel rings with a live metrics HUD and the "
            "latest ring / chainage / risk state.",
            "<b>Rotate:</b> left-drag. <b>Pan:</b> right-drag. <b>Zoom:</b> scroll wheel. The twin refreshes "
            "every few seconds.",
        ],
        "mod_twin.png",
    )

    module_section(
        7, "3D Editor - INSTRUMENT-3D.EXE",
        [
            "Design and assemble TBM and instrumentation models in 3D.",
            "Add parts from the toolbar: TBM, CUTTER, RING, SENSOR, PIPE, STRUT, BEACON. Select a part and use "
            "MOVE / ROT / SCALE via the 3D gizmo or the numeric panel.",
            "DUPLICATE clones the selection; FLAT-Y snaps to ground; COPY JSON exports the design; SAVE stores "
            "it to the database.",
            "You can also ask the AI assistant to create a design, which loads it directly into this editor.",
        ],
        "mod_editor.png",
    )

    module_section(
        8, "Structural Health Monitor - SHM.EXE",
        [
            "Streams structural health readings: seepage, segment displacement and lining strain.",
            "Each sensor shows its value, unit and status; alert readings are highlighted so follow-up inspection "
            "can be prioritised.",
        ],
        "mod_shm.png",
    )

    module_section(
        9, "Anomaly AI - ANOMALY.AI",
        [
            "Rolling z-score ML engine that scans settlement, thrust, torque, advance speed and grouting pressure "
            "and flags abnormal values with a severity.",
            "Use it to catch outlier sensor readings before they become risk alerts.",
        ],
        "mod_anomaly.png",
    )

    module_section(
        10, "Experience Transfer - TRANSFER.AI",
        [
            "Recommends cutterhead parameters for a target segment based on A/B/C source-segment experience and "
            "geology, accelerating parameter tuning between projects.",
        ],
        "mod_transfer.png",
    )

    module_section(
        11, "Spatial Planner - SPATIAL.PLN",
        [
            "3D clearance planning against nearby assets such as sewers, water mains and adjacent metro tunnels.",
            "Displays each asset's distance to the shield, clearance vs limit, and a safe / warning / critical "
            "level so excavation can be adjusted in advance.",
        ],
        "mod_spatial.png",
    )

    module_section(
        12, "Report - REPORT.EXE",
        [
            "One-click generation of the regulatory compliance report covering settlement validation, alarm "
            "distribution, SHM status, spatial clearances and ML anomaly screening.",
            "Click <b>EXPORT COMPLIANCE REPORT (HTML)</b> to download the report, then open it in a browser and "
            "use Print -> Save as PDF for a signed deliverable.",
            "A summary panel shows live counts for SHM alerts, critical clearances and ML anomalies.",
        ],
        "mod_report.png",
        note="The AI assistant can open this module and trigger a report with the command 'generate the report'.",
    )

    section("5", "AI Assistant")
    story.append(_img_flow(os.path.join(SHOTS_DIR, "mod_ai.png"), 160 * mm))
    story.append(para(
        "The AI ASSIST copilot answers questions about the platform, opens modules, builds 3D designs, runs data "
        "analysis and generates reports. It is a real LLM copilot when a key is configured and falls back to a "
        "built-in offline copilot otherwise."
    ))
    story.append(para("<b>Example commands</b>"))
    story.extend(bullets([
        "'how do I generate a report?' - shows step-by-step guidance",
        "'open the cyber twin' - navigates to a module",
        "'create a TBM design with sensors' - builds a 3D design in the editor",
        "'analyse the data' - runs the full platform analysis",
        "'generate the report' - opens the reporting module",
        "'live status' - current system overview",
    ]))
    story.append(para("<b>Backends</b>"))
    story.extend(bullets([
        "<b>ChatGPT:</b> set <font face='Courier' size='8'>OPENAI_API_KEY</font> in the .env file.",
        "<b>Google Gemini:</b> set <font face='Courier' size='8'>GEMINI_API_KEY</font>. Adds image generation "
        "(imagen-3.0-generate-002), quiz/question generation and multimodal Q&amp;A via "
        "<font face='Courier' size='8'>/api/assistant/gemini/*</font> endpoints.",
        "<b>Offline:</b> no key configured - the built-in rule-based copilot handles navigation, design, analysis "
        "and reporting.",
    ]))

    section("6", "Settings & Calibration")
    story.append(para("<b>Alert thresholds</b>"))
    story.append(para(
        "Right-click the desktop, choose <b>Set Alert Thresholds...</b> and enter three comma-separated values "
        "(orange, yellow, red) in millimetres. These drive the risk band classification for every calculated ring."
    ))
    story.append(para("<b>Sensor calibration</b>"))
    story.append(para(
        "Right-click the desktop, choose <b>Calibrate Sensors...</b> and enter a monitored settlement value "
        "(mm). The platform derives a calibration factor so the engine prediction matches the monitored baseline."
    ))

    section("7", "Data Export & Reports")
    story.extend(bullets([
        "<b>Export Data...</b> (right-click desktop) downloads <font face='Courier' size='8'>shield_export.json</font> "
        "with all loaded shield, monitoring and calculated rows.",
        "<b>REPORT.EXE</b> exports the full compliance report as HTML; use browser Print -> Save as PDF for a "
        "print-ready deliverable.",
        "All data is available programmatically through the REST API (see Appendix A).",
    ]))

    section("8", "Troubleshooting / FAQ")
    story.append(para("<b>Q: The status bar shows 'API OFFLINE - SIM MODE'.</b>"))
    story.append(para("A: The backend is not reachable. Start it with "
                      "<font face='Courier' size='8'>python -m uvicorn app.main:app --port 8000</font> and refresh. "
                      "The UI keeps working in simulation mode."))
    story.append(para("<b>Q: No rings / empty charts.</b>"))
    story.append(para("A: Seed the database with <font face='Courier' size='8'>python scripts/seed_data.py</font> "
                      "(and <font face='Courier' size='8'>python scripts/seed_advanced.py</font> for SHM/spatial/"
                      "anomaly data) then restart the server."))
    story.append(para("<b>Q: Login fails.</b>"))
    story.append(para("A: Use admin/admin123 or operator/shield123, or enter guest mode for read-only access."))
    story.append(para("<b>Q: The AI assistant replies with rule-based answers.</b>"))
    story.append(para("A: No OPENAI_API_KEY or GEMINI_API_KEY is set. Add a key to the .env file and restart."))
    story.append(para("<b>Q: Can I open the platform on another machine?</b>"))
    story.append(para("A: Yes - run uvicorn with --host 0.0.0.0 and open http://&lt;server-ip&gt;:8000, and allow "
                      "port 8000 in the firewall."))

    section("9", "Appendix A - REST API")
    story.append(para("Interactive API documentation is available at http://localhost:8000/docs. Key endpoints:"))
    api_table()

    builder.multiBuild(story, onFirstPage=footer, onLaterPages=footer)


def main() -> None:
    print(f"target server: {BASE_URL}")
    _ensure_server()
    print("capturing screenshots...")
    capture()
    print("building pdf...")
    build_pdf()
    print(f"wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
