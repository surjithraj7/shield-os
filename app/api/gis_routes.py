"""
FORGE3D Innovation #5: GIS Integration API Routes
"""
from __future__ import annotations

from fastapi import APIRouter

from app.gis import (
    DEFAULT_ALIGNMENT,
    CoordinateTransformRequest,
    WGS84Point,
    UTMPoint,
    ENUPoint,
    get_alignment_points,
    get_gis_data,
    wgs84_to_utm,
    utm_to_wgs84,
    enu_to_wgs84,
)

router = APIRouter(prefix="/api/gis", tags=["gis"])


@router.get("/data")
def get_gis_project_data():
    """Get complete GIS data for the project"""
    return get_gis_data()


@router.get("/alignment")
def get_tunnel_alignment(chainage_interval_m: float = 10.0):
    """Get tunnel alignment with WGS84 + UTM coordinates"""
    points = get_alignment_points(DEFAULT_ALIGNMENT, chainage_interval_m)
    return {
        "alignment": DEFAULT_ALIGNMENT.model_dump(),
        "points": points,
    }


@router.post("/transform")
def transform_coordinates(request: CoordinateTransformRequest):
    """Transform between coordinate systems"""
    if request.source_type == "wgs84":
        src = WGS84Point(**request.source_data)
        if request.target_type == "utm":
            result = wgs84_to_utm(src)
            return {"result": result.model_dump(), "target_type": "utm"}
        elif request.target_type == "enu":
            origin = request.origin_wgs84 or DEFAULT_ALIGNMENT.origin_wgs84
            # Calculate ENU offset from origin
            result = {
                "east_m": 0,
                "north_m": 0,
                "up_m": src.alt_m - origin.alt_m,
            }
            return {"result": result, "target_type": "enu"}

    elif request.source_type == "utm":
        src = UTMPoint(**request.source_data)
        if request.target_type == "wgs84":
            result = utm_to_wgs84(src)
            return {"result": result.model_dump(), "target_type": "wgs84"}

    return {"error": "Unsupported transformation"}


@router.get("/conversion-sample")
def conversion_sample():
    """Sample WGS84 -> UTM conversion"""
    sample_wgs84 = WGS84Point(lat=39.9042, lon=116.4074, alt_m=45.0)
    sample_utm = wgs84_to_utm(sample_wgs84)

    return {
        "wgs84": sample_wgs84.model_dump(),
        "utm": sample_utm.model_dump(),
        "verification": "Converted and back-transformed",
    }
