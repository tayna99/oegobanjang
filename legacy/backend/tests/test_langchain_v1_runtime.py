from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.agent_runtime.agents.multilingual_contact_agent as contact_agent_module
from backend.app.db.base import Base
from backend.app.models.approval import Approval
from backend.app.models import contact as contact_models  # noqa: F401
from backend.app.models.handoff import HandoffPackageDraft
from backend.app.services.handoff_persistence_service import save_handoff_package_draft
from app.agent_runtime.langchain_v1.contact_artifact_store import pop_contact_artifacts
from app.agent_runtime.langchain_v1.contact_subagents import (
    CONTACT_ONBOARDING_SUB_AGENT,
    WORKER_REPLY_INTERPRETER_SUB_AGENT,
    run_contact_onboarding_subagent,
    run_worker_reply_interpreter_subagent,
    summarize_contact_subagent_payload,
)
from app.agent_runtime.langchain_v1.middleware import _safe_rag_contexts_from_records
from app.agent_runtime.langchain_v1.runtime import (
    normalize_runtime_input,
    run_langchain_v1_agent,
    to_foreign_hiring_state,
)
from app.agent_runtime.langchain_v1.schemas import (
    ApprovalBlock,
    HandoffDraft,
    WorkBridgeAgentResponse,
)
from app.agent_runtime.langchain_v1.state_store import runtime_state_store
from app.agent_runtime.schemas import Intent


class FakeAgent:
    async def ainvoke(self, payload):
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="신규 고용 준비 초안입니다.",
                detected_intents=["HIRING"],
                risk_flags=[],
                approval=ApprovalBlock(required=False, status="NOT_REQUIRED"),
                handoff=HandoffDraft(available=False),
                rag_contexts=[
                    {
                        "source_id": "eps_employer_process",
                        "title": "사업주 고용절차",
                    }
                ],
                domain_payload={"runtime": "fake"},
                blocked_reason="",
            )
        }


class FakeContactSubAgentRuntimeAgent:
    def __init__(self) -> None:
        self.contact_raw: dict | None = None
        self.reply_raw: dict | None = None

    async def ainvoke(self, payload, **kwargs):
        del payload, kwargs
        worker_reply = (
            "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi. "
            "010-1234-5678 M12345678 900101-1234567"
        )
        self.contact_raw = run_contact_onboarding_subagent(
            worker_id="worker-demo-raw-001",
            worker_name="Nguyen",
            language_code="vi",
            message_purpose="safety_training_notice",
            user_request="베트남어 안전교육 안내 메시지 초안 생성",
            training_date="2026-05-10",
            training_time="10:00",
            location="교육장",
            contact_person="담당자",
        )
        self.reply_raw = run_worker_reply_interpreter_subagent(
            worker_id="worker-demo-raw-001",
            language_code="vi",
            worker_reply=worker_reply,
        )
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="다국어 컨택 초안과 근로자 답변 해석 후보를 준비했습니다.",
                detected_intents=["CONTACT"],
                risk_flags=[],
                approval=ApprovalBlock(
                    required=True,
                    status="PENDING",
                    reason="메시지 발송 및 상태 업데이트 확정 전 담당자 검토가 필요합니다.",
                ),
                handoff=HandoffDraft(available=False),
                domain_payload={
                    "contact_subagents": {
                        "contact_onboarding_subagent": summarize_contact_subagent_payload(
                            self.contact_raw
                        ),
                        "worker_reply_interpreter_subagent": summarize_contact_subagent_payload(
                            self.reply_raw
                        ),
                    }
                },
                blocked_reason="",
            )
        }


class FakeUnsafeContactSubAgentRuntimeAgent:
    async def ainvoke(self, payload, **kwargs):
        del payload, kwargs
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="다국어 컨택 요약입니다.",
                detected_intents=["CONTACT"],
                risk_flags=[],
                approval=ApprovalBlock(required=True, status="PENDING"),
                handoff=HandoffDraft(available=False),
                domain_payload={
                    "contact_subagents": [
                        {
                            "sub_agent": "contact_onboarding_subagent",
                            "status": "PENDING",
                            "approval_required": True,
                            "worker_id": "worker-demo-raw-001",
                            "korean_text": "여권 사본을 제출해 주세요.",
                            "translated_text": "Vui lòng gửi bản sao hộ chiếu.",
                        },
                        {
                            "sub_agent": "worker_reply_interpreter_subagent",
                            "status": "PENDING",
                            "approval_required": True,
                            "manager_review_required": True,
                            "status_update_candidate_count": 2,
                            "worker_reply": "Tôi có hộ chiếu.",
                            "translated_ko": "여권이 있습니다.",
                            "phone": "010-1234-5678",
                            "passport_number": "M12345678",
                            "alien_registration_number": "900101-1234567",
                        },
                    ]
                },
                blocked_reason="",
            )
        }


class FakeUnsafeHandoffRuntimeAgent:
    def __init__(self, *, package_type: str | None) -> None:
        self.package_type = package_type

    async def ainvoke(self, payload, **kwargs):
        del payload, kwargs
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="전문가 검토용 handoff package 초안을 준비했습니다.",
                detected_intents=["HIRING", "DOCUMENT_CHECK", "CONTACT"],
                risk_flags=[],
                approval=ApprovalBlock(
                    required=True,
                    status="PENDING",
                    reason="전문가 전달 전 담당자 승인이 필요합니다.",
                ),
                handoff=HandoffDraft(
                    available=True,
                    package_type=self.package_type,
                    approval_required=False,
                    approval_status="APPROVED",
                    not_for_legal_judgment=False,
                    raw_worker_reply_included=True,
                    full_translation_included=True,
                    message_body_included=True,
                    payload={
                        "package_type": "unsafe_package",
                        "case_type": "stay_extension",
                        "case_summary": {
                            "summary": "체류만료 임박. 여권번호 M12345678 확인됨",
                            "risk_level": "HIGH",
                            "risk_reasons": ["전화번호 010-1234-5678 확인됨"],
                        },
                        "worker_summary": {
                            "masked_worker_id": "worker_***",
                            "worker_id": "worker-demo-raw-001",
                            "worker_name": "Nguyen Van A",
                            "nationality": "Vietnam",
                            "visa_type": "E-9",
                            "stay_expires_at": "2026-05-10",
                        },
                        "document_summary": {
                            "submitted_documents": ["alien_registration"],
                            "missing_documents": ["passport_copy"],
                            "document_raw_text": "OCR 원문",
                        },
                        "contact_summary": {
                            "last_contact_summary": "translated_ko 전문",
                            "message_draft_exists": True,
                            "raw_worker_reply_included": True,
                            "full_translation_included": True,
                            "message_body_included": True,
                        },
                        "evidence": {
                            "citation_ids": ["gov24_stay_extension"],
                            "evidence_log_ids": [],
                            "not_for_legal_judgment": False,
                        },
                        "approval": {"status": "APPROVED"},
                        "worker_reply": "Tôi có hộ chiếu.",
                        "translated_ko": "여권이 있습니다.",
                        "message_body": "여권 사본을 제출해 주세요.",
                        "worker_id": "worker-demo-raw-001",
                        "passport_number": "M12345678",
                        "alien_registration_number": "900101-1234567",
                        "phone": "010-1234-5678",
                    },
                ),
                blocked_reason="",
            )
        }


class FakeRagContextRuntimeAgent:
    async def ainvoke(self, payload, **kwargs):
        del payload
        context = kwargs["context"]
        context.rag_contexts = _safe_rag_contexts_from_records(
            [
                {
                    "chunk_id": "chunk-safe-1",
                    "source_id": "gov24_stay_extension",
                    "title": "체류기간 연장 안내",
                    "doc_type": "official",
                    "evidence_grade": "A",
                    "collection": "workforce_official",
                    "distance": 0.12,
                    "content": "문서 원문 010-1234-5678 M12345678 900101-1234567",
                    "metadata": {
                        "case_type": "stay_extension",
                        "visa_type": "E-9",
                        "worker_id": "worker-demo-raw-001",
                    },
                },
                {
                    "chunk_id": "chunk-safe-1",
                    "source_id": "gov24_stay_extension",
                    "title": "중복 레코드",
                    "doc_type": "official",
                    "evidence_grade": "A",
                    "collection": "workforce_official",
                    "distance": 0.15,
                    "metadata": {"case_type": "stay_extension", "visa_type": "E-9"},
                },
                {
                    "chunk_id": "chunk-disallowed-grade",
                    "source_id": "low_grade_source",
                    "title": "낮은 등급 자료",
                    "doc_type": "official",
                    "evidence_grade": "D",
                    "collection": "workforce_official",
                    "metadata": {"case_type": "stay_extension", "visa_type": "E-9"},
                },
                {
                    "chunk_id": "chunk-disallowed-case",
                    "source_id": "case_record_source",
                    "title": "케이스 기록",
                    "doc_type": "case_record",
                    "evidence_grade": "A",
                    "collection": "workforce_official",
                    "metadata": {"case_type": "stay_extension", "visa_type": "E-9"},
                },
            ]
        )
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="RAG 근거를 확인했습니다.",
                detected_intents=["DOCUMENT_CHECK"],
                risk_flags=[],
                approval=ApprovalBlock(required=True, status="PENDING"),
                handoff=HandoffDraft(available=False),
                rag_contexts=[],
                blocked_reason="",
            )
        }


class FakeNeedsRagBackfillRuntimeAgent:
    async def ainvoke(self, payload, **kwargs):
        del payload, kwargs
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="공식 근거를 확인해야 하는 문서 점검입니다.",
                detected_intents=["DOCUMENT_CHECK"],
                risk_flags=[],
                approval=ApprovalBlock(required=True, status="PENDING"),
                handoff=HandoffDraft(available=False),
                rag_contexts=[],
                blocked_reason="",
            )
        }


class FakeContactArtifactRuntimeAgent:
    async def ainvoke(self, payload, **kwargs):
        del payload
        context = kwargs["context"]
        context.contact_artifacts[CONTACT_ONBOARDING_SUB_AGENT] = {
            "status": "SUCCESS",
            "worker_id": "worker-demo-raw-001",
            "message_purpose": "passport_request",
            "language_code": "vi",
            "korean_text": "여권 사본을 제출해 주세요.",
            "translated_text": "Vui lòng gửi bản sao hộ chiếu.",
            "approval_required": True,
            "sent": False,
            "sent_at": None,
            "citations": [],
            "risk_flags": [],
            "evidence_events": [
                {
                    "event_type": "message_draft_created",
                    "agent_name": "multilingual_contact_agent",
                    "summary": "다국어 메시지 초안을 생성했습니다.",
                    "source_ids": [],
                    "approval_required": True,
                }
            ],
        }
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="다국어 메시지 초안을 준비했습니다.",
                detected_intents=["CONTACT"],
                risk_flags=[],
                approval=ApprovalBlock(required=True, status="PENDING"),
                handoff=HandoffDraft(available=False),
                domain_payload={
                    "contact_subagents": {
                        CONTACT_ONBOARDING_SUB_AGENT: {
                            "status": "SUCCESS",
                            "approval_required": True,
                            "approval_status": "PENDING",
                            "risk_flags": [],
                        }
                    }
                },
                blocked_reason="",
            )
        }


class FakeWorkerReplyArtifactRuntimeAgent:
    async def ainvoke(self, payload, **kwargs):
        del payload
        context = kwargs["context"]
        context.contact_artifacts[WORKER_REPLY_INTERPRETER_SUB_AGENT] = {
            "status": "SUCCESS",
            "worker_id": "worker-demo-raw-001",
            "language_code": "vi",
            "translated_ko": "여권은 있고 사진은 내일 보낼 수 있습니다.",
            "summary_ko": "여권 보유, 사진은 내일 제출 예정",
            "translation_provider": "rule_based",
            "status_update_candidates": [
                {
                    "target_type": "worker_document",
                    "field": "passport_copy",
                    "candidate_status": "SUBMITTED",
                    "confidence": "MEDIUM",
                    "summary": "여권 사본 보유 가능성이 있습니다.",
                    "is_final": False,
                }
            ],
            "approval_required": True,
            "manager_review_required": True,
            "status_applied": False,
            "risk_flags": [],
            "evidence_events": [
                {
                    "event_type": "worker_reply_summarized",
                    "agent_name": "multilingual_contact_agent",
                    "summary": "근로자 답변을 요약하고 상태 업데이트 후보를 생성했습니다.",
                    "source_ids": [],
                    "approval_required": True,
                }
            ],
        }
        return {
            "structured_response": WorkBridgeAgentResponse(
                final_response="근로자 답변 요약과 상태 업데이트 후보를 준비했습니다.",
                detected_intents=["CONTACT"],
                risk_flags=[],
                approval=ApprovalBlock(required=True, status="PENDING"),
                handoff=HandoffDraft(available=False),
                domain_payload={
                    "contact_subagents": {
                        WORKER_REPLY_INTERPRETER_SUB_AGENT: {
                            "status": "SUCCESS",
                            "approval_required": True,
                            "approval_status": "PENDING",
                            "manager_review_required": True,
                            "status_update_candidate_count": 1,
                            "risk_flags": [],
                        }
                    }
                },
                blocked_reason="",
            )
        }


def _mock_contact_rag_tool(payload):
    del payload
    return SimpleNamespace(
        citations=[
            {
                "source_id": "kosha_safety_vi",
                "citation_label": "KOSHA, 외국인 안전교육 자료",
                "title": "외국인 안전교육 자료",
                "publisher": "KOSHA",
                "evidence_grade": "B",
            }
        ],
        risk_flags=[],
    )


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    return factory()


def test_user_request_is_normalized_into_runtime_input() -> None:
    runtime_input = normalize_runtime_input(
        user_request="베트남 근로자에게 안전교육 안내 메시지 작성해줘",
        input_payload={"task_type": "message_draft"},
    )

    assert runtime_input.user_message == "베트남 근로자에게 안전교육 안내 메시지 작성해줘"
    assert runtime_input.input_payload == {"task_type": "message_draft"}
    assert runtime_input.thread_id == runtime_input.request_id


@pytest.mark.asyncio
async def test_runtime_uses_structured_response_from_create_agent_shape() -> None:
    runtime_input = normalize_runtime_input(
        user_message="E-9 근로자 신규 고용 준비해줘",
        user_id="user-1",
        company_id="company-1",
    )

    state = await run_langchain_v1_agent(runtime_input, agent=FakeAgent())
    compat_state = to_foreign_hiring_state(state)

    assert state.structured_response.final_response == "신규 고용 준비 초안입니다."
    assert compat_state.detected_intents == [Intent.HIRING]
    assert len(compat_state.rag_contexts) == 1
    assert runtime_state_store.get(runtime_input.request_id) is not None


@pytest.mark.asyncio
async def test_runtime_preserves_contact_subagent_safe_domain_payload_with_fake_agent(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        contact_agent_module,
        "search_multilingual_contact_rag_tool",
        _mock_contact_rag_tool,
    )
    fake_agent = FakeContactSubAgentRuntimeAgent()
    runtime_input = normalize_runtime_input(
        user_message="베트남 근로자에게 안전교육 안내 초안을 만들고 답변도 해석해줘",
        user_id="user-1",
        company_id="company-1",
        worker_id="worker-demo-raw-001",
        input_payload={"task_type": "message_draft_and_reply_interpretation"},
    )

    state = await run_langchain_v1_agent(runtime_input, agent=fake_agent)
    foreign_state = to_foreign_hiring_state(state)
    domain_payload = state.structured_response.domain_payload
    contact_subagents = domain_payload["contact_subagents"]
    onboarding = contact_subagents["contact_onboarding_subagent"]
    interpreter = contact_subagents["worker_reply_interpreter_subagent"]

    assert isinstance(state.structured_response, WorkBridgeAgentResponse)
    assert isinstance(contact_subagents, dict)
    assert onboarding["status"] == "SUCCESS"
    assert onboarding["approval_required"] is True
    assert onboarding["approval_status"] == "PENDING"
    assert interpreter["status"] == "SUCCESS"
    assert interpreter["approval_required"] is True
    assert interpreter["approval_status"] == "PENDING"
    assert interpreter["manager_review_required"] is True
    assert interpreter["status_update_candidate_count"] >= 1

    domain_payload_json = json.dumps(domain_payload, ensure_ascii=False)
    forbidden_values = [
        "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi.",
        fake_agent.reply_raw["translated_ko"],
        fake_agent.contact_raw["korean_text"],
        fake_agent.contact_raw["translated_text"],
        "worker-demo-raw-001",
        "010-1234-5678",
        "M12345678",
        "900101-1234567",
    ]
    for forbidden in forbidden_values:
        assert forbidden not in domain_payload_json

    assert domain_payload.get("sent") in (None, False)
    assert domain_payload.get("status_applied") in (None, False)
    assert domain_payload.get("expert_handoff_sent") in (None, False)
    assert domain_payload.get("government_submission") in (None, False)
    assert "sent" not in contact_subagents["contact_onboarding_subagent"]
    assert "status_applied" not in contact_subagents["worker_reply_interpreter_subagent"]

    assert state.structured_response.approval.required is True
    assert state.structured_response.approval.status == "PENDING"
    assert foreign_state.approval.required is True
    assert foreign_state.approval.status == "PENDING"
    assert foreign_state.agent_results
    assert foreign_state.agent_results[0]["agent"] == "langchain_v1"
    assert foreign_state.final_response


@pytest.mark.asyncio
async def test_runtime_normalizes_contact_subagent_list_and_removes_raw_fields() -> None:
    runtime_input = normalize_runtime_input(
        user_message="베트남어 메시지와 답변 해석 요약해줘",
        user_id="user-1",
        company_id="company-1",
        worker_id="worker-demo-raw-001",
    )

    state = await run_langchain_v1_agent(
        runtime_input,
        agent=FakeUnsafeContactSubAgentRuntimeAgent(),
    )

    contact_subagents = state.structured_response.domain_payload["contact_subagents"]
    onboarding = contact_subagents[CONTACT_ONBOARDING_SUB_AGENT]
    interpreter = contact_subagents[WORKER_REPLY_INTERPRETER_SUB_AGENT]

    assert isinstance(contact_subagents, dict)
    assert onboarding["status"] == "SUCCESS"
    assert onboarding["approval_status"] == "PENDING"
    assert interpreter["status"] == "SUCCESS"
    assert interpreter["approval_status"] == "PENDING"
    assert interpreter["manager_review_required"] is True
    assert interpreter["status_update_candidate_count"] == 2

    payload_json = json.dumps(state.structured_response.domain_payload, ensure_ascii=False)
    for forbidden in (
        "worker-demo-raw-001",
        "여권 사본을 제출해 주세요.",
        "Vui lòng gửi bản sao hộ chiếu.",
        "Tôi có hộ chiếu.",
        "여권이 있습니다.",
        "010-1234-5678",
        "M12345678",
        "900101-1234567",
    ):
        assert forbidden not in payload_json


@pytest.mark.asyncio
@pytest.mark.parametrize("package_type", [None, "handoff_package"])
async def test_runtime_canonicalizes_handoff_payload_before_persistence(
    package_type: str | None,
) -> None:
    runtime_input = normalize_runtime_input(
        user_message="체류만료 임박 handoff package 초안을 준비해줘",
        user_id="manager-demo",
        company_id="company-demo-001",
        worker_id="worker-demo-raw-001",
    )

    state = await run_langchain_v1_agent(
        runtime_input,
        agent=FakeUnsafeHandoffRuntimeAgent(package_type=package_type),
    )
    foreign_state = to_foreign_hiring_state(state)
    draft = foreign_state.handoff_package_draft

    assert draft["package_type"] == "expert_handoff_draft"
    assert draft["approval_required"] is True
    assert draft["approval"]["status"] == "PENDING"
    assert draft["not_for_legal_judgment"] is True
    assert draft["raw_worker_reply_included"] is False
    assert draft["full_translation_included"] is False
    assert draft["message_body_included"] is False

    payload_json = json.dumps(draft, ensure_ascii=False)
    for forbidden in (
        "Tôi có hộ chiếu.",
        "여권이 있습니다.",
        "여권 사본을 제출해 주세요.",
        "worker-demo-raw-001",
        "Nguyen Van A",
        "Vietnam",
        "M12345678",
        "900101-1234567",
        "010-1234-5678",
        "OCR 원문",
    ):
        assert forbidden not in payload_json

    db = _session()
    result = save_handoff_package_draft(
        db,
        request_id=runtime_input.request_id,
        handoff_package_draft=draft,
        worker_id=runtime_input.worker_id,
        company_id=runtime_input.company_id,
        created_by=runtime_input.user_id,
    )
    db.commit()

    persisted = db.get(HandoffPackageDraft, result["handoff_package_draft_id"])
    approval = db.get(Approval, result["approval_id"])
    assert persisted is not None
    assert persisted.package_type == "expert_handoff_draft"
    assert persisted.status == "PENDING_APPROVAL"
    assert persisted.transferred_at is None
    assert approval is not None
    assert approval.status == "PENDING"

    persisted_json = persisted.package_json
    for forbidden in (
        "Tôi có hộ chiếu.",
        "여권이 있습니다.",
        "여권 사본을 제출해 주세요.",
        "worker-demo-raw-001",
        "M12345678",
        "900101-1234567",
        "010-1234-5678",
    ):
        assert forbidden not in persisted_json


@pytest.mark.asyncio
async def test_runtime_promotes_safe_tool_rag_contexts_when_structured_response_empty() -> None:
    runtime_input = normalize_runtime_input(
        user_message="체류기간 연장 공식 근거를 찾아줘",
        user_id="user-1",
        company_id="company-1",
        worker_id="worker-demo-raw-001",
    )

    state = await run_langchain_v1_agent(
        runtime_input,
        agent=FakeRagContextRuntimeAgent(),
    )
    foreign_state = to_foreign_hiring_state(state)

    assert len(state.structured_response.rag_contexts) == 1
    assert state.structured_response.rag_contexts == foreign_state.rag_contexts
    assert foreign_state.aggregated_output["rag_context_count"] == 1

    context = state.structured_response.rag_contexts[0]
    assert context | {"distance": 0.12} == {
        "source_id": "gov24_stay_extension",
        "title": "체류기간 연장 안내",
        "doc_type": "official",
        "evidence_grade": "A",
        "collection": "workforce_official",
        "chunk_id": "chunk-safe-1",
        "distance": 0.12,
        "case_type": "stay_extension",
        "visa_type": "E-9",
    }

    payload_json = json.dumps(state.structured_response.rag_contexts, ensure_ascii=False)
    for forbidden in (
        "문서 원문",
        "content",
        "metadata",
        "worker-demo-raw-001",
        "010-1234-5678",
        "M12345678",
        "900101-1234567",
        "low_grade_source",
        "case_record_source",
    ):
        assert forbidden not in payload_json


@pytest.mark.asyncio
async def test_runtime_backfills_safe_rag_contexts_when_tool_call_was_omitted(
    monkeypatch,
) -> None:
    from app.agent_runtime.langchain_v1 import runtime as runtime_module

    invoked: dict[str, Any] = {}

    class FakeRetrieveTool:
        def invoke(self, payload):
            invoked.update(payload)
            return {
                "records": [
                    {
                        "chunk_id": "chunk-backfill-1",
                        "source_id": "eps_document_check",
                        "title": "E-9 서류 점검 안내",
                        "doc_type": "official",
                        "evidence_grade": "B",
                        "collection": "workforce_official",
                        "distance": 0.2,
                        "content": "문서 원문 M12345678",
                        "metadata": {"case_type": "ALL", "visa_type": "E-9"},
                    }
                ],
                "approval_required": False,
            }

    monkeypatch.setattr(runtime_module, "retrieve_workforce_materials", FakeRetrieveTool())
    runtime_input = normalize_runtime_input(
        user_message="E-9 서류 누락 여부를 확인해줘",
        user_id="user-1",
        company_id="company-1",
        input_payload={"visa_type": "E-9"},
    )

    state = await run_langchain_v1_agent(
        runtime_input,
        agent=FakeNeedsRagBackfillRuntimeAgent(),
    )
    foreign_state = to_foreign_hiring_state(state)

    assert invoked["query"] == runtime_input.user_message
    assert len(state.structured_response.rag_contexts) == 1
    assert foreign_state.aggregated_output["rag_context_count"] == 1
    assert foreign_state.rag_contexts[0]["source_id"] == "eps_document_check"

    payload_json = json.dumps(foreign_state.rag_contexts, ensure_ascii=False)
    assert "content" not in payload_json
    assert "문서 원문" not in payload_json
    assert "M12345678" not in payload_json


@pytest.mark.asyncio
async def test_runtime_stores_contact_artifact_without_snapshot_exposure() -> None:
    runtime_input = normalize_runtime_input(
        user_message="베트남어 여권 사본 요청 메시지를 준비해줘",
        user_id="user-1",
        company_id="company-1",
        worker_id="worker-demo-raw-001",
    )

    state = await run_langchain_v1_agent(
        runtime_input,
        agent=FakeContactArtifactRuntimeAgent(),
    )

    state_json = state.model_dump_json()
    for forbidden in (
        "여권 사본을 제출해 주세요.",
        "Vui lòng gửi bản sao hộ chiếu.",
    ):
        assert forbidden not in state_json

    artifacts = pop_contact_artifacts(runtime_input.request_id)
    artifact = artifacts[CONTACT_ONBOARDING_SUB_AGENT]
    assert artifact["korean_text"] == "여권 사본을 제출해 주세요."
    assert artifact["translated_text"] == "Vui lòng gửi bản sao hộ chiếu."


@pytest.mark.asyncio
async def test_runtime_stores_worker_reply_artifact_without_snapshot_exposure() -> None:
    worker_reply = "Tôi có hộ chiếu, nhưng ảnh thì ngày mai tôi có thể gửi."
    translated_ko = "여권은 있고 사진은 내일 보낼 수 있습니다."
    runtime_input = normalize_runtime_input(
        user_message="베트남어 답변을 요약하고 상태 후보를 만들어줘",
        user_id="user-1",
        company_id="company-1",
        worker_id="worker-demo-raw-001",
        input_payload={"worker_reply": worker_reply},
    )

    state = await run_langchain_v1_agent(
        runtime_input,
        agent=FakeWorkerReplyArtifactRuntimeAgent(),
    )

    state_json = state.model_dump_json()
    assert worker_reply not in state_json
    assert translated_ko not in state_json

    artifacts = pop_contact_artifacts(runtime_input.request_id)
    artifact = artifacts[WORKER_REPLY_INTERPRETER_SUB_AGENT]
    assert "worker_reply" not in artifact
    assert artifact["translated_ko"] == translated_ko
    assert artifact["status_update_candidates"][0]["is_final"] is False


@pytest.mark.asyncio
async def test_runtime_missing_openai_key_returns_structured_blocked_response(
    monkeypatch,
) -> None:
    from app.agent_runtime.langchain_v1 import runtime as runtime_module
    from app.agent_runtime.langchain_v1.tools import RuntimePreflightError

    async def no_checkpointer():
        return None

    def fail_create_agent(*args, **kwargs):
        raise RuntimePreflightError("OPENAI_API_KEY is required for langchain_v1 runtime")

    monkeypatch.setattr(runtime_module, "get_async_langchain_checkpointer", no_checkpointer)
    monkeypatch.setattr(runtime_module, "create_workbridge_agent", fail_create_agent)
    runtime_input = normalize_runtime_input(
        user_message="E-9 근로자 3명 채용 준비해줘",
        user_id="user-1",
        company_id="company-1",
    )

    state = await run_langchain_v1_agent(runtime_input)
    compat_state = to_foreign_hiring_state(state)

    assert state.structured_response.blocked_reason
    assert compat_state.approval.required is True
    assert compat_state.approval.status == "PENDING"
    assert compat_state.detected_intents == [Intent.HIRING]


def test_production_api_and_runner_do_not_import_custom_graph_workflow() -> None:
    root = Path(__file__).resolve().parents[2]
    runner_source = (root / "backend/app/agent_runtime/runner.py").read_text(encoding="utf-8")
    api_source = (root / "backend/app/api/v1/agent.py").read_text(encoding="utf-8")
    legacy_workflow = "app.agent_runtime." + "graph.workflow"

    assert legacy_workflow not in runner_source
    assert legacy_workflow not in api_source
    assert "get_compiled_app" not in runner_source
    assert "get_compiled_app" not in api_source
