from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...db.session import get_sync_db
from ...services.auth_service import create_worker_with_account

router = APIRouter(prefix="/workers", tags=["workers"])


class CreateWorkerRequest(BaseModel):
    name: str
    email: str
    company_id: str | None = None
    temporary_password: str | None = None
    nationality: str | None = None
    preferred_language: str | None = "vi"
    visa_type: str | None = "E-9"


@router.post("")
def create_worker(body: CreateWorkerRequest, db: Session = Depends(get_sync_db)) -> dict[str, Any]:
    try:
        return create_worker_with_account(
            name=body.name,
            email=body.email,
            company_id=body.company_id,
            temporary_password=body.temporary_password,
            nationality=body.nationality,
            preferred_language=body.preferred_language,
            visa_type=body.visa_type,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
