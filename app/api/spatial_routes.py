from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import SpatialAsset
from app.spatial import evaluate_clearances

router = APIRouter(prefix="/api/spatial", tags=["spatial"])


class SpatialAssetIn(BaseModel):
    name: str
    asset_type: str = "structure"
    x_enu: float
    y_enu: float
    z_enu: float = -10.0
    radius_m: float = 0.5
    clearance_limit_m: float = 3.0
    note: str = ""


class ClearanceRequest(BaseModel):
    start_x: float = 100.0
    end_x: float = 244.0
    depth_m: float = 20.0


def _asset_out(r: SpatialAsset) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "asset_type": r.asset_type,
        "x_enu": r.x_enu,
        "y_enu": r.y_enu,
        "z_enu": r.z_enu,
        "radius_m": r.radius_m,
        "clearance_limit_m": r.clearance_limit_m,
        "note": r.note,
    }


@router.get("/assets")
def list_assets(db: Session = Depends(get_db)):
    rows = db.query(SpatialAsset).order_by(SpatialAsset.id.asc()).all()
    return [_asset_out(r) for r in rows]


@router.post("/assets")
def create_asset(req: SpatialAssetIn, db: Session = Depends(get_db)):
    row = SpatialAsset(**req.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _asset_out(row)


@router.delete("/assets/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    row = db.query(SpatialAsset).filter(SpatialAsset.id == asset_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(row)
    db.commit()
    return {"status": "deleted", "id": asset_id}


@router.get("/clearances")
def clearances(
    start_x: float = 100.0,
    end_x: float = 244.0,
    depth_m: float = 20.0,
    db: Session = Depends(get_db),
):
    assets = db.query(SpatialAsset).all()
    return evaluate_clearances(
        [_asset_out(r) for r in assets],
        start_x=start_x,
        end_x=end_x,
        depth_m=depth_m,
    )


@router.post("/clearances")
def clearances_post(req: ClearanceRequest, db: Session = Depends(get_db)):
    assets = db.query(SpatialAsset).all()
    return evaluate_clearances(
        [_asset_out(r) for r in assets],
        start_x=req.start_x,
        end_x=req.end_x,
        depth_m=req.depth_m,
    )
