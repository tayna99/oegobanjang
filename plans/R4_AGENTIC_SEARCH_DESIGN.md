# R4 — 에이전틱 검색·멀티턴 챗봇·다음액션 설계 (LLM 런타임 실연결)

> 상태: 설계(문서만). 코드 변경 없음. 채택 시 §11 태스크를 ROADMAP 형식(위임 레벨·스펙·DoD)으로 승격한다.
> 작성: 2026-07-20. 근거: `plans/NEXT_ROADMAP_2026-07-16.md` §R4(에이전트 런타임 실연결), `plans/ROADMAP.md` M5(RAG)·M7(오케스트레이션), `AGENTS.md` §2 핵심 원칙, `rules/safety.md`.
> 전제: OpenAI API 키를 `.env`(rag/·backend/)에 주입. R2(백엔드 배선)·M5(RAG 파이프라인)·M7(오케스트레이션 그래프) 완료 상태 위에서 진행.
> 이 문서가 답하는 것: (1) retrieval을 LLM으로 통과시켜 답변 품질을 올리는 법, (2) 3티어 에이전트 전부, (3) 동의어/유사어 검색, (4) 멀티턴 챗봇, (5) 참고 이미지(8 빌딩블록 + Orchestrator 패턴)에서 구현 가능한 것 전부, (6) 검색 품질 액션 전부, (7) LLM 기반 다음액션(맥락 종합).

---

## 0. 요약 (TL;DR)

외고반장은 **에이전트 인프라의 대부분이 이미 구현돼 있으나 사용자 검색창(CommandBar)에 배선되지 않은** 상태다. R4의 본질은 "새 챗봇을 만드는 것"이 아니라 **이미 있는 것을 검색창에 연결하고, 빠진 조각(멀티턴 메모리·하이브리드 검색·LLM 재랭킹·동의어층·다음액션 Proposer)을 채우는 것**이다.

이미 있는 것(수정 불필요, 배선만):
- 멀티턴 `create_agent` + `InMemorySaver` 체크포인터 + 안전 `SYSTEM_PROMPT` + `RagAnswer` 구조화출력 — [`rag/.../agent/factory.py`](../rag/src/oe_rag/agent/factory.py)
- RAG 검색 툴 3종(`@tool`) — [`rag/.../agent/tools.py`](../rag/src/oe_rag/agent/tools.py)
- 결정론 Intent Router(12 intent) + LangGraph 오케스트레이션 그래프(input_guard→router→planner→executor→aggregator→approval_gate→evidence) — [`rag/.../orchestration/`](../rag/src/oe_rag/orchestration/)
- 입력 가드(`redact_pii`·`find_forbidden_input_terms`) + **출력 가드**(`assert_output_safety`) — [`rag/.../orchestration/guard.py`](../rag/src/oe_rag/orchestration/guard.py)
- 승인 게이트(pending-first) + Evidence Log(append-only) + 자율성 사다리(`companies.autonomy_level`·`autonomy_grants`)

R4에서 새로 채우는 것:
1. **CommandBar → 오케스트레이션 배선** (지금은 `resolveCommandRunKey` 키워드 매칭뿐)
2. **멀티턴 대화 상태** (InMemorySaver → langgraph-checkpoint-postgres + thread_id 스코프 + 히스토리 트리밍)
3. **검색 품질 6종** (self-query, 하이브리드 pg_trgm, 동의어 3층, LLM 재랭킹, grounded synthesis, RAG×SQL 융합)
4. **3티어 에이전트** (Tier1 답변QA / Tier2 조립 / Tier3 프로액티브)
5. **에이전틱 Next-Action Proposer** (Rule은 사실·긴급도, Agent는 무엇을·어떻게·무엇을 첨부)

관통 원칙: **에이전트는 최종 상태를 쓰지 않는다 — 제안(proposal)을 조립해 승인 게이트 앞에 세운다.** 해자는 자동화가 아니라 감사가능성이다.

---

## 1. 설계 원칙 — 안전 아키텍처가 곧 배치 설계도

[`AGENTS.md`](../AGENTS.md) §2의 5줄이 "에이전트를 어디에 넣고 어디에 넣으면 안 되는지"를 그대로 규정한다. R4의 모든 컴포넌트는 이 경계 위에 있다.

| 계층 | 담당 | LLM 통과? | R4에서 |
|---|---|---|---|
| **RAG** | 공식 근거·절차 검색 | 검색=❌ / 재랭킹·합성=✅ | §5 전 액션 |
| **SQL/DB** | 현재 케이스·근로자 상태 | ❌ | §5.3 융합 재료 |
| **Rule** | 날짜 계산·true/false·severity | ❌ | §7 다음액션의 "사실·긴급도" |
| **LLM** | 자연어 구조화·요약·초안·설명·랭킹 | ✅ | §5·§6·§7의 생성/판단 |
| **Human 승인** | 발송·제출·전달·완료 전 관문 | — | §6 Tier2/3, §9 HITL |

절대 불변(rules/safety.md·AGENTS.md §7):
- LLM은 severity·D-day를 만들거나 바꾸지 않는다(Rule 소유). M7-G4에 "LLM이 severity 못 바꾸는 가드" 테스트 이미 존재.
- 근거 없으면 확정하지 않는다(`missing_evidence=true` → 행정사 검토 안내).
- 워커 프로파일링 금지(`agent_notes.category` 화이트리스트: response_pattern·deadline_practice·format_preference·channel_preference만).
- 자동 발송·제출 없음(승인 게이트 통과 필수).
- evidence에 PII 원문 저장 금지(요약·해시만).

---

## 2. 에이전트 8 빌딩블록 → 외고반장 매핑 (참고 이미지 1)

참고 이미지의 8개 개념이 이 코드베이스에 어떻게 대응하는지. **5개는 완비(✅ System Prompt·Tools·Middleware·HITL·Guardrail), 3개는 R4에서 보강(⚠️ Messages·Memory·Fallback)한다.**

| # | 빌딩블록 | 현재 상태 | 근거 파일 | R4 추가 작업 |
|---|---|---|---|---|
| 1 | **System Prompt** (역할·행동규칙) | ✅ 있음 | `factory.py` `SYSTEM_PROMPT` (근거검색 전용·금지사항·출력계약 내장) | 미션별 특화 프롬프트 3종(비자/컨택/워크포스)으로 분화 |
| 2 | **Messages** (히스토리 관리) | ⚠️ 부분 | `create_agent` 메시지 상태 있음 | 멀티턴 히스토리 트리밍·요약(§4), 케이스 스코프 |
| 3 | **Memory / Checkpoint** | ⚠️ 인메모리 | `factory.py` `InMemorySaver` | langgraph-checkpoint-postgres(M5.5 예고) + `agent_notes` 영속 메모리(§4) |
| 4 | **Tools** (도구 선택·외부행동) | ✅ 3종 | `tools.py` 3 RAG `@tool` | SQL 상태조회 툴 + 초안/패키지 조립 툴 추가(§6) |
| 5 | **Middleware (Before/After)** | ✅ 함수 존재 | `guard.py` `redact_pii`/`find_forbidden_input_terms`(Before) + **`assert_output_safety`(After)** | After-가드를 그래프 출구·챗 턴에 배선(§9) |
| 6 | **Human-in-the-loop** | ✅ 있음 | `graph.py` `approval_gate`(pending-first) | Tier2/3 조립 결과를 게이트로 라우팅(§6) |
| 7 | **Fallback / Retry** | ⚠️ 부분 | 미션→`rag_answer` 폴백, 오프라인 `FakeChatModel` | 검색 폴백 체인 + LLM 재시도(§9). 단 웹검색 대체는 **안 함**(등급필터 인덱스 밖 근거 금지) → "근거 없음+행정사 검토"로 정직 폴백 |
| 8 | **Guardrail** | ✅ 있음 | `guard.py` `FORBIDDEN_TERMS`, PII, D/F 등급 구조적 차단, 승인 게이트 | 유지 + 출력 재검사 강화(§9) |

> 이미지의 "한 문장 요약" 흐름(System Prompt → Messages → Memory → Tools → Middleware → HITL → Fallback → Guardrail)이 이 제품에서 그대로 성립한다. R4는 이 파이프라인을 **CommandBar 한 곳에 배선**하는 일이다.

---

## 3. 아키텍처 — Orchestrator + 미션 에이전트 (참고 이미지 2)

참고 이미지 2의 "Orchestrator(라우터) → 전문 에이전트(각자 Tools/Data/Workflow) + 하단 Guardrail" 패턴이 이 코드에 존재한다. **단, fan-out 박스는 LLM이 판단·합성하는 진짜 에이전트만이다** — 검색·Rule·집계처럼 LLM을 안 쓰는 결정론 부품은 에이전트가 아니라 *에이전트가 쓰는 도구·재료*(하단 밴드)다.

> **정정(2026-07-20)**: 이전 판은 "브리핑(rule-only·LLM 0회)"을 에이전트 자리에 그렸으나 — **LLM 0회짜리는 에이전트가 아니라 스케줄 잡**이다. 브리핑은 Rule 랭킹(결정론) 위에 LLM 내러티브를 얹어 에이전트로 승격하고(§8·§11 R4.9), 검색·Rule·Evidence 조회는 도구·재료로 내렸다.

```
                          사용자 입력 (CommandBar / 챗)
                                   │
                          [대화 셸: 멀티턴·메모리]  ← §4 (create_agent + checkpointer)
                                   │  매 턴
                       ┌───────────▼───────────┐
                       │  Orchestrator (라우터)  │  route_message() — 키워드 정본 + LLM 향상
                       └───────────┬───────────┘
   ── 에이전트 (LLM이 판단·합성·툴콜 — API 키 사용) ──────────────
     · 인력확보(m1) · 비자·서류(m2) · 다국어(m3)
         └ 각자 Tools(RAG 검색툴) · Data(pgvector+SQL) · Workflow(미션 스텝), 내부 LLM 합성 1회
     · 브리핑 = Rule 랭킹(결정론) → LLM 내러티브 + 첫 액션 제안 (하루 1회/회사 캐시)
                                   │  에이전트가 아래 도구·재료를 호출 (LLM 없음)
   ── 도구·재료 (에이전트가 쓰는 부품 — 에이전트가 아니다) ──────────
     · RAG 검색(벡터+어휘 수학) · Rule 엔진(severity·D-day) · SQL 상태(worker_docs·cases) · Evidence 조회(감사 로그)
                                   │
                                   ▼
                      [aggregator] Rule findings × 미션 결과 융합
                                   ▼
                      [approval_gate] 발송·제출·완료 → pending-first
                                   ▼
                      [Guardrail: 출력 재검사] assert_output_safety + PII 재스캔 + citation 필수
                                   ▼
                      Evidence Log (append-only) + 제안(proposal) DB 기록
                                   ▼
                      프론트: StepTimeline 스트리밍 + 액션 칩 + 초안 카드
```

이미지 2와의 대응:
- **Orchestrator(라우터)** = [`router.py`](../rag/src/oe_rag/orchestration/router.py) `route_message` (12 intent → 미션 dict)
- **에이전트 (LLM 사용)** = [`missions/`](../rag/src/oe_rag/missions/) m1_workforce·m2_visa·m3_contact (각자 Tools=RAG툴 / Data=pgvector+SQL / Workflow=미션 스텝, 내부 LLM 합성 1회) + 브리핑(Rule 랭킹 → LLM 내러티브, §8)
- **도구·재료 (LLM 없음)** = RAG 검색(벡터 수학)·Rule 엔진(날짜계산)·SQL 상태·Evidence 조회 — 에이전트가 호출하는 부품이지 에이전트가 아니다
- **하단 Guardrail** = [`guard.py`](../rag/src/oe_rag/orchestration/guard.py) + `approval_gate`

### 3.1 두 실행 모델의 관계 — 대화 셸이 미션 그래프를 감싼다

이 저장소에는 이미 두 경로가 공존한다(ARCHITECTURE 명시):
- **`create_agent`**(factory.py, `/agent/run`) — 툴 루프 + 체크포인터. **멀티턴 대화**에 적합.
- **`build_orchestration_graph`**(graph.py, `/graph/run`) — 결정론 순차 파이프라인. **액션이 필요한 1턴 미션**에 적합.

R4 설계: **멀티턴 대화 셸(create_agent, 메모리 보유)이 바깥, 액션이 필요한 턴은 안쪽 미션 그래프로 위임**한다.

```
매 턴:
  정보성 질문("체류연장 서류 뭐 필요해?")     → Tier1: RAG 툴 + LLM 합성 → 대화 내 답변(승인 불필요)
  액션 함의("Nguyen 체류연장 준비해줘")       → Tier2: 미션 그래프 실행 → 초안·패키지 조립 → approval_gate → 액션 칩
  이벤트 트리거(D-30 진입)                    → Tier3: 프로액티브 런(사람 개입 전) → 준비 완료 → 승인 대기
```

---

## 4. 멀티턴 챗봇 설계 (요구 4)

자유 채팅이 아니라 **경계 있는·근거 있는·게이트 있는 멀티턴 어시스턴트**. 이미지 블록 2·3(Messages·Memory)의 구현.

### 4.1 대화 상태 3층

| 층 | 무엇 | 저장 | 수명 | 주의 |
|---|---|---|---|---|
| **단기(Messages)** | 현재 대화 턴들 | 체크포인터 상태 | 대화 세션 | 긴 히스토리는 트리밍/요약(이미지 "필요한 정보만 유지") |
| **작업(Checkpoint)** | 진행 중 미션 상태 | langgraph-checkpoint-postgres | thread_id 재개까지 | pending-first라 HITL resume 필요 시(B7) |
| **영속(Memory)** | 회사·근로자 운영 패턴 | `agent_notes` 테이블 | 명시 삭제까지 | **화이트리스트 4종만** — 성실도·이탈 추정 금지 |

### 4.2 thread_id 스코프 — 케이스 단위

- `thread_id = f"{company_id}:{case_id}"` (케이스 없는 자유질의는 `{company_id}:adhoc:{uuid}`).
- 케이스 스코프 대화는 그 케이스의 상태·근거·스레드를 컨텍스트로 자동 주입(§5.3 융합).
- **크로스 워커 프로파일링 차단**: 메모리는 케이스/회사 스코프이지 "이 근로자는 어떤 사람" 프로파일이 아니다. `agent_notes.category`가 스키마 차원에서 이를 강제.

### 4.3 턴 계약 — 텍스트가 아니라 구조체

매 어시스턴트 턴은 `RagAnswer`를 확장한 구조체를 반환한다(프론트가 액션 칩으로 렌더 가능해야 함):

```ts
interface AssistantTurn {
  answer: string;                    // 한국어 답변
  citations: { sourceId; title; grade }[];   // 근거(등급 노출 — §5.2)
  proposedActions: NextActionRef[];  // §7 다음액션 (승인 필요 여부 포함)
  approvalNeeded: boolean;           // 발송·제출·완료 함의 시 true
  missingEvidence: boolean;          // 근거 부족 정직 신호
  riskFlags: string[];               // MISSING_EVIDENCE 등
}
```

이미 `RagAnswer`(final_response·citations·missing_evidence·risk_flags)가 이 계약의 3/6을 충족. R4는 `proposedActions`·`approvalNeeded`·`grade`를 추가한다.

### 4.4 이미지 블록 5(Middleware) 적용 — 매 턴 Before/After

- **Before**: `redact_pii`(PII 마스킹) + `find_forbidden_input_terms`(금지어 → 차단) — 이미 `input_guard`.
- **After**: `assert_output_safety`(출력 금지어 검사) + citation 존재 검사 + 출력 PII 재스캔 — **함수는 있으나 챗 턴에 미배선**. R4에서 배선.

---

## 5. 검색 품질 — 전 액션 구현 설계 (요구 1·3·6)

핵심 분리(요구 1의 개념): **검색(retrieval)은 LLM을 안 지나가고, 재랭킹·합성은 지나간다.** 이 분리가 안전장치다 — 등급필터 인덱스에 없는 근거는 hallucination이 구조적으로 불가능. "retrieval을 LLM으로 통과"시키는 것 = 아래 **레버 B의 LLM 재랭킹 + grounded 합성** 두 접점.

### 5.1 레버 A — 검색(LLM 없음): recall/precision

현재 [`retriever.py`](../rag/src/oe_rag/retriever.py)에 이미 있음: 쿼리 확장(`_expanded_query`), 어휘 재랭킹(`_rerank_results`), source_id dedup, 메타 사전필터(visa_type/case_type/evidence_grade). **추가 3종:**

**(A-1) Self-query — 자연어에서 필터 추출(LLM), 검색은 결정론.**
"베트남 근로자 안전교육 안내" → `{intent: safety, language_code: vi}` 추출 → `search_multilingual_contact_materials(intent=..., language_code=...)`. 툴 시그니처에 `intent`/`language_code` 파라미터가 이미 있어 반쯤 준비됨([`tools.py:135`](../rag/src/oe_rag/agent/tools.py)). LLM은 필터만 뽑고 실제 검색은 무LLM.

**(A-2) 하이브리드 검색 — pg_trgm/full-text를 1급 arm으로 승격.**
현재는 벡터 + 사후 어휘 재랭킹. 한국어 법령·고시 용어("고용허가서", "사증발급인정서")는 정확 매칭이 강하므로 PostgreSQL `pg_trgm`(또는 `tsvector`) 검색을 **벡터와 병렬 arm**으로 돌리고 RRF(Reciprocal Rank Fusion)로 합친다. pgvector 스키마(`rag` PG 스키마)에 `tsvector` 컬럼 + GIN 인덱스 추가.

**(A-3) 동의어/유사어 확장 — 요구 3 (아래 §5.4에서 상세).**

### 5.2 레버 B — 생성(LLM): grounding/faithfulness (요구 1)

**(B-1) LLM 재랭킹 — top-20 후보를 LLM이 재정렬 → top-5.**
`_query_collection`이 이미 `top_k*20` 후보를 뽑음([`retriever.py:134`](../rag/src/oe_rag/retriever.py)). 이 후보를 LLM cross-encoder식 재랭킹(질의 관련성 점수화)으로 정렬. **비용 有** → Tier1 유료층·저신뢰 질의에만 조건부. 키 없으면 기존 어휘 재랭킹으로 폴백.

**(B-2) Grounded 합성 — 검색 청크를 근거로 답변 생성, citation 필수.**
이미 `SYSTEM_PROMPT`에 계약 내장: "citations는 source_id만, 지어내지 않음, D/F 미인용, 비면 missing_evidence=true". R4는 이걸 CommandBar 답변 경로에 배선하고 프롬프트를 미션별로 특화.

**(B-3) 등급 노출 — 이 도메인의 킬러 UX.**
답변에 근거 등급을 표시("A등급 공식 근거 · 고용노동부" vs "E등급 내부 템플릿"). 담당자가 얼마나 신뢰할지 안다. `RagCitation.evidence_grade`가 이미 있음 — 프론트 렌더만 추가.

**(B-4) Faithfulness eval 게이트 — 이미 CI에.**
M5.3에 Hit@1≥0.60·Hit@3≥0.80·Hit@5≥0.90·MRR≥0.65·safety=0 게이트가 CI `rag` 잡으로 돈다. R4의 프롬프트/재랭킹 변경이 이 게이트를 회귀시키지 않아야 함(DoD).

### 5.3 레버 C — RAG(정책) × SQL(우리 회사 상태) 융합

일반 정책이 아니라 **"너희 Nguyen은 D-27, 여권사본 missing"**. `context_snapshot.rule_findings`가 이미 이 융합 자리([`graph.py:143`](../rag/src/oe_rag/orchestration/graph.py) aggregator). R4는 검색/답변 시 `worker_documents`·`cases` 상태를 SQL 툴로 읽어 근거와 합성. **정책(RAG) + 상태(SQL) + 긴급도(Rule)** 3자 결합이 진짜 답.

### 5.4 동의어/유사어 3층 설계 (요구 3)

한국어 행정 도메인은 표현 변주가 크다("체류연장"="비자연장"="체류기간 연장"="visa extension"; "고용변동신고"="근로자 변동신고"="이직 신고"). 3층으로 커버:

| 층 | 방식 | LLM | 예 |
|---|---|---|---|
| **1. 큐레이션 사전(정본)** | 도메인 동의어 dict, `_expanded_query` 확장 | ❌ | 체류연장 ↔ 비자연장 ↔ 체류기간연장 ↔ visa extension |
| **2. 임베딩(내재)** | 벡터 유사도가 근접 표현 자동 포착 | ❌ | "일 그만둔" ≈ "퇴사" ≈ "근로관계 종료" |
| **3. LLM 쿼리 재작성(향상)** | 구어체 → 표준 용어 + 동의어 정규화 | ✅(선택) | "얘 비자 언제 끝나" → "체류만료일 조회 · 체류연장 절차" |

- 1층은 **키 없이 동작하는 정본 폴백**(신규 파일 `rag/.../synonyms.py`, 도메인 사전 + `_expanded_query` 통합).
- 3층은 API 키 있을 때만 얹는 향상 — self-query(A-1)와 같은 LLM 호출에 합쳐 1회로.
- 동의어 사전은 evidence_grade가 붙은 근거처럼 **버전·출처를 기록**(감사 대상 — 왜 이 확장이 붙었는지 재현 가능).

---

## 6. 3티어 에이전트 (요구 2) — 사용성·비즈니스·에이전틱 중 하나라도 충족하면 설계

`companies.autonomy_level`(L1/L2/L3) + `autonomy_grants`(owner 명시 동의) = 신뢰 사다리 = 과금 사다리.

### Tier 1 — 답변 에이전트 (검색/QA · 읽기전용 · 승인 불필요)

| 항목 | 내용 |
|---|---|
| 충족 축 | **사용성** (검색창이 진짜 검색창이 됨) |
| 트리거 | CommandBar 정보성 질의, 챗 정보 턴 |
| 흐름 | route → RAG 툴(§5.1) → LLM 재랭킹(§5.2 B-1) → grounded 합성(B-2) → 등급 노출(B-3) |
| 출력 | `AssistantTurn`(answer + citations + grade), `approvalNeeded=false` |
| 데이터 | 읽기 전용. evidence: `rag_retrieved`·`final_response_generated` |
| 자율성 | L1 무관(부작용 없음) |
| DoD | 근거 있는 질의에 citation+등급 포함 답변, 근거 0건 시 "행정사 검토" 정직 응답, faithfulness eval 무회귀 |

### Tier 2 — 조립 에이전트 (초안·패키지 · 승인 게이트에서 정지)

| 항목 | 내용 |
|---|---|
| 충족 축 | **비즈니스** (담당자 준비 노동 대행) + **에이전틱** (툴 체이닝) |
| 트리거 | "Nguyen 체류연장 준비해줘", 액션 함의 턴 |
| 흐름 | route → 미션 그래프 → RAG 근거 수집 + SQL 상태 조회 + 다국어 초안(`drafts`/`draft_variants`) + 행정사 패키지(`handoff_packages`) 조립 → **approval_gate에서 정지** |
| 출력 | 초안 카드 + `proposedActions`(승인 필요), `approvalNeeded=true`. **발송·전달 실행 없음** |
| 데이터 | 제안만 씀: `drafts`·`next_actions`(state=ready)·`runs`·`run_steps`. evidence: `plan_created`·`tool_executed`·`approval_requested` |
| 자율성 | L2 기본(에이전트 준비, 사람이 전부 승인) |
| DoD | 조립 결과가 승인 없이 발송되지 않음(rules/safety.md 회귀), `next_actions` CHECK(send/handoff/export/complete=requires_approval) 유지, run 1건=evidence 1건 |

### Tier 3 — 프로액티브 에이전트 (이벤트 트리거 · 사람 개입 전 준비)

| 항목 | 내용 |
|---|---|
| 충족 축 | **비즈니스**(사전 감지=핵심 ROI) + **사용성**(사람이 눈치채기 전) + **에이전틱**(자율 기동) |
| 트리거 | D-30/D-7 진입, 인바운드 응답 도착, 신고기한 임박 (`runs.started_by='event'`, `trigger_event`) |
| 흐름 | 이벤트 → 자동 런(읽기+초안 툴 화이트리스트) → 준비 완료 → 승인 대기. 카드 `preparedBy='agent'`, `preparedRunRef` |
| 출력 | "AI가 준비를 마쳤습니다 · 런 #NNNN 보기" + 재생 뷰(읽기전용). 발송 전 정지 스텝 필수 |
| 데이터 | `cases.next_wake_at`/`next_wake_condition`, `runs`(event), 재생용 `run_steps`. evidence: 전 스텝 |
| 자율성 | L2에서 준비까지. 저위험 case_type만 owner가 `autonomy_grants`로 L1 개방 가능(명시 동의) |
| DoD | 재생 뷰 읽기전용, 가드레일 정지 스텝 존재(M3.1 이미 테스트), 발송 전 사람 승인 필수 |

> 뼈대 존재: Tier3는 `preparedBy:'agent'`·프로액티브 런 개념이 ROADMAP M3.1에 이미 있음. R4는 이를 실 LLM 런타임에 연결.

---

## 7. 에이전틱 Next-Action Proposer (요구 7) — "무엇을·어떻게·무엇을 첨부"

현재 다음액션은 룰베이스다: [`actionNav.ts`](../src/lib/actionNav.ts)가 `kind→이동` 고정 매핑, primary/secondary가 fixtures에 박힘. **하지만 에이전틱 패턴의 씨앗이 이미 한 곳에 있다**:

```ts
// src/types.ts:153 — 응답 해석(M6)
recommendedActions: { action: NextActionRef; reason: string }[]  // 액션 + 이유(reason) 쌍
```

이 "액션+이유" 쌍을 **케이스 전역으로 일반화**한다. 역할 분리가 핵심(룰을 없애지 않음):

| | 소유 | 왜 |
|---|---|---|
| **Rule** | 무엇이 사실이고 얼마나 급한가 (severity, D-day, 서류 누락 여부) | 결정론·감사가능. D-day를 LLM이 지어내면 안 됨 |
| **Agent(LLM)** | 그래서 **무엇을** 할지 + **어떻게** 문구를 쓸지 + **무엇을** 첨부할지 (랭킹 + rationale + citation) | 맥락 종합은 LLM이 잘함 |

### 7.1 NextAction Proposer 계약

```
입력:  case(상태) + rule_findings(severity·D-day) + 최근 thread + 연결 citations + agent_notes(포맷 선호)
처리:  LLM이 후보 액션을 impact×urgency로 랭킹, 각 액션에 rationale + citation 첨부
출력:  NextActionRef[] (slot=primary/secondary, state=ready, requiresApproval)
       각 액션: { action, reason(rationale), citationId, requiresApproval }
기록:  next_actions 행 + evidence(plan_created) — 랭킹 근거가 감사 대상
```

- **안전**: `next_actions` CHECK 제약(send/handoff/export/complete는 항상 requires_approval=true, [`schema.sql:322`](../db/schema.sql))이 에이전트 제안 액션도 자기발로 실행 못 하게 강제.
- **Rule 우선**: Agent가 제안한 액션이라도 severity/D-day는 Rule 값을 그대로 소비(변경 불가). LLM이 "급하지 않다"고 판단해도 Rule이 CRITICAL이면 CRITICAL.
- **문구 생성**: "어떻게 문구를 쓸지" = Tier2 초안 생성과 동일 경로(다국어 `draft_variants`), agent_notes의 `format_preference`·`channel_preference` 반영("지난번 형식 기억"—이미지 블록3, 단 워커 프로파일 아님).
- **첨부 선택**: "무엇을 첨부할지" = 케이스에 연결할 citation·서류 요구(`document_requirements`)를 근거와 함께 제안.

### 7.2 프론트 렌더

Proposer 출력 → `CaseCard.primaryAction`/`secondaryAction`(이미 `NextActionRef`, `preparedBy:'agent'`) 슬롯에 렌더. 각 액션에 rationale 툴팁 + citation 링크. 룰베이스 폴백 유지(키 없거나 저신뢰 시).

---

## 8. DB → 프론트 배선 (데이터 관점)

원칙: **에이전트는 최종 상태를 쓰지 않는다 — 제안(proposal)을 쓰고 사람이 승인해야 확정.**

### 8.1 에이전트 런 1회가 만드는 것

| 산출 | 테이블 | 성격 |
|---|---|---|
| 에이전틱 트레이스 | `runs` + `run_steps` | 재생용(읽기전용 뷰) |
| 감사 기록 | `evidence_events` | append-only, PII 마스킹, 해시만 |
| 메시지 초안 | `drafts` + `draft_variants` | 다국어, 승인 전 상태 |
| 다음액션 제안 | `next_actions` (state=ready, slot) | §7 Proposer 산출 |
| 응답 해석 제안 | `interpretations` (status=proposed) | 담당자 확인 필수 |

### 8.2 두 배선 경로 — 비용/지연의 핵심

| 경로 | 방식 | LLM | 이유 |
|---|---|---|---|
| **검색/챗/조립** | `/runs/:id` **SSE 스트리밍**(M7 B3' 설계됨) → `StepTimeline` 실시간 | ✅ | 사고 스텝을 흘려 신뢰·투명성 |
| **데일리 브리핑** | Rule 랭킹 = `briefings` 머티리얼라이즈(결정론·캐시, M7 G6) + LLM 내러티브(하루 1회/회사 캐시) | 랭킹 ❌ / 내러티브 ✅ | 랭킹은 매일·전사라 rule-only, 내러티브·첫 액션만 LLM(캐시로 비용 통제) |

- 읽기 API는 이미 R2.3 배선됨(`/cases`·`/briefings/latest`·`/threads`).
- 프론트 렌더 지점: `next_actions.slot`(primary/secondary)+`state`(ready/locked/scheduled) = "에이전트 제안을 케이스 카드에 렌더한 것". StepTimeline은 [`src/features/run/`](../src/features/run/RunScreen.tsx)에 이미 존재 — 챗 UI 신규 제작 불필요.

---

## 9. 안전·가드레일 (이미지 블록 5·6·7·8)

### 9.1 Middleware Before/After (블록 5) + Guardrail (블록 8)

- **Before(입력 전)**: `redact_pii` + `find_forbidden_input_terms` → 금지어 시 `blocked_response`(이미 `input_guard`).
- **After(출력 후)**: `assert_output_safety`(금지어) + citation 존재 검사 + 출력 PII 재스캔 → **R4에서 챗 턴·그래프 출구에 배선**(함수는 있음).
- **구조적 가드**: D/F 등급 색인 단계 배제(구조적으로 인용 불가), `next_actions` CHECK(발송류 승인 필수), `agent_notes` category 화이트리스트(프로파일링 불가).

### 9.2 Human-in-the-loop (블록 6)

`approval_gate`가 발송·제출·전달·완료를 pending-first로만 표시. Tier2/3 조립 결과가 전부 이 게이트를 통과. rules/safety.md 발송·승인 체크리스트가 회귀 가드.

### 9.3 Fallback / Retry (블록 7)

| 실패 | 폴백 | 주의 |
|---|---|---|
| 검색 0건 | `missing_evidence=true` → "근거 없음, 행정사 검토 필요" | **웹검색 대체 안 함** — 등급필터 인덱스 밖 근거는 법 도메인에서 금지 |
| LLM 호출 실패 | 지수 백오프 재시도 → 실패 시 키워드 라우터/어휘 재랭킹으로 degrade | 키 없어도 정본 동작 |
| 미션 미구현 | `rag_answer` 폴백 + `MISSION_NOT_IMPLEMENTED` 플래그(조용한 폴백 금지) | 이미 `graph.py` |
| API 키 없음 | 결정론 라우터 + 무LLM 검색 + 브리핑 랭킹만(LLM 내러티브 생략) | §10 |

---

## 10. API 키·비용·Graceful Degradation

API 키는 `.env`(rag/·backend/)에 주입. **키가 실제로 쓰이는 곳은 4곳뿐:**
1. Self-query 필터 추출 + 동의어 재작성 (§5.1 A-1, §5.4 3층)
2. LLM 재랭킹 (§5.2 B-1, 조건부)
3. Grounded 합성 (§5.2 B-2)
4. NextAction 맥락 종합 (§7)

**나머지는 키 없이 동작**(`_default_model`이 키 없으면 명시적 에러, 상위에서 degrade): 결정론 라우터, 무LLM 벡터/어휘 검색, rule 판정, 브리핑 랭킹, 전 가드레일. 스토리: **"당신의 API 키는 향상 레이어를 켜지만, 안전 바닥은 키 없이도 돈다."**

비용 모델: 브리핑 랭킹=무LLM(0원) + 내러티브=하루 1회/회사 캐시(1콜). 검색=self-query 1 + (재랭킹 1) + 합성 1 ≈ 2~3콜/질의. 조립=미션당 합성 1~2콜. 재랭킹은 유료층·저신뢰 질의로 게이팅. temperature=0(결정성·재현성).

---

## 11. 태스크 분해 (R4.x — 채택 시 ROADMAP 승격)

> 태스크 1개 = 세션 1개 크기. legacy 이관은 production import 금지(복사·재배선 후 `npm run verify`·rag pytest·backend pytest 통과).

| # | 태스크 | 레벨 | DoD | 선행 |
|---|---|---|---|---|
| R4.1 | **CommandBar → 오케스트레이션 배선** (Tier1 최소 수직 슬라이스) | L3 | CommandBar가 `resolveCommandRunKey` 대신 `/graph/run` 또는 `/agent/run` 호출(real 모드), 정보성 질의에 citation+등급 답변, mock 모드 무회귀 | R2.3 |
| R4.2 | **동의어 3층 + self-query** (`rag/.../synonyms.py`) | L2 | 1층 사전 키 없이 동작, self-query 필터 추출 테스트, `_expanded_query` 통합, faithfulness eval 무회귀 | R4.1 |
| R4.3 | **하이브리드 검색(pg_trgm/tsvector + RRF)** | L2 | `rag` 스키마에 tsvector+GIN, 벡터/어휘 병렬 arm RRF 융합, Hit@k 개선 또는 무회귀 측정 | R4.2 |
| R4.4 | **LLM 재랭킹 + grounded 합성 배선** (retrieval→LLM, 요구 1) | L3 | top-20→top-5 LLM 재랭킹(조건부·폴백), 미션별 특화 프롬프트, 등급 노출 프론트 렌더, safety eval=0 | R4.3 |
| R4.5 | **멀티턴 대화 상태** (postgres 체크포인터 + thread_id + 히스토리 트리밍) | L3(2~3세션) | InMemorySaver→langgraph-checkpoint-postgres, thread_id=company:case 스코프, 히스토리 트리밍/요약, After-미들웨어 배선 | R4.1 |
| R4.6 | **Tier2 조립 에이전트** (초안·패키지 → approval_gate) | L3 | 조립이 승인 없이 발송 안 됨(safety 회귀), drafts/next_actions 제안 기록, run 1건=evidence 1건 | R4.4 |
| R4.7 | **NextAction Proposer** (요구 7, `interpretation.recommendedActions` 일반화) | L3 | Rule severity/D-day 불변 소비, 액션+rationale+citation 출력, `next_actions` CHECK 유지, 룰베이스 폴백 | R4.4 |
| R4.8 | **Tier3 프로액티브 실연결** (이벤트→자동 런→승인 대기) | L3 | 재생 뷰 읽기전용, 발송 전 정지 스텝, `autonomy_grants` L1 게이팅 | R4.6 |
| R4.9 | **브리핑 에이전트 승격** (Rule 랭킹 위 LLM 내러티브·첫 액션) | L2 | Rule 랭킹 불변(결정론) 소비, LLM이 severity/D-day 못 바꿈(가드 테스트), 하루 1회/회사 캐시, 키 없으면 랭킹만 | R4.7 |

권장 순서: R4.1(배선 슬라이스) → R4.2·R4.3(검색 품질 무LLM) → R4.4(LLM 접점) → R4.5(멀티턴) → R4.6·R4.7(조립·다음액션) → R4.8(프로액티브) → R4.9(브리핑 에이전트 승격).

---

## 12. 명시적으로 안 하는 것 / 미결 / 후속

- **웹검색 폴백 안 함** — 등급필터 인덱스 밖 근거는 법 도메인에서 금지(§9.3). 근거 없으면 "행정사 검토".
- **실 발송·제출 안 함** — R3(메시징 실연동)·발송 어댑터는 별도 범위. R4는 초안·제안까지.
- **LLM이 severity/D-day 안 만짐** — Rule 소유(§1·§7). 위반 시 M7-G4 가드 회귀.
- **워커 프로파일링 안 함** — `agent_notes` 화이트리스트. 성실도·이탈 추정 스키마 차원 금지.
- **미결**: langgraph-checkpoint-postgres 도입은 M5.5에 후속으로 이미 예고 — R4.5가 이를 흡수. 운영 인덱스(OpenAI 임베딩 ≈$0.02, M5.5)는 R4 착수 시 함께 결정.
- **후속(R5)**: 컨트롤타워 실집계(§5.3 융합 데이터 활용), 알림·푸시 실발송, 법령·고시 상시 크롤러화.

---

## 부록 — 참고 이미지 매핑 요약

**이미지 1(8 빌딩블록)** → §2 표. 5개 완비(System Prompt·Tools·Middleware·HITL·Guardrail), 3개(Messages·Memory·Fallback) R4에서 보강.
**이미지 2(Orchestrator 멀티에이전트)** → §3. Orchestrator=router.py, 에이전트(LLM)=missions m1/m2/m3 + 브리핑(Rule 랭킹+LLM 내러티브), Guardrail=guard.py+approval_gate. **검색·Rule·Evidence 조회는 에이전트가 아니라 도구·재료**(LLM 없음) — 이전 판이 rule-only 브리핑·감사 조회를 에이전트로 그린 오류를 정정.
