"""
FORGE3D Innovation #2: 3D Geological Stratigraphy
Soil layer visualization, borehole data, face-ground interaction
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SoilLayer(BaseModel):
    """A single geological stratum"""
    name: str = Field(..., description="Layer name (e.g., 'Fill', 'Clay', 'Sand')")
    top_depth_m: float = Field(..., ge=0.0)
    bottom_depth_m: float = Field(..., gt=0.0)
    color_hex: str = Field("#8B7355", description="Display color hex")
    es_mpa: float = Field(30.0, gt=0.0, description="Elastic modulus [MPa]")
    poisson: float = Field(0.35, ge=0.0, lt=0.5)
    gamma_kn_m3: float = Field(18.0, gt=0.0, description="Unit weight [kN/m3]")
    cohesion_kpa: float = Field(25.0, ge=0.0)
    friction_deg: float = Field(22.0, ge=0.0)
    permeability_ms: float = Field(1e-8, gt=0.0, description="Permeability [m/s]")
    porosity: float = Field(0.35, ge=0.0, le=1.0)
    description: str = ""


class BoreholeLog(BaseModel):
    """Borehole data with layer sequence"""
    borehole_id: str
    x_enu: float
    y_enu: float
    surface_z_m: float = Field(0.0, description="Ground surface elevation [m]")
    total_depth_m: float = Field(50.0, gt=0.0)
    layers: list[SoilLayer]


class TunnelAlignment(BaseModel):
    """Tunnel centerline in geological space"""
    chainage_start_m: float = 0.0
    chainage_end_m: float = Field(500.0, gt=0.0)
    depth_m: float = Field(20.0, gt=0.0, description="Tunnel axis depth below surface")
    radius_m: float = Field(3.2, gt=0.0)


class GeologicalProfile(BaseModel):
    """Complete geological cross-section for 3D rendering"""
    alignment: TunnelAlignment
    boreholes: list[BoreholeLog]
    interpolated_layers: list[SoilLayer]


# Default Beijing Metro Line 12 geological profile
DEFAULT_GEOLOGICAL_PROFILE = GeologicalProfile(
    alignment=TunnelAlignment(chainage_start_m=0, chainage_end_m=500, depth_m=20, radius_m=3.2),
    boreholes=[
        BoreholeLog(
            borehole_id="BH-001",
            x_enu=-10.0,
            y_enu=0.0,
            surface_z_m=0.0,
            total_depth_m=50.0,
            layers=[
                SoilLayer(name="Fill", top_depth_m=0.0, bottom_depth_m=3.0, color_hex="#C4A97D", es_mpa=8.0, gamma_kn_m3=17.0, cohesion_kpa=10.0, friction_deg=15.0, description="Miscellaneous fill"),
                SoilLayer(name="Clay", top_depth_m=3.0, bottom_depth_m=12.0, color_hex="#8B6914", es_mpa=18.0, gamma_kn_m3=19.0, cohesion_kpa=35.0, friction_deg=18.0, description="Soft clay, high plasticity"),
                SoilLayer(name="Silty Clay", top_depth_m=12.0, bottom_depth_m=22.0, color_hex="#CD853F", es_mpa=30.0, gamma_kn_m3=19.5, cohesion_kpa=28.0, friction_deg=22.0, description="Stiff silty clay"),
                SoilLayer(name="Fine Sand", top_depth_m=22.0, bottom_depth_m=35.0, color_hex="#DEB887", es_mpa=45.0, gamma_kn_m3=18.5, cohesion_kpa=0.0, friction_deg=32.0, description="Dense fine sand layer"),
                SoilLayer(name="Cobble Gravel", top_depth_m=35.0, bottom_depth_m=50.0, color_hex="#A0522D", es_mpa=80.0, gamma_kn_m3=20.0, cohesion_kpa=0.0, friction_deg=38.0, description="Cemented cobble gravel"),
            ],
        ),
        BoreholeLog(
            borehole_id="BH-002",
            x_enu=10.0,
            y_enu=50.0,
            surface_z_m=0.5,
            total_depth_m=50.0,
            layers=[
                SoilLayer(name="Fill", top_depth_m=0.0, bottom_depth_m=3.5, color_hex="#C4A97D", es_mpa=8.0, gamma_kn_m3=17.0, cohesion_kpa=10.0, friction_deg=15.0, description="Miscellaneous fill"),
                SoilLayer(name="Clay", top_depth_m=3.5, bottom_depth_m=14.0, color_hex="#8B6914", es_mpa=16.0, gamma_kn_m3=18.8, cohesion_kpa=32.0, friction_deg=17.0, description="Soft clay, organic"),
                SoilLayer(name="Silty Clay", top_depth_m=14.0, bottom_depth_m=24.0, color_hex="#CD853F", es_mpa=28.0, gamma_kn_m3=19.2, cohesion_kpa=26.0, friction_deg=21.0, description="Medium stiff silty clay"),
                SoilLayer(name="Fine Sand", top_depth_m=24.0, bottom_depth_m=36.0, color_hex="#DEB887", es_mpa=42.0, gamma_kn_m3=18.3, cohesion_kpa=0.0, friction_deg=31.0, description="Dense fine sand"),
                SoilLayer(name="Bedrock", top_depth_m=36.0, bottom_depth_m=50.0, color_hex="#696969", es_mpa=200.0, gamma_kn_m3=24.0, cohesion_kpa=500.0, friction_deg=45.0, description="Weathered granite bedrock"),
            ],
        ),
    ],
    interpolated_layers=[
        SoilLayer(name="Fill", top_depth_m=0.0, bottom_depth_m=3.2, color_hex="#C4A97D", es_mpa=8.0, gamma_kn_m3=17.0, cohesion_kpa=10.0, friction_deg=15.0),
        SoilLayer(name="Clay", top_depth_m=3.2, bottom_depth_m=13.0, color_hex="#8B6914", es_mpa=17.0, gamma_kn_m3=18.9, cohesion_kpa=33.5, friction_deg=17.5),
        SoilLayer(name="Silty Clay", top_depth_m=13.0, bottom_depth_m=23.0, color_hex="#CD853F", es_mpa=29.0, gamma_kn_m3=19.35, cohesion_kpa=27.0, friction_deg=21.5),
        SoilLayer(name="Fine Sand", top_depth_m=23.0, bottom_depth_m=35.5, color_hex="#DEB887", es_mpa=43.5, gamma_kn_m3=18.4, cohesion_kpa=0.0, friction_deg=31.5),
        SoilLayer(name="Cobble Gravel / Bedrock", top_depth_m=35.5, bottom_depth_m=50.0, color_hex="#696969", es_mpa=140.0, gamma_kn_m3=22.0, cohesion_kpa=250.0, friction_deg=41.5),
    ],
)


def get_geological_profile() -> dict:
    """Return the default geological profile as dict"""
    return DEFAULT_GEOLOGICAL_PROFILE.model_dump()
