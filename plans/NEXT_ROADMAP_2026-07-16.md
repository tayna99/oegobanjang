# 전체 코드 검수 · 차기 구현 로드맵 — 2026-07-16

> 목적: 저장소 전체(현행 `src/`·`docs/`·`plans/`·`rules/`·`backend/`·`db/`·`reference/`·`legacy/`) 검수 결과를 바탕으로, **앞으로 무엇을 어떤 순서로 구현할지**를 R0~R5 단계로 고정한다.
> 성격: `plans/ROADMAP.md`(M0~M4.7, 기존 정본)의 **후속 제안**이다. 채택 시 이 문서의 태스크를 ROADMAP 형식(위임 레벨·스펙·DoD)으로 승격해 옮긴다.
> 검수 방법: 병렬 검수 4트랙(src 로직 전수 / src UI 전수 / docs·backend·db / legacy 자산) 후, 이 문서의 사실 주장 97건을 5트랙 적대적 검증으로 저장소와 재대조(교정 11건 반영 완료).

---

## 0. TL;DR

1. **프론트 MVP는 사실상 완성**이다 — M0~M4.7 전 마일스톤 완료, 가드레일(상태전이·멱등 승인·citation-lock·append-only evidence)은 순수 함수 + zustand로 견고하고 테스트(400+)로 보증된다. 단 **발송·인증·런엔진·CSV·영속성은 전부 목/각본**이다.
2. **루트 `backend/`는 이미 존재하고 동작한다** — FastAPI + ORM 모델 + Alembic + pytest 스위트가 CI에서 돌아간다(인증 OTP/세션 + 승인 결정 API). 그런데 **프론트는 이를 한 줄도 호출하지 않고**(`src/`에 fetch/API 호출 0건), 상위 문서들(README/AGENTS/CLAUDE)은 여전히 "루트 backend 없음"이라고 단언한다.
3. **legacy/는 폐기물이 아니라 자산 창고**다 — Daily Briefing 룰 엔진(3,400줄), RAG 코퍼스(법령 6종 + 1,000+ 청크), 다국어 템플릿 23종, 번역·응답해석 모듈, 평가 데이터셋이 이관 대기 상태다. DB 계층만은 이미 `db/schema.sql`로 승계가 끝났으므로 재이관 금지.
4. 따라서 순서는: **R0 부채 청산·문서 정합화 → R1 목 세계 안에서 흐름 완결 → R2 백엔드 배선(영속성+인증+승인) → R3 메시징 실연동 → R4 에이전트 런타임 실연결(legacy 이관) → R5 파일럿 확장**.

---

## 1. 현재 상태 스냅샷 (검수 결과)

### 1.1 실제로 동작하는 것 (mock 데이터 위에서 완결)

| 영역 | 내용 | 위치 |
|---|---|---|
| 상태 전이 가드레일 | `CASE_TRANSITIONS` 화이트리스트 + `GuardrailError`, returned 왕복, blocked 종착 | `src/stores/caseStore.ts` |
| 승인 규율 | idempotency key(`seenKeys`) 중복 차단, 승인 생애주기 단일 유닛 | `src/stores/approvalStore.ts`, `src/lib/approval.ts` (`useApprovalActions`) |
| 근거 게이트 | F등급 제외 `usableCitations()` → citation-0 승인 잠금 | `src/stores/citationStore.ts`, `src/lib/approval.ts` |
| 감사 로그 | append-only + `Object.freeze` + id 중복 방지 | `src/stores/evidenceStore.ts` |
| RBAC·위임 | 3역할(manager/owner/viewer) + 위임·정책·구성원 관리, owner 쓰기-런 차단 | `src/stores/companyStore.ts`, `src/lib/company.ts`, `src/lib/role.ts` |
| 화면 22라우트 | 모바일(2a~2d)·PC(3a~3c·4a~4f)·온보딩·화이트라벨 전부 렌더·인터랙션 완결 | `src/router.tsx`, `src/features/**` |
| DB 설계 정본 | PostgreSQL 16, 33테이블(login_otps·sessions 포함) + 트리거 강제(append-only·테넌트 격리) + CHECK 제약(외부 실행 차단) + 검증 178항목 | `db/schema.sql`, `db/validate.py` |
| 백엔드(독립) | FastAPI: OTP 인증·세션, 승인 요청 생성 + approve/reject(결정자는 세션 principal에서 도출), pytest 스위트, CI 편입 | `backend/app/api/v1/{auth,approvals}.py`, `.github/workflows/ci.yml` |

### 1.2 목(mock)/각본/하드코딩인 것 — "진짜"가 되려면 교체 필요

| # | 항목 | 현재 상태 | 위치 |
|---|---|---|---|
| M-1 | 발송(dispatch) | `approvalStore.dispatch()`는 승인 검사 후 `{dispatched:true, actionId}` 반환뿐. 채널 어댑터 없음(타입만 정의) | `src/stores/approvalStore.ts:69-78`, `src/types.ts:141` |
| M-2 | 발송 실행 큐 | 각본 기반 고정 큐. 실제 승인 파이프라인과 **actionId 체계가 분리**돼 자동 연동 안 됨 | `src/mocks/dispatch.ts:22`, `src/features/cases/DispatchQueuePage.tsx:30-36` |
| M-3 | 에이전트 런 | 정적 `RUN_CONFIGS` 각본을 430ms 간격으로 재생. LLM 없음 | `src/lib/runEngine.ts`, `src/mocks/runs.ts` |
| M-4 | 인증 | 전화 OTP는 6자리 입력만 게이트(값 미검증), 승인 PIN은 고정 `DEMO_PIN='1234'` | `src/features/onboarding/StepPhoneAuth.tsx:51-55`, `src/lib/pin.ts:3` |
| M-5 | CSV 업로드 | 고정 8행 각본. 실제 파일 파싱 없음 | `src/lib/csvUpload.ts:29-38` |
| M-6 | 영속성 | localStorage는 테마 1건뿐(`themeStore`). 나머지 전 스토어 인메모리 → **새로고침 시 소실**, 페이지별 재시드 패턴으로 연명 | `src/stores/themeStore.ts:18,43` 외 전 스토어 |
| M-7 | 커맨드 바 | 입력 내용 무관 항상 런 `#4797`로 이동 | `src/features/briefing/CommandBar.tsx:32-37` |
| M-8 | 온보딩 입력 | O3 회사명·O4 근로자 입력이 어디에도 반영 안 됨(홈 헤더 "그린푸드 제조" 하드코딩, 로스터는 픽스처 시딩) | `src/features/onboarding/StepCompany.tsx:1-4`, `src/features/briefing/BriefingHomePage.tsx:40` |
| M-9 | 초안 수정 요청 | 고정 `revisedText` 토글. 실제 편집·재생성 없음 | `src/features/draft/DraftPage.tsx:91-115` |
| M-10 | 사장님 월간 리포트 | 전부 하드코딩 상수(스토어 파생 아님) | `src/features/control/OwnerHomeWorkbench.tsx:14-21` |
| M-11 | 행정사 화이트라벨 인증 | URL의 expertId가 곧 토큰(mock). 서명 토큰·OTP·서버 scope 강제 없음 | `src/features/expert/ExpertPackagePage.tsx`, `reference/specs/7-1_행정사_화이트라벨_v0.md` §3 |

### 1.3 구조적 부채 (교체 전에 정리해야 배선 비용이 안 커지는 것)

| # | 부채 | 내용 | 위치 |
|---|---|---|---|
| D-1 | **메시지 도메인 이중 모델** | `types.ts`의 `MessageThread`(모바일: threadStore/`mocks/threads.ts`)와 `mocks/messages.ts`의 **동명 별개** `MessageThread`(PC `MessagesWorkbench` 전용)가 같은 도메인을 각자 표현. 같은 "메시지" 탭이 화면 폭에 따라 다른 데이터를 봄 | `src/types.ts:144-161`(메시지 도메인 블록 — `MessageThread`는 156-161) vs `src/mocks/messages.ts:24-34`, `src/features/messages/MessagesPage.tsx:14-15` |
| D-2 | **Badge→Chip 마이그레이션 미완** | Chip으로 개명(M2.5.2) 후에도 Badge·`badgeTone`이 thread/messages 피처에 잔존 | `src/features/messages/ThreadListItem.tsx:1,44`, `src/features/thread/InterpretationCard.tsx:1,28`, `src/lib/badgeTone.ts` |
| D-3 | **케이스 타임라인이 정적 데이터** | `CaseTimeline`이 `CASE_SHEETS` 고정 데이터만 읽어 런타임 이벤트(행정사 회신·해석 확인)가 케이스 상세에 실시간 반영 불가 | `src/mocks/fixtures.ts` (`CASE_SHEETS`), `src/features/packagePkg/ExpertLinkPage.tsx:8-10` |
| D-4 | 파생 로직 중복 | 정렬(`sortCards` vs `sortCaseList`), docUpdates 오버레이 2벌, `EVIDENCE_SEED` 병합 3벌, `SEVERITY_LABEL` 화면별 재정의(라벨 표기도 불일치) | `src/lib/briefing.ts:25-34`/`src/lib/cases.ts:74-85`, `src/features/case/CaseReviewPage.tsx:53-59`/`src/features/cases/CaseWorkbench.tsx:424-431`, `src/lib/audit.ts:96·110`+`src/features/case/CaseHistoryPage.tsx:45` |
| D-5 | Page/Screen/Workbench 명명 붕괴 | 데스크톱 전용인데 `*Page`(ControlTowerPage·GovernancePage), 모바일 전용인데 `*Page`(CaseReviewPage·GlobalEvidencePage), 컨테이너 유무 혼재 | `src/features/**` |
| D-6 | 실벽시계 vs 데모 날짜 혼용 | 런타임 evidence는 `new Date()`, 데모 세계관은 `DEMO_TODAY='2026-07-10'` — 병합 정렬(`audit.ts:97`)에서 런타임 이벤트가 항상 최상단으로 밀리고, 만료 판정은 혼용을 피하려고 "재발급 이벤트 존재 여부"만 보는 우회 로직을 씀 | `src/lib/packageLink.ts:11-16`, `src/lib/audit.ts:97` |

### 1.4 버그·결함 (즉시 수정 가능한 것)

| # | 결함 | 재현/영향 | 위치 |
|---|---|---|---|
| B-1 | 동일 사유 재반려가 조용히 유실 | 반려 evidence id가 `${actionId}-rejected:${reason}` 고정이라, 같은 사유로 반려→보완→재반려하면 evidenceStore의 id 중복 방지에 걸려 **두 번째 반려 기록이 무시**됨 | `src/lib/approval.ts:120-122` + `src/stores/evidenceStore.ts:17` |
| B-2 | 댕글링 참조 스레드 | `mocks/threads.ts`의 'bayar' 스레드가 `caseId:'bayar'`를 참조하지만 `CASE_CARDS`에 해당 케이스 없음 | `src/mocks/threads.ts:97-121` |
| B-3 | `threadIdForCase` 매핑 불완전 | `tranCase`/`nguyen`만 매핑 — 다른 케이스의 thread 액션은 의도한 스레드가 아닌 메시지 탭으로 폴백 | `src/mocks/threads.ts:128-131`, `src/lib/actionNav.ts:27-33` |
| B-4 | 죽은 버튼 | CSV "템플릿 다운로드" 버튼에 onClick 없음 | `src/features/cases/CsvUploadWorkbench.tsx:267` |
| B-5 | 데이터 미사용 정의 | `NextActionState`의 `locked/scheduled/waiting`, `DraftLangCode`의 `'en'`, `CitationGrade`의 `'C'` — 전부 목데이터에서 미사용(의도 여부 문서화 필요) | `src/types.ts:26-29`, `src/mocks/drafts.ts:4-6` |

### 1.5 문서 불일치 (에이전트 구동 저장소라 방치 비용이 큼)

| # | 불일치 | 위치 |
|---|---|---|
| DOC-1 | **[치명] "루트 backend 없음" 단언** — 실제 `backend/`는 CI에서 도는 동작 코드 (`CLAUDE.md`는 단언은 아니나 backend를 누락한 낡은 서술) | `AGENTS.md:48`, `README.md:121-123`, `docs/DB_SCHEMA.md:26·39`, `db/README.md`, `CLAUDE.md` |
| DOC-2 | `backend/README.md` 자체가 코드보다 낡음 — "인증 없음/decided_by를 바디로 받음/요청 생성 endpoint 없음" ↔ 실제는 전부 구현됨 | `backend/README.md:57,86-87` vs `backend/app/api/v1/approvals.py`, `auth.py` |
| DOC-3 | DB 수치 혼재 — 검증 건수 3종(178 정본 vs 160 vs 145) + 테이블 수(실제 33 vs 문서 31) | `docs/ARCHITECTURE.md:18`(160), `backend/README.md:42`(145), `db/README.md:9`·`docs/DB_SCHEMA.md`(31) |
| DOC-4 | 구 로스터 인용(Bayar M.·Mohammad I. — 6인 로스터에서 제거된 인물) | `docs/MESSAGING_CHANNELS.md:9` |
| DOC-5 | PR 템플릿이 legacy 시절 산물 참조(`docs/API_CONTRACT.md`, missions/active, Agent Runtime test 등 — 현행에 없음) | `.github/pull_request_template.md` |
| DOC-6 | 루트 `DESIGN.md`가 이 프로젝트와 무관한 Toss 디자인 시스템 참조 자료 — `rules/design.md`와 혼동 유발 | `DESIGN.md` |
| DOC-7 | 런엔진 경로 오기(`src/features/runs/` → 실제 `src/lib/`) | `docs/SPEC_INDEX.md:33` |
| DOC-8 | ROADMAP의 "GLOSSARY에 expert 없음" 노트 — 이미 반영돼 노트 쪽이 낡음 | `plans/ROADMAP.md`(M4.7 절) vs `docs/GLOSSARY.md:34` |

---

## 2. 순차 구현 로드맵 (R0 → R5)

> 순서 논리: ①문서·도메인 모델을 하나로 만들고(R0) → ②목 세계 안에서 사용자 플로우를 끝까지 잇고(R1) → ③그 단일 모델 위에 백엔드를 배선하고(R2) → ④외부로 나가는 채널을 열고(R3) → ⑤에이전트를 진짜로 만들고(R4) → ⑥파일럿 확장(R5).
> R2 전에 R0(특히 D-1 메시지 단일화)을 끝내야 하는 이유: 이중 모델 상태로 배선하면 API 계약을 두 벌 만들거나 배선 직후 다시 리팩터하게 된다.

### R0 — 부채 청산 · 문서 정합화 (배선 전 선행, 전부 소규모)

| # | 태스크 | 내용 | 근거 |
|---|---|---|---|
| 0.1 | 문서 일괄 정합화 | DOC-1~DOC-8 전건 수정. 특히 "루트 backend 없음" 서술을 실존 `backend/`에 맞게 갱신하고 `backend/README.md`를 코드 기준으로 재작성 | §1.5 |
| 0.2 | 버그 수정 | B-1(반려 evidence id에 시퀀스/타임스탬프 도입), B-2·B-3(스레드 픽스처 정리), B-4(템플릿 다운로드 연결 또는 제거) | §1.4 |
| 0.3 | **메시지 도메인 단일화** | `mocks/messages.ts` 병렬 모델 폐기, `MessagesWorkbench`를 `threadStore`/`mocks/threads.ts` 기반으로 재배선(모바일·PC가 같은 스레드를 보게) — HANDOFF(2026-07-16)가 이미 후속으로 명시 | D-1 |
| 0.4 | Badge→Chip 마무리 | ThreadListItem·InterpretationCard를 Chip으로 이전 후 `Badge`/`badgeTone.ts` 삭제 | D-2 |
| 0.5 | **케이스 타임라인 스토어 승격** | `CASE_SHEETS` 타임라인을 evidenceStore 병합 파생으로 리팩터 — R1.3(회신·해석의 실시간 반영)의 선행 조건 | D-3 |
| 0.6 | 파생 로직 통합 | 정렬·오버레이·시드 병합·SEVERITY_LABEL을 selector 한 곳으로(rules/frontend.md "파생값은 selector로" 원칙 회복). D-5 명명 규칙은 리네임 비용 대비 효과를 보고 선택 적용 | D-4, D-5 |

### R1 — 목 세계 안에서 플로우 완결 (백엔드 없이 가능한 제품 완성도)

| # | 태스크 | 내용 | 근거 |
|---|---|---|---|
| 1.1 | 회사 프로필 슬롯 | `companyStore`에 회사 프로필 추가 → 온보딩 O3 입력이 홈/케이스 헤더에 반영(하드코딩 "그린푸드 제조" 제거) | M-8 |
| 1.2 | 온보딩 근로자 → 실제 케이스 생성 | O4 입력값으로 CaseCard 생성(현재는 입력 무시하고 픽스처 6인 시딩). CSV(4.4)와 동일 데이터 계약 공유 | M-8 |
| 1.3 | 런타임 이벤트 → 케이스 타임라인 반영 | 행정사 회신(`package_reply`)·해석 확인이 케이스 상세 타임라인에 실시간 표시(0.5 선행) | D-3 |
| 1.4 | **승인 완료 → 발송 큐 자동 연동** | `human_approved` 전이 시 발송 큐에 자동 편입(고정 `DISPATCH_QUEUE` → 스토어 파생). actionId 체계 통일. "승인=상태 전이, 실행=담당자 확인" 분리 원칙(7단계 §2 각주²)의 앱 내 완성 | M-2 |
| 1.5 | CSV 실제 파일 파싱 | 고정 8행 각본 → 실 파일 업로드+파서(검증 규칙 `validateRows`는 재사용) | M-5 |
| 1.6 | 커맨드 바 최소 매핑 | 추천 칩 즉시 제출 + 입력→런 매핑 테이블(자연어 파싱은 R4에서 실 LLM으로) | M-7 |
| 1.7 | 초안 수정 요청 개선 | 고정 revisedText 토글 → 편집 가능한 수정 요청 UI(실 재생성은 R4) | M-9 |
| 1.8 | 사장님 리포트 파생화 | `MONTHLY_REPORT` 하드코딩 → 스토어 파생값(KPI=스토어 파생 원칙과 정합) | M-10 |

### R2 — 백엔드 배선 (mock → `backend/` + 영속성) ★ 가장 큰 전환점

> 전제: `backend/`에 인증(OTP/세션)·승인 결정 API는 **이미 있다**. 없는 것은 ①프론트의 호출 코드, ②케이스/브리핑/스레드 read API, ③위임 유효성 검증이다.
> 원칙 유지: 승인은 "서버 확정 후 반영"(GOTCHAS §2), 승인 결정 endpoint는 principal·본인확인·delegation 검증과 함께(README "후속 backend 이식" 절).

| # | 태스크 | 내용 | 근거 |
|---|---|---|---|
| 2.1 | API 클라이언트 계층 | `src/lib/api/` 신설 — mock/실서버를 플래그로 전환하는 어댑터(스토어 액션 시그니처 유지). 프론트에 현재 fetch 0건이므로 첫 배선 지점 | §1.1 |
| 2.2 | 인증 배선 | 온보딩 O1 전화 인증 → `POST /api/v1/auth/otp/*` 실호출, 세션 확립, `roleStore`를 세션 principal 파생으로 전환(현재 새로고침 시 manager 복귀) | M-4, M-6 |
| 2.3 | 읽기 API 신설+배선 | backend에 케이스 목록/상세·브리핑·스레드 read endpoint 추가(`db/schema.sql` 계약 준수) → caseStore/threadStore 서버 동기화. **여기서 M-6 영속성이 해소**된다(별도 localStorage 영속화를 만들지 말 것 — 이중 진실 방지) | M-6 |
| 2.4 | 승인 결정 배선 | ApprovePage → `POST /api/v1/approvals/{id}/approve|reject`. PIN을 서버 측 검증으로 승격, **위임(delegation) 유효성 검증 구현**(backend 잔여 갭, DB §13-10) | M-4 |
| 2.5 | Evidence 서버 영속화 | evidenceStore append → 서버 기록(append-only 트리거는 DB 계약에 이미 존재). 민감정보 원문 미저장 원칙 유지 | §1.1 |
| 2.6 | 행정사 링크 서버 강제 | `/link/:packageId` 만료·재발급·열람 로그를 서버 검증으로 승격(클라이언트 가드 → 404 강제) | M-11 |

### R3 — 메시징 실연동 (`docs/MESSAGING_CHANNELS.md` §5의 ②→③→④ 그대로)

| # | 태스크 | 내용 | 근거 |
|---|---|---|---|
| 3.1 | Outbox | outbox 테이블 + 발송 창(21:00~08:00 보류)·이벤트 idempotency·리마인드 쿨다운·48h 재발송 검사. `MessageDeliveryStatus`에 `queued/delivered/failed` 확장 | §5 ② |
| 3.2 | SmsAdapter + 응답 링크 인바운드 | 1차 실채널(솔라피류) + 만료형 토큰 응답 페이지(모국어 버튼+자유입력) → 인바운드 정규화 → N02 → M6 해석 큐 | §3, §5 ② |
| 3.3 | AlimtalkAdapter | 알림톡 + 실패 시 SMS 폴백 체인 | §5 ③ |
| 3.4 | ZaloAdapter | OA webhook 인바운드가 동일 정규화 지점에 합류 | §5 ④ |
| 3.5 | EmailAdapter | 행정사 패키지 전달 전용(근로자 채널과 분리 유지) — R2.6과 연결 | §2 |

> 불변식: `send_message`류 직접 발송 함수 금지는 백엔드에서도 유지 — 발신 입구는 Outbox 하나, Outbox 앞은 항상 승인(GOTCHAS §1).

### R4 — 에이전트 런타임 실연결 (legacy 자산 이관)

> legacy 이관 원칙: **로직·데이터·계약은 가져오고, DB 모델·API 배선·임시 인증(X-Company-Id)은 가져오지 않는다**(현행 `db/schema.sql`·인증 principal 기준으로 재배선). legacy 문서 중 `GRAPH_STATE.md`·`FOLDER_STRUCTURE.md`의 graph/nodes 서술은 삭제된 구 구조이므로 코드 기준으로 판단.

| # | 태스크 | 내용 | 이관 원천 |
|---|---|---|---|
| 4.1 | Daily Briefing 룰 엔진 이식 | 룰 4종(체류기간 연장·누락 서류·계약-체류 충돌·고용변동 신고기한)의 D-day 임계 기반 severity 계산(결정론적) → 브리핑 카드가 실데이터에서 생성 | `legacy/backend/app/services/daily_briefing_service.py`(3,464줄, 룰 정의 :51-54) |
| 4.2 | RAG 이관 | 법령 6종 JSONL + multilingual_contact 1,022청크 + workforce 레코드 → citation 실데이터화. 근거 등급 계약 유지(D/F는 법적 근거 금지, F는 승인 게이트에서 제외 — 현행 `usableCitations`와 접합) | `legacy/data-pipeline/`, `legacy/backend/app/agent_runtime/rag/` |
| 4.3 | 런엔진 교체 | 각본 재생 → LangChain/LangGraph `create_agent` 스트리밍. **`RunConfig`/`useRunEngine` 인터페이스 불변**(설계상 보장 지점). Safety·EvidenceCapture 미들웨어와 도구 5등급(TOOL_CONTRACT) 승계 — 발송 도구는 여전히 부재/`pending_approval` 강제 | `legacy/backend/app/agent_runtime/langchain_v1/`(runtime·middleware), `legacy/docs/TOOL_CONTRACT.md` |
| 4.4 | 다국어 초안 실생성 | 템플릿 22종(vi 11 + id 11) + 번역 모듈(rule 기본 + LLM opt-in, 실패 시 rule 폴백) → DraftPage 실초안·R1.7 수정 요청의 실 재생성 | `legacy/data-pipeline/seed/message_templates.csv`, `legacy/backend/app/agent_runtime/translation/` |
| 4.5 | M6 응답 해석 실연동 | reply_interpreter 이식 — `isFinal:false`·담당자 확인 필수 계약 유지, R3.2 인바운드와 접합 | `legacy/.../translation/reply_interpreter` 등, `legacy/docs/AGENT_COMMON_CONTRACTS.md` §10 |
| 4.6 | 평가 하네스 복원 | safety_guardrail·intent_router·workflow_e2e 등 데이터셋을 CI에 편입 — "Safety violation 0" 기준선 회복 | `legacy/evals/datasets/`, `legacy/docs/EVAL_HARNESS.md` |
| 4.7 | 프로액티브 런 실트리거 | 각본 프리시드 → 실제 이벤트(D-day 임계·인바운드) 기반 자동 런 + nextWake, 48h/72h 에스컬레이션 타이머 실구현(현재 프리시드 대체분) | ROADMAP M3, 7단계 §4 |

### R5 — 파일럿 확장 (독립 트랙, R2~R4와 부분 병행 가능)

| # | 태스크 | 내용 | 선행 조건 |
|---|---|---|---|
| 5.1 | 행정사 화이트라벨 v1 구현 | `ExpertGrant`/`ExpertOfficeMember`/`PackageViewLog` 백엔드 구현(설계 문서 완성 상태). **착수 전 최우선: 법무 분류(위탁 §26 vs 제3자 제공 §17) 확인** — 뒤집히면 ExpertGrant 스키마가 tenant→tenant+worker로 커짐 | `reference/specs/7-1_행정사_화이트라벨_v1.md`, R2 |
| 5.2 | 서류 스캔 OCR 파이프라인 | 4b "준비 중" 카드 실구현(업로드→분류→케이스 서류 상태 갱신) | R2.3 |
| 5.3 | 컨트롤 타워 실집계 | 파이프라인 델타·주간 추이 mock → 실데이터 집계(2.5.6에서 예고) | R2.3, R4.1 |
| 5.4 | 알림·푸시 | 알림 카탈로그(N01~) 실발송 — 딥링크 맵은 이미 구현돼 있어 수신부만 | R3.1 |
| 5.5 | PC 나비 IA 재정렬 | 최상위 탭 라벨·52/64px — 2.5.6부터 이어진 기존 미결(디자인 결정 필요) | 디자인 확정 |
| 5.6 | 후순위(파일럿 피드백 후) | viewer M8 PII 마스킹 차등, 승인 정책 케이스유형 세분화, 법령·고시 수집기 상시화(legacy crawler 3종은 1회성 생성기 — 상시 크롤러로 승격) | 파일럿 데이터 |

---

## 3. 착수 규칙

- 태스크 1개 = 세션 1개 크기 원칙(기존 ROADMAP 규약)을 유지하되, R2.3·R4.3은 세션 2~3개로 쪼갠다.
- 각 태스크는 착수 시 이 문서에서 `plans/ROADMAP.md` 형식(레벨·스펙·DoD)으로 승격해 옮기고, 완료 시 HANDOFF에 기록한다.
- 가드레일 불변식은 전 단계 공통: 발송 함수 금지(입구는 Outbox+승인), evidence append-only·원문 미저장, 일괄 승인 금지, F등급 근거 금지, 승인은 서버 확정 후 반영.
- R4의 어떤 이관도 legacy 코드를 production import 하지 않는다 — 복사·재배선 후 현행 검증(`npm run verify`, backend pytest, `db/validate.py`)을 통과시킨다.

---

## 부록 A — legacy 이관 자산 지도 (R4에서 사용)

| 자산 | 위치 | 상태 | 처분 |
|---|---|---|---|
| Daily Briefing 룰 엔진 | `legacy/backend/app/services/daily_briefing_service.py` | 성숙(3,464줄) | **이관**(DB 접근부만 재배선) |
| Agent Runtime(LangChain v1) | `legacy/backend/app/agent_runtime/langchain_v1/` | 성숙(runtime 690·middleware 534줄) | **이관**(계약·미들웨어 중심) |
| RAG 코퍼스·파이프라인 | `legacy/data-pipeline/`(법령 6종, 1,022+청크, seed CSV) | 데이터 완비 | **이관**(재수집 비용 큼) |
| 다국어 템플릿·번역 | `legacy/data-pipeline/raw/templates/`, `.../translation/` | vi/id 완비 | **이관** |
| 평가 하네스 | `legacy/evals/datasets/` | 데이터셋 완비 | **이관**(CI 편입) |
| API 계약 문서 | `legacy/docs/API_CONTRACT.md` 등 | 문서 완비 | **참조**(재연결 스펙) |
| DB 모델·마이그레이션 | `legacy/backend/app/models/`, migrations | 승계 완료 | **재이관 금지**(`db/schema.sql`이 정본, `docs/DB_SCHEMA.md` §11 처분표) |
| API 라우터 배선·임시 인증 | `legacy/backend/app/api/v1/`(X-Company-Id scope) | 데모용 | **참조만**(현행 인증 기준 재작성) |
| 빈 스텁 | `legacy/backend/app/api/v1/`의 companies/contacts/visas/health.py(0바이트) | 실체 없음 | 신규 구현 |
| 법령·고시 수집기 | `legacy/data-pipeline/crawlers/`(eps 실크롤링 + gov24/hrd 법령 기반 생성기, 각 20KB±) | 1회성 생성기(JSONL 산출 완료) | **참조·이관**(상시 크롤러화는 후속) |
| Next.js 프론트 | `legacy/frontend/` | 대체됨 | 폐기 유지 |
