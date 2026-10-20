from __future__ import annotations

import json
import logging
import os
import socket
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("assistant.gpt")

from sqlalchemy.orm import Session

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from app.assistant import WINDOW_IDS, _analyse, _status, _template_sensors, _template_tbm, _template_tunnel

KNOWN_WINDOWS = set(WINDOW_IDS.values())

SYSTEM_PROMPT = """You are TunnelArchitect-AI, the AI copilot of the Intelligent Tunneling Management Platform - a digital-twin settlement engine for urban shield tunneling.

PLATFORM MODULES (you can open these with the navigate tool):
- GEO DATA (win-sensor): live cutterhead metrics: thrust, torque, advance speed, grout pressure.
- CUTTERHEAD (win-camera): CCTV tunnel-face feed with AR overlay markers.
- RISK REPORTS (win-alerts): active risk sources from monitored calculations.
- SETTLEMENT (win-settlement): predicted vs monitored settlement curve + calibration.
- CYBER TWIN (win-twin): 3D digital twin of the shield + ground with a live metrics HUD.
- TBM DASHBOARD (win-dashboard): real-time monitoring dashboard - KPI sparklines (penetration speed, thrust force, soil volume), an interactive 3D TBM model editor with a glowing cutter head, personnel count and construction cost.
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


def is_configured() -> bool:
    return bool(
        os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("OPENROUTER_API_KEY", "").strip()
    )


def _relay_alive(base_url: str = "", timeout: float = 2.0) -> bool:
    if not base_url:
        base_url = (os.environ.get("OPENAI_BASE_URL") or "").strip()
    if not base_url:
        return True
    try:
        parsed = urlparse(base_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


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


def _consume_stream(stream) -> tuple[str, dict]:
    content_parts: list[str] = []
    tool_calls: dict[int, dict[str, str]] = {}
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta is None:
            continue
        if delta.content:
            content_parts.append(delta.content)
        if delta.tool_calls:
            for tc in delta.tool_calls:
                entry = tool_calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    entry["id"] = tc.id
                if tc.function:
                    if tc.function.name:
                        entry["name"] = tc.function.name
                    if tc.function.arguments:
                        entry["arguments"] += tc.function.arguments
    return "".join(content_parts), tool_calls


def respond_gpt(history: list[dict], db: Session) -> dict | None:
    if not is_configured():
        return None

    api_key = (
        os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("OPENROUTER_API_KEY", "").strip()
    )
    base_url = (os.environ.get("OPENAI_BASE_URL") or "").strip()
    if not base_url and api_key.startswith("sk-or-v1-"):
        base_url = "https://openrouter.ai/api/v1"

    if not _relay_alive(base_url):
        logger.info("GPT relay unreachable at %s - falling back", base_url or "default")
        return None
    try:
        from openai import OpenAI

        headers = {}
        if "openrouter.ai" in base_url:
            headers = {
                "HTTP-Referer": "https://shield-os.local",
                "X-OpenRouter-Title": "SHIELD-OS Tunneling Platform",
            }

        client = OpenAI(
            api_key=api_key,
            base_url=base_url or None,
            timeout=4.0,
            max_retries=1,
            default_headers=headers if headers else None,
        )
        model = os.environ.get("OPENAI_MODEL", "openrouter/free").strip() or "openrouter/free"

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT + _build_system_context(db)}
        ]
        for h in history[-12:]:
            role = "assistant" if h.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": str(h.get("text", ""))})

        actions: list[dict] = []
        for _ in range(3):
            try:
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.4,
                    stream=True,
                )
            except Exception as tool_exc:
                logger.warning("Tool completion failed (%s), falling back to standard completion", tool_exc)
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.4,
                    stream=True,
                )

            content, tool_calls = _consume_stream(stream)
            if not tool_calls:
                reply = (content or "").strip()
                if not reply:
                    reply = "Done. What would you like to do next?"
                return {"reply": reply, "actions": actions}
            messages.append(
                {
                    "role": "assistant",
                    "content": content or "",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": tc["arguments"]},
                        }
                        for tc in tool_calls.values()
                    ],
                }
            )
            for tc in tool_calls.values():
                try:
                    args = json.loads(tc["arguments"] or "{}")
                except Exception:
                    args = {}
                out = _execute_tool(tc["name"], args, db)
                actions.extend(out["actions"])
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": out["result"]})

        return {
            "reply": "I completed the requested actions. Ask me anything else about the platform.",
            "actions": actions,
        }
    except Exception as exc:  # noqa: BLE001 - fall back to offline copilot
        logger.error("GPT assistant error: %s: %s", type(exc).__name__, exc)
        return None
