# 최종 시나리오 통합 검증 계획

## Summary

이건 한 명이 혼자 끝까지 구현하는 작업이라기보다, 세 명이 나눠 만든 agent를 “하나의 실제 업무 흐름”으로 합치는 통합 검증입니다.

추천 구조는 `각 agent owner 3명 + 통합 오너 1명 역할`입니다. 사람이 세 명뿐이면 한 명이 통합 오너를 겸하되, 각자 만든 agent의 출력 계약은 각 owner가 책임지는 방식이 맞습니다.

현재 런타임은 routing은 있지만 진짜 병렬 구조는 아닙니다. `executor`가 `required_agents`를 순차 호출하고, 이후 `aggregator`가 결과를 합칩니다. 이번 검증은 우선 순차 구조로 최종 시나리오가 완주되는지 확인하고, 병렬 fan-out은 별도 개선 항목으로 둡니다.

## Team Split

- 담당자 A: 인력 확보 agent
  - 신규 인력 요청서 생성
  - 베트남 E-9 3명 조건 구조화
  - 후보 요건 매칭 결과 생성
  - 출력 계약: `hiring_request`, `candidate_requirements`, `candidate_matches`

- 담당자 B: 다국어 컨택 + 비자·서류 운영 agent
  - 베트남어 서류 요청 메시지 초안 생성
  - Nguyen 체류만료 D-day 계산
  - 누락 서류 탐지
  - 출력 계약: `message_drafts`, `stay_expiry_check`, `document_gaps`

- 담당자 C: 승인·전문가 전달 + 감사 로그·근거 저장 + 통합 검증
  - 담당자 승인 요청 생성
  - 행정사 전달 패키지 초안 생성
  - Evidence Log completeness 검증
  - 내부 데모 화면/API 응답에서 전체 흐름 확인 가능하게 연결
  - 출력 계약: `approval_request`, `expert_handoff_package`, `evidence_events`, `metrics`

## API And Frontend

프론트/API 설계는 건너뛰면 안 됩니다. 백엔드 테스트만 통과하면 “agent 내부가 돌아간다”는 건 알 수 있지만, 실제 사용자가 이 시나리오를 눈으로 확인할 수 있는지는 알 수 없습니다.

API는 기존 `/api/v1/agent/run`을 유지하되, 최종 시나리오 검증에 필요한 상세 응답을 포함해야 합니다.

필수 응답 필드:
- `detected_intents`
- `plan`
- `agent_results`
- `aggregated_output`
- `approval`
- `expert_handoff_package`
- `evidence_events`
- `metrics`
- `final_response`

프론트는 실제 제품 UI를 바로 크게 만들기보다, 먼저 내부 데모 화면을 만듭니다.

내부 데모 화면 구성:
- 입력창: 최종 사용자 문장 실행
- 진행 타임라인: routing, planning, hiring, contact, visa/document, approval, handoff, evidence
- Agent 결과 카드: 인력 확보, 다국어 컨택, 비자·서류, 승인/전달, 감사 로그
- 승인 대기 패널: 자동 실행 없이 `PENDING` 상태 확인
- 행정사 전달 패키지 미리보기
- Evidence Log 테이블
- 성공 지표 테이블: 이미지의 5개 지표 층위별 pass/fail/report-only 표시

## Test Plan

1. Agent contract 테스트
- 각 agent가 자기 출력 계약을 지키는지 개별 pytest로 확인합니다.
- 실패해도 다른 agent 탓을 하지 않도록 agent별 fixture를 고정합니다.

2. 통합 workflow 테스트
- 최종 문장 하나로 `run_workflow()`를 실행합니다.
- 기대 결과:
  - 인력 요청서 생성됨
  - 후보 요건 매칭 있음
  - 베트남어 서류 요청 메시지 초안 있음
  - Nguyen D-day 계산됨
  - 누락 서류 리스트 있음
  - `approval.required=true`
  - `approval.status="PENDING"`
  - 행정사 전달 패키지가 “초안/대기” 상태임
  - Evidence Log 이벤트가 완비됨

3. API smoke 테스트
- `/api/v1/agent/run`에 최종 문장을 POST합니다.
- 응답 JSON에서 프론트가 필요한 모든 필드를 받을 수 있는지 확인합니다.
- 금지 항목 확인:
  - 자동 발송 없음
  - 자동 제출 없음
  - 케이스 완료 처리 없음
  - 법률 판단 없음
  - 비자 가능 여부 확정 없음

4. 내부 데모 화면 테스트
- 브라우저에서 최종 문장을 입력합니다.
- 화면에서 아래를 눈으로 확인합니다.
  - 어떤 agent가 실행됐는지
  - 각 agent가 무엇을 만들었는지
  - 어떤 항목이 승인 대기인지
  - 행정사 전달 패키지에 무엇이 들어갔는지
  - Evidence Log가 어떤 근거와 이벤트를 남겼는지
  - 이미지의 성공 지표가 어디까지 자동 측정됐는지

5. 서비스 성공 지표 포함
- 자동 pass/fail 가능:
  - D-day 탐지 정확도
  - 서류 누락 탐지율
  - RAG Hit@3
  - Citation Accuracy
  - Evidence Grade Pass Rate
  - PII Masking Success Rate
  - Human Approval Required 유지 여부
  - Evidence Log Completeness
  - Trace 재현율

- report-only로 시작:
  - 관리자 승인 통과율
  - 수정 후 승인율
  - 거절 사유 분포
  - Cost per Case
  - 실제 케이스당 처리 시간
  - 이유: 운영 데이터와 승인 이력이 쌓여야 의미 있는 수치가 됩니다.

## How To See It

가장 좋은 확인 방식은 세 단계입니다.

1. 터미널 확인
- `uv run pytest backend/tests/test_agent_final_scenario.py -q`
- 최종 시나리오가 코드상으로 통과하는지 확인합니다.

2. API 확인
- `/api/v1/agent/run`에 최종 문장을 보내고 상세 JSON을 확인합니다.
- 이 단계에서 프론트가 받을 데이터가 충분한지 봅니다.

3. 브라우저 확인
- 내부 데모 화면에서 최종 문장을 실행합니다.
- “생성된 결과물”, “승인 대기”, “전달 패키지”, “감사 로그”, “성공 지표”가 한 화면에서 보여야 합니다.

눈으로 봤을 때 성공 기준:
- 사용자가 요청한 8단계가 타임라인에 모두 보인다.
- 자동 발송/자동 제출은 일어나지 않는다.
- Nguyen의 체류만료 D-day와 누락 서류가 명확히 보인다.
- 담당자 승인 대기 상태가 명확하다.
- 행정사 전달 패키지는 초안으로만 존재한다.
- Evidence Log와 citation이 연결되어 있다.
- 이미지의 성공 지표 중 자동 측정 가능한 항목이 pass/fail로 표시된다.

## Assumptions

- 이번 목표는 최종 시나리오 검증이지, 병렬 실행 구조 개편은 아닙니다.
- 프론트는 실제 제품 화면이 아니라 내부 데모 화면으로 먼저 만듭니다.
- API는 프론트가 검증 화면을 만들 수 있을 정도로 상세 응답을 확장합니다.
- 세 명이 agent별로 나눠 작업하고, 한 명이 통합 오너 역할을 겸합니다.
- 행정사 전달은 실제 전송이 아니라 승인 대기 패키지 생성까지만 검증합니다.
