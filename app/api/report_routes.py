from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.report import build_regulatory_report

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/regulatory")
def regulatory_report(
    start_x: float = 100.0,
    end_x: float = 244.0,
    db: Session = Depends(get_db),
):
    html = build_regulatory_report(db, start_x=start_x, end_x=end_x)
    return Response(
        content=html,
        media_type="text/html",
        headers={
            "Content-Disposition": 'attachment; filename="shield_regulatory_report.html"'
        },
    )
