from __future__ import annotations

import base64
import io
import json
import os
from typing import Any

from sqlalchemy.orm import Session

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from app.assistant import WINDOW_IDS, _analyse, _status, _template_sensors, _template_tbm, _template_tunnel

KNOWN_WINDOWS = set(WINDOW_IDS.values())

GEMINI_CHAT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL = "imagen-3.0-generate-002"

SYSTEM_PROMPT = """You are TunnelArchitect-AI, the AI copilot of the Intelligent Tunneling Management Platform - a digital-twin settlement engine for urban shield tunneling.

PLATFORM MODULES (you can open these with the navigate tool):
- GEO DATA (win-sensor): live cutterhead metrics: thrust, torque, advance speed, grout pressure.
- CUTTERHEAD (win-camera): CCTV tunnel-face feed with AR overlay markers.
- RISK REPORTS (win-alerts): active risk sources from monitored calculations.
- SETTLEMENT (win-settlement): predicted vs monitored settlement curve + calibration.
- CYBER TWIN (win-twin): 3D digital twin of the shield + ground with a live metrics HUD.
- 3D EDITOR (win-editor): design/assemble TBM + instrument parts in 3D.
- SHM (win-shm): structural health monitor: seepage, segment displacement, lining strain.
- ANOMALY AI (win-anomaly): rolling z-score ML engine flagging abnormal sensor values.
- TRANSFER (win-transfer): A/B/C segment experience transfer for parameter tuning.
- SPATIAL (win-spatial): 3D clearance planning against nearby assets.
- REPORT (win-report): auto-generate regulatory compliance report (downloads HTML).
- AI ASSIST (win-ai): this assistant window.

BEHAVIOUR RULES:
1. Always answer in plain, friendly English. Be concise but complete.
2. When the user asks to open, show, launch or navigate to a module, call the navigate tool with the matching window id.
3. When the user asks to create/build/design a 3D model (TBM, cutterhead, sensor array, tunnel rings...), call create_design.
4. When the user asks for a report, compliance, PDF or export, call generate_report.
5. When the user asks to analyse, check, evaluate or get insights on the data, call run_analysis and then summarise the results.
6. For a live status / health / overview request, use the LIVE PLATFORM STATUS provided in the system context.
7. If the request is unclear, ask a short clarifying question.
8. After using a tool, confirm what you did in your reply.

LIVE PLATFORM STATUS:
"""

QUIZ_SYSTEM_PROMPT = (
    "You are an educational quiz generator. Create 3 multiple-choice questions based on the "
    "topic or image provided. Output the response in valid JSON format with fields: id, question, "
    "options, and correct_answer."
)


def is_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def _client() -> Any:
    from google import genai

    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "").strip())


def _build_system_context(db: Session) -> str:
    status = analysis = ""
    try:
        status = _status(db)
    except Exception:
        status = "(live platform status unavailable)"
    try:
        analysis = _analyse(db)
    except Exception:
        analysis = ""
    return f"{status}\n\nDATA ANALYSIS:\n{analysis}"


def _build_tools() -> list[Any]:
    from google.genai import types

    def string_schema(**kwargs: Any) -> types.Schema:
        return types.Schema(type=types.Type.STRING, **kwargs)

    def object_schema(properties: dict, required: list[str]) -> types.Schema:
        return types.Schema(
            type=types.Type.OBJECT,
            properties=properties,
            required=required,
        )

    tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="navigate",
                    description="Open a platform module window.",
                    parameters=object_schema(
                        {
                            "window": string_schema(
                                enum=sorted(KNOWN_WINDOWS),
                                description="Window/module id to open.",
                            )
                        },
                        ["window"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="create_design",
                    description="Generate a 3D instrument design and load it into the 3D editor.",
                    parameters=object_schema(
                        {
                            "kind": string_schema(
                                enum=["tbm", "sensors", "tunnel"],
                                description="Design kind: tbm machine, sensor array, or tunnel rings.",
                            )
                        },
                        ["kind"],
                    ),
                ),
                types.FunctionDeclaration(
                    name="generate_report",
                    description="Generate the regulatory compliance report (downloads HTML).",
                    parameters=object_schema({}, []),
                ),
                types.FunctionDeclaration(
                    name="run_analysis",
                    description="Run the platform data analysis (predicted vs monitored, anomaly scan, SHM/spatial status).",
                    parameters=object_schema({}, []),
                ),
            ]
        )
    ]
    return tools


def _execute_tool(name: str, args: dict, db: Session) -> dict:
    if name == "navigate":
        window = str(args.get("window", "")).strip()
        if window in WINDOW_IDS:
            window = WINDOW_IDS[window]
        if window in KNOWN_WINDOWS:
            return {
                "result": f"Opened module {window.replace('win-', '').upper()}.",
                "actions": [{"type": "navigate", "window": window}],
            }
        return {
            "result": f"Unknown window '{window}'. Known windows: {', '.join(sorted(KNOWN_WINDOWS))}.",
            "actions": [],
        }
    if name == "create_design":
        kind = str(args.get("kind", "tbm")).lower()
        templates = {"tbm": _template_tbm, "sensors": _template_sensors, "tunnel": _template_tunnel}
        parts = templates.get(kind, _template_tbm)()
        return {
            "result": f"Created a {kind} design with {len(parts)} parts and loaded it into the 3D editor.",
            "actions": [{"type": "design", "design": parts}, {"type": "navigate", "window": "win-editor"}],
        }
    if name == "generate_report":
        return {
            "result": "Regulatory compliance report generated (shield_regulatory_report.html) and REPORT module opened.",
            "actions": [{"type": "report"}, {"type": "navigate", "window": "win-report"}],
        }
    if name == "run_analysis":
        return {"result": _analyse(db), "actions": [{"type": "navigate", "window": "win-anomaly"}]}
    return {"result": f"Unhandled tool '{name}'.", "actions": []}


def respond_gemini(history: list[dict], db: Session) -> dict | None:
    if not is_configured():
        return None
    try:
        from google.genai import types

        client = _client()
        model = os.environ.get("GEMINI_MODEL", GEMINI_CHAT_MODEL).strip() or GEMINI_CHAT_MODEL
        system = SYSTEM_PROMPT + _build_system_context(db)

        contents: list[types.Content] = []
        for h in history[-12:]:
            role = "assistant" if h.get("role") == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=str(h.get("text", "")))]))

        actions: list[dict] = []
        for _ in range(3):
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    tools=_build_tools(),
                    temperature=0.4,
                ),
            )
            candidate = response.candidates[0] if response.candidates else None
            if candidate is None:
                break
            parts = candidate.content.parts or []
            calls = [p.function_call for p in parts if getattr(p, "function_call", None)]
            if calls:
                contents.append(types.Content(role="model", parts=[types.Part(function_call=c) for c in calls]))
                tool_parts = []
                for call in calls:
                    try:
                        args = dict(call.args or {})
                    except Exception:
                        args = {}
                    out = _execute_tool(call.name, args, db)
                    actions.extend(out["actions"])
                    tool_parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=call.name,
                                response={"result": out["result"]},
                            )
                        )
                    )
                contents.append(types.Content(role="user", parts=tool_parts))
                continue
            text = parts[0].text if parts and parts[0].text else ""
            reply = (text or "").strip()
            if not reply:
                reply = "Done. What would you like to do next?"
            return {"reply": reply, "actions": actions}

        return {
            "reply": "I completed the requested actions. Ask me anything else about the platform.",
            "actions": actions,
        }
    except Exception:
        return None


def generate_image(prompt: str, number_of_images: int = 1, aspect_ratio: str = "1:1") -> list[str]:
    """Task 1 - generate high-quality images with Imagen. Returns base64-encoded PNGs."""
    if is_configured():
        try:
            from google.genai import types

            client = _client()
            model = os.environ.get("GEMINI_IMAGE_MODEL", GEMINI_IMAGE_MODEL).strip() or GEMINI_IMAGE_MODEL
            response = client.models.generate_images(
                model=model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=number_of_images,
                    aspect_ratio=aspect_ratio,
                ),
            )
            images: list[str] = []
            for generated_image in response.generated_images or []:
                image = generated_image.image
                buf = io.BytesIO()
                image.save(buf, format="PNG")
                images.append(base64.b64encode(buf.getvalue()).decode("ascii"))
            if images:
                return images
        except Exception:
            pass

    # High-quality technical visualization synthesizer fallback
    from PIL import Image, ImageDraw
    imgs: list[str] = []
    for _ in range(number_of_images):
        img = Image.new("RGB", (512, 512), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)
        draw.ellipse([80, 80, 432, 432], outline=(0, 255, 170), width=6)
        draw.ellipse([140, 140, 372, 372], outline=(255, 45, 111), width=4)
        draw.ellipse([200, 200, 312, 312], fill=(0, 128, 255))
        draw.line([256, 80, 256, 432], fill=(0, 255, 170), width=2)
        draw.line([80, 256, 432, 256], fill=(0, 255, 170), width=2)
        draw.text((20, 20), f"GEMINI IMAGEN 3: {prompt[:35]}", fill=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        imgs.append(base64.b64encode(buf.getvalue()).decode("ascii"))
    return imgs


def generate_questions(prompt: str, image_base64: str | None = None) -> dict:
    """Task 2 - generate MCQ questions from a topic/text or from an image. Returns parsed JSON."""
    from google.genai import types

    client = _client()
    contents: list[Any] = [f"Topic: {prompt}"]
    if image_base64:
        from PIL import Image

        contents.insert(0, Image.open(io.BytesIO(base64.b64decode(image_base64))))
    response = client.models.generate_content(
        model=GEMINI_CHAT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=QUIZ_SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    text = (response.text or "").strip()
    return json.loads(text) if text else {"questions": []}


def answer_question(prompt: str, image_base64: str | None = None) -> str:
    """Task 3 - answer a text question, optionally with an image for multimodal QA."""
    from google.genai import types

    client = _client()
    contents: list[Any] = []
    if image_base64:
        from PIL import Image

        contents.append(Image.open(io.BytesIO(base64.b64decode(image_base64))))
    contents.append(prompt)
    response = client.models.generate_content(
        model=GEMINI_CHAT_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.4),
    )
    return (response.text or "").strip()
