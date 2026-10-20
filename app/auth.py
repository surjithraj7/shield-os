from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.config import is_production
from app.db import get_db
from app.models import AuthSession, User

SESSION_DAYS = 7
_PBKDF2_ITERATIONS = 120_000


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, TypeError):
        return False


def create_session(db: Session, user: User) -> str:
    token = secrets.token_hex(32)
    now = utcnow()
    db.add(
        AuthSession(
            token=token,
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    return token


def revoke_session(db: Session, token: str) -> None:
    db.query(AuthSession).filter(AuthSession.token == token).delete()
    db.commit()


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[len("Bearer "):].strip()
    if not token:
        return None
    session = db.query(AuthSession).filter(AuthSession.token == token).first()
    if not session:
        return None
    if session.expires_at.replace(tzinfo=None) < utcnow():
        db.delete(session)
        db.commit()
        return None
    return db.query(User).filter(User.id == session.user_id).first()


def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def seed_users(db: Session) -> None:
    """Create the initial accounts without shipping production credentials.

    Development and test environments keep convenient demo defaults. Production
    deployments must provide ``SHIELD_ADMIN_PASSWORD``; otherwise startup fails
    rather than silently creating a known-password administrator.
    """
    if db.query(User).count() > 0:
        return

    production = is_production()
    admin_username = (os.environ.get("SHIELD_ADMIN_USERNAME") or "admin").strip()[:64]
    admin_password = (os.environ.get("SHIELD_ADMIN_PASSWORD") or "").strip()
    operator_username = (os.environ.get("SHIELD_OPERATOR_USERNAME") or "operator").strip()[:64]
    operator_password = (os.environ.get("SHIELD_OPERATOR_PASSWORD") or "").strip()

    if not admin_password:
        if production:
            raise RuntimeError(
                "SHIELD_ADMIN_PASSWORD is required for the first production startup. "
                "Set it as a secret environment variable and redeploy."
            )
        admin_password = "admin123"

    if production and len(admin_password) < 12:
        raise RuntimeError("SHIELD_ADMIN_PASSWORD must be at least 12 characters in production")

    accounts = [
        User(
            username=admin_username,
            password_hash=hash_password(admin_password),
            role="admin",
            full_name="System Administrator",
        )
    ]

    if not operator_password and not production:
        operator_password = "shield123"
    if operator_password:
        if production and len(operator_password) < 12:
            raise RuntimeError("SHIELD_OPERATOR_PASSWORD must be at least 12 characters in production")
        if operator_username == admin_username:
            raise RuntimeError("SHIELD_OPERATOR_USERNAME must differ from SHIELD_ADMIN_USERNAME")
        accounts.append(
            User(
                username=operator_username,
                password_hash=hash_password(operator_password),
                role="operator",
                full_name="Site Operator",
            )
        )

    db.add_all(accounts)
    db.commit()
