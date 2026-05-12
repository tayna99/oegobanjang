# WorkBridge progressive 문서 인덱스

이 폴더는 WorkBridge가 초기 RAG/Agent Runtime 실험에서 Daily Briefing 기반 운영 챗봇까지 넘어온 과정을 모아둔 작업 기록이다. (원문 기록을 지우지 않고, 어떤 파일을 어떤 순서로 읽으면 되는지 정리한 안내 문서다.)

## 한눈에 보는 흐름

```txt
2026-05-02~03  초기 방향성 / RAG thin slice / phase 결정
      ↓
2026-05-04     schema, state machine, evidence, guardrail 정리
      ↓
2026-05-05     Notion 실행 단위를 mission 구조로 재해석
      ↓
2026-05-06     Mission 001~013 완료 상태와 테스트 방법 정리
      ↓
2026-05-09     Workforce RAG, LangChain v1 runtime, approval/outbox/checkpoint 정리
      ↓
2026-05-10     durable checkpoint, frontend mission, legacy_graph 삭제, push/PR blocker 정리
      ↓
2026-05-13     Daily Briefing MVP, RAG-first chat, 다국어 챗봇 테스트 정리
```

## 빠른 결론

현재까지의 큰 결론은 아래와 같다.

- WorkBridge는 비자 대행 자동화가 아니라 외국인 고용 운영 리스크를 먼저 발견하고 정리하는 OS다.
- 인력확보 agent는 후보 추천기가 아니라 채용 전 절차, 서류, 근거, 승인 필요 작업을 정리하는 agent다.
- RAG는 답변 장식이 아니라 공식 근거와 절차를 찾는 층이다.
- LLM은 자연어 구조화, 요약, 초안 생성, 설명을 맡되 법률 판단/자동 제출/자동 발송은 하지 않는다.
- Human Approval은 메시지 발송, 전문가 전달, 상태 완료, 대외 제출 전 마지막 게이트다.
- 2026-05-13 기준으로 Daily Briefing과 RAG-first chat은 merge된 1차 구현이 있고, semantic orchestrator v2와 다국어 답변 품질 개선은 로컬 WIP다.

## 파일별 역할

| 파일 | 역할 | 먼저 볼 때의 포인트 |
|---|---|---|
| `history.md` | 2026-05-02~03 초기 의사결정 기록 | 왜 후보 추천이 아니라 절차/근거/승인 중심 제품으로 잡았는지 |
| `2026-05-04.md` | schema/state/evidence/guardrail 정리 | 공통 JSON 계약, 상태 머신, Evidence Log, Guardrail as Code |
| `2026-05-05.md` | Notion 실행 단위와 mission 구조 비교 | Mission 001 acceptance와 completed mission 전환 |
| `2026-05-06.md` | Mission 001~013 완료 상태 요약 | active mission이 비어 있는 이유와 다음 제품화 gap |
| `execution(0506).md` | 2026-05-06 기준 실행 테스트 방법 | backend/eval/frontend/API 수동 검증 순서 |
| `진행상황.md` | 2주차 RAG / 3주차 판단 체인 진행 정리 | RAG 구축, LLM 판단 체인, Mission 008~013 의미 |
| `2026-05-09.md` | Workforce RAG와 LangChain v1 전환 대형 기록 | raw ingest, retrieval eval, LangChain runtime, approval/outbox/checkpoint |
| `2026-05-10.md` | durable checkpoint와 frontend mission 완료 기록 | checkpoint, resume 제한, metrics, frontend routes, legacy_graph 삭제 |
| `2026-05-13.md` | Daily Briefing/RAG-first chat/다국어 테스트 기록 | PR #5 merge, semantic orchestrator v2 WIP, 다국어 guardrail 결과 |

## 목적별 읽기 순서

### 1. 제품 방향만 빠르게 알고 싶을 때

1. `history.md`
2. `2026-05-05.md`
3. `2026-05-13.md`

이 순서로 보면 "왜 이 제품을 만들었는가"에서 "현재 어떤 사용자 경험까지 왔는가"까지 빠르게 이어진다.

### 2. RAG와 검색 품질 흐름을 보고 싶을 때

1. `history.md`
2. `진행상황.md`
3. `2026-05-09.md`

이 순서로 보면 thin slice, chunking/embedding/vector DB, raw official source 기준 eval까지 연결된다.

### 3. Agent Runtime과 승인/Evidence 구조를 보고 싶을 때

1. `2026-05-04.md`
2. `2026-05-06.md`
3. `2026-05-09.md`
4. `2026-05-10.md`

이 순서로 보면 schema/state/evidence 계약에서 LangChain v1 runtime, approval resume, durable checkpoint까지 이어진다.

### 4. 현재 Daily Briefing / 챗봇 상태를 보고 싶을 때

1. `2026-05-10.md`
2. `2026-05-13.md`

이 순서로 보면 dashboard skeleton에서 Daily Briefing MVP와 RAG-first chat으로 넘어온 흐름이 보인다.

### 5. 실제로 실행해보고 싶을 때

1. `execution(0506).md`
2. `2026-05-13.md`

`execution(0506).md`는 오래된 실행 절차도 포함한다. 현재 Daily Briefing/RAG-first chat 검증은 `2026-05-13.md`의 `/api/v1/agent/chat` 테스트 기록을 같이 봐야 한다.

## 날짜별 핵심 요약

### 2026-05-04

Codex CLI와 작업 환경을 점검하고, WorkBridge runtime이 따라야 할 공통 계약을 정리했다. (공통 JSON schema, state machine, Evidence Log, Guardrail as Code가 이 날짜의 중심이다.)

핵심 키워드:

- `docs/SCHEMA_CONTRACT.md`
- `docs/STATE_MACHINE.md`
- Evidence Log / Audit Log
- Guardrail as Code
- 자동 발송/제출 금지

### 2026-05-05

Notion에 있던 실행 단위를 현재 repo의 `missions/*` 구조로 다시 해석했다. (이때부터 과거 phase 중심이 아니라 mission 중심으로 진행 상태를 판단한다.)

핵심 키워드:

- Mission 001 Agent Runtime acceptance
- `missions/completed/001~013`
- hiring_agent / quota_tool
- frontend dashboard skeleton
- 다음 제품화 후보 분리

### 2026-05-06

Mission 001~013이 완료된 상태라는 점을 정리하고, 실행 테스트 방법을 별도 문서로 남겼다. (active mission이 비어 있다는 것은 작업이 끝났다는 뜻이 아니라, 다음 제품화 gap을 새 mission으로 잘라야 한다는 뜻이다.)

핵심 키워드:

- active mission 없음
- completed mission 001~013
- provider 운영 호출
- DB 영속 저장
- source depth collection
- frontend build

### 2026-05-09

Workforce RAG와 LangChain v1 runtime 전환이 크게 진행된 날이다. (raw ingest, retrieval eval, structured output, custom graph 격리, approval/outbox/checkpoint/metrics까지 범위가 넓다.)

핵심 키워드:

- raw HTML/PDF/JSONL ingest
- seed RAG에서 official raw source 기준으로 전환
- Workforce Vector DB
- LangChain v1 `create_agent`
- approval/outbox/checkpoint/metrics
- CI workflow repair

### 2026-05-10

LangChain runtime을 durable checkpoint 기반으로 보강하고, frontend mission을 completed 상태로 정리했다. (승인 이후에도 외부 발송이 아니라 내부 상태 전이까지만 허용하는 원칙을 다시 고정했다.)

핵심 키워드:

- `langgraph-checkpoint-sqlite`
- `langchain_agent_checkpoints`
- approval resume internal action only
- worker_name lookup
- legacy_graph 삭제
- frontend route/page skeleton

### 2026-05-13

Daily Briefing MVP와 RAG-first agent chat이 merge됐고, 그 위에 semantic orchestrator v2 로컬 수정이 진행됐다. 다국어 메시지 요청도 실제 API로 테스트했다. (다국어 intent 감지와 즉시 발송 guardrail은 작동하지만, 베트남어/태국어 초안이 한국어로 나오는 문제와 답장 원문 없는 요약 문제가 남았다.)

핵심 키워드:

- PR #5 merge
- `/api/v1/agent/chat`
- RAG-first chat
- semantic orchestrator v2
- `document_request_message`
- 다국어 초안 생성
- 즉시 발송 guardrail

## 현재 상태 구분

### Git으로 고정된 것

- Daily Briefing MVP workflow
- RAG-first agent chat 1차 구현
- PR #5 merge
- 2026-05-09~10의 LangChain runtime / frontend mission 관련 주요 커밋 기록

### 로컬 WIP로 남은 것

- semantic orchestrator v2 추가 수정
- OpenAI/Ollama provider 설정 확장
- 다국어/자연어 테스트 보강
- `2026-05-13.md`와 이 인덱스 문서

### 제품화 gap

- 다국어 target language를 안정적으로 추출하고 실제 답변 언어에 반영
- 근로자 답장 요약 intent 분리와 원문 필수 guardrail
- Evidence Log append-only / citation 본문 검증 / chunk snapshot 같은 hardening
- approval/outbox 기반 실제 외부 전달 전 단계 설계
- frontend 실제 API 상태와 사용자 흐름 검증

## 문서 관리 규칙

- 날짜별 작업은 `YYYY-MM-DD.md`에 쓴다.
- 실행 방법만 따로 분리해야 할 때는 `execution(날짜).md`처럼 둔다.
- 전체 흐름이나 누적 상태는 이 `00_INDEX.md`와 `진행상황.md`를 갱신한다.
- 커밋된 일과 로컬 WIP는 섞어 쓰지 않는다. (나중에 실제 완료 상태를 착각하지 않기 위해서다.)
- 한글 문서는 PowerShell에서 `Get-Content -Encoding utf8`로 다시 읽어 깨짐 여부를 확인한다.

## 다음에 정리하면 좋은 것

- `진행상황.md`는 일부 내용이 앞부분과 뒷부분에서 반복된다. 다음 정리 때는 "요약 / 근거 / 현재 판정 / 남은 일" 구조로 한 번 더 압축하면 좋다.
- `execution(0506).md`는 2026-05-06 기준이라 최신 Daily Briefing/RAG-first chat 실행 방법을 별도 섹션으로 보강하면 좋다.
- `2026-05-09.md`는 하루 기록 안에 중간 백업과 최종 커밋이 모두 들어 있어 길다. 필요하면 "요약판"을 별도 파일로 만들고 원문은 상세 증거로 남기는 방식이 좋다.
