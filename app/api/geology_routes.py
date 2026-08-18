"""
FORGE3D Innovation #2: Geological Stratigraphy API Routes
"""
from __future__ import annotations

from fastapi import APIRouter

from app.geology import get_geological_profile

router = APIRouter(prefix="/api/geology", tags=["geology"])


@router.get("/profile")
def get_profile():
    """Get the full geological profile with boreholes and interpolated layers"""
    return get_geological_profile()


@router.get("/layers")
def get_layers():
    """Get interpolated soil layers for 3D rendering"""
    profile = get_geological_profile()
    return {
        "layers": profile["interpolated_layers"],
        "alignment": profile["alignment"],
    }


@router.get("/boreholes")
def get_boreholes():
    """Get borehole logs"""
    profile = get_geological_profile()
    return {
        "boreholes": profile["boreholes"],
    }
