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
| SD-4 | 런 SSE 배선 `streamCommandRun` (B4b) | L3 | SD-3 | ✅ 완료(2026-07-20) |
| SD-5 | drafts read API(`GET /cases/{id}/draft`) + DraftPage real 배선 | L2 | SD-2 | ✅ 완료(2026-07-20) |
| SD-6 | CASE_SHEETS 콘텐츠 패리티(checked_items·worker_documents·activity 파생) | L3 | SD-5 | ✅ 완료(2026-07-20) |
| SD-7 | KPI 실집계(stat_snapshots) — R5.3에 흡수, 별도 착수 금지 | — | R5.3 | ⬜ 흡수 |

### 이번 세션 구현 요약 (SD-0~SD-3, 2026-07-20)
- **신규(SD-0~SD-2)**: `db/seed_reference.sql`(전역 citations 20 + document_requirements 22), `db/load.py`, `docs/REALMODE_DEMO_RUNBOOK.md`, 이 문서.
- **신규(SD-3)**: `src/lib/api/citations.ts`(CitationOut→CitationRecord 매핑) + `citationStore.hydrate`, `src/stores/briefingStore.ts`(fetchLatestBriefing 최초 배선), `src/lib/briefing.ts`의 `formatBriefingDate`.
- **수정(SD-0~SD-2)**: `db/seed_demo.sql`(전역 시드 이동 + owner/viewer·스레드·evidence 보강), `db/validate.py`(로드 순서 + 불변식 5건, 181→187), `db/README.md`(3단 배포·드리프트 복구·187), `.github/workflows/ci.yml`(187), `docs/ARCHITECTURE.md`(§5.1 영구 mock 경계 + 187), `docs/DB_SCHEMA.md`·`backend/README.md`(187), `AGENTS.md`(시드 구조 + fetch 0건 정합), `plans/BACKEND_CONNECT.md`(경계 상호참조), `plans/ROADMAP.md`(SD 트랙).
- **수정(SD-3)**: `src/stores/sessionStore.ts`(`companyId` 필드 — citations.py가 cases.py/threads.py와 달리 company_id를 쿼리로 명시 요구), `src/lib/dataSeed.ts`(`useSeedCitations`/`useSeedBriefing`), `GovernancePage.tsx`/`BriefingHomePage.tsx` 배선. 부수: `.claude/launch.json` 로컬 프리뷰 서버 실행 버그 수정(별도 커밋).
- **검증**: `db/validate.py --reset` → **PASS 187 / FAIL 0**(citations 22·evidence 12·threads 3·users 5·document_requirements 22). backend pytest 241 passed. 프론트 `npm run verify`(typecheck→lint→test **586건**→build) 전부 PASS(SD-0~2는 프론트 무접촉, SD-3은 신규 25건 포함 무회귀). 브라우저 실검증: 모바일 BriefingHomePage·데스크톱 GovernancePage 둘 다 mock 모드 시각 변화 없음 확인. 스키마 변경 0.
- **불변 제약 준수**: 직접 발송 없음(스레드 시드=과거 이력, direction='system')·evidence append-only·PII 원문 없음(마스킹만)·F등급 0행·RUN_CONFIGS 보존·localStorage 무접촉·pin_hash AUTH_PEPPER 규칙 승계·승인 낙관적 갱신 금지(citations/briefings는 감사 게이트가 아니라 hydrate로 단순 교체, 승인 원칙과 무관).

### SD-4 구현 요약 (런 SSE 배선, 2026-07-20)

**설계 문제**: `POST /api/v1/runs/stream`은 조회 API가 없는 "생성+실행 겸용" SSE 엔드포인트고
POST+`Authorization` 헤더가 필요해 `EventSource`를 쓸 수 없다(Part B5 원안·`plans/BACKEND_CONNECT.md`
§3-2가 전제했던 "cancel=EventSource.close"는 실장 중 폐기 — 그 파일에 개정 노트로 남겼다). CommandBar가
런을 시작할 때는 아직 run_id를 모르고(서버가 첫 프레임으로 알려줌), RunPage가 독립적으로 다시
스트림을 열면 두 번째 실행(중복 부작용)이 된다.

**해결**: `src/stores/liveRunStore.ts`(신규 zustand 스토어)가 핸드오프를 소유한다. CommandBar가
real 모드에서 `startCommandRun({companyId, message})`을 호출하면 스토어가
`src/lib/api/runs.ts`의 `streamCommandRun()`(fetch+`ReadableStream` reader로 SSE 프레임을 직접
파싱, `cancel()=AbortController.abort()`)으로 스트림을 연다. `run_created` 프레임이 도착하는
즉시 스토어에 그 run_id로 항목을 만들고 promise를 resolve — CommandBar는 그 순간
`nav.toRun(runId)`한다. RunPage는 `/run/:runId`가 `RUN_CONFIGS`에 없고 real 모드면
`LiveRunPageContent`를 렌더하고, 신규 `useLiveRunEngine(runId)`(`useRunEngine`과 반환 계약
`{steps, status, currentIndex}` 동일)로 스토어를 구독만 한다 — 스트림을 다시 열지 않는다.
컴포넌트 마운트와 무관하게 스토어가 프레임을 계속 소비하므로, RunPage를 나갔다 들어와도(또는
CommandBar가 아직 언마운트되지 않은 순간에도) 지금까지 쌓인 상태를 그대로 이어 본다.

route 프레임이 `should_run=false`(금지어·미인식 의도)면 steps·structured 없이 곧장 `done`이
온다 — 이 경로는 RunScreen의 기존 `error` 상태(reason: `blocked`/`unknown`)로 매핑했다. 정상
경로는 mock 커맨드 런과 동일하게 question(=`structured.answer.final_response`)/altLabel/승인
버튼을 항상 노출한다(`approval_required`로 가리지 않는다 — mock도 caseId 없는 커맨드 런(candidate
등)이 승인 필요 여부와 무관하게 항상 결정 블록을 보여주는 것과 같은 패턴). 이 런 타입은 항상
caseId가 없으므로(케이스 생성은 Daily Briefing Rule 엔진 몫, 후속) 승인 버튼은 서버에 어떤
결정도 내리지 않고 DonePage로만 넘긴다(mock의 "caseId 없는 커맨드 런"과 동일 원칙 — 직접 발송 없음).

- **신규**: `src/lib/api/runs.ts`(`streamCommandRun`), `src/stores/liveRunStore.ts`,
  `src/lib/useLiveRunEngine.ts` + 각각의 테스트(`runs.test.ts`·`liveRunStore.test.ts`) +
  통합 테스트(`RunPage.realApi.test.tsx`·`CommandBar.realApi.test.tsx`, `global.fetch`를 실제
  `ReadableStream` 바디로 목킹).
- **수정**: `src/features/run/RunPage.tsx`(real 모드 live-run 분기 `LiveRunPageContent` 추가,
  mock config 분기는 무변경), `src/features/briefing/CommandBar.tsx`(real 모드 분기 추가, mock
  경로는 무변경), `docs/ARCHITECTURE.md`·`plans/BACKEND_CONNECT.md`(EventSource 전제 폐기 반영).
- backend는 무수정 — `backend/app/api/v1/runs.py`·`run_service.py`가 이미 계약과 정확히
  일치함을 확인했다(코드 리뷰 결과 버그 없음).
- **검증**: `npm run verify`(typecheck→lint→test 617건→build) 전부 PASS(mock 모드 기존 599건
  무회귀 + 신규 18건: 어댑터 6·스토어 7·RunPage 통합 3·CommandBar 통합 2). 실 backend+rag+Postgres
  브라우저 클릭스루는 격리 워크트리 제약상 생략 — mock-fetch 통합 테스트로 대체(태스크 지시 범위).
- **불변 제약 준수**: 직접 발송 없음(승인 버튼은 서버 결정 없이 DonePage만)·`RUN_CONFIGS`·
  `executeRun` 무변경(replay 각본 그대로)·mock 모드 시각/동작 무변화(모든 신규 분기는
  `API_MODE==='real'` 뒤에서만 실행).

### SD-5 구현 요약 (2026-07-20)

**drafts read API + DraftPage real 배선.**
- **신규**: `backend/app/schemas/draft.py`(`DraftLangVariantOut`·`DraftOut`), `backend/app/services/drafts.py`(`get_draft_out` — "가장 관련 있는 살아있는 초안" 선택 규칙: `rejected`/`superseded`가 아닌 것 중 최근 생성분, 전부 종결이면 최근 1건 폴백, 초안 자체가 없으면 None→404), `backend/tests/test_api_drafts.py`(8건 — 종결 상태 필터링·폴백·is_revised 노출·테넌트 격리·404 3종). `src/lib/api/drafts.ts`(DTO→`Draft`/`DraftLangVariant` 매핑 + 언어 라벨 맵), `src/lib/api/drafts.test.ts`(4건), `src/features/draft/DraftPage.realApi.test.tsx`(5건).
- **수정**: `backend/app/api/v1/cases.py`(`GET /{case_id}/draft` 라우트 추가), `src/features/draft/DraftPage.tsx`(mock/real 공용 `LangTab[]` 파생 — real은 `is_revised=false` 변형만 탭으로 노출, 수정 요청 시트 프리필은 서버에 없는 `revisedText` 대신 현재 활성 언어 원문으로 대체).
- **설계 결정**: draft 선택 규칙(위), langs 필터링(수정 이력 변형은 탭에 안 보이게 — mock의 "수정은 로컬 상태" 모델 유지), revisedText는 서버에 만들지 않음(미션 명시 지시).
- **검증**: backend pytest **249 passed**(241+8). 프론트 `npm run verify`(typecheck→lint→test **595건**→build) 전부 PASS(586+9 신규, 기존 무회귀).

### SD-6 구현 요약 (2026-07-20)

**케이스 시트 콘텐츠 패리티.**
- **신규**: `backend/app/services/cases.py`에 `_checked_items_out`/`_worker_documents_out` 헬퍼, `backend/app/schemas/case.py`에 `CheckedItemOut`/`WorkerDocumentOut` + `CaseDetailOut` 3필드 확장, `backend/tests/test_api_cases.py`에 2건 추가(전체 케이스 13건). `src/lib/audit.ts`에 `caseActivityFromEvents`(real 모드 전용 케이스 타임라인 파생 — 24종 EvidenceType→outcome 매핑 표를 코드 주석에 근거와 함께 명시), `src/lib/audit.test.ts`에 5건 추가. `src/features/cases/CaseWorkbench.realApi.test.tsx`(신규, 2건).
- **수정**: `src/lib/api/cases.ts`(`CaseDetailDto`/`CaseDetail`에 `checked_items`/`next_wake`/`documents`↔`checkedItems`/`nextWake`/`docs` 추가 — mock `CaseSheet`와 필드명을 맞춰 화면이 같은 렌더 로직을 재사용하게 함, `CaseDoc.statusLabel`은 상태값→고정 한국어 라벨 맵으로 생성), `src/lib/api/cases.test.ts`(`fetchCaseDetail` 단위 테스트 신설, 3건 — 기존엔 없었다), `src/features/case/CaseReviewPage.tsx`(누락 서류 섹션이 real 모드에서 `detail.docs`로도 채워짐 — `checkedItems`/activity는 이 화면이 mock에서도 안 쓰던 섹션이라 추가하지 않음), `src/features/case/CaseReviewPage.realApi.test.tsx`(+1건), `src/features/cases/CaseWorkbench.tsx`(선택된 케이스 1건만 real 모드에서 `fetchCaseDetail`로 보강 — `DocChecklist`/`CaseTimeline`/`EvidenceRail` 세 하위 컴포넌트를 `sheet` 통짜 대신 개별 파생값을 받도록 리팩터), `src/features/approve/ApprovePage.realApi.test.tsx`(`CaseDetailDto` 신규 필수 필드 3종을 테스트 픽스처에 추가 — 타입 확장의 파급 수정).
- **N+1 회피로 의도적으로 손대지 않은 화면**(문서화된 결정, DoD가 명시적으로 요구하는 화면은 2b/CaseWorkbench 둘뿐):
  - `WorkerDataWorkbench.tsx` — 근로자 전원의 서류 준비율/최근 업데이트를 real 모드로 채우려면 케이스마다 `GET /cases/{id}`를 호출해야 한다(목록 API는 개수만 내려주지 않는다) — 이미 `sheet?.docs ? … : '—'`로 안전하게 폴백 중이라 크래시는 없다.
  - `ControlTowerPage.tsx` — `controlTowerKpis`의 `evidenceShort` 하나만 `CASE_SHEETS`를 읽는다. 목록 API(`GET /cases`)에 `usable_citation_count`가 없어 정확한 real 모드 값을 얻으려면 케이스마다 상세를 불러야 한다 — SD-7이 "KPI 실집계는 R5.3에 흡수, 별도 착수 금지"라 명시했고, 이 KPI도 사실상 그 범주(목록 API 확장이 선행돼야 하는 집계형 지표)라 함께 보류. 카드 목록·활동/감사 레일(`useSeedCases`/`useSeedEvidence` 이미 배선됨)은 이미 real 모드에서 정상 동작한다.
  - `GovernancePage.tsx` — `linkedCaseCount(record.id, sheets)`의 `sheets`가 `CASE_SHEETS`뿐이라 real 모드에서 "연계" 열이 항상 0이지만 크래시는 없다. 근거 라이브러리 본체(`useSeedCitations`)는 이미 SD-3에서 real 배선 완료. 케이스별 연계 수를 정확히 내려주려면 근거→케이스 역참조 엔드포인트가 필요한데 SD-6 스코프(3필드 확장)를 벗어난다.
- **검증**: backend pytest **251 passed**(249+2). 프론트 `npm run verify`(typecheck→lint→test **606건**→build) 전부 PASS(595+11 신규, 기존 무회귀). 스키마 변경 0(마이그레이션 없음).

---

## Part D — 병렬 워크트리 확장 (SD-4~SD-6 + R3·R4.6·R5.1·R5.4, 2026-07-20 통합 완료)

SD-4~SD-6에 이어 사용자 지시("병렬로 구현할 수 있으면 구현해, 계획문서에서 구현 안 된 것들을
싹 다 구현해")에 따라 R3(메시징)·R4.6(평가 하네스)·R5.1(화이트라벨 v1 백엔드)·R5.4(알림
센터)까지 6개 워크트리 에이전트를 병렬로 착수했다. R5.2(OCR 벤더 미정)·R5.5(PC 나비 IA
디자인 결정 필요)·R5.6(파일럿 데이터 없음)·R4.7의 48h/72h 실시간 타이머(스케줄러 인프라
없음, 대부분 G6 룰엔진으로 이미 충족)는 사용자 확인 하에 명시적으로 제외했다. 외부 발송이
필요한 항목(R3 채널 어댑터·R5.4 푸시)은 `backend/app/api/v1/auth.py`의 `debug_code=code if
get_settings().is_local else None` 패턴을 그대로 승계한 **자격증명 게이트**로 구현 —
`SOLAPI_*`/`KAKAO_ALIMTALK_*`/`ZALO_OA_*`/`SMTP_*`/`PUSH_PROVIDER_CREDENTIALS`가 전부
미설정인 이 환경에서는 어떤 어댑터도 실제 외부 HTTP 호출을 시도하지 않는다(스텁 결과는
`external_id`에 `stub:{channel}:{uuid}` 접두로 실발송과 구조적으로 구분).

### 병합 시 발견한 구조적 사실
일부 병렬 워크트리(R5.1·R5.4)는 세션 시작 시점의 base 커밋(`9a40213`, SD-0~3 이전)에서
분기해 내 SD-1 작업(`db/validate.py` 로드 순서·카운트 변경)을 못 본 채 독립적으로
`db/validate.py`/마이그레이션을 수정했다 — 병합 시 실제 충돌로 나타났다(SD-4는 자체적으로
내 SD-3를 미리 병합해 충돌 없이 들어왔다). 스키마 변경 3건(R3=0004, R5.1=0005, R5.4=0006)이
전부 독립적으로 `down_revision="0003"`을 가리키고 있어 병합 후 `0003→0004→0005→0006`
선형 체인으로 수동 재정렬했다(`alembic heads`로 단일 head 확인). `plans/ROADMAP.md`·
`plans/SEED_DESIGN_2026-07-20.md`도 여러 브랜치가 같은 절(SD 트랙 표·"발송 어댑터" 섹션)을
각자 확장해 병합마다 텍스트 충돌이 났다 — 전부 union(양쪽 다 보존)으로 해소했다.

### 최종 통합 검증 (전 브랜치 병합 후, 2026-07-20)
- `db/validate.py --reset`(디스포저블 DB) → **PASS 211 / FAIL 0**(41테이블: 기존 33 + R3
  outbox 1 + R5.1 expert 화이트라벨 7).
- backend `TEST_DB_NAME=ogb_test_final_merge uv run pytest` → **358 passed**.
- 프론트 `npm run verify`(typecheck→lint→**655건**→build) → 전부 PASS, 단일 clean 실행(동시
  git 작업 없이)에서 플레이키 0건.
- 병합 중 발견·수정한 실제 타입 에러 1건: R3가 추가한 `EvidenceType.worker_reply_received`
  (N02)가 SD-6의 `caseActivityFromEvents` 매핑 테이블(`Record<EvidenceType, outcome>`)에
  없어 `tsc` 실패 — `'question'`(package_reply와 동일 범주: 사람의 추가 확인을 기다리는
  안내성 이벤트)으로 추가해 해소.
- 문서 수치 일괄 정합: `db/README.md`·`.github/workflows/ci.yml`의 검증 건수(178/181/187→
  **211**)·테이블 수(33→**41**). `plans/ROADMAP.md`·`plans/HANDOFF.md`의 날짜가 박힌
  개별 브랜치 완료 기록(예: "193/193"·"181/181")은 **그 시점 그 브랜치 단독 검증 결과라는
  역사적 사실**이므로 고치지 않았다 — 통합 이후의 진실은 이 절과 `db/README.md`가 정본.
