from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import seed_users, verify_password
from app.db import Base
from app.models import User


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_production_requires_bootstrap_password(monkeypatch):
    monkeypatch.setenv("SHIELD_ENV", "production")
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("SHIELD_ADMIN_PASSWORD", raising=False)

    db = _session()
    try:
        try:
            seed_users(db)
        except RuntimeError as exc:
            assert "SHIELD_ADMIN_PASSWORD" in str(exc)
        else:
            raise AssertionError("production should not seed known default credentials")
    finally:
        db.close()


def test_production_seeds_only_configured_accounts(monkeypatch):
    monkeypatch.setenv("SHIELD_ENV", "production")
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("SHIELD_ADMIN_USERNAME", "site-admin")
    monkeypatch.setenv("SHIELD_ADMIN_PASSWORD", "correct-horse-battery-staple")
    monkeypatch.setenv("SHIELD_OPERATOR_PASSWORD", "another-long-password")

    db = _session()
    try:
        seed_users(db)
        users = {user.username: user for user in db.query(User).all()}
        assert set(users) == {"site-admin", "operator"}
        assert verify_password("correct-horse-battery-staple", users["site-admin"].password_hash)
        assert verify_password("another-long-password", users["operator"].password_hash)
        assert "surjith" not in users
    finally:
        db.close()


def test_development_seeds_demo_accounts(monkeypatch):
    monkeypatch.setenv("SHIELD_ENV", "development")
    monkeypatch.delenv("RENDER", raising=False)
    for name in (
        "SHIELD_ADMIN_USERNAME",
        "SHIELD_ADMIN_PASSWORD",
        "SHIELD_OPERATOR_USERNAME",
        "SHIELD_OPERATOR_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)

    db = _session()
    try:
        seed_users(db)
        users = {user.username: user for user in db.query(User).all()}
        assert set(users) == {"admin", "operator"}
        assert verify_password("admin123", users["admin"].password_hash)
        assert verify_password("shield123", users["operator"].password_hash)
    finally:
        db.close()
