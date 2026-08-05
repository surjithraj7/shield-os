"""Generate a project-defense PowerPoint for the Intelligent Tunneling Management Platform.

Agenda (academic defense structure based on the base paper):
  1. Domain
  2. Sub Domain
  3. About base paper
  4. Base paper merits & demerits
  5. Problem statement
  6. Conclusion
  7. Reference
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
DARK = RGBColor(0x0F, 0x2A, 0x43)      # deep navy
NAVY = RGBColor(0x14, 0x36, 0x57)      # panel navy
ACCENT = RGBColor(0x1F, 0x6F, 0xEB)    # blue accent
TEAL = RGBColor(0x2A, 0xC4, 0x9D)      # teal accent
ORANGE = RGBColor(0xF2, 0x99, 0x0A)
RED = RGBColor(0xC0, 0x39, 0x2B)
GREEN = RGBColor(0x27, 0xAE, 0x60)
LIGHT = RGBColor(0xF2, 0xF6, 0xFB)     # light background
GREY = RGBColor(0x55, 0x5E, 0x6B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BODY = RGBColor(0x33, 0x3B, 0x45)
SOFT = RGBColor(0x9F, 0xB3, 0xC8)

FONT = "Calibri"
MONO = "Consolas"

SW, SH = 13.333, 7.5  # slide size in inches (16:9)
TOTAL = 12

prs = Presentation()
prs.slide_width = Inches(SW)
prs.slide_height = Inches(SH)
BLANK = prs.slide_layouts[6]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def slide():
    return prs.slides.add_slide(BLANK)


def rect(s, x, y, w, h, fill=None, line=None, line_w=None, shape=MSO_SHAPE.RECTANGLE):
    sp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(line_w or 1)
    sp.shadow.inherit = False
    return sp


def txt(s, x, y, w, h, text, size=18, color=BODY, bold=False, align=PP_ALIGN.LEFT,
        anchor=MSO_ANCHOR.TOP, font=FONT, italic=False, wrap=True):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    f = r.font
    f.name = font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color
    return tb


def para(s, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, gap=0):
    """runs: list of (text, size, color, bold) tuples on one paragraph."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    p.space_after = Pt(gap)
    for text, size, color, bold in runs:
        r = p.add_run()
        r.text = text
        r.font.name = FONT
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
    return tb


def bullets(s, x, y, w, h, items, size=15, color=BODY, gap=8, marker="\u25AA"):
    """items: list of (text, level) or (text, level, color)."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    first = True
    for it in items:
        text, lvl = it[0], it[1]
        col = it[2] if len(it) > 2 else color
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(gap)
        p.level = lvl
        m = (marker + "  ") if lvl == 0 else "\u2013  "
        r = p.add_run()
        r.text = m + text
        f = r.font
        f.name = FONT
        f.size = Pt(size - 1 if lvl else size)
        f.bold = lvl == 0
        f.color.rgb = col
    return tb


def header(s, num, title, kicker=None, page=None):
    rect(s, 0, 0, SW, 0.95, fill=DARK)
    rect(s, 0, 0.95, SW, 0.06, fill=ACCENT)
    if num:
        chip(s, 0.6, 0.26, 0.62, 0.44, num, fill=ACCENT, size=16)
    txt(s, 1.4, 0.22, 10.5, 0.55, title, size=23, color=WHITE, bold=True,
        anchor=MSO_ANCHOR.MIDDLE)
    if kicker:
        txt(s, 0.6, 1.15, 12.1, 0.35, kicker, size=13, color=ACCENT, bold=True)
    if page:
        txt(s, 12.35, 0.28, 0.45, 0.4, f"{page}/{TOTAL}", size=12, color=SOFT,
            align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)


def card(s, x, y, w, h, title, body, title_color=NAVY, body_color=BODY,
         title_size=15, body_size=12.5, accent=None, body_h=None):
    rect(s, x, y, w, h, fill=LIGHT, line=RGBColor(0xDD, 0xE5, 0xEF), line_w=1)
    if accent:
        rect(s, x, y, 0.08, h, fill=accent)
    top = 0.15
    if title:
        txt(s, x + 0.25, y + 0.15, w - 0.45, 0.6, title, size=title_size,
            color=title_color, bold=True)
        top = 0.65
    txt(s, x + 0.25, y + top, w - 0.45, (body_h or h - top - 0.15), body,
        size=body_size, color=body_color)


def chip(s, x, y, w, h, text, fill=NAVY, color=WHITE, size=12):
    sp = rect(s, x, y, w, h, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    sp.adjustments[0] = 0.5
    tf = sp.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.color.rgb = color
    return sp


def footer(s, text="Intelligent Tunneling Management Platform \u2014 Project Defense"):
    txt(s, 0.6, 7.12, 12.1, 0.3, text, size=10, color=GREY)


# ---------------------------------------------------------------------------
# Slide 1 — Title
# ---------------------------------------------------------------------------
s = slide()
rect(s, 0, 0, SW, SH, fill=DARK)
rect(s, 0, 0, 0.25, SH, fill=ACCENT)
rect(s, 0, 7.0, SW, 0.5, fill=NAVY)

chip(s, 0.9, 1.0, 3.3, 0.45, "FINAL YEAR PROJECT  \u2022  DEFENSE", fill=ACCENT, size=12)
txt(s, 0.9, 1.85, 11.5, 1.8, "Intelligent Tunneling Management Platform",
    size=44, color=WHITE, bold=True)
txt(s, 0.9, 3.15, 11.5, 1.0,
    "A Digital-Twin Settlement Prediction Engine for Urban Shield Tunneling",
    size=22, color=RGBColor(0xC9, 0xDB, 0xF2))
txt(s, 0.9, 4.25, 11.5, 1.0,
    "Extending the 3D intelligent management platform of Liu et al. (2024) with a "
    "validated analytical settlement engine, open REST API and AI copilot",
    size=15, color=SOFT, italic=True)

rect(s, 0.9, 5.75, 2.4, 0.03, fill=TEAL)
txt(s, 0.9, 5.9, 8.0, 0.9,
    "Presented by:  [Your Name]\nDepartment of Civil / Geotechnical Engineering \u2014 2026",
    size=15, color=WHITE)
txt(s, 0.9, 6.55, 8.0, 0.4, "Advisor:  [Advisor Name]", size=13, color=SOFT)

# ---------------------------------------------------------------------------
# Slide 2 — Agenda
# ---------------------------------------------------------------------------
s = slide()
header(s, None, "Agenda", page=2)

items = [
    ("01", "Domain", "Civil \u00b7 Geotechnical \u00b7 Underground Construction"),
    ("02", "Sub Domain", "Shield tunneling close to risk sources \u2014 settlement prediction"),
    ("03", "About Base Paper", "Liu et al. (2024) \u2014 3D intelligent management & control platform"),
    ("04", "Base Paper \u2014 Merits & Demerits", "Strengths of the platform + gaps to address"),
    ("05", "Problem Statement", "Why a new open, validated, API-driven platform is needed"),
    ("06", "Conclusion", "What the project achieves and its scope for future work"),
    ("07", "Reference", "Base paper citation and related literature"),
]
y = 1.55
for num, t, d in items:
    rect(s, 0.6, y, 12.1, 0.68, fill=LIGHT)
    rect(s, 0.6, y, 0.08, 0.68, fill=ACCENT)
    txt(s, 0.95, y, 0.95, 0.68, num, size=16, color=ACCENT, bold=True,
        anchor=MSO_ANCHOR.MIDDLE)
    txt(s, 1.95, y + 0.07, 4.6, 0.4, t, size=14.5, color=NAVY, bold=True)
    txt(s, 6.7, y + 0.1, 5.9, 0.5, d, size=11.5, color=BODY)
    y += 0.78

footer(s)

# ---------------------------------------------------------------------------
# Slide 3 — 1. Domain
# ---------------------------------------------------------------------------
s = slide()
header(s, "1", "Domain", "Where this project sits in engineering", page=3)

# Breadcrumb of domains
cr = ["Civil Engineering", "Geotechnical Engineering", "Underground Space Construction", "Tunnel Engineering (TBM)"]
x = 0.6
for i, d in enumerate(cr):
    w = 3.0
    chip(s, x, 1.7, w, 0.6, d, fill=NAVY if i < 3 else ACCENT, size=13)
    if i < 3:
        txt(s, x + w, 1.78, 0.5, 0.4, "\u2192", size=16, color=GREY,
            align=PP_ALIGN.CENTER)
    x += w + 0.5

card(s, 0.6, 2.7, 5.9, 2.3, "The engineering domain",
     "Mechanized (shield/TBM) tunneling is the dominant method for urban metro and "
     "utility tunnels. Construction must be carried out safely beneath dense cities, "
     "close to buildings, roads, bridges, pipelines and other existing infrastructure.",
     accent=ACCENT, body_h=1.4)
card(s, 6.7, 2.7, 6.0, 2.3, "Why this domain matters",
     "Ground movement control is the decisive safety and quality challenge: "
     "over-excavation, pressure loss or poor grouting cause surface settlement that "
     "can damage adjacent structures. Prediction, pre-warning and control are critical.",
     accent=TEAL, body_h=1.4)

card(s, 0.6, 5.3, 12.1, 1.6, "Digital technologies entering the domain",
     "BIM, GIS, CIM, 3D geological modeling, IoT monitoring and AI are being combined "
     "with settlement models to build \u201cintelligent platforms\u201d and digital twins \u2014 "
     "the exact research stream this project contributes to.",
     accent=ORANGE, body_h=0.9)

footer(s)

# ---------------------------------------------------------------------------
# Slide 4 — 2. Sub Domain
# ---------------------------------------------------------------------------
s = slide()
header(s, "2", "Sub Domain", "Approaching construction close to risk sources", page=4)

card(s, 0.6, 1.7, 12.1, 1.35, "Definition",
     "\u201cApproaching construction\u201d \u2014 shield tunneling that passes close to major risk "
     "sources: existing urban structures, operational railways/metro lines, bridges, "
     "rivers and high-pressure pipelines. This is the sub-domain addressed by the "
     "base paper and this project.",
     accent=ACCENT, body_h=0.6)

cols = [
    ("Risk sources", "Buildings \u00b7 metro & rail \u00b7 bridges \u00b7 rivers \u00b7 utilities \u00b7 historic structures"),
    ("Core technical challenge", "Predicting ground settlement (immediate + long-term consolidation) with accuracy and speed"),
    ("Engineering goal", "Pre-warning and control of construction risk via monitored data and prediction"),
]
x = 0.6
for t, d in cols:
    card(s, x, 3.25, 3.93, 2.0, t, d, accent=TEAL if t != "Core technical challenge" else ORANGE,
         body_h=1.1)
    x += 4.09

card(s, 0.6, 5.5, 12.1, 1.35, "Focus of this project",
     "A digital-twin platform that embeds an analytical settlement engine (Mindlin "
     "immediate + Hankel-transform consolidation), validates it against monitored "
     "settlement, and exposes it through a REST API \u2014 directly within the sub-domain "
     "of the base paper.",
     accent=ACCENT, body_h=0.6)

footer(s)

# ---------------------------------------------------------------------------
# Slide 5 — 3. About Base Paper (overview)
# ---------------------------------------------------------------------------
s = slide()
header(s, "3", "About the Base Paper", "Overview of the source study", page=5)

rect(s, 0.6, 1.7, 12.1, 1.3, fill=NAVY)
txt(s, 0.9, 1.85, 11.4, 0.55,
    "Liu B, Han Q, Fu C, Zhang G, He Y, Li W. \u201cDevelopment and engineering application of "
    "intelligent management and control platform for the shield tunneling construction "
    "close to risk sources.\u201d",
    size=14.5, color=WHITE, bold=True)
txt(s, 0.9, 2.55, 11.4, 0.4,
    "Journal of Intelligent Construction, 2024, 2(2): 9180018 \u00b7 "
    "DOI 10.26599/JIC.2024.9180018 \u00b7 China University of Mining and Technology (Beijing)",
    size=12, color=RGBColor(0xBF, 0xD5, 0xEF))

txt(s, 0.6, 3.2, 12.1, 0.4, "What the paper does (abstract summary)", size=14, color=ACCENT, bold=True)
bullets(s, 0.6, 3.7, 12.1, 3.2, [
    ("The project in the paper develops and applies a 3D intelligent management and "
     "control platform for shield tunneling construction near major risk sources "
     "(existing urban infrastructure).", 0),
    ("It proposes a novel analytical model to calculate the long-term settlement "
     "of existing structures, considering soil consolidation \u2014 beyond the usual "
     "immediate-settlement analysis.", 0, TEAL),
    ("The analysis model is embedded in the platform, which integrates BIM, GIS, CIM, "
     "geoscience (Geo) modeling and IoT monitoring.", 0),
    ("Risk data is determined by comparing calculated results, monitoring results and "
     "the control standard value.", 0),
    ("The platform provides construction-information management, pre-warning and risk "
     "control, and has been successfully applied in Beijing shield tunneling projects.",
     0),
], size=13.5, gap=9)

footer(s)

# ---------------------------------------------------------------------------
# Slide 6 — 3. About Base Paper (platform & methodology)
# ---------------------------------------------------------------------------
s = slide()
header(s, "3", "Base Paper \u2014 Platform & Methodology",
       "How the 3D intelligent platform is built and used", page=6)

blocks = [
    ("Analytical settlement models", "Immediate settlement of existing structures + "
     "novel long-term settlement considering soil consolidation.", ACCENT),
    ("Multi-source integration", "BIM (building) \u00b7 GIS (geography) \u00b7 CIM (city) \u00b7 "
     "Geo Model (geology) \u00b7 IoT (live sensor data).", TEAL),
    ("Risk determination", "Triple-source comparison: calculated vs monitored vs "
     "control standard value \u2192 pre-warning and control.", ORANGE),
]
x = 0.6
for t, d, c in blocks:
    card(s, x, 1.7, 3.93, 2.1, t, d, accent=c, body_h=1.2)
    x += 4.09

card(s, 0.6, 4.0, 12.1, 1.5, "Embedded 3D visual environment",
     "A 3D digital scene combining the tunnel, shield machine, surrounding geology "
     "and risk-source structures \u2014 monitored and calculated results are shown "
     "in context, supporting intuitive construction management and control.",
     accent=ACCENT, body_h=0.8)

card(s, 0.6, 5.7, 12.1, 1.15, "Engineering application",
     "Successfully applied in Beijing shield tunneling projects; the platform offers "
     "pre-warning functionality and economic value for similar approaching-construction "
     "projects.",
     accent=TEAL, body_h=0.5)

footer(s)

# ---------------------------------------------------------------------------
# Slide 7 — 4. Base Paper Merits
# ---------------------------------------------------------------------------
s = slide()
header(s, "4", "Base Paper \u2014 Merits", "Strengths of the proposed platform", page=7)

bullets(s, 0.6, 1.65, 12.1, 5.2, [
    ("Novel physics contribution", 0, TEAL),
    ("First-class analytical model for long-term settlement of existing structures "
     "considering soil consolidation \u2014 addresses a real, under-served mechanism.", 1),
    ("Real urban problem", 0, TEAL),
    ("Targets \u201capproaching construction\u201d near risk sources \u2014 a commonly encountered, "
     "high-stakes scenario in modern metro projects.", 1),
    ("Full integration stack", 0, TEAL),
    ("Combines BIM + GIS + CIM + Geo Model + IoT into one 3D platform \u2014 "
     "geology, structures, city context and live monitoring in a single view.", 1),
    ("Triple-source risk judgment", 0, TEAL),
    ("Risk levels computed by comparing calculated vs monitored vs control standard "
     "value \u2014 grounded, auditable alarm logic.", 1),
    ("Proven in practice", 0, TEAL),
    ("Applied in real Beijing shield tunneling projects, delivering pre-warning "
     "function and economic value.", 1),
], size=14, gap=10)

footer(s)

# ---------------------------------------------------------------------------
# Slide 8 — 4. Base Paper Demerits
# ---------------------------------------------------------------------------
s = slide()
header(s, "4", "Base Paper \u2014 Demerits / Gaps", "Limitations that motivate this project", page=8)

bullets(s, 0.6, 1.65, 12.1, 5.2, [
    ("Closed, project-embedded engine", 0, RED),
    ("The analytical model lives inside a bespoke platform \u2014 not reusable, "
     "reproducible or independently testable outside the specific project.", 1),
    ("No programmatic interface", 0, RED),
    ("No exposed REST API / data layer, so third-party tools, automation and further "
     "research cannot build on it.", 1),
    ("Risk by post-hoc comparison only", 0, RED),
    ("Risk is judged by comparing results after the fact; no calibration loop or "
     "validation metric (e.g. <5% error) is reported to lock the model to site reality.", 1),
    ("Heavy 3D/BIM modeling cost", 0, RED),
    ("Rich BIM/CIM/Geo scenes demand substantial data preparation and modeling "
     "effort per project.", 1),
    ("Limited intelligence", 0, RED),
    ("No AI/ML assistance \u2014 no anomaly detection on shield parameters and no "
     "conversational copilot for engineers.", 1),
], size=14, gap=10)

card(s, 0.6, 6.15, 12.1, 0.75, "",
     "These gaps are exactly what the present project addresses (see Problem Statement).",
     accent=ORANGE, body_size=13)

footer(s)

# ---------------------------------------------------------------------------
# Slide 9 — 5. Problem Statement
# ---------------------------------------------------------------------------
s = slide()
header(s, "5", "Problem Statement", "Gap analysis and formal statement", page=9)

card(s, 0.6, 1.65, 12.1, 2.1, "Formal problem statement",
     "Shield tunneling near urban risk sources demands accurate, fast and real-time "
     "settlement prediction and risk control. The base paper provides a strong 3D "
     "platform with a long-term consolidation model, but its engine is closed and "
     "project-specific, has no programmatic interface, and lacks calibration, "
     "quantified validation and intelligent assistance. There is a need for an open, "
     "API-driven digital-twin platform with a validated analytical settlement engine, "
     "live monitoring, risk alarms and AI support.",
     accent=RED, body_h=1.3, body_size=13.5)

card(s, 0.6, 4.0, 12.1, 2.75, "Research questions derived from the gaps",
     "Q1  How can the long-term consolidation settlement model be delivered as an open, "
     "reusable analytical engine?\n"
     "Q2  How can the model be calibrated and validated against monitored settlement "
     "with a quantified accuracy target?\n"
     "Q3  How can monitoring data, risk alarms and prediction be exposed through a "
     "standard API and a 3D digital-twin interface?\n"
     "Q4  How can AI assist engineers in analysis, design and reporting?",
     accent=ACCENT, body_h=1.9, body_size=13)

footer(s)

# ---------------------------------------------------------------------------
# Slide 10 — 5. Problem Statement (proposed solution)
# ---------------------------------------------------------------------------
s = slide()
header(s, "5", "Problem Statement \u2014 Proposed Work",
       "How this project answers the research questions", page=10)

sols = [
    ("Open analytical engine", "Mindlin immediate + Hankel-transform consolidation \u2014 "
     "the base-paper idea delivered as a reusable, closed-form engine.", ACCENT),
    ("Validation & calibration", "Beijing Line 12 reference \u2014 4.2 mm predicted vs "
     "4.4 mm monitored (0.08% deviation), <5% target enforced by tests.", TEAL),
    ("API + database", "REST API over FastAPI, SQLite monitoring DB "
     "(shield / monitoring / calculated results).", ORANGE),
    ("Digital twin UI", "React + Three.js 3D scene, settlement charts, SHM monitor, "
     "risk alarms and ML anomaly detection.", NAVY),
    ("AI copilot", "ChatGPT and Gemini assistants for analysis, design support, "
     "image generation and QA.", GREEN),
]
y = 1.65
for t, d, c in sols:
    rect(s, 0.6, y, 12.1, 0.85, fill=LIGHT)
    rect(s, 0.6, y, 0.1, 0.85, fill=c)
    txt(s, 0.95, y + 0.1, 3.4, 0.4, t, size=14, color=NAVY, bold=True)
    txt(s, 4.5, y + 0.12, 8.1, 0.65, d, size=11.5, color=BODY)
    y += 0.98

card(s, 0.6, 6.35, 12.1, 0.6, "",
     "Each proposed component maps directly onto a demerit of the base paper.",
     accent=TEAL, body_size=12.5)

footer(s)

# ---------------------------------------------------------------------------
# Slide 11 — 6. Conclusion
# ---------------------------------------------------------------------------
s = slide()
header(s, "6", "Conclusion", "What the project delivers", page=11)

card(s, 0.6, 1.65, 6.4, 3.0, "Achievements",
     "1.  A physically rigorous dual analytical engine (Mindlin + Hankel "
     "consolidation) \u2014 the base paper\u2019s long-term model made open and reusable.\n"
     "2.  Quantified validation against real monitoring: 4.2 vs 4.4 mm on Beijing "
     "Line 12, 0.08% deviation, <5% target.\n"
     "3.  A complete digital-twin platform \u2014 REST API, monitoring database, 3D UI, "
     "risk alarms, ML anomaly detection.\n"
     "4.  Dual-AI copilot (ChatGPT + Gemini) with offline fallback.",
     accent=TEAL, body_h=2.3, body_size=13)
card(s, 7.2, 1.65, 5.5, 3.0, "Future work",
     "\u2022  Coupled 3D FEM verification for complex geology.\n"
     "\u2022  Real sensor streaming via IoT / SCADA.\n"
     "\u2022  Multi-line interference and building-specific impact.\n"
     "\u2022  Cloud deployment, multi-project tenancy.\n"
     "\u2022  RL-based shield parameter control.",
     accent=ACCENT, body_h=2.3, body_size=13)

rect(s, 0.6, 4.95, 12.1, 1.15, fill=DARK)
txt(s, 0.9, 5.08, 11.5, 0.5,
    "In short: a digital twin that sees settlement before it happens \u2014 "
    "and tells the shield driver what to do about it.",
    size=16, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
txt(s, 0.9, 5.62, 11.5, 0.4, "Thank you \u2014 questions welcome.",
    size=13, color=TEAL, align=PP_ALIGN.CENTER)

rect(s, 0, 6.5, SW, 1.0, fill=NAVY)
txt(s, 0.6, 6.62, 12.1, 0.4, "Stack: Python 3.14 \u00b7 FastAPI \u00b7 SQLAlchemy \u00b7 NumPy/SciPy \u00b7 "
    "React \u00b7 Three.js \u00b7 OpenAI \u00b7 Google GenAI", size=11, color=RGBColor(0xCF, 0xE3, 0xFC))

# ---------------------------------------------------------------------------
# Slide 12 — 7. Reference
# ---------------------------------------------------------------------------
s = slide()
header(s, "7", "Reference", "Base paper and related literature", page=12)

rect(s, 0.6, 1.6, 12.1, 1.35, fill=NAVY)
txt(s, 0.9, 1.72, 11.4, 0.4, "[1]  Base paper (this project is based on)", size=12.5,
    color=TEAL, bold=True)
txt(s, 0.9, 2.1, 11.4, 0.8,
    "Liu B, Han Q, Fu C, Zhang G, He Y, Li W. Development and engineering application "
    "of intelligent management and control platform for the shield tunneling "
    "construction close to risk sources. Journal of Intelligent Construction, 2024, "
    "2(2): 9180018. https://doi.org/10.26599/JIC.2024.9180018",
    size=12.5, color=WHITE)

refs = [
    ("[2]", "Mindlin R D. Force at a point in the interior of a semi-infinite solid. "
     "Journal of Applied Physics (Physics), 1936, 7(5): 195\u2013202."),
    ("[3]", "Terzaghi K. Theoretical Soil Mechanics. John Wiley & Sons, New York, 1943."),
    ("[4]", "Peck R B. Deep excavations and tunneling in soft ground. State of the Art "
     "Report, Proc. 7th Int. Conf. Soil Mechanics and Foundation Engineering, 1969: "
     "225\u2013290."),
    ("[5]", "Bi Z, et al. Application and outlook of information and intelligence "
     "technology for safe and efficient TBM construction. Tunnelling and Underground "
     "Space Technology, 2019."),
]
y = 3.2
for tag, ref in refs:
    rect(s, 0.6, y, 12.1, 0.75, fill=LIGHT)
    txt(s, 0.9, y, 0.85, 0.75, tag, size=12.5, color=ACCENT, bold=True,
        anchor=MSO_ANCHOR.MIDDLE)
    txt(s, 1.75, y + 0.08, 10.8, 0.6, ref, size=11.5, color=BODY)
    y += 0.88

card(s, 0.6, 6.85, 12.1, 0.6, "",
     "All settlement formulas in the engine follow the physics of references [2]\u2013[4].",
     accent=TEAL, body_size=12)

# ---------------------------------------------------------------------------
prs.save(r"C:\Users\SURJITH RAJ\tunneling-platform\Project_Defense.pptx")
print("Saved Project_Defense.pptx with", len(prs.slides._sldIdLst), "slides")
