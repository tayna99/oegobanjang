from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

try:
    from app.db.base import Base
    from app.db.session import get_sync_db
    from app.models.hiring import CandidatePreEntryPackage
    from app.services.context_data_service import (
        calculate_candidate_readiness,
        get_candidate_profile_data,
        mark_candidate_hired,
    )
except ModuleNotFoundError:
    from backend.app.db.base import Base
    from backend.app.db.session import get_sync_db
    from backend.app.models.hiring import CandidatePreEntryPackage
    from backend.app.services.context_data_service import (
        calculate_candidate_readiness,
        get_candidate_profile_data,
        mark_candidate_hired,
    )

router = APIRouter(prefix="/hiring", tags=["hiring"])


class CandidatePackagePayload(BaseModel):
    sections: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "DRAFT"


def _ensure_candidate_package_table(db: Session) -> None:
    Base.metadata.create_all(bind=db.get_bind(), tables=[CandidatePreEntryPackage.__table__])


@router.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: str, db: Session = Depends(get_sync_db)) -> dict:
    candidate = get_candidate_profile_data(candidate_id, db=db)
    if candidate is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    readiness = calculate_candidate_readiness(candidate_id=candidate_id, db=db)
    return {
        "candidate": candidate,
        "readiness": readiness[0] if readiness else None,
        "lifecycle": {
            "stage": "pre_hire",
            "delete_after_worker_registration": True,
        },
    }


@router.get("/candidates/{candidate_id}/pre-entry-package")
def get_candidate_pre_entry_package(candidate_id: str, db: Session = Depends(get_sync_db)) -> dict:
    candidate = get_candidate_profile_data(candidate_id, db=db)
    if candidate is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    _ensure_candidate_package_table(db)
    package = (
        db.query(CandidatePreEntryPackage)
        .filter(CandidatePreEntryPackage.candidate_id == candidate_id)
        .one_or_none()
    )
    if package is None:
        return {"candidate_id": candidate_id, "sections": [], "status": "EMPTY", "saved": False}
    try:
        sections = json.loads(package.payload_json)
    except json.JSONDecodeError:
        sections = []
    return {
        "candidate_id": candidate_id,
        "sections": sections,
        "status": package.status,
        "saved": True,
        "updated_at": package.updated_at.isoformat() if package.updated_at else None,
    }


@router.put("/candidates/{candidate_id}/pre-entry-package")
def save_candidate_pre_entry_package(
    candidate_id: str,
    payload: CandidatePackagePayload,
    db: Session = Depends(get_sync_db),
) -> dict:
    candidate = get_candidate_profile_data(candidate_id, db=db)
    if candidate is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    _ensure_candidate_package_table(db)
    package_id = f"pre-entry-{candidate_id}"
    try:
        package = db.get(CandidatePreEntryPackage, package_id)
        if package is None:
            package = CandidatePreEntryPackage(
                id=package_id,
                candidate_id=candidate_id,
                payload_json=json.dumps(payload.sections, ensure_ascii=False),
                status=payload.status,
            )
            db.add(package)
        else:
            package.payload_json = json.dumps(payload.sections, ensure_ascii=False)
            package.status = payload.status
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="failed to save candidate package") from exc
    return {
        "candidate_id": candidate_id,
        "sections": payload.sections,
        "status": payload.status,
        "saved": True,
    }


@router.post("/candidates/{candidate_id}/hire")
def hire_candidate(candidate_id: str, db: Session = Depends(get_sync_db)) -> dict:
    _ensure_candidate_package_table(db)
    result = mark_candidate_hired(candidate_id, db=db, delete_after_hire=True)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail="candidate not found")
    return result
