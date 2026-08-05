from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

UTC = timezone.utc


class ShieldParameter(Base):
    __tablename__ = "shield_parameters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    line: Mapped[str] = mapped_column(String(64), index=True)
    section: Mapped[str] = mapped_column(String(64), index=True)
    ring_no: Mapped[int] = mapped_column(Integer, index=True)
    chainage_m: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)
    thrust_kn: Mapped[float] = mapped_column(Float)
    advance_speed_mm_min: Mapped[float] = mapped_column(Float)
    torque_knm: Mapped[float] = mapped_column(Float)
    grouting_pressure_mpa: Mapped[float] = mapped_column(Float)
    grouting_volume_m3: Mapped[float] = mapped_column(Float)
    face_pressure_kpa: Mapped[float] = mapped_column(Float)
    pitch_deg: Mapped[float] = mapped_column(Float, default=0.0)
    yaw_deg: Mapped[float] = mapped_column(Float, default=0.0)


class MonitoringData(Base):
    __tablename__ = "monitoring_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    line: Mapped[str] = mapped_column(String(64), index=True)
    section: Mapped[str] = mapped_column(String(64), index=True)
    ring_no: Mapped[int] = mapped_column(Integer, index=True)
    chainage_m: Mapped[float] = mapped_column(Float)
    sensor_id: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str] = mapped_column(String(32), index=True)
    measured_value_mm: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)


class CalculatedResult(Base):
    __tablename__ = "calculated_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    line: Mapped[str] = mapped_column(String(64), index=True)
    section: Mapped[str] = mapped_column(String(64), index=True)
    ring_no: Mapped[int] = mapped_column(Integer, index=True)
    chainage_m: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)
    model_name: Mapped[str] = mapped_column(String(64), index=True)
    immediate_mm: Mapped[float] = mapped_column(Float, default=0.0)
    consolidation_mm: Mapped[float] = mapped_column(Float, default=0.0)
    predicted_value_mm: Mapped[float] = mapped_column(Float)
    monitored_value_mm: Mapped[float] = mapped_column(Float, nullable=True)
    difference_mm: Mapped[float] = mapped_column(Float, default=0.0)
    relative_error_pct: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(8), default="green")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default="operator")
    full_name: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class InstrumentModel(Base):
    __tablename__ = "instrument_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(String(512), default="")
    design_json: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(64), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class ShmReading(Base):
    __tablename__ = "shm_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    line: Mapped[str] = mapped_column(String(64), index=True)
    section: Mapped[str] = mapped_column(String(64), index=True)
    ring_no: Mapped[int] = mapped_column(Integer, index=True)
    chainage_m: Mapped[float] = mapped_column(Float)
    sensor_id: Mapped[str] = mapped_column(String(64), index=True)
    sensor_type: Mapped[str] = mapped_column(String(32), index=True)
    measured_value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16), default="mm")
    status: Mapped[str] = mapped_column(String(16), default="normal")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)


class SpatialAsset(Base):
    __tablename__ = "spatial_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    asset_type: Mapped[str] = mapped_column(String(32), index=True)
    x_enu: Mapped[float] = mapped_column(Float)
    y_enu: Mapped[float] = mapped_column(Float)
    z_enu: Mapped[float] = mapped_column(Float)
    radius_m: Mapped[float] = mapped_column(Float, default=0.5)
    clearance_limit_m: Mapped[float] = mapped_column(Float, default=3.0)
    note: Mapped[str] = mapped_column(String(256), default="")


class RingEyeReading(Base):
    __tablename__ = "ringeye_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    line: Mapped[str] = mapped_column(String(64), index=True)
    section: Mapped[str] = mapped_column(String(64), index=True)
    ring_no: Mapped[int] = mapped_column(Integer, index=True)
    chainage_m: Mapped[float] = mapped_column(Float)
    nominal_diameter_mm: Mapped[float] = mapped_column(Float, default=6400.0)
    delta_d_mm: Mapped[float] = mapped_column(Float)
    ovalization_pct: Mapped[float] = mapped_column(Float)
    eccentricity_mm: Mapped[float] = mapped_column(Float)
    joint_gap_mm: Mapped[float] = mapped_column(Float)
    seepage_risk: Mapped[str] = mapped_column(String(16), default="normal")
    status: Mapped[str] = mapped_column(String(16), default="normal")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)


class ExperienceTransfer(Base):
    __tablename__ = "experience_transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_line: Mapped[str] = mapped_column(String(64), index=True)
    source_segment: Mapped[str] = mapped_column(String(32), index=True)
    target_line: Mapped[str] = mapped_column(String(64), index=True)
    target_segment: Mapped[str] = mapped_column(String(32), index=True)
    params_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

