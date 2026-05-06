from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.approval import Approval
from backend.app.models.contact import ContactMessage, StatusUpdateCandidate
from backend.app.models.evidence import EvidenceLog


MESSAGE_INITIAL_STATUS = "PENDING_APPROVAL"
APPROVAL_INITIAL_STATUS = "PENDING"
CANDIDATE_INITIAL_STATUS = "PENDING_REVIEW"
FORBIDDEN_EVIDENCE_MARKERS = (
    "여권번호",
    "외국인등록번호",
    "전화번호 전체",
    "주소 전체",
)


def save_message_draft_result(
    db: Session,
    *,
    agent_result: dict[str, Any],
    worker_id: str | None = None,
    created_by: str | None = None,
    request_id: str | None = None,
) -> ContactMessage:
    _validate_message_draft_result(agent_result)
    source_ids = _citation_source_ids(agent_result.get("citations") or [])
    risk_flags = _as_list(agent_result.get("risk_flags"))

    message = ContactMessage(
        worker_id=worker_id or agent_result.get("worker_id"),
        message_purpose=agent_result["message_purpose"],
        language_code=agent_result["language_code"],
        korean_text=agent_result["korean_text"],
        translated_text=agent_result.get("translated_text"),
        status=MESSAGE_INITIAL_STATUS,
        approval_required=True,
        citation_source_ids=_json_dumps(source_ids),
        risk_flags=_json_dumps(risk_flags),
        created_by=created_by,
        sent_at=None,
    )
    db.add(message)
    db.flush()

    approval = create_approval_for_contact_message(
        db,
        message,
        requested_by=created_by,
    )
    message.approval_id = approval.id

    save_evidence_events(
        db,
        evidence_events=agent_result.get("evidence_events") or [],
        request_id=request_id,
        worker_id=message.worker_id,
        contact_message_id=message.id,
        approval_id=approval.id,
        risk_flags=risk_flags,
        default_source_ids=source_ids,
        forbidden_texts=[
            agent_result.get("korean_text"),
            agent_result.get("translated_text"),
        ],
    )
    db.flush()
    return message


def save_worker_reply_summary_result(
    db: Session,
    *,
    agent_result: dict[str, Any],
    worker_id: str,
    request_id: str | None = None,
    source_message_id: str | None = None,
    requested_by: str | None = None,
    worker_reply: str | None = None,
) -> list[StatusUpdateCandidate]:
    _validate_worker_reply_summary_result(agent_result)
    candidates: list[StatusUpdateCandidate] = []
    risk_flags = _as_list(agent_result.get("risk_flags"))

    for item in agent_result.get("status_update_candidates") or []:
        _validate_status_update_candidate(item)
        candidate = StatusUpdateCandidate(
            worker_id=worker_id,
            target_type=item.get("target_type") or "worker_document",
            target_key=item["field"],
            candidate_status=item["candidate_status"],
            confidence=item.get("confidence"),
            manager_review_required=True,
            status=CANDIDATE_INITIAL_STATUS,
            source_message_id=source_message_id,
        )
        db.add(candidate)
        db.flush()

        approval = create_approval_for_status_update_candidate(
            db,
            candidate,
            requested_by=requested_by,
        )
        candidate.approval_id = approval.id
        candidates.append(candidate)

        save_evidence_events(
            db,
            evidence_events=agent_result.get("evidence_events") or [],
            request_id=request_id,
            worker_id=worker_id,
            status_update_candidate_id=candidate.id,
            approval_id=approval.id,
            risk_flags=risk_flags,
            forbidden_texts=[worker_reply],
        )

    db.flush()
    return candidates


def save_evidence_events(
    db: Session,
    *,
    evidence_events: list[dict[str, Any]],
    request_id: str | None = None,
    worker_id: str | None = None,
    contact_message_id: str | None = None,
    status_update_candidate_id: str | None = None,
    approval_id: str | None = None,
    risk_flags: list[str] | None = None,
    default_source_ids: list[str] | None = None,
    forbidden_texts: list[str | None] | None = None,
) -> list[EvidenceLog]:
    logs: list[EvidenceLog] = []
    for event in evidence_events:
        summary = str(event.get("summary") or "").strip()
        _validate_evidence_summary(summary, forbidden_texts or [])
        source_ids = event.get("source_ids") or default_source_ids or []
        log = EvidenceLog(
            event_type=str(event.get("event_type") or "unknown"),
            agent_name=str(event.get("agent_name") or "unknown"),
            tool_name=event.get("tool_name"),
            summary=summary,
            source_ids=_json_dumps(_as_list(source_ids)),
            approval_required=bool(event.get("approval_required", False)),
            risk_flags=_json_dumps(risk_flags or []),
            request_id=request_id,
            worker_id=worker_id,
            contact_message_id=contact_message_id,
            status_update_candidate_id=status_update_candidate_id,
            approval_id=approval_id,
        )
        db.add(log)
        logs.append(log)

    db.flush()
    return logs


def create_approval_for_contact_message(
    db: Session,
    contact_message: ContactMessage,
    *,
    requested_by: str | None = None,
) -> Approval:
    approval = Approval(
        target_type="contact_message",
        target_id=contact_message.id,
        status=APPROVAL_INITIAL_STATUS,
        requested_by=requested_by,
        reason="다국어 메시지 발송 전 담당자 승인이 필요합니다.",
    )
    db.add(approval)
    db.flush()
    return approval


def create_approval_for_status_update_candidate(
    db: Session,
    candidate: StatusUpdateCandidate,
    *,
    requested_by: str | None = None,
) -> Approval:
    approval = Approval(
        target_type="status_update_candidate",
        target_id=candidate.id,
        status=APPROVAL_INITIAL_STATUS,
        requested_by=requested_by,
        reason="상태 업데이트 후보 반영 전 담당자 승인이 필요합니다.",
    )
    db.add(approval)
    db.flush()
    return approval


def _validate_message_draft_result(agent_result: dict[str, Any]) -> None:
    if agent_result.get("status") != "SUCCESS":
        raise ValueError("Only successful message draft results can be saved")
    if not agent_result.get("korean_text"):
        raise ValueError("korean_text is required")
    if agent_result.get("approval_required") is not True:
        raise ValueError("message draft must require approval")
    if agent_result.get("sent_at") is not None:
        raise ValueError("message draft cannot have sent_at")
    if str(agent_result.get("status", "")).upper() in {"SENT", "APPROVED"}:
        raise ValueError("message draft cannot start as SENT or APPROVED")


def _validate_worker_reply_summary_result(agent_result: dict[str, Any]) -> None:
    if agent_result.get("status") != "SUCCESS":
        raise ValueError("Only successful worker reply summary results can be saved")
    if agent_result.get("approval_required") is not True:
        raise ValueError("worker reply summary must require approval")
    if agent_result.get("manager_review_required") is not True:
        raise ValueError("worker reply summary must require manager review")


def _validate_status_update_candidate(candidate: dict[str, Any]) -> None:
    if candidate.get("is_final") is True:
        raise ValueError("status update candidate cannot be final")
    if str(candidate.get("status", "")).upper() == "APPLIED":
        raise ValueError("status update candidate cannot start as APPLIED")
    if not candidate.get("field") or not candidate.get("candidate_status"):
        raise ValueError("candidate field and candidate_status are required")


def _validate_evidence_summary(
    summary: str,
    forbidden_texts: list[str | None],
) -> None:
    if not summary:
        raise ValueError("evidence summary is required")
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        if marker in summary:
            raise ValueError("evidence summary contains forbidden personal data marker")
    for text in forbidden_texts:
        if text and text in summary:
            raise ValueError("evidence summary must not contain original text")


def _citation_source_ids(citations: list[dict[str, Any]]) -> list[str]:
    return [
        str(citation["source_id"])
        for citation in citations
        if citation.get("source_id")
    ]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
