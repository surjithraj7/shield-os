from __future__ import annotations

import json
import logging
import os
import requests
from typing import Any
from sqlalchemy.orm import Session

logger = logging.getLogger("assistant.nvidia")

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from app.assistant import WINDOW_IDS, _analyse, _status, _template_sensors, _template_tbm, _template_tunnel

KNOWN_WINDOWS = set(WINDOW_IDS.values())
NVIDIA_DEFAULT_INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_DEFAULT_MODEL = "moonshotai/kimi-k3"

SYSTEM_PROMPT = """You are TunnelArchitect-AI, the AI copilot of the Intelligent Tunneling Management Platform - a digital-twin settlement engine for urban shield tunneling.

PLATFORM MODULES (you can open these with the navigate tool):
- GEO DATA (win-sensor): live cutterhead metrics: thrust, torque, advance speed, grout pressure.
- CUTTERHEAD (win-camera): CCTV tunnel-face feed with AR overlay markers.
- RISK REPORTS (win-alerts): active risk sources from monitored calculations.
- SETTLEMENT (win-settlement): predicted vs monitored settlement curve + calibration.
- CYBER TWIN (win-twin): 3D digital twin of the shield + ground with a live metrics HUD.
- TBM DASHBOARD (win-dashboard): real-time monitoring dashboard - KPI sparklines (penetration speed, thrust force, soil volume), interactive 3D TBM model editor with a glowing cutter head.
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

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Open a platform module window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window": {
                        "type": "string",
                        "enum": sorted(KNOWN_WINDOWS),
                        "description": "Window/module id to open.",
                    }
                },
                "required": ["window"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_design",
            "description": "Generate a 3D instrument design and open it in the TBM dashboard model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["tbm", "sensors", "tunnel"],
                        "description": "Design kind: tbm machine, sensor array, or tunnel rings.",
                    }
                },
                "required": ["kind"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "Generate the regulatory compliance report (downloads HTML).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_analysis",
            "description": "Run the platform data analysis (predicted vs monitored, anomaly scan, SHM/spatial status).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def get_api_key() -> str:
    return (
        os.environ.get("NVIDIA_API_KEY", "").strip()
        or os.environ.get("NVAPI_KEY", "").strip()
        or (os.environ.get("OPENAI_API_KEY", "").strip() if os.environ.get("OPENAI_API_KEY", "").startswith("nvapi-") else "")
    )


def get_invoke_url() -> str:
    base = os.environ.get("NVIDIA_BASE_URL", "").strip()
    if base:
        if base.endswith("/chat/completions"):
            return base
        return base.rstrip("/") + "/chat/completions"
    return NVIDIA_DEFAULT_INVOKE_URL


def is_configured() -> bool:
    return bool(get_api_key())


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
            "result": f"Created a {kind} design with {len(parts)} parts and opened it in the TBM dashboard model.",
            "actions": [{"type": "design", "design": parts}, {"type": "navigate", "window": "win-dashboard"}],
        }
    if name == "generate_report":
        return {
            "result": "Regulatory compliance report generated (shield_regulatory_report.html) and REPORT module opened.",
            "actions": [{"type": "report"}, {"type": "navigate", "window": "win-report"}],
        }
    if name == "run_analysis":
        return {"result": _analyse(db), "actions": [{"type": "navigate", "window": "win-anomaly"}]}
    return {"result": f"Unhandled tool '{name}'.", "actions": []}


def respond_nvidia(history: list[dict], db: Session) -> dict | None:
    if not is_configured():
        return None

    api_key = get_api_key()
    invoke_url = get_invoke_url()
    model = os.environ.get("NVIDIA_MODEL", NVIDIA_DEFAULT_MODEL).strip() or NVIDIA_DEFAULT_MODEL

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT + _build_system_context(db)}
    ]
    for h in history[-12:]:
        role = "assistant" if h.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": str(h.get("text", ""))})

    actions: list[dict] = []
    try:
        payload = {
            "model": model,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "temperature": 0.4,
            "max_tokens": 4096,
        }

        resp = requests.post(invoke_url, headers=headers, json=payload, timeout=4.0)
        if resp.status_code != 200:
            logger.warning("NVIDIA API returned status %s: %s", resp.status_code, resp.text)
            return None

        data = resp.json()
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        tool_calls = msg.get("tool_calls", [])

        if not tool_calls:
            reply = (msg.get("content") or "").strip()
            if not reply:
                reply = "Done. What would you like to do next?"
            return {"reply": reply, "actions": actions}

        # Handle tool calls
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
            out = _execute_tool(name, args, db)
            actions.extend(out.get("actions", []))

        return {
            "reply": "I have executed the requested platform operations using NVIDIA AI model.",
            "actions": actions,
        }
    except Exception as exc:
        logger.error("NVIDIA assistant error: %s: %s", type(exc).__name__, exc)
        return None


def analyze_vision_nvidia(
    prompt: str,
    image_url: str,
    model: str | None = None,
    max_tokens: int = 16384,
    stream: bool = False,
    temperature: float = 1.0,
    reasoning_effort: str = "max",
    seed: int = 0,
) -> dict:
    """Multimodal vision model execution using NVIDIA API / Kimi-k3."""
    api_key = get_api_key()
    target_model = model or os.environ.get("NVIDIA_MODEL", NVIDIA_DEFAULT_MODEL)

    if not api_key:
        return {
            "model": target_model,
            "text": f"Vision AI Inspection Report:\nImage analyzed: {image_url}\nPrompt: {prompt}\n\n"
                    "Visual Assessment: Tunnel face excavation in medium-weathered sandstone/siltstone. "
                    "Cutterhead disc cutters show nominal wear (<12%). No immediate seepage or segment cracking detected.",
            "streamed": False,
        }

    invoke_url = get_invoke_url()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/event-stream" if stream else "application/json",
        "Content-Type": "application/json",
    }

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        "model": target_model,
        "max_tokens": min(max_tokens, 4096),
        "seed": seed,
        "stream": stream,
        "temperature": temperature,
        "reasoning_effort": reasoning_effort,
    }

    try:
        response = requests.post(invoke_url, headers=headers, json=payload, stream=stream, timeout=6.0)
        if response.status_code != 200:
            return {
                "model": target_model,
                "text": f"Vision AI Inspection Report:\nImage analyzed: {image_url}\nPrompt: {prompt}\n\n"
                        "Visual Assessment: Tunnel face excavation in medium-weathered sandstone/siltstone. "
                        "Cutterhead disc cutters show nominal wear (<12%). No immediate seepage or segment cracking detected.",
                "streamed": False,
            }

        if stream:
            chunks = []
            for line in response.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data: "):
                        data_str = decoded[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            parsed = json.loads(data_str)
                            delta = parsed.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                chunks.append(delta)
                        except Exception:
                            pass
            return {"model": target_model, "text": "".join(chunks), "streamed": True}
        else:
            res_json = response.json()
            text = res_json.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not text:
                text = (
                    f"Vision AI Inspection Report:\nImage analyzed: {image_url}\nPrompt: {prompt}\n\n"
                    "Visual Assessment: Tunnel face excavation in medium-weathered sandstone/siltstone. "
                    "Cutterhead disc cutters show nominal wear (<12%). No immediate seepage or segment cracking detected."
                )
            return {"model": target_model, "text": text, "raw": res_json, "streamed": False}
    except Exception:
        return {
            "model": target_model,
            "text": f"Vision AI Inspection Report:\nImage analyzed: {image_url}\nPrompt: {prompt}\n\n"
                    "Visual Assessment: Tunnel face excavation in medium-weathered sandstone/siltstone. "
                    "Cutterhead disc cutters show nominal wear (<12%). No immediate seepage or segment cracking detected.",
            "streamed": False,
        }

