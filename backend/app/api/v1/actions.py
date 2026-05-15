from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.daily_briefing_service import (
    build_sqlalchemy_daily_briefing_service,
    resolve_daily_briefing_allowed_company_ids,
)
from app.db.session import get_sync_db


router = APIRouter(prefix="/actions", tags=["actions"])

DOC_CODE_TO_KO: dict[str, str] = {
    "work_permit": "고용허가서 사본",
    "alien_registration": "외국인등록증 사본",
    "employment_contract": "표준근로계약서",
    "labor_contract": "표준근로계약서",
    "passport_copy": "여권 사본",
    "passport": "여권 사본",
    "health_certificate": "건강검진 결과서",
    "criminal_record": "범죄경력 조회서",
    "standard_contract": "표준근로계약서",
}


def _doc_codes_to_ko(codes: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for code in codes:
        name = DOC_CODE_TO_KO.get(code.lower(), code)
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


class AgentReviewResult(BaseModel):
    action_id: str
    worker_id: str | None = None
    risk_flags: list[str] = []
    summary: str = ""
    summary_structured: dict = {}


class ExternalDeliveryJobRequest(BaseModel):
    channel: str = "admin_scrivener"
    provider: str = "manual"


def _error(error_code: str, message: str, trace_id: str = "trace_unavailable") -> dict[str, str]:
    return {"error_code": error_code, "message": message, "trace_id": trace_id}


@router.post("/{action_id}/agent-review")
def run_agent_review(
    action_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    from app.agent_runtime.agents.visa_agent import run_visa_agent
    from app.agent_runtime.schemas.state import ForeignHiringState

    service = build_sqlalchemy_daily_briefing_service(db)
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
        authorization=authorization,
    )

    action = service.repository.actions.get(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=_error("ACTION_NOT_FOUND", "Action not found."))

    try:
        service._assert_case_scope(action.case_id, allowed_company_ids)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=_error(str(exc.args[0]), "Permission denied.")) from exc

    case = service.repository.cases.get(action.case_id)
    worker_id: str | None = case.worker_id if case else None

    all_briefing_items = [
        item
        for briefing in service.repository.briefings.values()
        for item in briefing.items
    ]
    item = next((i for i in all_briefing_items if i.case_id == action.case_id), None)
    item_missing: list[str] = item.missing_documents if item else []

    try:
        state = ForeignHiringState(request_id=f"review_{action_id}")
        result = run_visa_agent(state, worker_id=worker_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_error("AGENT_ERROR", str(exc))) from exc

    risk_flags: list[str] = result.get("risk_flags", [])
    raw_summary: str = result.get("summary", "")

    structured: dict = {}
    if risk_flags:
        structured["visa_risk"] = risk_flags[0]
    if item_missing:
        structured["doc_priority"] = f"필수 서류 누락 {len(item_missing)}건"
        structured["missing_critical"] = _doc_codes_to_ko(item_missing)

    review = AgentReviewResult(
        action_id=action_id,
        worker_id=worker_id,
        risk_flags=risk_flags,
        summary=raw_summary,
        summary_structured=structured,
    )
    return review.model_dump()


@router.get("/{action_id}/handoff-preview")
def get_handoff_preview(
    action_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    service = build_sqlalchemy_daily_briefing_service(db)
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
        authorization=authorization,
    )
    try:
        preview = service.get_handoff_preview(
            action_id,
            allowed_company_ids=allowed_company_ids,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=_error(str(exc.args[0]), "Requested action is outside the allowed company scope."),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error(str(exc.args[0]), "Handoff preview was not found."),
        ) from exc
    return preview.model_dump()


@router.get("/{action_id}/document-request-draft")
def get_document_request_draft(
    action_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    service = build_sqlalchemy_daily_briefing_service(db)
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
        authorization=authorization,
    )
    try:
        draft = service.get_document_request_draft(
            action_id,
            allowed_company_ids=allowed_company_ids,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=_error(str(exc.args[0]), "Requested action is outside the allowed company scope."),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error(str(exc.args[0]), "Document request draft was not found."),
        ) from exc
    return draft.model_dump()


@router.get("/{action_id}/handoff-export-draft")
def get_handoff_export_draft(
    action_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    service = build_sqlalchemy_daily_briefing_service(db)
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
        authorization=authorization,
    )
    try:
        export = service.generate_handoff_export_draft(
            action_id,
            allowed_company_ids=allowed_company_ids,
        )
        pdf = _minimal_pdf_from_text(export.content_markdown)
        service.record_handoff_export_artifact(
            action_id,
            export_format="pdf",
            content=pdf,
            allowed_company_ids=allowed_company_ids,
        )
        db.commit()
    except PermissionError as exc:
        status_code = 409 if exc.args and exc.args[0] == "APPROVAL_REQUIRED" else 403
        raise HTTPException(
            status_code=status_code,
            detail=_error(str(exc.args[0]), "Handoff export requires an approved action."),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error(str(exc.args[0]), "Handoff export target was not found."),
        ) from exc
    return export.model_dump()


def _pdf_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", "")
    )


def _minimal_pdf_from_text(text: str) -> bytes:
    safe_lines = [
        line.encode("ascii", errors="ignore").decode("ascii")
        for line in text.splitlines()
    ][:42]
    stream_lines = ["BT", "/F1 10 Tf", "50 780 Td"]
    for index, line in enumerate(safe_lines):
        if index:
            stream_lines.append("0 -14 Td")
        stream_lines.append(f"({_pdf_escape(line[:90])}) Tj")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines).encode("ascii")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        b"5 0 obj << /Length "
        + str(len(stream)).encode("ascii")
        + b" >> stream\n"
        + stream
        + b"\nendstream endobj\n",
    ]
    offsets: list[int] = []
    output = bytearray(b"%PDF-1.4\n")
    for obj in objects:
        offsets.append(len(output))
        output.extend(obj)
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


@router.get("/{action_id}/handoff-export.pdf")
def get_handoff_export_pdf(
    action_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> Response:
    service = build_sqlalchemy_daily_briefing_service(db)
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
        authorization=authorization,
    )
    try:
        export = service.generate_handoff_export_draft(
            action_id,
            allowed_company_ids=allowed_company_ids,
        )
        pdf = _minimal_pdf_from_text(export.content_markdown)
        service.record_handoff_export_artifact(
            action_id,
            export_format="pdf",
            content=pdf,
            allowed_company_ids=allowed_company_ids,
        )
        db.commit()
    except PermissionError as exc:
        status_code = 409 if exc.args and exc.args[0] == "APPROVAL_REQUIRED" else 403
        raise HTTPException(
            status_code=status_code,
            detail=_error(str(exc.args[0]), "Handoff export requires an approved action."),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error(str(exc.args[0]), "Handoff export target was not found."),
        ) from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{action_id}-handoff-export.pdf"'
        },
    )


@router.get("/{action_id}/handoff-exports")
def list_handoff_exports(
    action_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> list[dict]:
    service = build_sqlalchemy_daily_briefing_service(db)
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
        authorization=authorization,
    )
    try:
        artifacts = service.list_handoff_export_artifacts(
            action_id,
            allowed_company_ids=allowed_company_ids,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=_error(str(exc.args[0]), "Requested action is outside the allowed company scope."),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error(str(exc.args[0]), "Handoff exports were not found."),
        ) from exc
    return [artifact.model_dump() for artifact in artifacts]


@router.post("/{action_id}/external-delivery-jobs")
def create_external_delivery_job(
    action_id: str,
    payload: ExternalDeliveryJobRequest,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_sync_db),
) -> dict:
    service = build_sqlalchemy_daily_briefing_service(db)
    allowed_company_ids = resolve_daily_briefing_allowed_company_ids(
        db,
        user_id=x_user_id,
        header_company_id=x_company_id,
        authorization=authorization,
    )
    try:
        job = service.create_external_delivery_job(
            action_id,
            channel=payload.channel,
            provider=payload.provider,
            allowed_company_ids=allowed_company_ids,
        )
        db.commit()
    except PermissionError as exc:
        status_code = 409 if exc.args and exc.args[0] == "APPROVAL_REQUIRED" else 403
        message = (
            "External delivery job requires an approved action."
            if status_code == 409
            else "Requested action is outside the allowed company scope."
        )
        raise HTTPException(
            status_code=status_code,
            detail=_error(str(exc.args[0]), message),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error(str(exc.args[0]), "External delivery target was not found."),
        ) from exc
    return job.model_dump()
