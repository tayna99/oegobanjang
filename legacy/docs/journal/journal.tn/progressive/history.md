# WorkBridge Project Journal — History

> 인력 확보 agent 담당으로 5~7월 외국인 고용 Agentic OS MVP 작업 중.
> Q+A+의사결정 누적 기록. 2026-05-02 ~ 2026-05-03.

---

## 1. 프로젝트 방향성

### Q. 인력 확보 agent 어디부터 시작?
**A.** RAG 기본 구축이 맞지만 그 전에 *입출력 계약(contract)* 먼저 잡아야 안전. 7단계(수집→정제→chunking→embedding→VectorDB→검색→품질) 그대로 가되, 처음엔 thin slice로 5문서·12 eval로 끝까지 돌려보고 freeze.

**결정**:
- 단순 매칭이 아니라 *절차·서류·증거 정리* agent로 포지션
- RAG 인덱스 1차는 작게 시작, 도메인 chunking 우선
- Eval 12문항 + 합성 케이스 3건으로 vertical slice

---

### Q. workvisa 같은 채용 매칭 플랫폼?
**A.** 양면 시장(사업주+노동자) cold-start 비싸고, EPS·송출회사가 이미 매칭 함. 사업주 단면(행정 부담)을 풀어주는 게 차별화.

**결정**:
- PRD Non-Goals에 "Candidate ranking, suitability scoring, nationality preference" 박음
- 인력 확보 agent도 *후보 추천*이 아니라 *채용 전 절차 어시스턴트*로 정의
- Worker pool 만들지 않음

---

### Q. 도메인을 어떻게 추상화? (case_type)
**A.** EPS의 4가지 사업주 인력 확보 경로로 잡음:
- `new_hiring` (신규 도입)
- `rehire_loyalty` (성실근로자 재입국)
- `workplace_change_intake` (사업장 변경 intake)
- `same_worker_rehire` (동일 외국인 재고용)

**결정**: chunk_type 6종(`law_clause / procedure_step / industry_entry / form_field / template / scoring_criterion`)도 동시에 enum 박음.

---

## 2. 아키텍처 — 세 agent 수렴 지점

### Q. 인력 확보·다국어·비자·서류 agent가 어디서 만나나?
**A.** 4개 layer에서 만남. 직접 호출 X.
- **Layer 1 Data**: companies/employees/candidates (SQLite) + RAG (regulation_chunks + cache)
- **Layer 2 Schema**: case_type 4종, chunk_type 6종, evidence_grade A~F
- **Layer 3 Workflow**: LangGraph 그래프. 진짜 만나는 곳은 `Aggregator` + `Human Approval` 두 노드만
- **Layer 4 Output**: case_id로 그룹화, chunk_id 인용, audit_logs INSERT-only

**결정**:
- Agent 간 직접 호출 금지 (shared state로만 소통)
- Single source of truth (DB·RAG·audit_logs)
- Human approval gate 통일

---

## 3. 엔지니어 측 기획 — 신뢰성 5

### Q. Product 안전 가드 외에 엔지니어로서 추가할 게 있나?
**A.** 5개. *demo → production-ready*의 가장 짧은 길.

| # | 항목 | 위치 | 우선순위 |
|---|---|---|---|
| 1 | PII 마스킹 (외국인등록번호·여권번호) | router 앞 middleware | P0 |
| 2 | Embedding cache (sha256 → vector) | ingest pipeline | P0 |
| 3 | Idempotency in state machine | `(case_id, from_state, to_state)` | P1 |
| 4 | Audit log as event source (INSERT-only) | data/state.db | P1 |
| 5 | Failure mode 명시 (silent fallback 금지) | 모든 phase Stop Conditions | P1 |

**결정**: `docs/ENGINEERING_PLAN.md`로 저장. ADR-003·004·005·006 후보로 박아둠.

---

## 4. Phase 1C 디버깅 (가장 길었던 구간)

### Q. Phase 1 외형 통과(Hit@3 = 83%)지만 chunk·embedding 미생성. 어떻게?
**A.** Phase 1C 신규 phase 작성. spec에 chunking + embedding + Hit@3 ≥ 90% 박음.

**결정**: 외형 통과 ≠ 내실 통과. retrieval 품질이 후속 Phase 인용 품질에 직결되므로 보강.

---

### Q. Codex가 Phase 2 review에서 4개 fail로 reject. 진짜 fail인가?
**A.** 아니. review tool이 *내 채팅 메시지를 spec*으로 잘못 비교한 결과. 실제 `phases/mvp/phase2-router.md` spec 기준으로는 4개 다 PASS.

**결정**: review skill 호출 시 phase 파일 명시적으로 입력하도록. 이후 Phase 2A에 PII middleware로 분리 계획.

---

### Q. Phase 1C blocker 1: dependency 추가 권한 없음
**A.** spec의 Allowed Writes에 `pyproject.toml`, `uv.lock` 추가 + Allowed Dependencies 5개(`openai, chromadb, rank-bm25, pdfplumber, python-dotenv`) 명시.

---

### Q. Phase 1C blocker 2: OPENAI_API_KEY를 코드가 못 읽음
**A.** `load_dotenv()`가 인자 없이 호출되어 sandbox에서 .env 못 찾음. `load_dotenv(root / ".env")`로 명시 경로 박음.
+ `.env` 파일 첫 글자에 잘못 들어간 `e`(eOPENAI_API_KEY=...) 발견. 정규식으로 수정.

**결정**: `src/embed.py`, `src/retrieve.py` 모두 명시 경로 사용.

---

### Q. Phase 1C blocker 3: Chroma PersistentClient disk I/O 사고
**A.** Windows에서 chromadb의 SQLite layer가 안정적으로 안 열림. 우회 결정 — cache (raw sqlite3) + numpy cosine similarity로 dense retrieval.

**결정**:
- `data/cache/embeddings.sqlite`만 영속 (chromadb 안 씀)
- `src/retrieve.py`에서 numpy로 cosine similarity 직접 계산
- 정공법은 별도 Phase 1D로 미룸 (Windows Defender 예외 / 다른 path / 버전 변경 등)

---

### Q. Phase 1C blocker 4: `evaluate.py`가 sources.json case_type을 ALL로 덮어씀
**A.** Phase 1 코드의 `write_sources_metadata()`가 main()에서 호출되며 case_type 정확 매핑을 파괴. main()에서 호출 제거 + report path를 `phase1c_retrieval_report.md`로 변경.

---

### Q. Hit@3 = 83% 그대로, Q2/Q7 실패 원인?
**A.** `eps_allowed_industries_001` chunk가 "제조업" 키워드는 있지만 "E-9", "허용업종" 키워드 없음. BM25/dense가 그 키워드 가진 다른 chunk를 위로 올림.

**결정**: `build_industry_chunks()`에서 chunk_text 앞에 `[외국인근로자(E-9) 고용허용 업종]` 섹션 prefix 박음. *chunk text가 단독으로 의미 통하게 만들기*가 일반 원칙.

---

## 5. 노션 페이지 업데이트

### Q. 기획 md 파일 4개 기준으로 노션 4개 페이지(PRD/운영이슈/제품로드맵/리스크) 업데이트해줘.
**A.** 4개 페이지 다 업데이트:

- **PRD 1**: §1-bis Agentic OS 포지션 + 3 Mission/8 Sub-agent 매핑 + §12-bis BM 방향(화이트라벨) + Non-goals 추가
- **제품 로드맵**: Phase 0 (4-5주 학원 MVP) 신설, Week 1~5 일정 + 15개 명시적 구현 항목
- **리스크 및 제약 조건**: 전면 재작성 — Top Risks 15개 + 즉시중단 트리거 8개 + 가정 7개 + Non-goals 11개
- **운영 이슈 DB**: 7개 시드 entry (P0 PII, P0 BM 미검증, P1 Phase 1 baseline 등)

---

## 6. 폴더 구조 마이그레이션

### Q. 폴더 구조를 monorepo (backend/data-pipeline/evals/...)로 바꾸고 싶음
**A.** 좋은 방향. 다만 Phase 1C 끝나기 전 진행은 위험. 별도 Phase 1E spec 작성하고, Phase 1C completed 이후 실행으로 고정.

→ 그 사이 *팀이 GitHub origin/main에 새 monorepo 구조를 먼저 정리*. Phase 1E를 사실상 자동 완료.

**결정**:
- 로컬 main 강제 동기화 X (15 ahead 작업 보존)
- `backup/main-before-oegobanjang-sync` 브랜치 + `stash@{0}`로 백업
- `port-rag-indexing-new-structure` 브랜치 위에 RAG 작업 *재구현* (bulk-port X)

---

### Q. 6 commit으로 push 마무리
**A.** `.gitignore` 패치 → RAG 코드 → 테스트 → 데이터(10개 chunks) → eval cases → 최신 리포트 2개 → push.

**결정**:
- `data-pipeline/cache/`, `data-pipeline/index/`, `evals/reports/*.json` 무시
- 최신 리포트 2개만 `-f`로 강제 add (증거용)

PR 링크: https://github.com/PotenupAI/oegobanjang/pull/new/port-rag-indexing-new-structure

---

## 누적 의사결정 (한눈에)

1. **방향성**: 채용 매칭 X, 서류·리스크 알리미 ✓
2. **case_type 4종**: new_hiring / rehire_loyalty / workplace_change_intake / same_worker_rehire
3. **chunk_type 6종 + evidence_grade A~F**: enum 강제
4. **agent 간 직접 호출 금지**: shared state로만 소통
5. **Human approval 게이트 통일**: 외부 발송 시도는 단 한 곳에서만
6. **Chroma 우회**: cache + numpy (Windows disk I/O 사고)
7. **PII 마스킹**: 1순위 신뢰성 항목, Phase 2A 신규 phase
8. **Phase 1E**: 폴더 구조 migration이지만 팀이 origin/main에서 먼저 정리
9. **gitignore 정책**: cache·index·timestamped reports 무시, 최신 리포트만 force-add
10. **학습 매핑**: 5일차 builtin middleware (PII/HITL/Summarization)가 도메인에 직접 적용

---

## Out-of-scope (절대 안 함, 11종)

기획문서 §15에서 박힘. PRD Non-goals + 리스크 페이지에 일관 반영.

1. 정부 포털 자동 제출
2. AI 단독 비자 가능/불가능 판정
3. AI 단독 법률·노무 자문
4. 이탈 예측
5. 국적별 추천
6. 외국인 직원 평가 점수
7. SNS·단톡방·커뮤니티 감시
8. 출입국 직원 개인 성향 분석
9. 브로커 색출
10. 승인 없는 메시지 자동 발송
11. 후보자 성격·성실도·장기근속 가능성 평가

---

## 다음 액션 (이 시점 이후)

1. PR review 받고 merge
2. Phase 1C status를 completed로 갱신 (Hit@3 ≥ 90% 확인 후)
3. Phase 2A (PII middleware) 신규 spec 작성·실행
4. Phase 3 (LangGraph state machine) 진입 — Week 3.5 학습과 병행
5. Mission 단위로 phase spec 옮기는 정책 팀과 합의 (`phases/` → `missions/`)
