# 미구현 전수조사 · 시드/필러 데이터 설계 — 2026-07-20

> 성격: 저장소 전체의 **미구현 지점 전수조사**(Part A)와 **시드/필러 데이터 설계**(Part B), 그리고
> 그 설계를 ROADMAP으로 승격한 **SD 트랙**(Part C)의 정본. `plans/NEXT_ROADMAP_2026-07-16.md`의
> 후속이다 — 그 문서가 R0~R5를 고정한 뒤, 이 문서는 "빈 DB에서도 제품이 동작하려면 필요한 시드"를
> 별도 트랙으로 분리·설계·구현했다.
> 조사 방법: 프론트 전수(Explore)·백엔드+DB 전수(Explore)·시드 설계(Plan) 3개 에이전트 병렬 후,
> 계획이 의존하는 핵심 사실을 원본 파일(seed_demo·schema·context_service·rag CSV·dataSeed 등)에서
> 직접 재검증. 구현분은 Part C의 SD-0~SD-2(이번 세션 완료).

---

## Part A — 미구현 전수조사

> 코드 마커(TODO/FIXME/미구현)는 backend·src 전역 0건 — 아래는 문서·구조로 추적되는 실제 인벤토리.

### A1. 로드맵상 미착수 마일스톤
- **R3 메시징 실연동** — outbox·SmsAdapter·응답링크 인바운드·AlimtalkAdapter(+SMS폴백)·ZaloAdapter·EmailAdapter. 현재 ①MockAdapter까지만(`docs/MESSAGING_CHANNELS.md` §5).
- **R4 에이전트 런타임 실연결** — legacy 자산 이관(Daily Briefing 룰엔진·번역·응답해석·평가하네스). M5(RAG)·M7(오케스트레이션 G1~G6)이 rag·backend 측은 선행했으나 프론트 결선 미완.
- **R5 파일럿 확장** — 5.1 화이트라벨 v1 백엔드(법무 §26 vs §17 분류 선확인 필수), 5.2 OCR 파이프라인, 5.3 컨트롤타워 실집계, 5.4 알림·푸시, 5.5 PC 나비 IA, 5.6 후순위.
- **M5.5 후속** — Playwright 크롤러 `[crawl]`, OpenAI 운영 인덱스(≈$0.02), langgraph-checkpoint-postgres.

### A2. 백엔드는 준비됐는데 프론트가 안 부르는 것 (BACKEND_CONNECT B4 잔여 — 배선 대기, 영구 mock 아님)
| 서버 (완료) | 프론트 상태 |
|---|---|
| `GET /api/v1/citations` (B2) | 어댑터 `src/lib/api/citations.ts`가 **아예 없음** — citationStore가 mock `CITATION_LIBRARY` 직접 소비 |
| `POST /api/v1/runs/stream` (B3', SSE) | 미배선 — runEngine이 430ms 각본 재생만 |
| `GET /api/v1/briefings/latest` | `fetchLatestBriefing()`는 있으나 **어느 화면에도 미배선** — `dataSeed.ts:19-25`가 사유 자체 진단(브리핑 서브셋이 caseStore 오염 → 전용 스토어 슬롯 필요) |

### A3. 백엔드 미구현 (ORM 모델만 있고 서비스/API 경로 0인 테이블 10개)
worker_intake_files·**drafts·draft_variants**(M3 초안 — 시드는 있는데 read API 없음)·status_update_proposals·package_exports(PDF 서버측 없음)·notifications·csv_imports·autonomy_grants·agent_notes·stat_snapshots(파생 캐시, 소비자 0).
- `run_service.py:129-135`: 커맨드 런이 승인 필요 시 `waiting_approval` 상태만 — **approvals 행·case 미생성**(case 생성은 Daily Briefing 룰엔진 몫, 후속).
- 쓰기 API 없는 도메인: workers, worker_documents, drafts, threads(쓰기), 위임 관리, package export.
- DB_SCHEMA §10 페이징: P1 18테이블(완료) → P2(threads·interpretations·handoff read 완료) → **P3**(delegations 관리·notifications·csv_imports·intake·autonomy·agent_notes·stat_snapshots).

### A4. R2 완료 후 명시적으로 남긴 경계 (문서화된 mock 또는 후속)
- 패키지 문서 **콘텐츠**(검토요청서 본문·항목 토글) → `mocks/packages.ts`. 서버는 링크 생존만 검증.
- 행정사 구조화된 회신(`package_reply`) → 서버 엔드포인트 없음, real 모드 "준비 중" 안내.
- 위임 **관리**(발급/철회) 화면·API 없음(P3) — `GET /delegations/mine` 조회만.
- CASE_SHEETS 콘텐츠(summary·docs·activity·nextWake) → real 모드 3필드 서브셋만.
- 화이트라벨 개인 경로(`/expert/:expertId/*`) → mock 인증(M-11 잔여, R5.1).
- CSV → 클라이언트 파싱만. OCR 서류스캔 2곳 "준비 중" 정적 카드. 인증 목업(mock OTP 임의 6자리, DEMO_PIN='1234').

### A5. 필러(하드코딩 KPI)·구조적 부채
- `OwnerHomeWorkbench` MOCK_APPROVAL_DURATION, `EXECUTED_WEEKLY_MOCK=12`, 컨트롤타워 PIPELINE_DELTAS·WEEKLY_ACTIVE_TREND — 전부 하드코딩(D-6 실벽시계/DEMO_TODAY 혼용).
- B-5 미사용 타입(`NextActionState` locked/scheduled/waiting, `DraftLangCode` 'en', `CitationGrade` 'C') — **의도적 보존**(스키마 CHECK·향후 화면 참조). `docs/ARCHITECTURE.md` §5.1에 명시.
- D-5(Page/Screen/Workbench 명명) 보류, PC 프리셋 필터 5종 미채택.

> **영구 mock vs 배선 대기**의 구분은 `docs/ARCHITECTURE.md` §5.1(영구 mock 경계)이 정본.

---

## Part B — 시드/필러 데이터 설계

### 핵심 통찰
**빈 DB(신규 테넌트)에서도 구조적으로 필요한 부트스트랩 시드는 정확히 2개 테이블** — `document_requirements`(전역 룩업, `context_service._load_document_requirements`가 전량 읽어 ContextSnapshot에 실음)와 전역 `citations`(A/B, 승인 citation-gate·`v_global_usable_citations`·`document_requirements.citation_id` FK 공급원). 나머지 31개는 테넌트 런타임 데이터이거나 소비자 없는 P3 → "시드=데모". 이 2개를 `seed_demo.sql`에서 분리해 **`db/seed_reference.sql`(전 환경 필수)**로 승격하는 것이 설계의 축이다.

### B1. 33테이블 시드 전략
- **프로덕션 부트스트랩 (2)**: `document_requirements`, 전역 `citations`(A/B) → `seed_reference.sql`.
- **데모 보강 (4)**: `users`/`memberships`(이대표 owner·최감사 viewer 부재), `threads`/`thread_messages`(mock 3 ↔ 시드 1), `evidence_events`(스레드 발신 대응 소폭) → `seed_demo.sql`.
- **런타임 유지 (17)**: companies·workers·cases·approvals·runs·drafts·briefings 등. `handoff_packages`는 **link_token 시드 금지**(회전 원칙) — 데모는 발급 API 스텝.
- **P3 보류 (10)**: worker_intake_files·notifications·csv_imports·autonomy_grants·agent_notes·stat_snapshots·package_exports 등.

### B2. document_requirements → rag CSV 직접 로드 불가, curated SQL 신규작성
rag `document_requirements.csv`(22행)는 `case_type` 영문(stay_extension 등)·doc명 영문 슬러그라 DB 계약과 불일치. **정본 = 한국어 라벨**(worker_documents·프론트·데모 전부 한국어). CSV 지식을 원천으로 매핑표를 사람이 검수해 재작성: `stay_extension→visa_expiry`, `employment_change→reporting_deadline`, `new_hiring→hiring`. E-9·H-2 모두 수록. `citation_id`는 전역 citation FK(트리거 강제, 연결불가 행 NULL). CSV는 rag 코퍼스(E등급) 정본으로 존치 — 파일 통합 안 함, 헤더 주석에 원천·매핑·양쪽 갱신 규칙 기록.

### B3. 전역 citations → 정적 SQL curated 시드가 정본 (인제스천 아님)
rag 인제스천(`upsert_citations`)은 조문/청크 granularity(6법령=수백 조문)라 라이브러리를 수백 행으로 만든다. 소비자 3곳은 "문서 수준 제목"을 원함. 인제스천은 **런이 실제 인용한 근거만 lazy upsert하는 증분 경로**로 역할 분리. 데모 전역 7행(cit_001~011) 승격 + 코퍼스 문서 메타(publisher·url·retrieved_at)에서 확장한 ~20행. A/B만 전역(company_id NULL·official), E등급 0행, D/F 0행 — validate.py 불변식 검증으로 회귀 잠금.

### B4. 데모 시드 패리티 (real 모드 8단계 대본)
- **추가**: 이대표(owner)·최감사(viewer) 계정(pin_hash '1234' 규칙 승계, viewer는 NULL) / th_nguyen(빈 스레드)·th_bayar(SMS 발신)+발신 메시지(direction='system')+evidence #4742·#4720(dispatch_executed) / real 모드 데모 runbook(`docs/REALMODE_DEMO_RUNBOOK.md`).
- **추가 안 함**: expert 계정(서비스 DB에 expert 테이블 없음, R5.1) / 2번째 테넌트·levan 패키지(소비 화면 mock 전용) / link_token 시드(런타임 발급) / 공동대표 프리셋 케이스(데모 대본 보존).

### B5. 프론트 mock↔서버 갭 해소 순서 → (d)경계문서화 → (a)미배선 API → (b)drafts API → (c)CASE_SHEETS
1. **(d)** RUN_CONFIGS·replay·DEMO_TODAY·KPI 필러를 "영구 mock"으로 문서화(코드 0줄) — SD-0(완료).
2. **(a)** `GET /citations`→hydrate, `GET /briefings/latest`→전용 스토어 슬롯, `POST /runs/stream`→SSE — SD-3·SD-4.
3. **(b)** `GET /cases/{id}/draft` 신설(시드 완비, 읽기전용) — SD-5. 쓰기는 R4.4.
4. **(c)** `GET /cases/{id}` 확장(checked_items·next_wake 컬럼 존재)+worker_documents+activity 파생 — SD-6.

### B6. 필러 KPI → 전부 mock 유지 + R5.3에서 stat_snapshots 파생 전환 예약 (SD-7)
지난주 이력값이라 활성 상태 파생 불가 — stat_snapshots가 정확히 이 용도. mock 모드는 영구 mock, real 파생만 R5.3에 흡수(별도 착수 금지).

### B7. 시드 로딩 메커니즘
- 시드는 **마이그레이션 밖**(Alembic=스키마 단일 진실). 배포 3단: `alembic upgrade head` → `seed_reference.sql`(전 환경) → `seed_demo.sql`(데모만).
- 얇은 러너 **`db/load.py`**(uv 인라인 psycopg, `--reset/--reference-only/--with-demo`) — psql 없는 환경 대응, SQL이 정본.
- conftest 전역 주입 안 함(건수 세는 테스트 깨짐) — validate.py 불변식 검증 + backend 통합 테스트로 대신.
- alembic_version 드리프트 복구 절차를 `db/README.md`에 명문화(dev는 재구축이 정본, stamp 조작 금지).

---

## Part C — SD 트랙 (ROADMAP 승격)

R3(메시징)·R4(에이전트)·R5(파일럿)와 독립인 시드·배선 트랙. 스키마 변경 0(마이그레이션 0004 불필요)이 전 태스크 공통.

| # | 태스크 | 레벨 | 의존 | 상태 |
|---|---|---|---|---|
| SD-0 | mock-forever 경계 문서화 + 178/181→187 정합 | L1 | — | ✅ 완료(2026-07-20) |
| SD-1 | `db/seed_reference.sql` + `db/load.py` + validate 불변식 5건 | L2 | SD-0 | ✅ 완료(2026-07-20) |
| SD-2 | 데모 패리티 시드(owner/viewer·스레드 3종·evidence #4720/#4742) + real 모드 runbook | L1 | SD-1 | ✅ 완료(2026-07-20) |
| SD-3 | citations hydrate + briefings 전용 슬롯 배선 (B4a) | L2 | SD-1 | ✅ 완료(2026-07-20) |
| SD-4 | 런 SSE 배선 `streamRunSteps` (B4b) | L3 | SD-3 | ⬜ 후속 |
| SD-5 | drafts read API(`GET /cases/{id}/draft`) + DraftPage real 배선 | L2 | SD-2 | ✅ 완료(2026-07-20) |
| SD-6 | CASE_SHEETS 콘텐츠 패리티(checked_items·worker_documents·activity 파생) | L3 | SD-5 | ⬜ 후속 |
| SD-7 | KPI 실집계(stat_snapshots) — R5.3에 흡수, 별도 착수 금지 | — | R5.3 | ⬜ 흡수 |

### 이번 세션 구현 요약 (SD-0~SD-3, 2026-07-20)
- **신규(SD-0~SD-2)**: `db/seed_reference.sql`(전역 citations 20 + document_requirements 22), `db/load.py`, `docs/REALMODE_DEMO_RUNBOOK.md`, 이 문서.
- **신규(SD-3)**: `src/lib/api/citations.ts`(CitationOut→CitationRecord 매핑) + `citationStore.hydrate`, `src/stores/briefingStore.ts`(fetchLatestBriefing 최초 배선), `src/lib/briefing.ts`의 `formatBriefingDate`.
- **수정(SD-0~SD-2)**: `db/seed_demo.sql`(전역 시드 이동 + owner/viewer·스레드·evidence 보강), `db/validate.py`(로드 순서 + 불변식 5건, 181→187), `db/README.md`(3단 배포·드리프트 복구·187), `.github/workflows/ci.yml`(187), `docs/ARCHITECTURE.md`(§5.1 영구 mock 경계 + 187), `docs/DB_SCHEMA.md`·`backend/README.md`(187), `AGENTS.md`(시드 구조 + fetch 0건 정합), `plans/BACKEND_CONNECT.md`(경계 상호참조), `plans/ROADMAP.md`(SD 트랙).
- **수정(SD-3)**: `src/stores/sessionStore.ts`(`companyId` 필드 — citations.py가 cases.py/threads.py와 달리 company_id를 쿼리로 명시 요구), `src/lib/dataSeed.ts`(`useSeedCitations`/`useSeedBriefing`), `GovernancePage.tsx`/`BriefingHomePage.tsx` 배선. 부수: `.claude/launch.json` 로컬 프리뷰 서버 실행 버그 수정(별도 커밋).
- **검증**: `db/validate.py --reset` → **PASS 187 / FAIL 0**(citations 22·evidence 12·threads 3·users 5·document_requirements 22). backend pytest 241 passed. 프론트 `npm run verify`(typecheck→lint→test **586건**→build) 전부 PASS(SD-0~2는 프론트 무접촉, SD-3은 신규 25건 포함 무회귀). 브라우저 실검증: 모바일 BriefingHomePage·데스크톱 GovernancePage 둘 다 mock 모드 시각 변화 없음 확인. 스키마 변경 0.
- **불변 제약 준수**: 직접 발송 없음(스레드 시드=과거 이력, direction='system')·evidence append-only·PII 원문 없음(마스킹만)·F등급 0행·RUN_CONFIGS 보존·localStorage 무접촉·pin_hash AUTH_PEPPER 규칙 승계·승인 낙관적 갱신 금지(citations/briefings는 감사 게이트가 아니라 hydrate로 단순 교체, 승인 원칙과 무관).

### SD-5 구현 요약 (2026-07-20)

**drafts read API + DraftPage real 배선.**
- **신규**: `backend/app/schemas/draft.py`(`DraftLangVariantOut`·`DraftOut`), `backend/app/services/drafts.py`(`get_draft_out` — "가장 관련 있는 살아있는 초안" 선택 규칙: `rejected`/`superseded`가 아닌 것 중 최근 생성분, 전부 종결이면 최근 1건 폴백, 초안 자체가 없으면 None→404), `backend/tests/test_api_drafts.py`(8건 — 종결 상태 필터링·폴백·is_revised 노출·테넌트 격리·404 3종). `src/lib/api/drafts.ts`(DTO→`Draft`/`DraftLangVariant` 매핑 + 언어 라벨 맵), `src/lib/api/drafts.test.ts`(4건), `src/features/draft/DraftPage.realApi.test.tsx`(5건).
- **수정**: `backend/app/api/v1/cases.py`(`GET /{case_id}/draft` 라우트 추가), `src/features/draft/DraftPage.tsx`(mock/real 공용 `LangTab[]` 파생 — real은 `is_revised=false` 변형만 탭으로 노출, 수정 요청 시트 프리필은 서버에 없는 `revisedText` 대신 현재 활성 언어 원문으로 대체).
- **설계 결정**: draft 선택 규칙(위), langs 필터링(수정 이력 변형은 탭에 안 보이게 — mock의 "수정은 로컬 상태" 모델 유지), revisedText는 서버에 만들지 않음(미션 명시 지시).
- **검증**: backend pytest **249 passed**(241+8). 프론트 `npm run verify`(typecheck→lint→test **595건**→build) 전부 PASS(586+9 신규, 기존 무회귀). SD-6은 후속 커밋.
