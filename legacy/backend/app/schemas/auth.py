from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthUser(BaseModel):
    id: str
    email: str | None = None
    display_name: str | None = None
    role: str
    company_id: str | None = None
    worker_id: str | None = None
    must_change_password: bool = False


class LoginResponse(BaseModel):
    user: AuthUser
    access_token: str
    token_type: str = "demo"
    redirect_to: str


class CreateWorkerAccountRequest(BaseModel):
    worker_id: str
    email: str
    temporary_password: str
    company_id: str | None = None


class ChangePasswordRequest(BaseModel):
    user_id: str
    current_password: str
    new_password: str
