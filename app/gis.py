"""
FORGE3D Innovation #5: GIS Integration
UTM/WGS84 coordinate transformation, real-world positioning, map overlay
"""
from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# Coordinate Transformation Models
# ============================================================

class WGS84Point(BaseModel):
    """WGS84 geographic coordinates"""
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude [degrees]")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Longitude [degrees]")
    alt_m: float = Field(0.0, description="Altitude [meters]")


class UTMPoint(BaseModel):
    """UTM projected coordinates"""
    zone: int = Field(..., ge=1, le=60)
    letter: str = Field("N", description="N or S hemisphere")
    easting_m: float = Field(..., description="Easting [meters]")
    northing_m: float = Field(..., description="Northing [meters]")
    alt_m: float = Field(0.0)


class ENUPoint(BaseModel):
    """Local East-North-Up coordinates (relative to origin)"""
    east_m: float
    north_m: float
    up_m: float = 0.0


# ============================================================
# Coordinate Conversion Functions
# ============================================================

# WGS84 constants
_WGS84_A = 6378137.0  # Semi-major axis
_WGS84_F = 1 / 298.257223563  # Flattening
_WGS84_E = math.sqrt(2 * _WGS84_F - _WGS84_F ** 2)
_WGS84_EP2 = _WGS84_E ** 2 / (1 - _WGS84_E ** 2)


def wgs84_to_utm(point: WGS84Point) -> UTMPoint:
    """Convert WGS84 to UTM coordinates"""
    lat_rad = math.radians(point.lat)
    lon_rad = math.radians(point.lon)

    zone = int((point.lon + 180) / 6) + 1

    # UTM zone central meridian
    lon0_rad = math.radians((zone - 1) * 6 - 180 + 3)

    N = _WGS84_A / math.sqrt(1 - _WGS84_E ** 2 * math.sin(lat_rad) ** 2)
    T = math.tan(lat_rad) ** 2
    C = _WGS84_EP2 * math.cos(lat_rad) ** 2
    A = (lon_rad - lon0_rad) * math.cos(lat_rad)

    M = _WGS84_A * (
        (1 - _WGS84_E ** 2 / 4 - 3 * _WGS84_E ** 4 / 64 - 5 * _WGS84_E ** 6 / 256) * lat_rad
        - (3 * _WGS84_E ** 2 / 8 + 3 * _WGS84_E ** 4 / 32 + 45 * _WGS84_E ** 6 / 1024) * math.sin(2 * lat_rad)
        + (15 * _WGS84_E ** 4 / 256 + 45 * _WGS84_E ** 6 / 1024) * math.sin(4 * lat_rad)
        - (35 * _WGS84_E ** 6 / 3072) * math.sin(6 * lat_rad)
    )

    k0 = 0.9996
    easting = k0 * N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T ** 2 + 72 * C - 58 * _WGS84_EP2) * A ** 5 / 120) + 500000
    northing = k0 * (M + N * math.tan(lat_rad) * (A ** 2 / 2 + (5 - T + 9 * C + 4 * C ** 2) * A ** 4 / 24 + (61 - 58 * T + T ** 2 + 600 * C - 330 * _WGS84_EP2) * A ** 6 / 720))

    if point.lat < 0:
        northing += 10000000

    letter = "N" if point.lat >= 0 else "S"

    return UTMPoint(
        zone=zone,
        letter=letter,
        easting_m=round(easting, 3),
        northing_m=round(northing, 3),
        alt_m=point.alt_m,
    )


def utm_to_wgs84(point: UTMPoint) -> WGS84Point:
    """Convert UTM to WGS84 coordinates"""
    k0 = 0.9996
    e = _WGS84_E
    e2 = e ** 2
    ep2 = _WGS84_EP2

    x = point.easting_m - 500000
    y = point.northing_m
    if point.letter == "S":
        y -= 10000000

    M = y / k0
    mu = M / (_WGS84_A * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))

    phi1 = mu + (3 * e / 2 - 27 * e ** 3 / 32) * math.sin(2 * mu) + (21 * e ** 2 / 16 - 55 * e ** 4 / 32) * math.sin(4 * mu) + (151 * e ** 3 / 96) * math.sin(6 * mu)

    N1 = _WGS84_A / math.sqrt(1 - e2 * math.sin(phi1) ** 2)
    T1 = math.tan(phi1) ** 2
    C1 = ep2 * math.cos(phi1) ** 2
    R1 = _WGS84_A * (1 - e2) / (1 - e2 * math.sin(phi1) ** 2) ** 1.5
    D = x / (N1 * k0)

    lat = phi1 - (N1 * math.tan(phi1) / R1) * (D ** 2 / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 ** 2 - 9 * ep2) * D ** 4 / 24 + (61 + 90 * T1 + 298 * C1 + 45 * T1 ** 2 - 252 * ep2 - 3 * C1 ** 2) * D ** 6 / 720)
    lon = (D - (1 + 2 * T1 + C1) * D ** 3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1 ** 2 + 8 * ep2 + 24 * T1 ** 2) * D ** 5 / 120) / math.cos(phi1)

    zone_central = (point.zone - 1) * 6 - 180 + 3

    return WGS84Point(
        lat=round(math.degrees(lat), 8),
        lon=round(math.degrees(lon) + zone_central, 8),
        alt_m=point.alt_m,
    )


def enu_to_wgs84(
    point: ENUPoint,
    origin: WGS84Point,
) -> WGS84Point:
    """Convert ENU (local) to WGS84 relative to an origin point"""
    lat_rad = math.radians(origin.lat)
    lon_rad = math.radians(origin.lon)

    d_lat = point.north_m / _WGS84_A
    d_lon = point.east_m / (_WGS84_A * math.cos(lat_rad))

    return WGS84Point(
        lat=round(origin.lat + math.degrees(d_lat), 8),
        lon=round(origin.lon + math.degrees(d_lon), 8),
        alt_m=origin.alt_m + point.up_m,
    )


# ============================================================
# Tunnel Alignment GIS Data
# ============================================================

class TunnelAlignmentGIS(BaseModel):
    """Tunnel alignment with real-world coordinates"""
    name: str
    origin_wgs84: WGS84Point
    origin_utm: UTMPoint
    chainage_start_m: float = 0.0
    chainage_end_m: float = 500.0
    azimuth_deg: float = 90.0  # Tunnel heading from north
    depth_m: float = 20.0


def get_alignment_points(
    alignment: TunnelAlignmentGIS,
    chainage_interval_m: float = 10.0,
) -> list[dict]:
    """Generate WGS84 points along tunnel alignment"""
    points = []
    n_points = int((alignment.chainage_end_m - alignment.chainage_start_m) / chainage_interval_m) + 1

    azimuth_rad = math.radians(alignment.azimuth_deg)

    for i in range(n_points):
        chainage = alignment.chainage_start_m + i * chainage_interval_m

        # Local ENU offset from origin
        east_offset = chainage * math.sin(azimuth_rad)
        north_offset = chainage * math.cos(azimuth_rad)

        wgs84 = enu_to_wgs84(
            ENUPoint(east_m=east_offset, north_m=north_offset, up_m=-alignment.depth_m),
            alignment.origin_wgs84,
        )

        utm = wgs84_to_utm(wgs84)

        points.append({
            "chainage_m": chainage,
            "wgs84": wgs84.model_dump(),
            "utm": utm.model_dump(),
        })

    return points


# Default Beijing Metro Line 12 alignment (approximate)
DEFAULT_ALIGNMENT = TunnelAlignmentGIS(
    name="Beijing Metro Line 12 - Section 3",
    origin_wgs84=WGS84Point(lat=39.9042, lon=116.4074, alt_m=45.0),
    origin_utm=UTMPoint(zone=50, letter="N", easting_m=449500.0, northing_m=4418000.0),
    chainage_start_m=0.0,
    chainage_end_m=500.0,
    azimuth_deg=95.0,
    depth_m=20.0,
)


# ============================================================
# API Schemas
# ============================================================

class CoordinateTransformRequest(BaseModel):
    """Request for coordinate transformation"""
    source_type: str = Field(..., description="wgs84, utm, or enu")
    source_data: dict
    target_type: str = Field(..., description="wgs84, utm, or enu")
    origin_wgs84: WGS84Point | None = None


class AlignmentRequest(BaseModel):
    """Request for tunnel alignment GIS data"""
    chainage_interval_m: float = Field(10.0, gt=0)


def get_gis_data() -> dict:
    """Return complete GIS data for the project"""
    alignment = DEFAULT_ALIGNMENT
    points = get_alignment_points(alignment, chainage_interval_m=10.0)

    return {
        "alignment": alignment.model_dump(),
        "points": points,
        "coordinate_systems": {
            "wgs84": {"name": "WGS84", "type": "geographic"},
            "utm": {"name": f"UTM {alignment.origin_utm.zone}{alignment.origin_utm.letter}", "type": "projected"},
            "enu": {"name": "Local ENU", "type": "local", "origin": alignment.origin_wgs84.model_dump()},
        },
    }
