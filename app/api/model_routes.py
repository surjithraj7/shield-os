from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_user
from app.db import get_db
from app.models import InstrumentModel, User

router = APIRouter(prefix="/api/models", tags=["models"])


class InstrumentModelIn(BaseModel):
    name: str
    description: str = ""
    design_json: str


class InstrumentModelOut(BaseModel):
    id: int
    name: str
    description: str
    design_json: str
    updated_at: str


class InstrumentModelMeta(BaseModel):
    id: int
    name: str
    description: str
    updated_at: str
    part_count: int


def _to_meta(row: InstrumentModel) -> dict:
    try:
        import json

        part_count = len(json.loads(row.design_json))
    except Exception:
        part_count = 0
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "updated_at": row.updated_at.isoformat(),
        "part_count": part_count,
    }


@router.get("", response_model=list[InstrumentModelMeta])
def list_models(db: Session = Depends(get_db)):
    rows = db.query(InstrumentModel).order_by(InstrumentModel.updated_at.desc()).all()
    return [_to_meta(r) for r in rows]


@router.post("", response_model=InstrumentModelOut)
def create_model(
    req: InstrumentModelIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    row = InstrumentModel(
        name=req.name,
        description=req.description,
        design_json=req.design_json,
        created_by=user.username,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.get("/{model_id}", response_model=InstrumentModelOut)
def get_model(model_id: int, db: Session = Depends(get_db)):
    row = db.query(InstrumentModel).filter(InstrumentModel.id == model_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Model not found")
    return _to_out(row)


@router.put("/{model_id}", response_model=InstrumentModelOut)
def update_model(
    model_id: int,
    req: InstrumentModelIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    row = db.query(InstrumentModel).filter(InstrumentModel.id == model_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Model not found")
    row.name = req.name
    row.description = req.description
    row.design_json = req.design_json
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.delete("/{model_id}")
def delete_model(
    model_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    row = db.query(InstrumentModel).filter(InstrumentModel.id == model_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Model not found")
    db.delete(row)
    db.commit()
    return {"status": "deleted", "id": model_id}


def _to_out(row: InstrumentModel) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "design_json": row.design_json,
        "updated_at": row.updated_at.isoformat(),
    }
