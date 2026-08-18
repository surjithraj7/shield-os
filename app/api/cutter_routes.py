"""
FORGE3D Innovation #3: Cutter Wear AI API Routes
"""
from __future__ import annotations

from fastapi import APIRouter

from app.ml.cutter_wear import CutterWearRequest, predict_cutter_wear, schedule_maintenance

router = APIRouter(prefix="/api/cutter", tags=["cutter-wear"])


@router.post("/wear")
def get_wear_prediction(request: CutterWearRequest):
    """Predict cutter wear for current ring"""
    return predict_cutter_wear(request)


@router.post("/maintenance")
def get_maintenance_schedule(request: dict):
    """Get maintenance schedule"""
    from app.ml.cutter_wear import MaintenanceScheduleRequest, predictor
    req = MaintenanceScheduleRequest(**request)
    return schedule_maintenance(req)


@router.get("/summary")
def get_cutter_summary():
    """Get current cutter fleet status"""
    from app.ml.cutter_wear import predictor
    if not predictor.cutter_states:
        return {
            "status": "no_data",
            "message": "No cutter wear data available. Run /api/cutter/wear first.",
            "cutters": [],
        }

    cutters = []
    for cid, state in predictor.cutter_states.items():
        cutters.append({
            "cutter_id": cid,
            "remaining_life_pct": round(state.remaining_life_pct, 1),
            "wear_category": state.wear_category,
            "current_thickness_mm": round(state.current_thickness_mm, 2),
            "rings_remaining": state.estimated_rings_remaining,
        })

    return {
        "status": "ok",
        "total_cutters": len(cutters),
        "cutters_in_good_condition": sum(1 for c in cutters if c["wear_category"] == "good"),
        "cutters_moderate": sum(1 for c in cutters if c["wear_category"] == "moderate"),
        "cutters_worn": sum(1 for c in cutters if c["wear_category"] == "worn"),
        "cutters_critical": sum(1 for c in cutters if c["wear_category"] == "critical"),
        "cutters": cutters,
    }
