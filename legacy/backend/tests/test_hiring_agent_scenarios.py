"""
인력 확보 에이전트 시나리오 테스트 (10개)

실제 사업주가 물어볼 만한 자연어 FAQ 형식으로 작성한다.
- route: rag_first_chat 여부
- sources: 정책 문서 RAG 소스 반환 여부
- answer: 관련 키워드 포함 여부
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


HEADERS = {
    "X-Company-Id": "company_001",
    "X-User-Role": "manager",
    "X-User-Id": "manager_001",
}

BASE_PAYLOAD = {
    "companyId": "company_001",
    "date": "2026-05-13",
    "workspaceId": "hiring",
    "activeTab": "today",
}


@pytest.fixture(autouse=True)
def disable_openai_planner(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_chat_rag.OpenAIAgentChatQueryPlanner.enabled",
        lambda self: False,
    )


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def chat(client, message: str, session_id: str, **extra) -> tuple[int, dict]:
    payload = {**BASE_PAYLOAD, "message": message, "sessionId": session_id, **extra}
    resp = client.post("/api/v1/agent/chat", json=payload, headers=HEADERS)
    return resp.status_code, resp.json()


def rag_sources_count(body: dict) -> int:
    return len(body.get("sources", []))


def has_rag_route(body: dict) -> bool:
    return body.get("route") == "rag_first_chat"


# ── S01: E-9 처음 도전 ───────────────────────────────────────────────────────

def test_scenario_01_where_to_start(client):
    """외국인 처음 써보는데 어디서 시작해?"""
    status, body = chat(
        client,
        "외국인 처음 써보는데 어디서 시작해?",
        "hiring-01",
    )

    assert status == 200
    answer = body.get("answer", "")

    assert has_rag_route(body), f"route={body.get('route')}"
    assert rag_sources_count(body) > 0, f"소스 없음 — answer={answer[:200]}"

    assert any(kw in answer for kw in ["고용허가", "내국인", "절차", "신청", "고용센터", "E-9"]), (
        f"핵심 키워드 없음: {answer[:200]}"
    )
    print(f"\n[S01] intent={body.get('normalized_intent')} sources={rag_sources_count(body)}")
    print(f"      answer[:150]={answer[:150]}")


# ── S02: 내국인 구인 의무 ────────────────────────────────────────────────────

def test_scenario_02_native_recruitment(client):
    """내국인 구인 먼저 해야 한다는 게 뭐야?"""
    status, body = chat(
        client,
        "내국인 구인 먼저 해야 한다는 게 뭐야?",
        "hiring-02",
    )

    assert status == 200
    answer = body.get("answer", "")

    assert has_rag_route(body), f"route={body.get('route')}"
    assert rag_sources_count(body) > 0, f"소스 없음 — answer={answer[:200]}"

    assert any(kw in answer for kw in ["내국인", "구인", "고용센터", "노력", "기간"]), (
        f"내국인 구인 키워드 없음: {answer[:200]}"
    )
    print(f"\n[S02] intent={body.get('normalized_intent')} sources={rag_sources_count(body)}")
    print(f"      answer[:150]={answer[:150]}")


# ── S03: 고용허가서 발급 ─────────────────────────────────────────────────────

def test_scenario_03_employment_permit(client):
    """고용허가서 어디서 받아?"""
    status, body = chat(
        client,
        "고용허가서 어디서 받아?",
        "hiring-03",
    )

    assert status == 200
    answer = body.get("answer", "")

    assert has_rag_route(body), f"route={body.get('route')}"
    assert rag_sources_count(body) > 0, f"소스 없음 — answer={answer[:200]}"

    assert any(kw in answer for kw in ["고용허가서", "고용센터", "발급", "신청"]), (
        f"고용허가서 키워드 없음: {answer[:200]}"
    )
    print(f"\n[S03] intent={body.get('normalized_intent')} sources={rag_sources_count(body)}")
    print(f"      answer[:150]={answer[:150]}")


# ── S04: E-9 허용 업종 ──────────────────────────────────────────────────────

def test_scenario_04_allowed_industries(client):
    """E-9 처음인데 전체 과정 어떻게 돼? 우리 업종 돼?"""
    status, body = chat(
        client,
        "E-9 처음인데 전체 과정 어떻게 돼? 우리 업종 돼?",
        "hiring-04",
    )

    assert status == 200
    answer = body.get("answer", "")

    assert has_rag_route(body), f"route={body.get('route')}"
    assert rag_sources_count(body) > 0, f"소스 없음 — answer={answer[:200]}"

    assert any(kw in answer for kw in ["업종", "허용", "E-9", "제조", "농업", "고용허가", "절차"]), (
        f"허용업종/절차 키워드 없음: {answer[:200]}"
    )
    print(f"\n[S04] intent={body.get('normalized_intent')} sources={rag_sources_count(body)}")
    print(f"      answer[:150]={answer[:150]}")


# ── S05: 표준근로계약서 ──────────────────────────────────────────────────────

def test_scenario_05_labor_contract(client):
    """외국인 직원이랑 계약서 쓸 때 어떻게 해?"""
    status, body = chat(
        client,
        "외국인 직원이랑 계약서 쓸 때 어떻게 해? 표준근로계약서 있어?",
        "hiring-05",
    )

    assert status == 200
    answer = body.get("answer", "")

    assert has_rag_route(body), f"route={body.get('route')}"
    assert rag_sources_count(body) > 0, f"소스 없음 — answer={answer[:200]}"

    assert any(kw in answer for kw in ["근로계약", "표준", "임금", "계약", "근무"]), (
        f"근로계약서 키워드 없음: {answer[:200]}"
    )
    print(f"\n[S05] intent={body.get('normalized_intent')} sources={rag_sources_count(body)}")
    print(f"      answer[:150]={answer[:150]}")


# ── S06: 취업교육 ────────────────────────────────────────────────────────────

def test_scenario_06_entry_education(client):
    """취업교육 어디서 받아?"""
    status, body = chat(
        client,
        "취업교육 어디서 받아?",
        "hiring-06",
    )

    assert status == 200
    answer = body.get("answer", "")

    assert has_rag_route(body), f"route={body.get('route')}"
    assert rag_sources_count(body) > 0, f"소스 없음 — answer={answer[:200]}"

    assert any(kw in answer for kw in ["취업교육", "교육", "입국", "한국산업인력공단", "배치"]), (
        f"취업교육 키워드 없음: {answer[:200]}"
    )
    print(f"\n[S06] intent={body.get('normalized_intent')} sources={rag_sources_count(body)}")
    print(f"      answer[:150]={answer[:150]}")


# ── S07: 비자 신청 절차 ──────────────────────────────────────────────────────

def test_scenario_07_visa_procedure(client):
    """고용허가서 받은 다음에 비자 신청은 어떻게 해?"""
    status, body = chat(
        client,
        "고용허가서 받은 다음에 비자 신청은 어떻게 해?",
        "hiring-07",
    )

    assert status == 200
    answer = body.get("answer", "")

    assert has_rag_route(body), f"route={body.get('route')}"
    assert rag_sources_count(body) > 0, f"소스 없음 — answer={answer[:200]}"

    assert any(kw in answer for kw in ["사증", "비자", "발급", "입국", "고용허가", "절차"]), (
        f"비자신청 키워드 없음: {answer[:200]}"
    )
    print(f"\n[S07] intent={body.get('normalized_intent')} sources={rag_sources_count(body)}")
    print(f"      answer[:150]={answer[:150]}")


# ── S08: 행정사 인력 요청 초안 ───────────────────────────────────────────────

def test_scenario_08_hiring_checklist(client):
    """행정사한테 뭐 보내야 해?"""
    status, body = chat(
        client,
        "행정사한테 뭐 보내야 해? E-9 신규 고용 준비 중이야",
        "hiring-08",
    )

    assert status == 200
    answer = body.get("answer", "")

    assert body.get("route") in ("rag_first_chat", "unsupported"), (
        f"route={body.get('route')}"
    )
    assert answer, "빈 답변"
    print(f"\n[S08] intent={body.get('normalized_intent')} route={body.get('route')} "
          f"approval={body.get('approval_required')}")
    print(f"      answer[:150]={answer[:150]}")


# ── S09: 사업장 변경 후 재채용 ───────────────────────────────────────────────

def test_scenario_09_replacement_after_transfer(client):
    """외국인 직원 나가고 다시 뽑을 수 있어?"""
    status, body = chat(
        client,
        "외국인 직원 나가고 다시 뽑을 수 있어?",
        "hiring-09",
    )

    assert status == 200
    answer = body.get("answer", "")

    assert has_rag_route(body), f"route={body.get('route')}"
    assert rag_sources_count(body) > 0, f"소스 없음 — answer={answer[:200]}"

    assert any(kw in answer for kw in ["사업장", "변경", "신규", "고용허가", "재신청", "절차", "이직"]), (
        f"사업장변경 후 재채용 키워드 없음: {answer[:200]}"
    )
    print(f"\n[S09] intent={body.get('normalized_intent')} sources={rag_sources_count(body)}")
    print(f"      answer[:150]={answer[:150]}")


# ── S10: H-2 방문취업 ────────────────────────────────────────────────────────

def test_scenario_10_h2_visiting(client):
    """뽑으려면 얼마나 걸려? H-2 방문취업 비자는 달라?"""
    status, body = chat(
        client,
        "뽑으려면 얼마나 걸려? H-2 방문취업 비자는 절차가 달라?",
        "hiring-10",
    )

    assert status == 200
    answer = body.get("answer", "")

    assert has_rag_route(body), f"route={body.get('route')}"
    assert rag_sources_count(body) > 0, f"소스 없음 — answer={answer[:200]}"

    assert any(kw in answer for kw in ["H-2", "방문취업", "고용허가", "절차", "E-9"]), (
        f"H-2 방문취업 키워드 없음: {answer[:200]}"
    )
    print(f"\n[S10] intent={body.get('normalized_intent')} sources={rag_sources_count(body)}")
    print(f"      answer[:150]={answer[:150]}")
