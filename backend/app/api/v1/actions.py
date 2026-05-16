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
    "labor_contract": "근로계약서",
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


def _find_tool_result(tool_results: list[dict], tool_name: str) -> dict:
    for tr in tool_results:
        if tr.get("tool_name") == tool_name:
            return tr
    return {}


def _build_action_plan(
    risk_flags: list[str],
    missing_critical_codes: list[str],
    handoff_triggered: bool,
    visa_d_day: int | None,
    risk_type: str | None = None,
) -> list[str]:
    plan: list[str] = []
    if missing_critical_codes:
        docs_ko = _doc_codes_to_ko(missing_critical_codes)
        plan.append(f"근로자에게 서류 요청: {', '.join(docs_ko)}")
    if risk_type == "contract_visa_conflict" or any("계약" in f for f in risk_flags):
        plan.append("계약 기간 연장 또는 비자 만료일 전 계약 조정 검토")
    if visa_d_day is not None:
        try:
            d = int(visa_d_day)
            if d < 0:
                plan.append(f"체류기간 초과 {abs(d)}일 — 즉시 조치 필요")
            elif d <= 14:
                plan.append("체류기간 연장 신청 즉시 준비 필요 (D-14 이내)")
            elif d <= 30:
                plan.append(f"체류기간 연장 신청 준비 시작 (D-{d})")
        except (ValueError, TypeError):
            pass
    if handoff_triggered:
        plan.append("행정사에게 체류 연장 검토 패키지 전달")
    return plan or ["현재 긴급 처리 항목 없음 — 정기 모니터링 유지"]


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
    case_risk_type = case.risk_type if case else None

    try:
        state = ForeignHiringState(request_id=f"review_{action_id}")
        result = run_visa_agent(state, worker_id=worker_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_error("AGENT_ERROR", str(exc))) from exc

    risk_flags: list[str] = result.get("risk_flags", [])
    raw_summary: str = result.get("summary", "")

    visa_sub = next((s for s in result.get("sub_agents", []) if "visa_risk" in s.get("name", "")), {})
    doc_sub = next((s for s in result.get("sub_agents", []) if "document_priority" in s.get("name", "")), {})

    # 비자 위험도 툴 결과에서 d_day, risk_level 추출
    visa_tool = _find_tool_result(visa_sub.get("tool_results", []), "assess_visa_risk")
    visa_output = visa_tool.get("output", {})
    visa_d_day: int | None = visa_output.get("visa_d_day")
    visa_risk_level: str = visa_output.get("risk_level", "")

    # 서류 우선순위 툴 결과에서 누락 서류 추출
    doc_tool = _find_tool_result(doc_sub.get("tool_results", []), "assess_document_priority")
    doc_output = doc_tool.get("output", {})

    raw_critical = doc_output.get("critical_missing", [])
    raw_supplementary = doc_output.get("supplementary_missing", [])
    raw_present = doc_output.get("present_docs", [])
    missing_critical_codes = [
        d["doc_type"] for d in raw_critical if isinstance(d, dict) and d.get("doc_type")
    ]
    missing_supplementary_codes = [
        d["doc_type"] for d in raw_supplementary if isinstance(d, dict) and d.get("doc_type")
    ]
    present_doc_codes = [
        d["doc_type"] if isinstance(d, dict) else str(d)
        for d in raw_present
        if d
    ]
    submission_readiness: str = doc_output.get("submission_readiness", "")

    # handoff는 체류만료/계약-체류 충돌이 D-30 이내면 서류 누락 여부와 별개로 검토 대상이다.
    handoff_triggered: bool = False
    if visa_d_day is not None and case_risk_type in {"visa_expiry", "contract_visa_conflict"}:
        try:
            if int(visa_d_day) <= 30:
                handoff_triggered = True
        except (ValueError, TypeError):
            pass
    if result.get("handoff_triggered"):
        handoff_triggered = True

    structured: dict = {
        "visa_risk": visa_risk_level or (risk_flags[0] if risk_flags else ""),
        "visa_d_day": visa_d_day,
        "doc_priority": f"필수 서류 누락 {len(missing_critical_codes)}건" if missing_critical_codes else "",
        "missing_critical": _doc_codes_to_ko(missing_critical_codes),
        "missing_critical_codes": missing_critical_codes,
        "visa_risk_flags": visa_sub.get("risk_flags", []),
        "doc_risk_flags": doc_sub.get("risk_flags", []),
        "missing_supplementary": _doc_codes_to_ko(missing_supplementary_codes),
        "missing_supplementary_codes": missing_supplementary_codes,
        "present_docs": _doc_codes_to_ko(present_doc_codes),
        "present_doc_codes": present_doc_codes,
        "submission_readiness": submission_readiness,
        "action_plan": _build_action_plan(risk_flags, missing_critical_codes, handoff_triggered, visa_d_day, case_risk_type),
        "handoff_triggered": handoff_triggered,
    }

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


@router.get("/{action_id}/contact-threads")
def list_action_contact_threads(
    action_id: str,
    x_company_id: str | None = Header(default=None, alias="X-Company-Id"),
    db: Session = Depends(get_sync_db),
) -> list[dict]:
    from app.models.contact import ContactThread
    from sqlalchemy import select

    threads = list(
        db.execute(
            select(ContactThread).where(ContactThread.source_action_id == action_id)
        ).scalars()
    )
    return [
        {
            "id": t.id,
            "worker_id": t.worker_id,
            "title": t.title,
            "status": t.status,
            "source_action_id": t.source_action_id,
            "last_message_at": t.last_message_at.isoformat() if t.last_message_at else None,
        }
        for t in threads
    ]
