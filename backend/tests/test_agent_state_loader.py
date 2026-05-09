from app.agent_runtime.legacy_graph.nodes.state_loader import (
    InMemoryContextRepository,
    state_loader_node,
)
from app.agent_runtime.schemas import ForeignHiringState


def test_state_loader_populates_normalized_contexts() -> None:
    repo = InMemoryContextRepository(
        companies={
            "company-1": {
                "id": "company-1",
                "name": "테스트 제조",
                "business_number": "123-45-67890",
                "address": "서울시 중구 테스트로 1",
                "region": "서울",
            }
        },
        workers={
            "worker-1": {
                "id": "worker-1",
                "company_id": "company-1",
                "name": "Nguyen Van A",
                "nationality": "Vietnam",
                "preferred_language": "vi",
                "visa_type": "E-9",
                "visa_expires_at": "2026-06-01",
                "phone": "010-1234-5678",
                "passport_number": "M12345678",
            }
        },
        candidates={
            "candidate-1": {
                "id": "candidate-1",
                "company_id": "company-1",
                "name": "Tran Candidate",
                "nationality": "Vietnam",
                "phone": "010-9999-8888",
            }
        },
    )
    state = ForeignHiringState(
        request_id="req-1",
        company_id="company-1",
        worker_id="worker-1",
        candidate_id="candidate-1",
    )

    loaded = state_loader_node(state, repository=repo)

    assert loaded.context_loaded is True
    assert loaded.context_blockers == []
    assert loaded.company_context["id"] == "company-1"
    assert loaded.worker_context["id"] == "worker-1"
    assert loaded.candidate_context["id"] == "candidate-1"


def test_state_loader_returns_structured_blockers_for_missing_context() -> None:
    repo = InMemoryContextRepository()
    state = ForeignHiringState(
        request_id="req-missing",
        company_id="missing-company",
        worker_id="missing-worker",
    )

    loaded = state_loader_node(state, repository=repo)

    assert loaded.context_loaded is False
    assert loaded.company_context == {}
    assert loaded.worker_context == {}
    assert {
        "type": "missing_company",
        "message": "사업장 정보를 찾을 수 없습니다.",
        "severity": "MEDIUM",
        "id": "missing-company",
    } in [blocker.model_dump() for blocker in loaded.context_blockers]
    assert {
        "type": "missing_worker",
        "message": "근로자 정보를 찾을 수 없습니다.",
        "severity": "MEDIUM",
        "id": "missing-worker",
    } in [blocker.model_dump() for blocker in loaded.context_blockers]


def test_state_loader_masks_sensitive_values_in_contexts() -> None:
    repo = InMemoryContextRepository(
        companies={
            "company-1": {
                "id": "company-1",
                "name": "테스트 제조",
                "business_number": "123-45-67890",
                "address": "서울시 중구 테스트로 1",
            }
        },
        workers={
            "worker-1": {
                "id": "worker-1",
                "company_id": "company-1",
                "name": "Nguyen Van A",
                "phone": "010-1234-5678",
                "passport_number": "M12345678",
                "worker_reply": "Tôi có hộ chiếu, ảnh mai gửi",
                "translated_ko": "저는 여권이 있고 사진은 내일 보내겠습니다.",
            }
        },
    )
    state = ForeignHiringState(
        request_id="req-mask",
        company_id="company-1",
        worker_id="worker-1",
    )

    loaded = state_loader_node(state, repository=repo)
    dumped = loaded.model_dump_json()

    assert "010-1234-5678" not in dumped
    assert "M12345678" not in dumped
    assert "Tôi có hộ chiếu" not in dumped
    assert "저는 여권이 있고" not in dumped
    assert loaded.worker_context["phone"] == "[전화번호]"
    assert loaded.worker_context["passport_number"] == "[여권번호]"
    assert "worker_reply" not in loaded.worker_context
    assert "translated_ko" not in loaded.worker_context
