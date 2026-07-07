from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from ..db.base import Base
from ..models.company import Company
from ..models.user import User
from ..models.worker import Worker


AUTH_TABLES = [User.__table__]
WORKER_AUTH_TABLES = [Company.__table__, Worker.__table__, User.__table__]
DEFAULT_COMPANY_ID = "550e8400-e29b-41d4-a716-446655440001"
DEFAULT_WORKER_ID = "650e8400-e29b-41d4-a716-446655440001"
SCRIVENER_COMPANY_ID = "850e8400-e29b-41d4-a716-446655440001"
SCRIVENER_WORKER_ID = "750e8400-e29b-41d4-a716-446655440001"


def ensure_auth_tables(db: Session) -> None:
    Base.metadata.create_all(bind=db.get_bind(), tables=AUTH_TABLES)
    _ensure_user_columns(db)
    _ensure_worker_columns(db)
    _seed_demo_users(db)
    _seed_scrivener_worker(db)


def _seed_scrivener_worker(db: Session) -> None:
    try:
        existing = db.get(Worker, SCRIVENER_WORKER_ID)
        if existing is None:
            worker = Worker(
                id=SCRIVENER_WORKER_ID,
                company_id=SCRIVENER_COMPANY_ID,
                name="행정사 박과장",
                nationality="KR",
                preferred_language="ko",
                email="scrivener@oegobanjang.local",
                contact_channel="email",
                visa_type=None,
                worker_type="scrivener",
                status="ACTIVE",
            )
            db.add(worker)
            db.commit()
        elif existing.worker_type != "scrivener":
            existing.worker_type = "scrivener"
            db.commit()
    except Exception:
        db.rollback()


def authenticate_user(email: str, password: str, db: Session) -> dict[str, Any] | None:
    ensure_auth_tables(db)
    normalized = email.strip().lower()
    user = db.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
    if user is None or user.status != "ACTIVE":
        return None
    if not user.password_hash or not verify_password(password, user.password_hash):
        return None
    return user_payload(user)


def user_payload(user: User) -> dict[str, Any]:
    role = (user.role or "ADMIN").upper()
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": role,
        "company_id": user.company_id,
        "worker_id": user.worker_id,
        "must_change_password": bool(user.must_change_password),
    }


def issue_demo_token(user: dict[str, Any]) -> str:
    raw = f"{user['id']}:{user.get('role')}:{datetime.now(timezone.utc).timestamp()}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"pbkdf2_sha256${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt_b64, digest_b64 = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(digest_b64.encode())
    except Exception:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return hmac.compare_digest(actual, expected)


def _ensure_worker_columns(db: Session) -> None:
    inspector = inspect(db.get_bind())
    if not inspector.has_table("workers"):
        return
    existing = {column["name"] for column in inspector.get_columns("workers")}
    if "worker_type" not in existing:
        db.execute(text(
            "ALTER TABLE workers ADD COLUMN worker_type VARCHAR(40) DEFAULT 'foreign_worker' NOT NULL"
        ))
        db.commit()


def _ensure_user_columns(db: Session) -> None:
    inspector = inspect(db.get_bind())
    if not inspector.has_table("users"):
        return
    existing = {column["name"] for column in inspector.get_columns("users")}
    migrations = {
        "password_hash": "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)",
        "company_id": "ALTER TABLE users ADD COLUMN company_id VARCHAR(64)",
        "worker_id": "ALTER TABLE users ADD COLUMN worker_id VARCHAR(64)",
        "status": "ALTER TABLE users ADD COLUMN status VARCHAR(40) DEFAULT 'ACTIVE' NOT NULL",
        "must_change_password": "ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT 0 NOT NULL",
    }
    for column, ddl in migrations.items():
        if column not in existing:
            db.execute(text(ddl))
    db.commit()


def _seed_demo_users(db: Session) -> None:
    demo_users = [
        {
            "id": "user-admin-001",
            "email": "admin@oegobanjang.local",
            "password": "admin1234",
            "display_name": "김대리",
            "role": "ADMIN",
            "company_id": DEFAULT_COMPANY_ID,
            "worker_id": None,
            "must_change_password": False,
        },
        {
            "id": "user-expert-001",
            "email": "expert@oegobanjang.local",
            "password": "expert1234",
            "display_name": "박행정사",
            "role": "EXPERT",
            "company_id": DEFAULT_COMPANY_ID,
            "worker_id": None,
            "must_change_password": False,
        },
        {
            "id": "user-worker-nguyen",
            "email": "potenup3@gmail.com",
            "password": "worker1234",
            "display_name": "Nguyen V.",
            "role": "WORKER",
            "company_id": DEFAULT_COMPANY_ID,
            "worker_id": DEFAULT_WORKER_ID,
            "must_change_password": True,
        },
        {
            "id": "user-scrivener-001",
            "email": "scrivener@oegobanjang.local",
            "password": "scrivener1234",
            "display_name": "행정사 박과장",
            "role": "SCRIVENER",
            "company_id": SCRIVENER_COMPANY_ID,
            "worker_id": SCRIVENER_WORKER_ID,
            "must_change_password": False,
        },
    ]
    for item in demo_users:
        user = db.get(User, item["id"])
        created = user is None
        if user is None:
            user = User(id=item["id"])
            db.add(user)
        user.email = item["email"]
        user.display_name = item["display_name"]
        user.role = item["role"]
        user.company_id = item["company_id"]
        user.worker_id = item["worker_id"]
        user.status = "ACTIVE"
        if created:
            user.must_change_password = bool(item["must_change_password"])
        elif (
            item["must_change_password"]
            and user.password_hash
            and not verify_password(item["password"], user.password_hash)
        ):
            user.must_change_password = False
        if not user.password_hash:
            user.password_hash = hash_password(item["password"])
    db.commit()


def create_worker_account(
    *,
    worker_id: str,
    email: str,
    temporary_password: str,
    company_id: str | None,
    db: Session,
) -> dict[str, Any]:
    ensure_auth_tables(db)
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise ValueError("email is required")
    if len(temporary_password) < 8:
        raise ValueError("temporary password must be at least 8 characters")
    worker = db.get(Worker, worker_id)
    if worker is None:
        raise ValueError("worker not found")

    user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if user is None:
        user = db.execute(select(User).where(User.worker_id == worker_id)).scalar_one_or_none()
    if user is None:
        user = User(id=f"user-worker-{worker_id[-12:]}")
        db.add(user)

    user.email = normalized_email
    user.display_name = _display_worker_name(worker.name)
    user.role = "WORKER"
    user.company_id = company_id or worker.company_id
    user.worker_id = worker_id
    user.status = "ACTIVE"
    user.password_hash = hash_password(temporary_password)
    user.must_change_password = True

    worker.email = normalized_email
    worker.contact_channel = "portal"
    db.commit()
    return user_payload(user)


def create_worker_with_account(
    *,
    name: str,
    email: str,
    company_id: str | None,
    temporary_password: str | None,
    nationality: str | None,
    preferred_language: str | None,
    visa_type: str | None,
    db: Session,
) -> dict[str, Any]:
    Base.metadata.create_all(bind=db.get_bind(), tables=WORKER_AUTH_TABLES)
    ensure_auth_tables(db)
    normalized_email = email.strip().lower()
    if not name.strip():
        raise ValueError("worker name is required")
    if not normalized_email:
        raise ValueError("email is required")
    existing = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if existing is not None:
        raise ValueError("email already exists")

    password = temporary_password.strip() if temporary_password else generate_temporary_password()
    if len(password) < 8:
        raise ValueError("temporary password must be at least 8 characters")

    worker = Worker(
        id=f"worker_{uuid4().hex[:12]}",
        company_id=company_id or DEFAULT_COMPANY_ID,
        name=name.strip(),
        nationality=nationality.strip() if nationality else None,
        preferred_language=preferred_language or "vi",
        email=normalized_email,
        contact_channel="portal",
        visa_type=visa_type or "E-9",
        status="ACTIVE",
    )
    db.add(worker)
    db.flush()

    user = User(
        id=f"user-worker-{worker.id[-12:]}",
        email=normalized_email,
        password_hash=hash_password(password),
        display_name=_display_worker_name(worker.name),
        role="WORKER",
        company_id=worker.company_id,
        worker_id=worker.id,
        status="ACTIVE",
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    return {
        "worker": {
            "id": worker.id,
            "company_id": worker.company_id,
            "name": worker.name,
            "nationality": worker.nationality,
            "preferred_language": worker.preferred_language,
            "email": worker.email,
            "visa_type": worker.visa_type,
            "status": worker.status,
        },
        "user": user_payload(user),
        "temporary_password": password,
    }


def change_password(
    *,
    user_id: str,
    current_password: str,
    new_password: str,
    db: Session,
) -> dict[str, Any]:
    ensure_auth_tables(db)
    if len(new_password) < 8:
        raise ValueError("new password must be at least 8 characters")
    user = db.get(User, user_id)
    if user is None or not user.password_hash:
        raise ValueError("user not found")
    if not verify_password(current_password, user.password_hash):
        raise ValueError("invalid current password")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.commit()
    return user_payload(user)


def generate_temporary_password() -> str:
    return f"worker{uuid4().hex[:8]}"


def _display_worker_name(name: str | None) -> str:
    if not name:
        return "근로자"
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1][0]}."
    return name
