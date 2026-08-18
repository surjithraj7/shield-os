"""
FORGE3D Innovation #1: WebSocket Live Streaming
Real-time data push to all connected clients - no more polling
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import CalculatedResult, MonitoringData, ShieldParameter, ShmReading

router = APIRouter(prefix="/api/ws", tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.last_broadcast: dict[str, Any] = {}
        self._broadcast_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        self.last_broadcast = message
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    async def send_personal(self, websocket: WebSocket, message: dict[str, Any]):
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)


manager = ConnectionManager()


def _get_latest_data() -> dict[str, Any]:
    """Fetch latest sensor + calculated data from DB"""
    db = SessionLocal()
    try:
        shield = db.query(ShieldParameter).order_by(ShieldParameter.timestamp.desc()).first()
        monitoring = db.query(MonitoringData).order_by(MonitoringData.timestamp.desc()).first()
        calc = db.query(CalculatedResult).order_by(CalculatedResult.timestamp.desc()).first()
        shm = db.query(ShmReading).order_by(ShmReading.timestamp.desc()).first()

        shield_data = {}
        if shield:
            shield_data = {
                "thrust_kn": shield.thrust_kn,
                "torque_knm": shield.torque_knm,
                "advance_speed_mm_min": shield.advance_speed_mm_min,
                "grouting_pressure_mpa": shield.grouting_pressure_mpa,
                "grouting_volume_m3": shield.grouting_volume_m3,
                "face_pressure_kpa": shield.face_pressure_kpa,
                "screw_rpm": 8.5,
                "ring_no": shield.ring_no,
                "chainage_m": shield.chainage_m,
            }

        settlement_data = {}
        if calc:
            settlement_data = {
                "ring_no": calc.ring_no,
                "predicted_mm": calc.predicted_value_mm,
                "monitored_mm": calc.monitored_value_mm,
                "difference_mm": calc.difference_mm,
                "relative_error_pct": calc.relative_error_pct,
                "risk_level": calc.risk_level,
            }

        shm_data = {}
        if shm:
            shm_data = {
                "sensor_id": shm.sensor_id,
                "sensor_type": shm.sensor_type,
                "measured_value": shm.measured_value,
                "unit": shm.unit,
                "status": shm.status,
            }

        return {
            "type": "live_update",
            "timestamp": time.time(),
            "metrics": shield_data,
            "settlement": settlement_data,
            "shm": shm_data,
        }
    finally:
        db.close()


async def _periodic_broadcast():
    """Background task: broadcast live data every 2 seconds"""
    while True:
        await asyncio.sleep(2)
        if manager.active_connections:
            data = _get_latest_data()
            await manager.broadcast(data)


@router.on_event("startup")
async def start_broadcast_task():
    manager._broadcast_task = asyncio.create_task(_periodic_broadcast())


@router.on_event("shutdown")
async def stop_broadcast_task():
    if manager._broadcast_task:
        manager._broadcast_task.cancel()


@router.websocket("/live")
async def websocket_live(websocket: WebSocket):
    """
    Primary live data stream.
    Sends: metrics, settlement, SHM every 2s
    Receives: client commands (subscribe, ping)
    """
    await manager.connect(websocket)
    try:
        # Send initial snapshot immediately
        initial = _get_latest_data()
        initial["type"] = "initial_snapshot"
        await manager.send_personal(websocket, initial)

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            cmd = msg.get("command", "")

            if cmd == "ping":
                await manager.send_personal(websocket, {"type": "pong", "timestamp": time.time()})

            elif cmd == "snapshot":
                snapshot = _get_latest_data()
                snapshot["type"] = "snapshot_response"
                await manager.send_personal(websocket, snapshot)

            elif cmd == "subscribe_metrics":
                # Client can request specific data
                data = _get_latest_data()
                await manager.send_personal(websocket, data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


def _get_twin_data() -> dict[str, Any]:
    db = SessionLocal()
    try:
        calc_rows = (
            db.query(CalculatedResult)
            .order_by(CalculatedResult.timestamp.desc())
            .limit(160)
            .all()
        )
        shield = db.query(ShieldParameter).order_by(ShieldParameter.timestamp.desc()).first()

        tunnel = [
            {
                "ring_no": r.ring_no,
                "chainage_m": r.chainage_m,
                "predicted_mm": r.predicted_value_mm,
                "monitored_mm": r.monitored_value_mm,
                "risk": r.risk_level,
            }
            for r in calc_rows
        ]

        latest_calc = calc_rows[0] if calc_rows else None

        metrics = {}
        if shield:
            metrics = {
                "thrust_kn": shield.thrust_kn,
                "torque_knm": shield.torque_knm,
                "advance_speed_mm_min": shield.advance_speed_mm_min,
                "grouting_pressure_mpa": shield.grouting_pressure_mpa,
                "grouting_volume_m3": shield.grouting_volume_m3,
                "face_pressure_kpa": shield.face_pressure_kpa,
                "screw_rpm": 8.5,
            }

        settlement = None
        if latest_calc:
            settlement = {
                "ring_no": latest_calc.ring_no,
                "chainage_m": latest_calc.chainage_m,
                "predicted_mm": latest_calc.predicted_value_mm,
                "monitored_mm": latest_calc.monitored_value_mm,
                "difference_mm": latest_calc.difference_mm,
                "relative_error_pct": latest_calc.relative_error_pct,
                "risk": latest_calc.risk_level,
            }

        return {
            "type": "twin_update",
            "timestamp": time.time(),
            "tunnel": tunnel,
            "current_ring": shield.ring_no if shield else (latest_calc.ring_no if latest_calc else None),
            "chainage_m": shield.chainage_m if shield else (latest_calc.chainage_m if latest_calc else None),
            "metrics": metrics,
            "settlement": settlement,
        }
    finally:
        db.close()


@router.websocket("/twin")
async def websocket_twin(websocket: WebSocket):
    """
    Digital twin specific stream.
    Sends: tunnel ring data, cutterhead state, metrics, settlement, risk levels every 3s
    """
    await manager.connect(websocket)
    try:
        initial = _get_twin_data()
        await manager.send_personal(websocket, initial)

        while True:
            await asyncio.sleep(3)
            data = _get_twin_data()
            await manager.send_personal(websocket, data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
