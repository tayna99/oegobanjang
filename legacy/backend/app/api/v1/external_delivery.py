from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_sync_db
from app.services.daily_briefing_service import (
    daily_briefing_role_from_request,
    build_sqlalchemy_daily_briefing_service,
    resolve_daily_briefing_allowed_company_ids,
)


router = APIRouter(prefix="/external-delivery-jobs", tags=["external-delivery"])


def _error(error_code: str, message: str, trace_id: str = "trace_unavailable") -> dict[str, str]:
    return {"error_code": error_code, "message": message, "trace_id": trace_id}


@router.post("/{job_id}/dispatch")
def dispatch_external_delivery_job(
    job_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str = Header(default="viewer", alias="X-User-Role"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    service = build_sqlalchemy_daily_briefing_service(db)
    try:
        allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
            db,
            user_id=x_user_id,
            header_company_id=x_company_id,
            authorization=authorization,
        )
        user_role = daily_briefing_role_from_request(
            header_role=x_user_role,
            authorization=authorization,
        )
        job = service.dispatch_external_delivery_job(
            job_id,
            user_role=user_role,
            allowed_company_ids=allowed_company_ids,
        )
        db.commit()
    except PermissionError as exc:
        db.rollback()
        status_code = 409 if exc.args and exc.args[0] == "PROVIDER_NOT_CONFIGURED" else 403
        raise HTTPException(
            status_code=status_code,
            detail=_error(str(exc.args[0]), "External delivery dispatch was blocked safely."),
        ) from exc
    except LookupError as exc:
        db.rollback()
        raise HTTPException(
            status_code=404,
            detail=_error(str(exc.args[0]), "External delivery job was not found."),
        ) from exc
    return job.model_dump()
