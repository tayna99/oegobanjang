"""POST /api/v1/runs/stream — 2-phase(/intent→스냅샷→/graph/run) 오케스트레이션 SSE (B3').

rag 서비스는 respx로 목킹한다(fake rag 서버 통합 테스트 원칙 — 실제 rag 프로세스 불필요).
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models.evidence import EvidenceEvent
from app.models.run import Run, RunStep

RAG_BASE = "http://localhost:8100"
PHONE_BY_USER = {"u_owner": "010-0000-0001", "u_other": "010-0000-0009"}


@pytest.fixture()
def seeded(db: Session) -> Session:
    db.execute(
        text(
            """
        INSERT INTO companies (id, name) VALUES ('cmp1','테스트제조'), ('cmp2','다른회사');
        INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
          ('u_owner','010-0000-0001','김대표', now()),
          ('u_other','010-0000-0009','타사대표', now());
        INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
          ('m_owner','cmp1','u_owner','owner','active'),
          ('m_other','cmp2','u_other','owner','active');
        INSERT INTO workers (id, company_id, display_name, nationality, stay_expires_at) VALUES
          ('w1','cmp1','Nguyen Van A','베트남','2026-08-06');
    """
        )
    )
    db.flush()
    return db


@pytest.fixture()
def client(seeded):
    def _override():
        yield seeded

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _login(client: TestClient, phone: str) -> str:
    req = client.post("/api/v1/auth/otp/request", json={"phone": phone})
    code = req.json()["debug_code"]
    verify = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": code})
    return verify.json()["session_token"]


def _auth_headers(client: TestClient, user: str) -> dict:
    return {"Authorization": f"Bearer {_login(client, PHONE_BY_USER[user])}"}


def _sse_body(*frames: tuple[str, dict]) -> bytes:
    text_body = "".join(
        f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n" for name, data in frames
    )
    return text_body.encode("utf-8")


def _parse_backend_sse(text_body: str) -> list[tuple[str, dict]]:
    events = []
    for block in text_body.strip().split("\n\n"):
        if not block.strip():
            continue
        lines = block.splitlines()
        event = next((l.removeprefix("event: ") for l in lines if l.startswith("event: ")), "")
        data = next((l.removeprefix("data: ") for l in lines if l.startswith("data: ")), "{}")
        events.append((event, json.loads(data)))
    return events


@respx.mock
def test_happy_path_records_run_steps_evidence_and_citations(client: TestClient, seeded: Session) -> None:
    respx.post(f"{RAG_BASE}/intent").mock(
        return_value=httpx.Response(
            200,
            json={
                "should_run": True,
                "intent": "visa_expiry",
                "mission": "m2_visa",
                "required_context": ["company", "workers"],
                "approval_required": True,
                "execution_allowed": True,
                "blocked_actions": [],
                "plan_steps": [],
                "entities": {},
            },
        )
    )
    graph_body = _sse_body(
        ("step", {"kind": "thinking", "label": "입력 검증"}),
        ("evidence", {"event_type": "intent_classified", "summary": "ok", "request_id": "r1"}),
        ("evidence", {"event_type": "rag_retrieved", "summary": "근거 3건", "citation_ids": ["E9_STAY_EXT_STEP1"]}),
        (
            "structured",
            {
                "answer": {
                    "final_response": "체류 연장 준비 안내",
                    "citations": [{"source_id": "E9_STAY_EXT_STEP1", "title": "체류연장 1단계", "evidence_grade": "B"}],
                    "missing_evidence": False,
                    "risk_flags": [],
                },
                "citation_catalog": [
                    {
                        "source_id": "E9_STAY_EXT_STEP1",
                        "title": "체류연장 1단계",
                        "evidence_grade": "B",
                    }
                ],
                "approval": {"required": True, "status": "PENDING", "blocked_actions": [], "reason": "승인 필요"},
            },
        ),
        ("done", {}),
    )
    respx.post(f"{RAG_BASE}/graph/run").mock(
        return_value=httpx.Response(200, content=graph_body, headers={"content-type": "text/event-stream"})
    )

    response = client.post(
        "/api/v1/runs/stream",
        json={"company_id": "cmp1", "message": "Nguyen 체류만료 확인해줘"},
        headers=_auth_headers(client, "u_owner"),
    )

    assert response.status_code == 200
    events = _parse_backend_sse(response.text)
    types = [t for t, _ in events]
    assert types == ["run_created", "route", "step", "evidence", "evidence", "structured", "done"]

    run_id = events[0][1]["run_id"]
    assert events[-1][1]["status"] == "waiting_approval"
    assert events[-1][1]["approval_required"] is True

    run = seeded.get(Run, run_id)
    assert run.status == "waiting_approval"
    assert run.case_id is None
    assert "체류 연장" in run.result_summary

    steps = seeded.execute(select(RunStep).where(RunStep.run_id == run_id)).scalars().all()
    assert len(steps) == 1
    assert steps[0].kind == "thinking"

    evidences = seeded.execute(select(EvidenceEvent).where(EvidenceEvent.run_id == run_id)).scalars().all()
    assert len(evidences) == 2
    assert {e.type for e in evidences} == {"intent_classified", "rag_retrieved"}

    citation = seeded.execute(text("SELECT id, grade, company_id FROM citations WHERE id = 'E9_STAY_EXT_STEP1'")).fetchone()
    assert citation is not None
    assert citation.grade == "B"
    assert citation.company_id is None  # B등급은 전역 스코프


@respx.mock
def test_blocked_intent_completes_without_calling_graph_run(client: TestClient, seeded: Session) -> None:
    respx.post(f"{RAG_BASE}/intent").mock(
        return_value=httpx.Response(
            200,
            json={
                "should_run": False,
                "intent": "forbidden",
                "mission": None,
                "required_context": [],
                "approval_required": True,
                "execution_allowed": False,
                "blocked_actions": ["government_portal_submission"],
                "plan_steps": [],
                "entities": {},
            },
        )
    )
    graph_route = respx.post(f"{RAG_BASE}/graph/run").mock(return_value=httpx.Response(200))

    response = client.post(
        "/api/v1/runs/stream",
        json={"company_id": "cmp1", "message": "정부 포털 자동 제출해줘"},
        headers=_auth_headers(client, "u_owner"),
    )

    events = _parse_backend_sse(response.text)
    types = [t for t, _ in events]
    assert types == ["run_created", "route", "done"]
    assert not graph_route.called  # 차단 시 그래프 자체를 호출하지 않는다

    run_id = events[0][1]["run_id"]
    run = seeded.get(Run, run_id)
    assert run.status == "completed"
    assert "forbidden" in run.result_summary


@respx.mock
def test_rag_service_down_marks_run_failed(client: TestClient, seeded: Session) -> None:
    respx.post(f"{RAG_BASE}/intent").mock(side_effect=httpx.ConnectError("refused"))

    response = client.post(
        "/api/v1/runs/stream",
        json={"company_id": "cmp1", "message": "아무 질의"},
        headers=_auth_headers(client, "u_owner"),
    )

    events = _parse_backend_sse(response.text)
    types = [t for t, _ in events]
    assert types == ["run_created", "error"]

    run_id = events[0][1]["run_id"]
    run = seeded.get(Run, run_id)
    assert run.status == "failed"


@respx.mock
def test_redacts_pii_before_persisting_or_calling_rag(client: TestClient, seeded: Session) -> None:
    raw_phone = "010-1234-5678"
    raw_passport = "M12345678"
    raw_message = f"Please check {raw_passport} and call {raw_phone}"
    captured: dict[str, dict] = {}

    def _intent_response(request: httpx.Request) -> httpx.Response:
        captured["intent"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "should_run": True,
                "intent": "visa_expiry",
                "mission": "m2_visa",
                "required_context": [],
                "approval_required": False,
                "execution_allowed": True,
                "blocked_actions": [],
                "plan_steps": [],
                "entities": {},
            },
        )

    def _graph_response(request: httpx.Request) -> httpx.Response:
        captured["graph"] = json.loads(request.content)
        body = _sse_body(
            ("step", {"kind": "thinking", "label": "check", "detail": raw_phone}),
            (
                "evidence",
                {
                    "event_type": "intent_classified",
                    "summary": raw_passport,
                    "metadata": {"echo": raw_phone},
                },
            ),
            (
                "structured",
                {
                    "answer": {
                        "final_response": f"Result for {raw_phone} / {raw_passport}",
                        "citations": [],
                        "missing_evidence": False,
                        "risk_flags": [],
                    },
                    "citation_catalog": [],
                    "approval": {"required": False, "status": "NOT_REQUIRED"},
                },
            ),
            ("done", {}),
        )
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    respx.post(f"{RAG_BASE}/intent").mock(side_effect=_intent_response)
    respx.post(f"{RAG_BASE}/graph/run").mock(side_effect=_graph_response)

    response = client.post(
        "/api/v1/runs/stream",
        json={"company_id": "cmp1", "message": raw_message},
        headers=_auth_headers(client, "u_owner"),
    )

    assert response.status_code == 200
    assert raw_phone not in response.text
    assert raw_passport not in response.text
    assert raw_phone not in captured["intent"]["message"]
    assert raw_passport not in captured["graph"]["message"]
    assert captured["graph"]["thread_id"].startswith("run:")

    run_id = _parse_backend_sse(response.text)[0][1]["run_id"]
    run = seeded.get(Run, run_id)
    assert run is not None
    assert raw_phone not in run.goal_text
    assert raw_passport not in run.goal_text
    assert raw_phone not in (run.result_summary or "")
    assert raw_passport not in (run.result_summary or "")

    step = seeded.execute(select(RunStep).where(RunStep.run_id == run_id)).scalar_one()
    evidence = seeded.execute(select(EvidenceEvent).where(EvidenceEvent.run_id == run_id)).scalar_one()
    assert raw_phone not in (step.detail or "")
    assert raw_passport not in evidence.summary
    assert raw_phone not in (evidence.payload_ref or "")


def test_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/runs/stream", json={"company_id": "cmp1", "message": "질의"})

    assert response.status_code == 401


def test_rejects_run_for_company_without_membership(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs/stream",
        json={"company_id": "cmp1", "message": "질의"},
        headers=_auth_headers(client, "u_other"),
    )

    assert response.status_code == 403


def test_rejects_client_controlled_thread_id(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs/stream",
        json={"company_id": "cmp1", "message": "question", "thread_id": "cmp2:case-other"},
        headers=_auth_headers(client, "u_owner"),
    )

    assert response.status_code == 422
