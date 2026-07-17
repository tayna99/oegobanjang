# 백엔드 접속점 계획 (M6) — rag 서비스화 · backend 오케스트레이션 · 프론트 진입점

> ROADMAP "백엔드 접속점 (이후 — 별도 계획)"의 그 별도 계획이다. M5(RAG 인제스천 파이프라인,
> 2026-07-17 완료)가 만든 서버측 부품을 실제 제품 루프(브리핑→케이스시트→초안→승인)에 결선한다.
> 발송 어댑터·알림톡은 계속 범위 밖(`docs/MESSAGING_CHANNELS.md` §5). HWP 파서도 범위 밖(M5 주석).

## 0. 전제와 제약

| 사실 | 결과 |
|---|---|
| `backend/` = Python 3.14 핀(uuid7), `rag/` = 3.12~3.13 핀(langchain 스택) | **한 프로세스로 합칠 수 없다** — rag는 별도 서비스로 뜬다. langchain 스택의 3.14 지원이 확정되면 그때 병합 재검토 |
| AGENTS.md §2: RAG=근거 검색 / DB=상태 / LLM=구조화·초안 | 상태 기록(evidence_events·citations·runs)의 주인은 **backend**. rag는 검색·생성만 하고 상태를 쓰지 않는다 |
| ROADMAP:192 "인증 principal·본인확인·delegation 검증 전에는 승인 결정 endpoint를 만들지 않는다" | 승인 결선(B6)은 인증(B5) **이후**로 강제 |
| ARCHITECTURE.md §5 + `src/lib/runEngine.ts:11` "executeRun 시그니처와 RunConfig 인터페이스는 실 LLM 백엔드로 교체되어도 바뀌지 않아야 한다" | 프론트 교체는 **공급원 교체**이지 인터페이스 교체가 아니다 |
| MVP는 오프라인 데모가 핵심 가치 | mock은 삭제하지 않는다 — `VITE_API_BASE` 미설정이면 지금 동작 그대로(영구 fallback) |

## 1. 목표 토폴로지

```txt
src/ (Vite :5173)
  │  fetch/SSE — VITE_API_BASE 설정 시에만
  ▼
backend/ (FastAPI :8000, py3.14, PG :55432)     ← 프론트의 유일한 접속점
  │  ① run 오케스트레이션(runs·run_steps 기록)
  │  ② rag_retrieved → evidence_events 영속화
  │  ③ RagCitation → citations 테이블 upsert → 근거 라이브러리 서빙
  │  httpx (RAG_SERVICE_URL)
  ▼
rag/ (FastAPI :8100, py3.13, pgvector :55433)   ← 내부 전용(backend만 호출)
  │  /retrieve (3버킷 검색) · /agent/run (create_agent SSE) · /health (preflight)
  ▼
pgvector (workforce_official 945 · workforce_templates 38)
```

프론트가 rag 서비스를 직접 치지 않는 이유: 상태 기록 일관성(경계 원칙), CORS·인증 표면 단일화,
rag는 인증 개념이 없는 내부 부품이기 때문이다.

## 2. 단계 (태스크 1개 = 세션 1개)

### B1 — rag 서비스화 (`rag/src/oe_rag/api.py`) · L2 · ✅ 완료 (2026-07-17)
- FastAPI 앱 추가 (`uv run uvicorn oe_rag.api:app --port 8100`):
  - `GET /health` → `preflight_pgvector()` (컬렉션 존재·비어있지 않음)
  - `POST /retrieve` `{query, case_type, sub_agent, visa_type, top_k}` → 3버킷 결과 + `rag_retrieved` 페이로드(해시·source_ids·grades — 원문 없음). 로컬 JSONL 이벤트도 계속 남긴다
  - `POST /agent/run` `{query, case_type, thread_id}` → **SSE**: LangGraph 스트림(`stream_mode="updates"`)을 스텝 이벤트로 중계, 마지막에 `RagAnswer` structured 이벤트
- 오프라인 테스트: `OfflineEchoChatModel`로 SSE 계약 스모크(키 불필요), CI rag 잡에 추가
- DoD: `uv run pytest` 그린, `curl /health` OK, SSE 스모크에서 step→structured 순서 보장

**구현 노트**:
- `astream(stream_mode="updates")` 실측 확인 — 노드는 `model`(AIMessage, tool_calls 있으면 도구 호출 직전)과 `tools`(ToolMessage, 검색 결과)만 나온다. `model` 노드에서 tool_calls가 근거검색 도구(`retrieve_workforce_materials`/`search_policy_documents`/`search_multilingual_contact_materials`)면 `kind="thinking"`, `RagAnswer` 호출이면 step으로 안 보내고 최종 `structured` 이벤트로 처리. `tools` 노드는 `retrieved_count`로 `missing_evidence`면 `kind="guardrail"`, 아니면 `kind="tool_call"`로 매핑.
- `POST /agent/run`의 `model` 의존성은 `Depends(get_chat_model)`로 주입 — 기본은 `None`(→ `ChatOpenAI` 폴백), 테스트는 `app.dependency_overrides[get_chat_model]`로 `OfflineEchoChatModel`을 꽂아 키 없이 SSE 계약을 검증한다(`tests/test_api.py`, pgvector 마커).
- 부가 발견: `create_agent`의 기본 `InMemorySaver`가 커스텀 `response_format`(RagAnswer)을 msgpack 체크포인트에 저장할 때 "등록되지 않은 타입, 향후 버전에서 차단 예정" 경고를 냈다 — `JsonPlusSerializer(allowed_msgpack_modules=[RagAnswer])`로 명시 허용해 해결(`agent/factory.py:_default_checkpointer`). `with_msgpack_allowlist()`를 permissive 기본값에 체이닝하면 조기 반환(no-op)되는 라이브러리 함정이 있어 생성자에 직접 전달해야 한다.
- CI `rag` 잡 마지막에 실제 `uvicorn` 기동 후 `curl /health`·`curl /retrieve` 스모크 추가(OPENAI_API_KEY 불필요 경로만 — `/agent/run`은 오프라인 dependency override가 pytest 쪽에만 있어 CI 라이브 서버 스모크에서는 검증하지 않음, 후속 B2에서 실제 통합 시 재검토).

### B2 — backend RAG 클라이언트 + 근거 영속화 (읽기 전용부터) · L2
- `backend/app/services/rag_client.py`: httpx로 rag 서비스 호출(`RAG_SERVICE_URL` 설정, 기본 `http://localhost:8100`). rag 다운 시 503 명시(fallback 검색 금지 — RAG_STRATEGY 런타임 경계)
- `rag_retrieved` 페이로드 → `evidence_events` INSERT (append-only, 트리거가 수정·삭제 차단)
- RagCitation(A/B/E) → `citations` upsert. **등급 매핑 정본**: rag `evidence_grade` A→A, B→B, E→E. C는 rag에 없음(정의만 유지), D/F는 서버가 아예 주지 않지만 backend도 재차 거른다(이중 방어)
- `GET /api/v1/citations` — 프론트 `CitationRecord` 형태(`{id, grade, title, source, updatedAt, status}`)로 서빙. `status`는 파생(A·B→official, E→internal, retrieved_at 오래됨→stale)
- DoD: backend pytest에 rag_client 목킹 테스트 + citations API 계약 테스트(스키마가 src/types.ts와 일치)

### B3 — backend runs API + SSE 프록시 · L3
- `POST /api/v1/runs` `{caseId, mode, query}` → run 레코드 생성(models/run.py), RunConfig JSON 반환
  (runKey·agent·evidenceRef·autonomyLabel·question·altLabel — steps는 비움)
- `GET /api/v1/runs/{run_id}/stream` → rag `/agent/run` SSE를 구독하며:
  ① 스텝을 **프론트 RunStep 계약 그대로**(`{kind, label, detail}`) 재발행 ② run_steps 기록
  ③ rag_retrieved → evidence_events ④ 종료 시 citations upsert + 승인 대기 생성(mode=approval)
- **RunStep kind 매핑 정본** (rag 스트림 → 프론트 5종):
  | rag 이벤트 | RunStep.kind |
  |---|---|
  | 모델 추론 시작/계속 | `thinking` |
  | `retrieve_workforce_materials` 등 tool 실행 | `tool_call` |
  | D/F 차단·`MISSING_EVIDENCE`·금지 판단 차단 | `guardrail` |
  | 행정사 전달 패키지 준비 | `handoff` |
  | 재검색/질의 재작성 | `replan` |
- DoD: SSE 통합 테스트(fake rag 서버), run_steps·evidence_events 기록 검증, `writesData` 런의 owner 차단 규칙 유지

### B4 — 프론트 진입점 (읽기 전용: citations + 런 스트리밍) · L3
§3에 상세. DoD: `VITE_API_BASE` 미설정 시 기존 419 테스트 전부 그린(무변경 동작),
설정 시 근거 라이브러리·런 타임라인이 backend에서 온다. `npm run verify` 그린.

### B5 — 인증 결선 · L3
- backend `auth.py`(이미 존재) ↔ 프론트 로그인/세션. principal 없이는 쓰기 API 전부 401
- DoD: 미인증 시 승인·run 생성 403/401, 인증 후 정상

### B6 — 승인 결선 (쓰기) · L3
- `approvalStore.decide()` → `POST /api/v1/approvals/{id}/decide` (**이미 있는 approvals.py 활용**)
- 프론트가 이미 만들어 쓰는 `idempotencyKey`(GOTCHAS §2)를 요청 헤더/바디로 전달 — 서버가 중복 승인 차단의 최종 방어선이 된다
- 반려 사유(reason) → evidence_events 기록
- DoD: 같은 키 재전송 시 2xx-멱등(상태 불변), citation 0건 승인 잠금은 서버에서도 거부

### B7(후속·병행 가능) — 운영 품질
- OpenAI 임베딩 전환(`rag index --embedding-provider openai --reset`, ≈$0.02) + eval 게이트 재통과
- langgraph-checkpoint-postgres (thread 재개), Playwright 크롤러 `[crawl]` extra로 코퍼스 갱신
- docker-compose(로컬 4프로세스: vite·backend·rag·PG×2 통합 기동)

## 3. 프론트 진입점 상세 (B4의 설계)

원칙: **진입점은 3곳으로 최소화**하고, 각각 "mock이 기본, API는 opt-in".

### 3-1. `src/lib/api/` 신설 — 유일한 네트워크 레이어
```txt
src/lib/api/client.ts     # VITE_API_BASE 읽기. 미설정이면 isApiEnabled()=false — 모든 소비자가 mock 유지
src/lib/api/citations.ts  # fetchCitationLibrary(): Promise<CitationRecord[]>
src/lib/api/runs.ts       # fetchRunConfig(runKey): Promise<RunConfig>  (steps 비어 있음)
                          # streamRunSteps(runKey, onStep, onDone): RunEngineHandle  (SSE, cancel=close)
```
- 컴포넌트에서 fetch 직접 호출 금지 — 이 레이어만 네트워크를 안다(rules/frontend.md 결에 맞춤)
- 타입 정본은 `src/types.ts` — API 레이어는 서버 JSON을 이 타입으로 파싱·검증(zod 등 신규 의존성 없이 좁은 런타임 가드 함수)

### 3-2. 런 타임라인 — `executeRun` 불변, 공급원만 교체
- `src/lib/runEngine.ts`의 `executeRun` **무수정**. 같은 핸들 계약의 `streamRunSteps`가 형제로 추가될 뿐이다(`{cancel}` 반환, cancel=EventSource.close)
- 선택 지점은 **`useRunEngine` 한 곳**: config가 mock 각본(`steps.length > 0` 또는 `mode: 'replay'`)이면 지금처럼 `executeRun`, API 모드에서 steps가 비어 오면 `streamRunSteps(config.runKey, …)` 구독. 반환 계약(`{steps, status, currentIndex}`)은 그대로라 RunPage·StepTimeline 등 소비 컴포넌트는 **0줄 변경**
- `RUN_CONFIGS` mock은 삭제하지 않는다: replay 런(판단 기록 다시보기)과 오프라인 데모의 정본
- 승인 대기 전이("런의 종착점은 requestApproval()")도 불변 — SSE `done` 이벤트가 기존 `onDone()` 경로로 합류

### 3-3. 근거 라이브러리 — citationStore hydrate
- `useCitationStore`에 `hydrate(records: CitationRecord[])` 액션 추가. 앱 부팅 시(또는 거버넌스 화면 진입 시) `isApiEnabled()`면 `fetchCitationLibrary()` → hydrate, 실패하면 조용히 mock 유지(데모 안전)
- `usableCitations`(F등급 차단)·`citationKpis`·`linkedCaseCount` 파생 로직 **무수정** — 서버가 F를 안 주더라도 프론트 게이트는 최종 방어선으로 남긴다
- 케이스 시트의 citations도 같은 원리: mock 케이스는 그대로, API 케이스가 생기면 서버 citations 참조

### 3-4. 승인 — 마지막에, 서버가 최종 방어선 (B6)
- `approvalStore.decide()`의 로컬 상태 전이는 유지하되, API 모드에서는 서버 응답 성공 후 커밋(낙관적 갱신 금지 — 승인은 감사 대상)
- `idempotencyKey`·citation-0 잠금·F등급 차단 등 프론트 가드는 전부 유지하고, 서버가 같은 규칙을 재검증

### 진입점 요약 표

| # | 파일 | 변경 | 프론트 계약 |
|---|---|---|---|
| ① | `src/lib/api/*` (신규) | 네트워크 레이어 + `VITE_API_BASE` 스위치 | 미설정=현행 유지 |
| ② | `src/lib/useRunEngine.ts` | 소스 선택(각본 ↔ SSE) | `executeRun`·`RunConfig`·반환값 불변 |
| ③ | `src/stores/citationStore.ts` | `hydrate` 액션 | `usableCitations`·KPI 파생 불변 |
| ④ | `src/stores/approvalStore.ts` (B6) | decide() 서버 왕복 | idempotencyKey·잠금 규칙 불변 |

## 4. 계약 검증 (각 단계 공통)

- 타입 정합: backend Pydantic 응답 스키마 ↔ `src/types.ts` 필드명·유니온 값 일치를 계약 테스트로 고정
  (RunStep kind 5종, CitationGrade A|B|C|E|F, ApprovalStatus)
- 가드레일 회귀: D/F 근거 비노출, rag_retrieved에 원문·PII 없음, 발송·제출 자동 실행 금지
- 게이트: `cd rag && uv run pytest` + `rag eval`(hit@3≥0.80) / `cd backend && uv run pytest` / `npm run verify` — 세 스위트가 각자 그린이어야 완료
