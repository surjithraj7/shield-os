"""
Collaborative Multi-Agent System for Autonomous Shield Tunneling Operations
==========================================================================
Built with LangGraph / LangChain graph topology. Coordinates dynamic reasoning,
geotechnical analysis, TBM parameter optimization, structural auditing,
and safety veto enforcement.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional, Literal, TypedDict
from dataclasses import dataclass, field

try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    END = "__END__"
    class StateGraph:
        def __init__(self, state_schema):
            self.state_schema = state_schema
            self.nodes = {}
            self.edges = {}
            self.entry_point = None
        def add_node(self, name, func): self.nodes[name] = func
        def add_edge(self, src, dst): self.edges[src] = dst
        def set_entry_point(self, name): self.entry_point = name
        def add_conditional_edges(self, src, router, mapping): self.edges[src] = (router, mapping)
        def compile(self): return self

logger = logging.getLogger("app.engine.multi_agent")

# =====================================================================
# 1. State Definition
# =====================================================================

class AgentMessage(TypedDict):
    sender: str
    content: str
    payload: Dict[str, Any]


class TunnelAgentState(TypedDict):
    # Geotechnical Context
    ring_number: int
    chainage_m: float
    geology_type: str
    soil_elasticity_mpa: float
    pore_water_pressure_kpa: float
    gpr_anomaly_detected: bool

    # Current Live TBM Operating Telemetry
    current_thrust_kn: float
    current_rpm: float
    current_epb_kpa: float
    current_advance_speed_mm_min: float
    screw_rpm: float

    # Agent Decisions & Outputs
    geotech_risk_level: str
    geotech_recommendations: Dict[str, Any]
    
    proposed_tbm_setpoints: Dict[str, float]
    copilot_rationale: str

    structural_settlement_mm: float
    ring_ovalization_mm: float
    structural_risk_flag: bool
    structural_audit_log: str

    safety_decision: Literal["APPROVED", "VETOED_RETRY", "EMERGENCY_HALT"]
    safety_veto_reason: Optional[str]
    emergency_grout_protocol: Optional[Dict[str, Any]]

    # Conversation & Loop Control
    iteration_count: int
    max_iterations: int
    audit_trail: List[AgentMessage]


# =====================================================================
# 2. JSON Tool Calling Specifications & Function Schemas
# =====================================================================

GEOTECH_ANALYST_TOOL_SCHEMA = {
    "name": "interpret_geotech_data",
    "description": "Analyzes borehole logs, GPR radar anomalies, and ground displacement telemetry to classify risk level and estimate soil parameters.",
    "parameters": {
        "type": "object",
        "properties": {
            "ring_number": {"type": "integer"},
            "geology_type": {"type": "string"},
            "gpr_anomaly": {"type": "boolean"},
            "pore_pressure_kpa": {"type": "number"}
        },
        "required": ["ring_number", "geology_type"]
    }
}

TBM_COPILOT_TOOL_SCHEMA = {
    "name": "recommend_tbm_setpoints",
    "description": "Calculates optimal TBM operating parameters (RPM, thrust force, face pressure balance) for current geological zone.",
    "parameters": {
        "type": "object",
        "properties": {
            "geotech_risk": {"type": "string"},
            "target_advance_speed": {"type": "number"},
            "target_epb_pressure": {"type": "number"},
            "target_thrust_kn": {"type": "number"},
            "target_rpm": {"type": "number"}
        },
        "required": ["target_epb_pressure", "target_thrust_kn", "target_rpm"]
    }
}

STRUCTURAL_INTEGRITY_TOOL_SCHEMA = {
    "name": "audit_structural_integrity",
    "description": "Audits ring segment strain, ovalization convergence, gasket extrusion, and surface settlement risks.",
    "parameters": {
        "type": "object",
        "properties": {
            "ring_number": {"type": "integer"},
            "monitored_settlement_mm": {"type": "number"},
            "ring_ovalization_mm": {"type": "number"}
        },
        "required": ["ring_number", "monitored_settlement_mm"]
    }
}

SAFETY_ARBITER_TOOL_SCHEMA = {
    "name": "arbitrate_safety_veto",
    "description": "Holds absolute veto power. Checks safety envelopes, triggers emergency grouting, or approves parameter changes.",
    "parameters": {
        "type": "object",
        "properties": {
            "proposed_setpoints": {"type": "object"},
            "predicted_settlement_mm": {"type": "number"},
            "epb_lower_bound_kpa": {"type": "number"},
            "decision": {"type": "string", "enum": ["APPROVED", "VETOED_RETRY", "EMERGENCY_HALT"]}
        },
        "required": ["decision"]
    }
}


# =====================================================================
# 3. Agent Node Logic
# =====================================================================

def geotech_analyst_node(state: TunnelAgentState) -> Dict[str, Any]:
    """Geotech_Analyst_Agent: Interprets geological strata, GPR anomalies, and soil properties."""
    gpr_flag = state.get("gpr_anomaly_detected", False)
    geology = state.get("geology_type", "Silty Clay")
    
    if gpr_flag or geology in ["Bouldery Sand", "Karst Cavity Zone"]:
        risk_level = "HIGH_ANOMALY"
        rec = {
            "face_pressure_boost_kpa": 30.0,
            "slurry_viscosity_target": "High",
            "bentonite_injection_rate_l_min": 120.0
        }
    else:
        risk_level = "NOMINAL"
        rec = {
            "face_pressure_boost_kpa": 0.0,
            "slurry_viscosity_target": "Standard",
            "bentonite_injection_rate_l_min": 80.0
        }

    msg: AgentMessage = {
        "sender": "Geotech_Analyst_Agent",
        "content": f"Geotechnical analysis complete for Ring #{state['ring_number']}. Zone: {geology}, Risk: {risk_level}.",
        "payload": rec
    }

    return {
        "geotech_risk_level": risk_level,
        "geotech_recommendations": rec,
        "audit_trail": state.get("audit_trail", []) + [msg]
    }


def tbm_copilot_node(state: TunnelAgentState) -> Dict[str, Any]:
    """TBM_CoPilot_Agent: Recommends optimal operating setpoints."""
    risk_level = state.get("geotech_risk_level", "NOMINAL")
    rec = state.get("geotech_recommendations", {})
    iter_count = state.get("iteration_count", 0) + 1
    
    # Base calculation adjusted by geotech recommendations
    epb_boost = rec.get("face_pressure_boost_kpa", 0.0)
    
    # Adjust parameters if previously vetoed by Safety Arbiter
    veto_penalty = 15.0 if state.get("safety_decision") == "VETOED_RETRY" else 0.0

    target_epb = max(220.0, state["current_epb_kpa"] + epb_boost + veto_penalty)
    target_thrust = min(28000.0, state["current_thrust_kn"] * 0.98 if veto_penalty > 0 else state["current_thrust_kn"])
    target_rpm = max(1.0, min(3.2, 2.4 - (0.3 if risk_level == "HIGH_ANOMALY" else 0.0)))
    target_advance = max(15.0, min(50.0, 35.0 - (10.0 if veto_penalty > 0 else 0.0)))

    setpoints = {
        "target_epb_kpa": round(target_epb, 2),
        "target_thrust_kn": round(target_thrust, 2),
        "target_rpm": round(target_rpm, 2),
        "target_advance_speed_mm_min": round(target_advance, 2),
        "target_screw_rpm": round(target_rpm * 3.5, 2)
    }

    rationale = f"Optimization step {iter_count}: Selected setpoints for EPB balance={target_epb}kPa under {risk_level} conditions."
    msg: AgentMessage = {
        "sender": "TBM_CoPilot_Agent",
        "content": rationale,
        "payload": setpoints
    }

    return {
        "proposed_tbm_setpoints": setpoints,
        "copilot_rationale": rationale,
        "iteration_count": iter_count,
        "audit_trail": state.get("audit_trail", []) + [msg]
    }


def structural_integrity_node(state: TunnelAgentState) -> Dict[str, Any]:
    """Structural_Integrity_Agent: Audits segment strain and surface settlement trends."""
    setpoints = state.get("proposed_tbm_setpoints", {})
    epb = setpoints.get("target_epb_kpa", 250.0)
    
    # Empirical physics surrogate estimate of surface settlement for auditing
    estimated_settlement_mm = max(1.2, 12.0 - (epb - 150.0) * 0.04)
    ovalization_mm = max(2.0, estimated_settlement_mm * 0.6)
    
    risk_flag = estimated_settlement_mm > 10.0 or ovalization_mm > 8.0
    audit_text = f"Ring #{state['ring_number']} predicted settlement: {estimated_settlement_mm:.2f}mm, Ovalization: {ovalization_mm:.2f}mm."

    msg: AgentMessage = {
        "sender": "Structural_Integrity_Agent",
        "content": audit_text,
        "payload": {"settlement_mm": estimated_settlement_mm, "ovalization_mm": ovalization_mm, "risk_flag": risk_flag}
    }

    return {
        "structural_settlement_mm": estimated_settlement_mm,
        "ring_ovalization_mm": ovalization_mm,
        "structural_risk_flag": risk_flag,
        "structural_audit_log": audit_text,
        "audit_trail": state.get("audit_trail", []) + [msg]
    }


def safety_arbiter_node(state: TunnelAgentState) -> Dict[str, Any]:
    """Safety_Arbiter_Agent: Holds absolute VETO power and handles conflict resolution."""
    settlement = state.get("structural_settlement_mm", 0.0)
    setpoints = state.get("proposed_tbm_setpoints", {})
    epb = setpoints.get("target_epb_kpa", 0.0)
    iter_count = state.get("iteration_count", 1)
    max_iters = state.get("max_iterations", 3)

    min_safe_epb = 200.0  # Geotechnical lower bound for collapse prevention
    max_safe_settlement = 12.0  # Surface building safety threshold

    if settlement > 15.0 or epb < min_safe_epb - 50.0:
        # Severe safety breach -> Immediate Emergency Halt
        decision = "EMERGENCY_HALT"
        veto_reason = f"CRITICAL: Settlement ({settlement:.2f}mm) or EPB pressure ({epb}kPa) breached collapse safety envelopes!"
        emergency_grout = {
            "action": "EMERGENCY_TAIL_GROUTING",
            "grout_pressure_mpa": 3.5,
            "volume_m3": 4.5,
            "accelerator_ratio_pct": 5.0,
            "tbm_status": "CUTTERHEAD_HALTED"
        }
    elif (settlement > max_safe_settlement or epb < min_safe_epb) and iter_count < max_iters:
        # Mild conflict -> Veto and demand re-optimization from TBM CoPilot
        decision = "VETOED_RETRY"
        veto_reason = f"VETO: Settlement ({settlement:.2f}mm) exceeds target ({max_safe_settlement}mm). Re-adjust EPB pressure upwards."
        emergency_grout = None
    else:
        # Passed safety audit
        decision = "APPROVED"
        veto_reason = None
        emergency_grout = None

    msg: AgentMessage = {
        "sender": "Safety_Arbiter_Agent",
        "content": f"Safety Arbitration Result: {decision}. Reason: {veto_reason or 'All safety constraints satisfied.'}",
        "payload": {"decision": decision, "emergency_grout": emergency_grout}
    }

    return {
        "safety_decision": decision,
        "safety_veto_reason": veto_reason,
        "emergency_grout_protocol": emergency_grout,
        "audit_trail": state.get("audit_trail", []) + [msg]
    }


# =====================================================================
# 4. Graph Topology & Routing Logic
# =====================================================================

def router_after_safety(state: TunnelAgentState) -> str:
    decision = state.get("safety_decision", "APPROVED")
    if decision == "APPROVED":
        return END
    elif decision == "EMERGENCY_HALT":
        return END
    elif decision == "VETOED_RETRY":
        return "tbm_copilot_node"
    return END


def build_tunnel_multi_agent_graph():
    """Constructs the executable LangGraph multi-agent workflow."""
    workflow = StateGraph(TunnelAgentState)

    # Add Nodes
    workflow.add_node("geotech_analyst_node", geotech_analyst_node)
    workflow.add_node("tbm_copilot_node", tbm_copilot_node)
    workflow.add_node("structural_integrity_node", structural_integrity_node)
    workflow.add_node("safety_arbiter_node", safety_arbiter_node)

    # Set Entry Point
    workflow.set_entry_point("geotech_analyst_node")

    # Define Linear Edges
    workflow.add_edge("geotech_analyst_node", "tbm_copilot_node")
    workflow.add_edge("tbm_copilot_node", "structural_integrity_node")
    workflow.add_edge("structural_integrity_node", "safety_arbiter_node")

    # Conditional Routing for Conflict Resolution / Veto Loop
    workflow.add_conditional_edges(
        "safety_arbiter_node",
        router_after_safety,
        {
            END: END,
            "tbm_copilot_node": "tbm_copilot_node"
        }
    )

    return workflow.compile()


# Multi-agent graph singleton instance
tunnel_agent_app = build_tunnel_multi_agent_graph()
