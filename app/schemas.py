from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class SoilInput(BaseModel):
    es_mpa: float = Field(30.0, gt=0.0, description="Soil elastic modulus [MPa]")
    poisson: float = Field(0.35, gt=0.0, lt=0.5)
    gamma_kn_m3: float = Field(18.0, gt=0.0)


class ShieldInput(BaseModel):
    depth_m: float = Field(20.0, gt=0.0)
    radius_m: float = Field(3.2, gt=0.0)
    y_center_m: float = Field(0.0)
    length_m: float = Field(8.0, gt=0.0)
    face_pressure_kpa: float = Field(300.0, ge=0.0)
    skin_friction_kpa: float = Field(60.0, ge=0.0)
    volume_loss_pct: float = Field(0.13, ge=0.0)
    trough_width_coef: float = Field(0.5, gt=0.0)


class ConsolidationInput(BaseModel):
    depth_m: float = Field(20.0, gt=0.0)
    tunnel_radius_m: float = Field(3.2, gt=0.0)
    base_depth_m: float = Field(40.0, gt=0.0)
    mv_per_mpa: float = Field(0.02, gt=0.0)
    cv_m2_per_day: float = Field(2.0, gt=0.0)
    ch_m2_per_day: float = Field(2.5, gt=0.0)
    p0_kpa: float = Field(20.0, ge=0.0)
    sigma_r_m: float = Field(8.0, gt=0.0)
    sigma_z_m: float = Field(2.5, gt=0.0)
    n_modes: int = Field(60, ge=4, le=300)


class EngineConfigInput(BaseModel):
    calibration_immediate: float = Field(1.0, ge=0.0)
    calibration_consolidation: float = Field(1.0, ge=0.0)


class ImmediateRequest(BaseModel):
    station: float = Field(..., description="Longitudinal distance from tunnel face [m], negative = behind")
    shield: ShieldInput = ShieldInput()
    soil: SoilInput = SoilInput()
    calibration: float = Field(1.0, ge=0.0)
    y_max: float = Field(40.0, gt=0.0)
    n_y: int = Field(201, ge=21, le=2001)


class ConsolidationRequest(BaseModel):
    t_days: list[float] = Field(..., min_length=1)
    consolidation: ConsolidationInput = ConsolidationInput()
    r_max: float = Field(40.0, gt=0.0)
    n_r: int = Field(201, ge=21, le=2001)


class TotalRequest(BaseModel):
    station: float = -30.0
    t_days: float = 60.0
    shield: ShieldInput = ShieldInput()
    soil: SoilInput = SoilInput()
    consolidation: ConsolidationInput = ConsolidationInput()
    engine: EngineConfigInput = EngineConfigInput()
    y_max: float = Field(40.0, gt=0.0)
    n_y: int = Field(201, ge=21, le=2001)


class EvaluateRequest(BaseModel):
    monitored_mm: float = Field(..., description="Measured settlement at the point [mm]")
    station: float = -30.0
    t_days: float = 60.0
    shield: ShieldInput = ShieldInput()
    soil: SoilInput = SoilInput()
    consolidation: ConsolidationInput = ConsolidationInput()
    engine: EngineConfigInput = EngineConfigInput()


class AlarmEvaluation(BaseModel):
    predicted_value_mm: float
    monitored_value_mm: Optional[float] = None
    difference_mm: Optional[float] = None
    relative_error_pct: Optional[float] = None
    passes_5pct_threshold: bool = True
    risk_level: str
    alert_color: str


class ShieldParamCreate(BaseModel):
    line: str = "Beijing Metro Line 12"
    section: str = "TBM-left-line"
    ring_no: int
    chainage_m: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    thrust_kn: float
    advance_speed_mm_min: float
    torque_knm: float = 0.0
    grouting_pressure_mpa: float = 0.0
    grouting_volume_m3: float = 0.0
    face_pressure_kpa: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0


class MonitoringCreate(BaseModel):
    line: str = "Beijing Metro Line 12"
    section: str = "TBM-left-line"
    ring_no: int
    chainage_m: float
    sensor_id: str
    target_type: str = "surface"
    measured_value_mm: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GroutInput(BaseModel):
    pumpable_window_hours: float = Field(4.0, ge=0.0)
    gel_time_hours: float = Field(6.0, ge=0.0)
    final_stiffness_mpa: float = Field(12.0, gt=0.0)
    stiffness_rate: float = Field(0.45, gt=0.0)
    stiffness_shape: float = Field(1.4, gt=0.0)
    initial_viscosity_pas: float = Field(0.4, ge=0.0)
    gel_viscosity_pas: float = Field(600.0, gt=0.0)
    viscosity_rate: float = Field(0.9, gt=0.0)
    max_support_fraction: float = Field(0.85, gt=0.0, le=1.0)


class GroutHydrationRequest(BaseModel):
    t_hours: list[float] = Field(..., min_length=1)
    grout: GroutInput = GroutInput()


class GroutImpactRequest(BaseModel):
    station: float = -30.0
    t_grout_hours: float = 6.0
    shield: ShieldInput = ShieldInput()
    soil: SoilInput = SoilInput()
    grout: GroutInput = GroutInput()
    calibration: float = Field(1.0, ge=0.0)


class AutodriveRequest(BaseModel):
    face_pressure_kpa: float = Field(300.0, ge=0.0)
    grouting_volume_m3: float = Field(2.4, ge=0.0)
    grouting_pressure_mpa: float = Field(2.6, ge=0.0)
    advance_speed_mm_min: float = Field(45.0, ge=0.0)
    predicted_mm: float = Field(..., description="Predicted settlement at the face zone [mm]")
    monitored_mm: float | None = Field(None, description="Latest monitored settlement [mm]")
    target_mm: float = Field(4.4, gt=0.0)


class RingEyeRequest(BaseModel):
    ring_no: int
    chainage_m: float
    radial_devs_mm: list[float] = Field(..., min_length=4)
    nominal_diameter_mm: float = Field(6400.0, gt=0.0)
    segment_count: int = Field(8, ge=4, le=24)


class RingEyeScanRequest(BaseModel):
    ring_no: int
    chainage_m: float
    ovalization_mm: float = Field(8.0, ge=0.0)
    n_points: int = Field(48, ge=16, le=256)


class XRayRequest(BaseModel):
    start_x: float = 100.0
    end_x: float = 244.0
    depth_m: float = 20.0
    t_days: float = 60.0
    shield: ShieldInput = ShieldInput()
    soil: SoilInput = SoilInput()
    consolidation: ConsolidationInput = ConsolidationInput()
    engine: EngineConfigInput = EngineConfigInput()

