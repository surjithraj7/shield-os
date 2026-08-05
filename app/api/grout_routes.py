from __future__ import annotations

import numpy as np
from fastapi import APIRouter

from app.engine.grout import (
    GroutParams,
    effective_volume_loss,
    grout_impact,
    hydration_timeseries,
)
from app.engine.mindlin import SoilParams, ShieldParams
from app.schemas import GroutHydrationRequest, GroutImpactRequest

router = APIRouter(prefix="/api/grout", tags=["grout"])


def _grout(g) -> GroutParams:
    return GroutParams(
        pumpable_window_hours=g.pumpable_window_hours,
        gel_time_hours=g.gel_time_hours,
        final_stiffness_mpa=g.final_stiffness_mpa,
        stiffness_rate=g.stiffness_rate,
        stiffness_shape=g.stiffness_shape,
        initial_viscosity_pas=g.initial_viscosity_pas,
        gel_viscosity_pas=g.gel_viscosity_pas,
        viscosity_rate=g.viscosity_rate,
        max_support_fraction=g.max_support_fraction,
    )


def _shield(s) -> ShieldParams:
    return ShieldParams(
        depth_m=s.depth_m,
        radius_m=s.radius_m,
        y_center_m=s.y_center_m,
        length_m=s.length_m,
        face_pressure_kpa=s.face_pressure_kpa,
        skin_friction_kpa=s.skin_friction_kpa,
        volume_loss_pct=s.volume_loss_pct,
        trough_width_coef=s.trough_width_coef,
    )


def _soil(soil) -> SoilParams:
    return SoilParams(es_mpa=soil.es_mpa, poisson=soil.poisson, gamma_kn_m3=soil.gamma_kn_m3)


@router.post("/hydration")
def hydration(req: GroutHydrationRequest):
    params = _grout(req.grout)
    series = hydration_timeseries(np.array(req.t_hours), params)
    return {
        "t_hours": series["t_hours"].tolist(),
        "viscosity_pas": series["viscosity_pas"].tolist(),
        "stiffness_mpa": series["stiffness_mpa"].tolist(),
        "hardening_fraction": series["hardening_fraction"].tolist(),
        "effective_volume_loss_pct": [
            effective_volume_loss(1.0, float(t), params) for t in req.t_hours
        ],
        "pumpable_window_hours": params.pumpable_window_hours,
        "gel_time_hours": params.gel_time_hours,
        "final_stiffness_mpa": params.final_stiffness_mpa,
    }


@router.post("/impact")
def impact(req: GroutImpactRequest):
    result = grout_impact(
        req.station,
        req.t_grout_hours,
        _shield(req.shield),
        _soil(req.soil),
        _grout(req.grout),
        calibration=req.calibration,
    )
    return result
