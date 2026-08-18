"""
FORGE3D Innovation #3: Predictive Cutter Wear AI
ML-based cutter life prediction, maintenance scheduling, wear rate estimation
Uses physics-informed wear model (Cerchar-based) + operational parameter correlation
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# Wear Prediction Models
# ============================================================

@dataclass
class CutterState:
    """State of a single disc cutter"""
    cutter_id: int
    position_radius_m: float  # Distance from center
    initial_thickness_mm: float = 25.0
    current_thickness_mm: float = 25.0
    wear_rate_mm_per_m: float = 0.0  # Current wear rate
    total_distance_m: float = 0.0  # Total掘進 distance
    last_inspection_ring: int = 0
    vitrinite_reflectance: float = 1.5  # Rock abrasivity index

    @property
    def remaining_life_pct(self) -> float:
        return max(0.0, (self.current_thickness_mm / self.initial_thickness_mm) * 100)

    @property
    def wear_category(self) -> str:
        pct = self.remaining_life_pct
        if pct > 70:
            return "good"
        elif pct > 40:
            return "moderate"
        elif pct > 15:
            return "worn"
        else:
            return "critical"

    @property
    def estimated_rings_remaining(self) -> int:
        if self.wear_rate_mm_per_m <= 0:
            return 9999
        mm_remaining = self.current_thickness_mm - 5.0  # 5mm minimum
        if mm_remaining <= 0:
            return 0
        meters_remaining = mm_remaining / self.wear_rate_mm_per_m
        return max(0, int(meters_remaining / 1.6))  # 1.6m per ring


# ============================================================
# Physics-Informed Wear Model
# ============================================================

def calculate_wear_rate(
    thrust_kn: float,
    torque_knm: float,
    ucS_mpa: float = 30.0,  # Unconfined compressive strength
    cerchar_ai: float = 1.5,  # Cerchar abrasivity index
    advance_speed_mm_min: float = 45.0,
    radius_m: float = 3.2,
    n_discs: int = 12,
) -> float:
    """
    Estimate cutter wear rate using physics-informed model.
    Based on: Cerchar abrasivity + normal force + rock strength
    Returns: mm per meter of advance
    """
    # Normal force per cutter (simplified from total thrust)
    normal_force_kn = thrust_kn / n_discs

    # Wear index (Rabinowicz-type model)
    # WI = (AI * F_n) / (H * UCS)
    hardness_h = ucS_mpa * 10  # Approximate Vickers hardness
    if hardness_h <= 0:
        hardness_h = 1.0

    wear_index = (cerchar_ai * normal_force_kn) / (hardness_h * max(ucS_mpa, 1.0))

    # Base wear rate (mm/m) - calibrated to typical TBM operations
    base_wear = 0.008 * wear_index

    # Speed correction
    speed_factor = (advance_speed_mm_min / 45.0) ** 0.5

    # Torque correction (higher torque = more abrasion)
    torque_factor = (torque_knm / 2000.0) ** 0.3 if torque_knm > 0 else 1.0

    return base_wear * speed_factor * torque_factor


# ============================================================
# Pydantic Schemas
# ============================================================

class CutterWearRequest(BaseModel):
    """Input for wear prediction"""
    ring_no: int
    chainage_m: float
    thrust_kn: float = Field(12000.0, gt=0)
    torque_knm: float = Field(2000.0, gt=0)
    advance_speed_mm_min: float = Field(45.0, gt=0)
    ucS_mpa: float = Field(30.0, gt=0, description="Rock UCS [MPa]")
    cerchar_ai: float = Field(1.5, gt=0, description="Cerchar Abrasivity Index")
    n_cutters: int = Field(12, ge=4, le=24)
    cutter_positions: list[float] | None = None


class CutterHealthResponse(BaseModel):
    """Response with cutter health data"""
    ring_no: int
    chainage_m: float
    cutters: list[dict]
    overall_health_pct: float
    worst_cutter_id: int
    worst_cutter_health_pct: float
    maintenance_recommendation: str
    estimated_rings_to_maintenance: int
    next_inspection_ring: int
    alerts: list[dict]


class MaintenanceScheduleRequest(BaseModel):
    """Request for maintenance scheduling"""
    current_ring: int
    current_chainage_m: float
    advance_rate_m_per_day: float = Field(8.0, gt=0)
    planned_stop_interval_rings: int = Field(50, ge=10, le=200)


# ============================================================
# Wear Prediction Engine
# ============================================================

class CutterWearPredictor:
    """Main cutter wear prediction engine"""

    def __init__(self):
        self.cutter_states: dict[int, CutterState] = {}
        self.wear_history: list[dict] = []

    def initialize_cutters(self, n_cutters: int, positions: list[float] | None = None):
        """Initialize cutter array"""
        self.cutter_states = {}
        for i in range(n_cutters):
            radius = positions[i] if positions and i < len(positions) else (i + 1) * 0.25
            self.cutter_states[i] = CutterState(
                cutter_id=i,
                position_radius_m=radius,
                initial_thickness_mm=25.0,
                current_thickness_mm=25.0,
            )

    def update_wear(self, request: CutterWearRequest) -> CutterHealthResponse:
        """Calculate wear for current ring and update states"""
        if not self.cutter_states:
            self.initialize_cutters(request.n_cutters, request.cutter_positions)

        # Calculate wear rate
        wear_rate = calculate_wear_rate(
            thrust_kn=request.thrust_kn,
            torque_knm=request.torque_knm,
            ucS_mpa=request.ucS_mpa,
            cerchar_ai=request.cerchar_ai,
            advance_speed_mm_min=request.advance_speed_mm_min,
            n_discs=request.n_cutters,
        )

        # Update each cutter (position-dependent wear)
        cutters_data = []
        for cid, state in self.cutter_states.items():
            # Edge cutters wear faster
            edge_factor = 1.0 + (state.position_radius_m / 3.2) * 0.4
            effective_rate = wear_rate * edge_factor

            state.total_distance_m += 1.6  # one ring
            state.wear_rate_mm_per_m = effective_rate
            state.current_thickness_mm = max(
                2.0,
                state.initial_thickness_mm - (state.total_distance_m * effective_rate),
            )
            state.last_inspection_ring = request.ring_no

            cutters_data.append({
                "cutter_id": cid,
                "position_radius_m": state.position_radius_m,
                "remaining_life_pct": round(state.remaining_life_pct, 1),
                "wear_category": state.wear_category,
                "current_thickness_mm": round(state.current_thickness_mm, 2),
                "wear_rate_mm_per_m": round(state.wear_rate_mm_per_m, 5),
                "rings_remaining": state.estimated_rings_remaining,
            })

        # Overall health
        healths = [c["remaining_life_pct"] for c in cutters_data]
        overall = sum(healths) / len(healths) if healths else 100
        worst_idx = healths.index(min(healths))
        worst = cutters_data[worst_idx]

        # Maintenance recommendation
        if overall < 25:
            recommendation = "CRITICAL: Immediate cutter change required"
            stop_rings = 0
        elif overall < 50:
            recommendation = "WARNING: Schedule cutter change within next stop"
            stop_rings = 10
        elif overall < 70:
            recommendation = "NOTICE: Monitor cutter wear, plan maintenance soon"
            stop_rings = 30
        else:
            recommendation = "NORMAL: Cutters in good condition"
            stop_rings = 60

        # Alerts
        alerts = []
        for c in cutters_data:
            if c["wear_category"] == "critical":
                alerts.append({
                    "severity": "critical",
                    "message": f"Cutter #{c['cutter_id']} at {c['remaining_life_pct']}% - CHANGE IMMEDIATELY",
                })
            elif c["wear_category"] == "worn":
                alerts.append({
                    "severity": "warning",
                    "message": f"Cutter #{c['cutter_id']} at {c['remaining_life_pct']}% - plan replacement",
                })

        return CutterHealthResponse(
            ring_no=request.ring_no,
            chainage_m=request.chainage_m,
            cutters=cutters_data,
            overall_health_pct=round(overall, 1),
            worst_cutter_id=worst["cutter_id"],
            worst_cutter_health_pct=worst["remaining_life_pct"],
            maintenance_recommendation=recommendation,
            estimated_rings_to_maintenance=stop_rings,
            next_inspection_ring=request.ring_no + 25,
            alerts=alerts,
        )


# Singleton predictor
predictor = CutterWearPredictor()


def predict_cutter_wear(request: CutterWearRequest) -> CutterHealthResponse:
    """Public API for wear prediction"""
    return predictor.update_wear(request)


def schedule_maintenance(request: MaintenanceScheduleRequest) -> dict:
    """Generate maintenance schedule"""
    days_remaining = predictor.predictor_state.get("days_to_maintenance", 30)
    rings_per_day = request.advance_rate_m_per_day / 1.6

    return {
        "current_ring": request.current_ring,
        "current_chainage_m": request.current_chainage_m,
        "planned_stop_interval_rings": request.planned_stop_interval_rings,
        "estimated_days_to_maintenance": days_remaining,
        "recommended_stop_ring": request.current_ring + min(
            request.planned_stop_interval_rings,
            int(days_remaining * rings_per_day),
        ),
        "cutter_change_count": sum(
            1 for s in predictor.cutter_states.values()
            if s.wear_category in ("worn", "critical")
        ),
    }
