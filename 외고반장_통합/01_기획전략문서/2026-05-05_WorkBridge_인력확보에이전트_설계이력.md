# WorkBridge 인력확보 에이전트 설계 및 실행 정리

날짜: 2026년 5월 5일
담당: Tenacity
대안: RAG/Guardrail 페이지에 계속 누적, mission별 분산 기록, 코드 변경만 추적
상태: 활성
영향: 시스템
이유: 외고반장 Workforce Agent의 목적, 자료 근거, 의사결정, 실제 실행 결과와 남은 작업을 한 페이지에서 추적하기 위함

# 전수 확인 범위

이번 정리는 현재 로컬 markdown과 `backup/main-before-oegobanjang-sync` 브랜치의 markdown을 전수 목록화한 뒤 작성했다.

| 구분 | 확인 수 | 비고 |
| --- | --- | --- |
| --- | ---: | --- |
| 현재 로컬 md | 49개 | `.claude/`, `docs/`, `missions/`, `backend`, `evals`, 루트 문서 포함 |
| 백업 브랜치 md | 25개 | 예전 phase harness, Workforce schema, Week 1 eval, engineering plan 포함 |
| 빈 문서 | 2개 | `docs/journal/journal.tn/2026-05-04.md`, `docs/journal/journal.tn/history.md`는 0바이트 |

핵심 의사결정은 주로 아래 파일에서 나왔다.

- `backup/main-before-oegobanjang-sync:01_workforce_agent_schema.md`
- `backup/main-before-oegobanjang-sync:02_week1_checklist_eval.md`
- `backup/main-before-oegobanjang-sync:03_codex_harness_engineering.md`
- `backup/main-before-oegobanjang-sync:docs/REMAINING_EXECUTION.md`
- `backup/main-before-oegobanjang-sync:docs/ENGINEERING_PLAN.md`
- `backup/main-before-oegobanjang-sync:docs/PHASE3_REVIEW_NOTES.md`
- `backup/main-before-oegobanjang-sync:phases/mvp/*.md`
- 현재 `docs/journal/history.md`
- 현재 `docs/journal/2026-05-04.md`
- 현재 `docs/SCHEMA_CONTRACT.md`, `docs/STATE_MACHINE.md`, `docs/EVIDENCE_LOG_SCHEMA.md`, `docs/EVAL_METRICS.md`
- 현재 `missions/active/*.md`

# 한 줄 결론

WorkBridge의 인력확보 에이전트는 처음부터 “후보를 추천하는 AI”로 계획된 것이 아니다. 로컬 md 흐름을 순서대로 보면, 방향은 계속 더 명확해졌다. 공식 근거, 데이터 계약, eval, deterministic routing, human approval, evidence log, guardrail을 먼저 세우고, 그 위에 Workforce Agent를 올리는 구조로 발전했다.

# 1. 출발점: 채용 매칭이 아니라 운영 리스크 관리

초기 제품 방향은 `docs/PRD.md`, 현재 `docs/PROJECT_BRIEF.md`, `docs/journal/history.md`에 남아 있다.

처음부터 핵심 질문은 “외국인 인력을 자동 추천할 것인가?”가 아니라 “사업주가 외국인 고용 절차와 서류, 일정, 근거를 놓치지 않게 할 것인가?”였다.

초기 의사결정은 다음과 같다.

- WorkBridge/외고반장은 외국인 고용 운영 OS다.
- 비자 신청 대행 서비스가 아니다.
- 채용 매칭 플랫폼도 아니다.
- EPS와 송출회사 체계가 이미 매칭을 담당하므로, 제품은 사업주 쪽 행정 부담과 리스크를 줄이는 쪽으로 간다.
- Workforce Agent는 후보자 추천, 성실도 판단, 국적 선호를 하지 않는다.
- 대신 신규 인력 요청서, 사업장 조건 체크리스트, 송출회사/행정사 질문 리스트, 공식 근거를 정리한다.

이 결정 때문에 이후 모든 phase에 `candidate ranking`, `suitability scoring`, `nationality preference` 금지가 반복해서 들어간다.

# 2. 먼저 세운 계약: Workforce Agent 입출력과 case_type

`01_workforce_agent_schema.md`가 인력확보 에이전트의 첫 단일 진실 문서였다.

여기서 Workforce Agent의 책임은 이렇게 정리됐다.

```
사업주가 새 외국인 인력을 확보하려 할 때,
공식 절차·조건·허용업종·점수제·쿼터 정보를 확인해서
신규 인력 요청서, 사업장 조건 체크리스트,
송출회사/행정사에게 물어볼 질문 리스트를 만든다.
```

초기 입출력 계약은 다음 구조였다.

| 영역 | 내용 |
| --- | --- |
| Input | 사용자 자연어, 회사 상태, 후보 상태, 추가 입력 |
| Internal Flow | intent/case_type 파싱 → 회사 상태 로드 → RAG 검색 → 룰 검사 → 출력 조립 → 사람 승인 대기 |
| Output | 신규 인력 요청서, 사업장 조건 체크리스트, 질문 리스트, risk flag |
| Out of Scope | 후보 추천, 국적 선호, 법령 해석, 외부 발송, 점수제 자동 산정 |

여기서 `case_type` 4종도 고정됐다.

| case_type | 의미 |
| --- | --- |
| `new_hiring` | 신규 도입 |
| `rehire_loyalty` | 성실근로자 재입국 |
| `workplace_change_intake` | 사업장 변경으로 받는 케이스 |
| `same_worker_rehire` | 동일 외국인 재고용 |

처음부터 phase 필드는 선택 필드였고, `site_check`, `candidate_intake`, `contract_prep` 같은 단계 구분을 위해 쓰였다. 이 개념은 2026-05-04에 현재 브랜치의 `docs/STATE_MACHINE.md`와 `docs/SCHEMA_CONTRACT.md`로 다시 정리된다.

# 3. Week 1 계획: 에이전트보다 RAG thin slice 먼저

`02_week1_checklist_eval.md`와 `docs/REMAINING_EXECUTION.md`의 Week 1 계획은 명확했다.

처음 실행 순서는 다음이었다.

```
문서 읽기
→ Workforce schema 확인
→ Week 1 eval 확인
→ Phase 1 Data Schema + RAG Thin Slice
→ Phase 2 Router
→ Phase 3 Workflow State Machine
→ Phase 4 Demo UI
```

Week 1의 목표는 agent를 바로 구현하는 것이 아니라, 공식 문서 6개로 RAG thin slice를 끝까지 한 번 돌리는 것이었다.

필수 raw source는 다음으로 잡았다.

- EPS 사업주 고용절차
- E-9 허용업종 안내
- 고용허가 신청 안내
- 외국인근로자고용법
- 외국인근로자 고용변동 등 신고서
- 사업장 점수제 안내

평가 기준은 `eval/retrieval_eval.jsonl` 12문항 기준 `Hit@3 >= 80%`였다. 즉, “검색이 되는 것처럼 보인다”가 아니라 기대 `source_id`가 top 3 안에 들어오는지를 측정하기로 했다.

# 4. Codex 하네스 결정: 범위를 phase로 묶고 멈출 조건을 명시

`03_codex_harness_engineering.md`, 백업 `AGENTS.md`, `.agents/skills/harness/SKILL.md`, `phases/templates/phase_template.md`에서 하네스 방식이 정리됐다.

핵심 흐름은 다음이었다.

```
docs → AGENTS → Phase → execute → verify → review
```

이 결정의 이유는 WorkBridge 도메인이 쉽게 범위를 넘기 때문이다. 인력확보를 하다 보면 후보 추천, 법률 판단, 외부 제출, 국적 선호 같은 금지 영역으로 미끄러질 수 있다. 그래서 각 phase는 반드시 아래를 포함하도록 했다.

- `Goal`
- `Inputs`
- `Allowed Writes`
- `Forbidden`
- `Steps`
- `Verification`
- `Stop Conditions`
- `Final Output Requirement`

이때 이미 중요한 원칙이 박혔다.

- 필요한 파일이나 schema가 없으면 guessing하지 않고 `blocked`로 멈춘다.
- phase 범위 밖 파일은 수정하지 않는다.
- 테스트나 eval 같은 verification path를 반드시 둔다.
- `status: completed | blocked | error`로 끝내서 자동 러너가 상태를 판단하게 한다.

# 5. Phase 1 실행: 데이터 계약과 검색 기준을 먼저 고정

`phase1-data-schema.md`는 Workforce Agent 상세 구현 전에 데이터 계약과 RAG thin slice를 만드는 phase였다.

Phase 1의 핵심 작업은 다음이었다.

1. `docs/DATA_GUIDE.md` 작성
2. 회사, 후보자, synthetic case, chunk, source metadata, retrieval eval schema 고정
3. 공식 raw source snapshot 확인
4. `src/ingest.py`, `src/retrieve.py`, `src/evaluate.py` 구현
5. `eval/retrieval_eval.jsonl` 12문항 평가
6. `Hit@3 >= 80%` 확인

백업 `eval/results/phase1_retrieval_report.md`에는 결과가 남아 있다.

```
Hit@3 = 10/12 = 83%
```

실패 케이스는 Q6, Q10이었다. 둘 다 `law_form_employment_change_001`를 기대했지만 다른 EPS 절차/업종 문서가 top result로 올라왔다.

이 결과의 의미는 두 가지다.

- Phase 1은 목표치 80%는 넘겼다.
- 하지만 source-level 검색만으로는 후속 phase의 citation 품질이 부족하다는 문제가 드러났다.

# 6. 더미 운영 데이터: Agent 테스트용 상태 데이터 확보

현재 `DATA_GENERATION_REPORT.md`는 새 구조에서 Phase 1 완료 보고서 역할을 한다.

여기서는 seed 운영 데이터가 만들어졌다.

| 파일 | 내용 |
| --- | --- |
| `companies.csv` | 제조업 사업장 5개 |
| `workers.csv` | 근로자 30명 |
| `visas.csv` | D-day 분포 포함 비자 상태 30건 |
| `worker_documents.csv` | 서류 상태 44건, 누락 11건 |
| `document_requirements.csv` | 케이스별 필수 서류 기준 22건 |
| `visa_lookup.csv` | 비자별 기준 |
| `country_lookup.csv` | 국적-언어 매핑 |
| `message_templates.jsonl` | 다국어 메시지 템플릿 16건 |

이 데이터는 실제 개인정보가 아니라 테스트/데모용 상태 데이터다. 중요한 점은 RAG가 공식 근거를 담당하고, 현재 사업장/근로자/후보자 상태는 seed/DB가 담당한다는 분리가 실제 데이터 구조에도 반영됐다는 것이다.

# 7. Phase 2 전에 생긴 변화: Phase 1B 추가

원래 계획은 다음이었다.

```
Phase 1 → Phase 2 Router
```

하지만 Phase 2 검증에 필요한 synthetic case JSON이 malformed 상태였고, `phase2-router.md`는 data file 수정을 금지하고 있었다.

그래서 phase boundary를 지키기 위해 새 phase가 끼어들었다.

```
Phase 1 → Phase 1B Repair Synthetic Cases → Phase 2 Router
```

`phase1b-repair-synthetic-cases.md`의 목표는 좁았다.

- `case_001.json`, `case_002.json`, `case_003.json`이 parse되게 고친다.
- 기존 `case_type`, `phase`, fixture intent는 보존한다.
- `human_approval_required=true`를 유지한다.
- 법적 근거를 새로 발명하지 않는다.

이 결정은 중요한 운영 방식이다. 막힌 문제가 있어도 다음 phase의 금지 범위를 깨지 않고, prerequisite phase를 별도로 만든 것이다.

# 8. Phase 1C: 검색 가능성에서 evidence 품질로 기준 상승

`phase1c-chunk-and-embedding.md`는 Phase 1 이후 생긴 개선 phase다.

이 phase의 전제는 분명하다.

```
Phase 1 reached Hit@3 = 83%, but chunking and case_type metadata are missing.
```

즉, 단순히 검색이 되느냐가 아니라, 후속 Workflow/Agent가 근거 chunk를 안정적으로 인용할 수 있느냐가 문제였다.

Phase 1C에서 계획한 변화는 다음이다.

- `src/chunk.py`로 문서 의미 단위 chunking
- `src/embed.py`로 embedding
- `src/cache/embedding_cache.py`로 sha256 기반 embedding cache
- `src/retrieve.py`를 BM25 + dense hybrid로 refactor
- `data/processed/regulation_chunks.jsonl` 생성
- `data/index/` vector index 생성
- `eval/results/phase1c_retrieval_report.md` 생성
- 목표를 `Hit@3 >= 90%`로 상향

여기서 중요한 의사결정은 `sources.json`의 `case_type: ["ALL"]` 문제를 고치는 것이었다. 모든 source가 `ALL`이면 `new_hiring`, `workplace_change_intake` 같은 케이스별 필터링이 의미 없어지기 때문이다.

# 9. Phase 1C 디버깅에서 바뀐 결정들

현재 `docs/journal/history.md`에는 Phase 1C에서 겪은 변화가 구체적으로 남아 있다.

## 9.1 Dependency 권한 문제

처음에는 Phase 1C가 새 dependency를 추가해야 했지만 phase의 `Allowed Writes`에 `pyproject.toml`, `uv.lock`이 없었다. 그래서 dependency 추가 권한을 phase spec에 명시하는 쪽으로 바뀌었다.

허용 dependency는 다음으로 제한했다.

- `openai`
- `chromadb`
- `rank-bm25`
- `pdfplumber`
- `python-dotenv`

## 9.2 `.env` 로딩 문제

`OPENAI_API_KEY`를 코드가 못 읽는 문제가 있었다. 원인은 `load_dotenv()`가 경로 없이 호출되어 sandbox에서 `.env`를 못 찾는 것이었다. 해결 방향은 `load_dotenv(root / ".env")`처럼 명시 경로를 쓰는 것이었다.

## 9.3 Chroma disk I/O 문제

Windows에서 Chroma PersistentClient의 SQLite layer가 안정적으로 열리지 않았다. 그래서 정공법인 Chroma persistent index 대신 우회 결정을 했다.

변경된 결정:

- `data/cache/embeddings.sqlite`만 영속화한다.
- dense retrieval은 numpy cosine similarity로 직접 계산한다.
- Chroma persistent storage fix는 별도 Phase 1D 후보로 미룬다.

## 9.4 `sources.json` case_type 덮어쓰기 문제

`evaluate.py`가 `sources.json`의 정확한 `case_type` mapping을 다시 `ALL`로 덮어쓰는 문제가 있었다. 이건 Phase 1C의 핵심 버그였다.

변경된 결정:

- `write_sources_metadata()`를 main flow에서 제거한다.
- report path를 `phase1c_retrieval_report.md`로 바꾼다.
- source metadata는 검색 품질의 핵심 계약으로 취급한다.

## 9.5 Q2/Q7 실패 원인과 chunk prefix 결정

`eps_allowed_industries_001` chunk에는 제조업 키워드는 있었지만 `E-9`, `허용업종` 같은 질의 핵심 키워드가 부족했다. 그래서 다른 chunk가 더 위로 올라왔다.

결정:

- industry chunk text 앞에 `[외국인근로자(E-9) 고용허용 업종]` 같은 prefix를 붙인다.
- chunk는 원문에서 잘라낸 조각이더라도, 검색 단위로는 단독 의미를 가져야 한다.

이 결정은 RAG 품질 개선의 일반 원칙으로 남았다.

# 10. Engineering Plan: 기능보다 실패 모드를 먼저 다룸

`docs/ENGINEERING_PLAN.md`는 제품 안전 기준 다음 단계의 엔지니어링 기준을 정리했다.

핵심은 “실패해도 안전하게 무너지기”다.

| 신뢰성 항목 | 결정 |
| --- | --- |
| PII masking | router 앞 middleware에서 외국인등록번호, 여권번호, 전화번호 마스킹 |
| Embedding cache | ingest pipeline 안에서 sha256 key + SQLite cache 사용 |
| Idempotency | state machine transition key로 중복 처리 방지 |
| Audit log | UPDATE 없이 INSERT-only event source로 기록 |
| Failure mode | silent fallback 금지, `blocked` 또는 `error`로 드러내기 |

이 문서 이후 phase들에는 `Silent fallback on missing metadata is forbidden`이 반복해서 들어간다. 즉, 실패를 숨기지 않는 것이 WorkBridge의 핵심 안전 설계가 됐다.

# 11. Phase 2: Router는 LLM 없이 deterministic하게

`phase2-router.md`의 목표는 workforce request intent, `case_type`, optional phase routing을 deterministic하게 구현하는 것이었다.

중요한 결정은 다음이다.

- LLM 호출 금지
- 후보 ranking 금지
- 국적 선호 추론 금지
- data file 수정 금지
- ambiguous request는 blocked style error로 처리
- `company_id`, `headcount` 같은 slot extraction은 Phase 3으로 넘김

이 단계에서 Workforce Agent는 “자연어를 잘 해석하는 AI”가 아니라 deterministic router와 schema 기반 workflow 위에 올라가야 한다는 방향이 확정됐다.

# 12. Phase 2A: PII middleware가 새로 생김

초기 실행 순서에는 Phase 2A가 없었다. 하지만 `ENGINEERING_PLAN.md`에서 PII masking이 P0로 올라오면서 `phase2a-pii-middleware.md`가 생겼다.

목표는 router, retriever, LLM call 전에 다음 값을 마스킹하는 것이다.

- 외국인등록번호
- 여권번호
- 휴대폰 번호

금지 사항은 명확했다.

- raw PII 저장 금지
- raw PII를 `retrieve.py`나 LLM에 전달 금지
- 외부 storage/network 추가 금지

즉, 개인정보 처리는 agent 내부 기능이 아니라 agent 앞단의 middleware 책임으로 분리됐다.

# 13. Phase 3: 상태 머신에서 책임 분리로 변화

`phase3-state-machine.md`의 초기 계획은 `src/case_factory.py`, `src/workflow_state.py`, `data/state.db`를 중심으로 했다.

초기 목표:

- explicit slot assembly
- evidence retrieval
- risk flags
- human approval
- idempotency
- audit_logs event source

그런데 `docs/PHASE3_REVIEW_NOTES.md`에서 중요한 리뷰가 나왔다. `workflow_state.py` 하나에 request prep, evidence retrieval, risk flags, human approval이 모두 들어가면 너무 커진다는 것이다.

제안된 v2 방향:

| 모듈 | 책임 |
| --- | --- |
| `workflow_state.py` | 상태와 전이 |
| `risk_flags.py` | risk flag 산정 룰 |
| `evidence_assembler.py` | retrieved chunks를 evidence package로 조립 |

추가 결정:

- Phase 3도 LLM 호출 금지
- risk flag enum 명시
- synthetic case 3건으로 E2E fixture 검증
- `human_approved`는 approval token 없이 도달 불가

이 변화는 단순 구현 계획 변경이 아니라, Workforce Agent의 내부 구조를 테스트 가능한 deterministic workflow로 쪼개자는 결정이었다.

# 14. Phase 4와 UI: 추천 화면이 아니라 evidence/approval 화면

`phase4-demo-ui.md`, 백업 `docs/UI_GUIDE.md`, 현재 `missions/active/005-frontend-dashboard.md`, 현재 `.claude/prompts/frontend-agent.md`는 같은 방향을 말한다.

UI는 마케팅 랜딩이나 후보 추천 화면이 아니다. 보여줘야 하는 것은 다음이다.

- 요청 입력
- checklist output
- evidence source ID
- risk flag
- approval state
- 민감정보 마스킹
- Evidence Log 접근 경로

금지:

- 후보 ranking UI
- 국적 선호 표현
- evidence source ID 숨김
- 버튼 클릭만으로 외부 발송/전송/제출 실행

# 15. 새 구조로 전환: phases에서 missions로 이동

현재 `docs/journal/history.md`와 `docs/journal/2026-05-04.md`를 보면 구조 전환 결정이 나온다.

예전 구조:

```
src/
data/
eval/
tests/
phases/
```

새 구조:

```
backend/
data-pipeline/
evals/
frontend/
infra/
missions/
docs/
```

로컬 main은 origin/main과 크게 갈라져 있었고, 예전 작업을 새 구조에 강제로 merge하면 구조 충돌과 의미 충돌이 생길 수 있었다.

그래서 결정은 다음이었다.

1. 예전 상태를 `backup/main-before-oegobanjang-sync` 브랜치로 보존한다.
2. Phase 1C WIP는 `stash@{0}`에 보존한다.
3. 새 구조 기준으로 `port-rag-indexing-new-structure` 브랜치를 만든다.
4. bulk-port하지 않고 RAG runtime/eval/chunk/report를 새 구조에 맞춰 재구현한다.
5. 예전 phase decision은 현재 docs와 missions로 이식한다.

이 결정으로 실행 단위가 바뀌었다.

| 예전 | 현재 |
| --- | --- |
| `phases/mvp/*.md` | `missions/active/*.md` |
| `src/` | `backend/app/agent_runtime/` |
| `data/raw/` | `data-pipeline/raw/` |
| `data/processed/` | `data-pipeline/processed/` |
| `eval/` | `evals/` |

# 16. 새 구조에서 정리된 mission

현재 `missions/active/*.md`는 예전 phase를 새 구조 기준으로 다시 나눈 것이다.

| Mission | 역할 | 예전 phase와의 관계 |
| --- | --- | --- |
| `001-agent-runtime-skeleton.md` | Intent Router, Planner, Executor mock, Approval Gate, Evidence Logger skeleton | Phase 2/3의 공통 runtime 기반 |
| `002-rag-indexing.md` | 공식 문서 수집, chunk metadata, retrieval eval | Phase 1/1C의 새 구조 버전 |
| `003-approval-evidence-log.md` | Human Approval, Evidence Log 저장 구조 | Phase 3의 approval/audit 부분 |
| `004-backend-core-api.md` | FastAPI API/DB/model skeleton | 새 backend 제품 API 기반 |
| `005-frontend-dashboard.md` | dashboard, approvals, evidence UI skeleton | Phase 4 demo UI의 제품 구조 버전 |

이 전환 때문에 현재 새 구조 브랜치에는 `phases/` 디렉터리가 없다. 대신 예전 phase의 결정들이 `missions/active`와 `docs/*.md`에 흡수됐다.

# 17. 2026-05-04 결정: 공통 계약과 Guardrail as Code

현재 `docs/journal/2026-05-04.md`와 새 docs 파일들은 예전 phase decision을 새 구조에 맞춰 재정리한 결과다.

추가/수정된 문서:

- `docs/SCHEMA_CONTRACT.md`
- `docs/STATE_MACHINE.md`
- `docs/EVAL_METRICS.md`
- `docs/EVIDENCE_LOG_SCHEMA.md`
- `docs/OBSERVABILITY.md`

핵심 변화:

| 변경 | 의미 |
| --- | --- |
| `case_id` → `work_item_id` | case/eval/work item 식별자 표준화 |
| `phase` → `current_state` / `next_state` | 단계가 아니라 상태 전이로 표현 |
| `human_approval_required` → `requires_human` | 승인 필요 여부 표준화 |
| audit log event source | 상태 복원 가능한 append-only 기록 |
| `action_type` 표준화 | `retrieve`, `judge`, `approve`, `handoff`, `route`, `plan`, `execute_tool`, `block` |
| eval metric 3분리 | 자동화 지표, 휴먼 리뷰 지표, 비즈니스 지표 분리 |

또 `backend/app/agent_runtime/guardrails.py`가 추가됐다. 이건 금지 행동을 문서에만 두지 않고 코드에서 차단하기 위한 결정이다.

차단 대상:

- 후보 추천
- 국적 선호
- 비자 가능 여부 자동 확정
- 법률/노무 자문
- 정부 포털 제출
- 승인 없는 외부 제출
- 근로자 감시
- 이탈 가능성 예측
- 성실도/신뢰도 점수화
- 사업장 공개 평판 점수화
- 브로커 색출

검증 기록:

```powershell
uv run pytest backend/tests/test_guardrails.py
uv run pytest
```

기록된 결과는 guardrail 단위 테스트 `5 passed`, 전체 backend test suite `13 passed`다.

# 18. 현재 실제 상태

현재 브랜치 `port-rag-indexing-new-structure` 기준으로 상태를 나누면 다음과 같다.

## 커밋된 것

- RAG runtime: `backend/app/agent_runtime/rag/*`
- RAG tests: `backend/tests/test_rag_*`
- seed/eval/chunk 산출물: `data-pipeline/seed/*`, `data-pipeline/processed/chunks/*`, `evals/datasets/rag_retrieval_cases.jsonl`, `evals/reports/*`
- ingest entrypoint: `scripts/ingest_rag_docs.py`
- generated artifact ignore 정책: `.gitignore`

## 로컬 변경으로 남은 것

- `backend/app/agent_runtime/guardrails.py`
- `backend/tests/test_guardrails.py`
- `docs/SCHEMA_CONTRACT.md`
- `docs/STATE_MACHINE.md`
- `docs/EVAL_METRICS.md`
- `docs/EVIDENCE_LOG_SCHEMA.md`
- `docs/OBSERVABILITY.md`
- `docs/journal/2026-05-04.md`

## 아직 상세 구현 전인 것

현재 파일 크기 기준으로 아래는 0바이트 또는 skeleton 이전 상태다.

- `backend/app/agent_runtime/agents/hiring_agent.py`
- `backend/app/agent_runtime/tools/quota_tool.py`
- `backend/app/agent_runtime/graph/nodes/intent_router.py`
- `backend/app/agent_runtime/graph/nodes/planner.py`
- `backend/app/agent_runtime/graph/nodes/executor.py`
- `backend/app/agent_runtime/graph/nodes/approval_gate.py`
- `backend/app/agent_runtime/graph/nodes/evidence_logger.py`
- `backend/app/agent_runtime/graph/workflow.py`
- `backend/app/agent_runtime/schemas/*.py`

즉, 지금 완료된 것은 Workforce Agent 상세 실행 로직이 아니라, 그 실행 로직이 올라갈 RAG 기반, 문서 계약, mission 구조, guardrail 정책이다.

# 19. 의사결정 변화 요약

| 순서 | 원래 계획/상태 | 바뀐 결정 | 이유 |
| --- | --- | --- | --- |
| ---: | --- | --- | --- |
| 1 | 인력확보 agent 구상 | 채용 매칭이 아니라 절차·서류·근거 정리 agent | EPS/송출회사가 매칭을 담당하고 사업주 pain은 행정 부담이기 때문 |
| 2 | 바로 agent 구현 가능 | schema/eval/RAG thin slice 먼저 | 공식 근거와 안전 범위를 먼저 고정해야 해서 |
| 3 | 5문서 수준 RAG | 6개 공식 문서 + 점수제 source 추가 | EPS 현실의 점수제·도입 경로를 반영하기 위해 |
| 4 | 5 chunk type | `scoring_criterion` 추가해 6 chunk type | 사업장 점수제 항목별 근거 인용 필요 |
| 5 | Phase 1 후 Router | Phase 1B fixture repair 추가 | Phase 2가 data 수정을 금지했고 synthetic JSON이 깨져 있었음 |
| 6 | Hit@3 83%면 충분 | Phase 1C로 structured chunk + dense retrieval | citation 품질과 case_type filter가 부족했음 |
| 7 | Chroma persistent index | SQLite cache + numpy cosine similarity 우회 | Windows Chroma disk I/O 문제 |
| 8 | source metadata 생성 | `case_type=ALL` 덮어쓰기 제거 | 케이스별 evidence filtering이 망가졌기 때문 |
| 9 | product guardrail 중심 | PII/cache/idempotency/audit/failure mode 추가 | 데모가 아니라 안전하게 실패하는 구조 필요 |
| 10 | Phase 3 단일 `workflow_state.py` | state/risk/evidence 책임 분리 제안 | 한 파일에 책임이 몰리면 테스트와 리뷰가 어려움 |
| 11 | 예전 `phases/` 유지 | 새 구조 `missions/active`  • `docs`로 이식 | repo가 oegobanjang monorepo 구조로 바뀜 |
| 12 | 문서 guardrail | Guardrail as Code | 금지 행동은 최종 출력에서 코드로 차단해야 함 |

# 20. 다음 실행 기준

다음 작업은 예전 phase를 그대로 복원하는 것보다 새 구조 기준으로 이어가는 것이 맞다.

추천 순서:

1. `data-pipeline/raw/`로 공식 raw source migration을 별도 커밋으로 처리한다.
2. `source_manifest.json`을 새 경로 기준으로 수정한다.
3. `docs/SCHEMA_CONTRACT.md`와 `docs/STATE_MACHINE.md` 기준으로 Workforce eval fixture를 작성한다.
4. `intent_router_cases.jsonl`, `workflow_e2e_cases.jsonl`, `safety_guardrail_cases.jsonl`을 비어 있는 상태에서 실제 케이스로 채운다.
5. `intent_router.py`, `planner.py`를 LLM 없이 deterministic하게 구현한다.
6. `hiring_agent.py`는 후보 추천기가 아니라 `site_check`, `candidate_intake`, `contract_prep` 초안 생성기로 구현한다.
7. `quota_tool.py`는 EPS 점수 확정기가 아니라 입력 상태 기반 readiness/checklist 계산 도구로 제한한다.
8. `guardrails.py`를 executor output 또는 final response 직전에 연결한다.
9. Evidence Logger는 `route`, `plan`, `retrieve`, `execute_tool`, `block`, `approve`를 append-only event로 남긴다.
10. 승인 필요한 작업이 자동 실행되지 않는지 E2E로 검증한다.

# 검토 파일 분류

전수 확인한 md는 아래처럼 분류된다.

| 분류 | 파일 |
| --- | --- |
| 제품/방향성 | 현재 `README.md`, `AGENTS.md`, `docs/PROJECT_BRIEF.md`, `docs/AI_OS_DESIGN.md`, 백업 `docs/PRD.md`, 백업 `README.md` |
| Workforce 원계약 | 백업 `01_workforce_agent_schema.md`, `02_week1_checklist_eval.md`, `docs/DATA_GUIDE.md` |
| 하네스/실행 방식 | 백업 `03_codex_harness_engineering.md`, `.agents/skills/*`, `phases/templates/phase_template.md`, 현재 `.claude/*`, `missions/README.md` |
| phase 실행 계획 | 백업 `phases/harness/phase0-harness-bootstrap.md`, `phases/mvp/phase1*`, `phase2*`, `phase3*`, `phase4-demo-ui.md` |
| 현재 mission | 현재 `missions/active/001`부터 `005`까지 |
| 현재 설계 계약 | 현재 `docs/SCHEMA_CONTRACT.md`, `STATE_MACHINE.md`, `EVIDENCE_LOG_SCHEMA.md`, `EVAL_METRICS.md`, `OBSERVABILITY.md` |
| 데이터/DB/API | 현재 `docs/DB_SCHEMA.md`, `API_CONTRACT.md`, `DATA_GENERATION_REPORT.md`, `backend/README.md` |
| 평가/검증 | 현재 `docs/EVAL_HARNESS.md`, `evals/README.md`, 백업 `eval/results/phase1_retrieval_report.md` |
| 인수인계/구조 | 현재 `docs/HANDOFF.md`, `FOLDER_STRUCTURE.md`, 백업 `docs/ARCHITECTURE.md`, 현재 `docs/ARCHITECTURE.md` |
| 작업 기록 | 현재 `docs/journal/history.md`, `docs/journal/2026-05-04.md` |

결론적으로, md 전수 확인 후에도 큰 흐름은 바뀌지 않는다. 다만 이전 정리보다 더 분명해진 점은 “처음부터 agent 구현보다 계약과 eval이 우선이었다”는 것이다. 인력확보 에이전트는 채용 추천 AI가 아니라, 공식 근거 기반으로 신규 고용 준비 업무를 안전하게 상태화하고, 사람 승인 전까지 초안과 검토 항목을 만드는 agent로 점점 좁혀졌다.