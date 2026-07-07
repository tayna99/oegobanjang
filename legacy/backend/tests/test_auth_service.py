from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.services.auth_service import authenticate_user, change_password, ensure_auth_tables


def _session(tmp_path) -> Session:
    engine = create_engine(f"sqlite:///{tmp_path / 'auth.sqlite3'}", future=True)
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)()


def test_demo_worker_password_change_flag_is_not_reset_on_next_login(tmp_path):
    db = _session(tmp_path)
    try:
        ensure_auth_tables(db)
        first_login = authenticate_user("potenup3@gmail.com", "worker1234", db)
        assert first_login is not None
        assert first_login["must_change_password"] is True

        changed = change_password(
            user_id=first_login["id"],
            current_password="worker1234",
            new_password="changed1234",
            db=db,
        )
        assert changed["must_change_password"] is False

        db.execute(
            text("UPDATE users SET must_change_password = 1 WHERE id = :user_id"),
            {"user_id": first_login["id"]},
        )
        db.commit()

        next_login = authenticate_user("potenup3@gmail.com", "changed1234", db)
        assert next_login is not None
        assert next_login["must_change_password"] is False
    finally:
        db.close()
