from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...db.session import get_sync_db
from ...schemas.auth import (
    AuthUser,
    ChangePasswordRequest,
    CreateWorkerAccountRequest,
    LoginRequest,
    LoginResponse,
)
from ...services.auth_service import (
    authenticate_user,
    change_password,
    create_worker_account,
    ensure_auth_tables,
    issue_demo_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_sync_db)) -> LoginResponse:
    user = authenticate_user(body.email, body.password, db)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    role = user["role"]
    redirect_to = "/change-password" if user.get("must_change_password") else ("/worker" if role == "WORKER" else "/dashboard")
    return LoginResponse(
        user=AuthUser(**user),
        access_token=issue_demo_token(user),
        redirect_to=redirect_to,
    )


@router.post("/worker-accounts")
def create_worker_user(body: CreateWorkerAccountRequest, db: Session = Depends(get_sync_db)) -> dict[str, object]:
    try:
        user = create_worker_account(
            worker_id=body.worker_id,
            email=body.email,
            temporary_password=body.temporary_password,
            company_id=body.company_id,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user": user}


@router.post("/change-password")
def change_user_password(body: ChangePasswordRequest, db: Session = Depends(get_sync_db)) -> dict[str, object]:
    try:
        user = change_password(
            user_id=body.user_id,
            current_password=body.current_password,
            new_password=body.new_password,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user": user}


@router.get("/demo-users")
def demo_users(db: Session = Depends(get_sync_db)) -> dict[str, list[dict[str, str]]]:
    ensure_auth_tables(db)
    return {
        "users": [
            {
                "role": "ADMIN",
                "email": "admin@oegobanjang.local",
                "password": "admin1234",
                "redirect_to": "/dashboard",
            },
            {
                "role": "WORKER",
                "email": "potenup3@gmail.com",
                "password": "worker1234",
                "redirect_to": "/worker",
            },
            {
                "role": "WORKER",
                "email": "scrivener@oegobanjang.local",
                "password": "scrivener1234",
                "redirect_to": "/worker",
                "label": "행정사",
            },
        ]
    }
