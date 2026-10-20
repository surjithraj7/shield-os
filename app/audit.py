"""Audit logging helper for privileged and state-changing actions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def record_audit(
    db: Session,
    *,
    actor: str,
    action: str,
    object_type: str = "",
    object_id: str = "",
    details: dict[str, Any] | None = None,
) -> AuditLog:
    row = AuditLog(
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        actor=actor or "system",
        action=action,
        object_type=object_type,
        object_id=str(object_id or ""),
        details_json=json.dumps(details or {}, default=str, sort_keys=True),
    )
    db.add(row)
    return row
