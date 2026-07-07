"""
인력 확보 에이전트 시나리오 진단 스크립트
pytest assertion 없이 실제 응답을 그대로 출력한다.
"""
from __future__ import annotations
import sys
import json

# monkeypatch를 위해 직접 임포트
sys.path.insert(0, ".")

from unittest.mock import patch
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

SCENARIOS = [
    ("S01", "E-9 신규 고용 전체 절차",
     "E-9 비자로 외국인 처음 고용하려면 어떤 절차를 밟아야 해?"),
    ("S02", "내국인 구인노력 기간·방법",
     "외국인 고용하기 전에 내국인 구인노력을 얼마나, 어떻게 해야 해?"),
    ("S03", "고용허가서 발급 신청",
     "고용허가서 발급 신청을 어디서 어떻게 해야 해?"),
    ("S04", "E-9 허용 업종 확인",
     "E-9 비자 근로자가 일할 수 있는 업종이 어디야? 우리 업종이 허용되는지 확인하고 싶어"),
    ("S05", "표준근로계약서 작성",
     "외국인 근로자 표준근로계약서 어떻게 작성해? 포함해야 할 내용이 뭐야?"),
    ("S06", "취업교육 및 입국 후 절차",
     "E-9으로 새로 입국한 외국인 근로자 취업교육을 어디서, 얼마나 받아야 해?"),
    ("S07", "사증발급인정서 신청",
     "고용허가서 받은 다음에 비자 신청은 어떻게 해? 사증발급인정서 절차가 어떻게 돼?"),
    ("S08", "행정사 인력 요청서 초안",
     "E-9 신규 고용 준비 중인데 행정사한테 전달할 인력 요청 체크리스트 초안 만들어줘"),
    ("S09", "사업장 변경 후 재채용",
     "E-9 근로자가 사업장 변경 신청을 해서 나갔어. 그 자리에 새 사람 다시 뽑으려면 어떻게 해?"),
    ("S10", "H-2 방문취업 vs E-9",
     "H-2 방문취업 비자 가진 외국인도 고용할 때 E-9처럼 고용허가서 받아야 해? 절차가 달라?"),
]

DIVIDER = "─" * 70


def run():
    with patch(
        "app.services.agent_chat_rag.OpenAIAgentChatQueryPlanner.enabled",
        new=lambda self: False,
    ):
        client = TestClient(create_app())

        print(f"\n{'='*70}")
        print("  인력 확보 에이전트 시나리오 진단 보고서")
        print(f"{'='*70}\n")

        results = []

        for sid, title, message in SCENARIOS:
            payload = {
                **BASE_PAYLOAD,
                "message": message,
                "sessionId": f"diag-{sid.lower()}",
            }
            resp = client.post("/api/v1/agent/chat", json=payload, headers=HEADERS)
            body = resp.json()

            route = body.get("route", "N/A")
            intent = body.get("normalized_intent", "N/A")
            sources = body.get("sources", [])
            source_labels = body.get("source_labels", [])
            answer = body.get("answer", "")
            approval = body.get("approval_required", False)
            tool_calls = body.get("tool_calls", [])
            actions = body.get("actions", [])

            rag_ok = route == "rag_first_chat"
            source_ok = len(sources) > 0

            results.append({
                "id": sid,
                "title": title,
                "status": resp.status_code,
                "route": route,
                "intent": intent,
                "rag_ok": rag_ok,
                "source_count": len(sources),
                "source_ids": [s.get("citation_id", s.get("source_id", "?")) for s in sources[:3]],
                "source_labels": source_labels[:3],
                "answer_preview": answer[:200],
                "approval_required": approval,
                "tools": [t.get("name") for t in tool_calls[:2]],
                "action_count": len(actions),
            })

            rag_mark = "OK" if rag_ok else "NG"
            src_mark = "OK" if source_ok else "NG"

            print(f"[{sid}] {title}")
            print(f"  질문: {message[:60]}...")
            print(f"  HTTP: {resp.status_code}  |  Route: {route}  |  Intent: {intent}")
            print(f"  RAG라우트 {rag_mark}  |  소스 {src_mark}({len(sources)}개)  |  승인필요: {approval}")
            if source_labels:
                print(f"  소스라벨: {source_labels[:3]}")
            if tool_calls:
                print(f"  도구호출: {[t.get('name') for t in tool_calls[:2]]}")
            print(f"  답변(앞200자): {answer[:200]}")
            print(DIVIDER)

        # 요약
        total = len(results)
        rag_pass = sum(1 for r in results if r["rag_ok"])
        src_pass = sum(1 for r in results if r["source_count"] > 0)
        status_pass = sum(1 for r in results if r["status"] == 200)

        print(f"\n{'='*70}")
        print("  요약")
        print(f"{'='*70}")
        print(f"  HTTP 200 성공:       {status_pass}/{total}")
        print(f"  RAG 라우트 확인:      {rag_pass}/{total}")
        print(f"  소스 반환 확인:       {src_pass}/{total}")
        print()

        intent_map = {}
        for r in results:
            intent_map.setdefault(r["intent"], []).append(r["id"])
        print("  [의도 분류 결과]")
        for intent, ids in intent_map.items():
            print(f"    {intent:35s} → {', '.join(ids)}")

        print()
        print("  [소스 미반환 시나리오]")
        for r in results:
            if r["source_count"] == 0:
                print(f"    {r['id']} {r['title']}")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    run()
