# HANDOFF — 세션 인수인계 기록

> 규칙: 태스크를 끝내거나 컨텍스트 40%에 도달해 세션을 넘길 때, 에이전트가 아래 형식으로 **맨 위에** 추가한다.
> 새 세션의 첫 행동: 이 파일의 최신 항목 1개 + ROADMAP의 다음 태스크를 읽는 것. (전체 히스토리 로드 금지)

---

## 형식

```
### [날짜] 태스크 번호 — 상태 (완료/중단)
- 한 일:
- 남은 일 / 중단 지점:
- 결정 사항 (다음 세션이 알아야 할 것):
- verify 상태: PASS/FAIL(원인)
- 지도/규칙 갱신: (했으면 무엇을)
```

---

### [2026-07-17] R2.4 — 승인 결정 배선 — 완료

- 한 일: `ApprovePage`를 실 `POST /api/v1/approvals`(생성)·`/approve`·`/reject`로 배선. 로드맵이
  지목한 두 백엔드 갭을 닫았다.
  - **위임(delegation) 유효성 검증(§13-10)**: `decide_approval()`이 이제 `delegations` 테이블을
    실제로 조회한다 — `on_behalf_of_user_id`(위임자)→`decided_by_user_id`(대리인) 방향의
    활성(`revoked_at IS NULL`)·기간 내·`scope='approval'` 행이 있어야 승인/반려 가능
    (`ApprovalDelegationInvalidError`, 403). **검증된 위임은 `manager는 대표만 가능` 정책
    게이트를 우회한다** — 처음엔 이 우회를 빼먹어서 위임이 있어도 정책 게이트에 다시 막히는
    버그를 만들었다가, 통합 테스트로 바로 잡았다(`delegated = False`부터 시작해 검증 성공
    시에만 `True`로 바꾸고, `if membership.role == "manager" and not delegated:` 로 게이트).
  - **PIN 서버 검증**: `ApprovalDecisionRequest.pin` 신설, `users.pin_hash` + 기존
    `hash_secret`/`secrets_match`(`domain/auth_tokens.py`, 원래 OTP·세션 토큰용으로 만든
    유틸 — docstring이 이미 "users.pin_hash와 동일 원칙"이라고 예고해뒀었다) 재사용.
    PIN 미제출·미등록(`pin_hash` NULL)·불일치를 전부 동일한 에러/메시지로 처리해 등록 여부가
    새지 않게 한다.
  - **approval_id 브리징**: `NextActionOut.pending_approval_id` 신설 — 백엔드는 `action_id`가
    아니라 `Approval` 행의 실제 `id`로 approve/reject를 받는데, mock 세계는 이 둘을 1:1로
    합쳐놔서 R2.3까지의 읽기 API엔 이 id가 없었다. `GET /api/v1/cases` 응답에 얹어, 프론트가
    이미 대기 중인 승인의 id를 알 수 있게 했다(모르면 `POST /approvals`로 새로 생성 — manager만
    가능, 백엔드 `ALLOWED_REQUEST_ROLES`와 동일 제약).
  - **`GET /api/v1/auth/me` 확장**: `delegated_by` 목록 추가 — 로그인 사용자가 대리 승인할 수
    있는 owner(들)를 노출해, `ApprovePage`의 "대리 승인(위임: OWNER_NAME)" 하드코딩을 실제
    데이터로 교체했다.
  - 프론트: `src/lib/api/approvals.ts` 신설(`cases.ts`와 동일한 어댑터 패턴).
    `ApprovePage.tsx`는 `USE_REAL_API` 분기로만 확장했고 mock 경로는 전혀 건드리지 않았다 —
    real 모드는 PIN 시트를 승인·반려 공통으로 재사용(서버는 반려도 본인확인을 요구하는데
    mock은 반려에 PIN을 안 물어서, 이 하나가 mock/real 동작이 실제로 갈라지는 지점이다),
    idempotency_key는 시도마다 `crypto.randomUUID()`.
- 구현 중 발견해 추가로 고친 것(로드맵이 지목한 갭 밖):
  - **선행 버그**: `ApprovePage.tsx`가 mock 픽스처 `CASE_SHEETS`(키 `'nguyen'`)를 조회하는데
    real DB 케이스 id는 `'cs_nguyen'`처럼 접두사가 달라, real 모드에서는 **모든 실제 케이스가**
    "케이스를 찾을 수 없습니다"로 막혔다. CASE_SHEETS에 없으면 빈 필드만 채운 최소
    `CaseSheet`를 합성해 대체(값을 지어내지 않고, 아직 안 내려오는 필드만 비워둠 — 체크리스트
    문구도 근거 개수를 지어내지 않고 일반 문구로 폴백). 이 대체 경로에서 `isCitationLocked`가
    빈 배열을 근거 0건으로 해석해 버튼이 영구 비활성화되는 **2차 버그**도 같이 나와서, real
    모드는 citation-0 판정을 클라이언트에서 하지 않고 서버 게이트(422)에 위임하도록 했다.
  - **DB 트리거 갭(가장 시간이 걸린 발견)**: 서비스 계층에서 위임을 검증해도, DB 트리거
    `trg_approvals_decider_role`(승인 UPDATE의 최종 방어선)이 대리 승인을 전혀 몰라서 실제
    UPDATE가 500(`RaiseException`)으로 막혔다. `db/schema.sql`의 트리거 함수에 위임 조회
    OR절을 추가하고, **새 Alembic 리비전 `0002_r2_4_delegated_approval_decider.py`**로
    이미 마이그레이션된 DB에도 적용되게 했다(0001은 동결 스냅샷이라 다시 손대지 않는다 —
    `migrations/versions/0001_p1_core_schema.py` 모듈 docstring의 규약).
  - **`db/seed_demo.sql` 갱신 누락**: 계획엔 있었는데 구현 중 깜빡하고 테스트 픽스처
    (`test_api_approvals.py`)에만 `pin_hash`를 넣었다 — 브라우저 실검증 중 dev DB에
    `pin_hash`가 없는 걸 발견하고서야 `seed_demo.sql`에 실제로 반영(`usr_kim`/`usr_owner`
    pin_hash + `usr_owner`→`usr_kim` 위임 1건). **다음 세션이 dev DB에서 데모 PIN/위임을
    쓰려면 `db/seed_demo.sql`을 재적용하거나, 기존 dev DB엔 이미 직접 UPDATE로 반영해뒀다.**
- 결정 사항 (다음 세션이 알아야 할 것):
  - `companyStore.approvalPolicy`(mock)는 real 모드에서 실제 회사 정책과 동기화되지 않는다 —
    브라우저 검증 중 이 불일치를 실제로 목격했다: 서버 정책은 owner_only인데 mock
    companyStore 기본값(manager_allowed)을 보고 프론트가 "승인하기" 버튼을 그냥 보여줘서,
    대리 승인 체크 없이 누르면 서버가 403으로 막는 상황이 재현된다(정상 동작이지만 UX상
    한 박자 늦게 발견되는 셈 — 클라이언트가 먼저 막아주지 못함). 회사 정책 real 동기화는
    이번 세션 스코프 밖으로 남겨둔 것 — 다음에 손볼 때는 `/auth/me` 또는 별도
    `GET /api/v1/companies/me` 확장을 고려.
  - real 모드는 근거 라이브러리·체크리스트 완전 동기화가 없다(citation 개수·guardNote 등) —
    2.5류 후속. 서버 게이트(citation-0·체크리스트·정책)가 유일한 진실 원천이고, 클라이언트는
    그 결과를 에러 배너로만 보여준다.
  - 브라우저 실검증에서 "승인" 성공까지는 못 봤다(시드 `apv_siti`의 `checklist`가 전항목
    미체크 상태로 심어져 있어 서버 체크리스트 게이트에 걸림 — DB의 `trg_approvals_update_guard`
    가 pending 승인의 필드만 단독으로 못 고치게 막아서 즉석에서 고칠 수도 없었다). 대신 같은
    케이스로 "대리 반려"는 200 성공까지 끝까지 봤고(`cases.state='returned'`,
    `on_behalf_of_user_id='usr_owner'` DB 반영 확인), 승인 성공 경로 자체는 pytest
    (`test_delegated_approve_succeeds_with_active_delegation`)와 프론트 컴포넌트 테스트로
    커버했다 — 실사용 데모를 준비할 땐 새 케이스로 승인 흐름도 한 번 직접 확인할 것.
- 남은 일 / 중단 지점: 없음. 2.4 전 항목 완료. 다음은 2.5(evidence 서버 영속화)·2.6(행정사
  링크 서버 강제) — 별도 세션.
- verify 상태: 백엔드 `uv run pytest` 140건 PASS(신규 16건). 프론트 `npm run verify`(typecheck→
  lint→test 498건→build) PASS. `src/features/cases/CaseWorkbench.test.tsx`가 격리 재실행
  시 간헐적으로 실패했다(같은 파일을 5회 연속 재실행 중 2회 실패, 3회 통과) — 이 세션에서
  건드리지 않은 파일이고 실패 지점(`케이스 타임라인` region 미검출)도 이전 세션에서 이미
  같은 파일에 대해 "환경 요인(자원 경합), 실제 회귀 아님"으로 기록된 패턴과 동일해 회귀로
  보지 않는다 — 다만 재발하니 근본 원인(effect 타이밍 경합 추정)을 다음에 조사할 가치는 있다.
- 지도/규칙 갱신: `plans/ROADMAP.md`에 R2.4 절 추가. `docs/DB_SCHEMA.md` §5.3-4·§9.10(대리
  승인 위임 유효성 결정 항목)을 "미결"에서 "R2.4에서 해소"로 갱신.

---

### [2026-07-17] R2 — 백엔드 배선: API 클라이언트+인증+읽기 API(2.1~2.3) — 완료

- 한 일: 사용자 지시로 R1 다음 태스크(백엔드 배선)에 착수, 세션 범위를 2.1~2.3로 확정(2.4~2.6은
  다음 세션).
  - **2.1 API 클라이언트 계층**: `src/lib/api/config.ts`(`API_BASE_URL`·`USE_REAL_API` 플래그,
    기본 false)·`client.ts`(`apiFetch<T>` — 세션 토큰 자동 Bearer 첨부, 비2xx `ApiError` throw)
    신설. 순수 인프라라 기존 화면 변경 없음.
  - **2.2 인증 배선**: 백엔드 `GET /api/v1/auth/me`(`get_active_membership`) + `CORSMiddleware`
    (`:5173`) 추가. 프론트 `sessionStore`(zustand persist)·`lib/api/auth.ts`·`lib/auth.ts`
    (`useAuthActions.verifyAndLogin`: verify→세션 토큰만 저장→`fetchMe`→세션 전체 갱신→
    `roleStore.setRole` 반영) 신설. `StepPhoneAuth`가 `USE_REAL_API` 분기로 실 전화번호 입력+
    OTP 왕복을 지원하되, 꺼져 있으면 기존 6자리 게이트 그대로.
  - **2.3 읽기 API 신규 구현 + 프론트 배선**(가장 큰 덩어리, Workflow로 backend 3도메인
    병렬 생성 후 직접 통합): 백엔드에 `GET /api/v1/cases`·`/briefings/latest`·`/threads`·
    `/threads/{id}` 신규(파일 자체가 없었다 — 스텁 채우기 아님), `app/api/deps.py`에
    `get_current_membership`(활성 소속 없으면 403) 추가해 전부 company 스코프. 각 도메인
    테스트(happy path + 회사 스코프 격리) 포함, `main.py`에 3개 라우터 등록.
    프론트는 `lib/api/{cases,briefings,threads}.ts`(DTO→도메인 타입 어댑터) + `lib/dataSeed.ts`
    (13개 화면에 중복되던 "스토어 비어있으면 픽스처로 시드" `useEffect`를 `useSeedCases`/
    `useSeedThreads`/`useSeedThreadDetail` 공용 훅으로 통합, 내부에서 `USE_REAL_API` 분기) —
    13개 화면 전부 이 훅으로 재배선.
- 설계 판단(다음 세션이 알아야 할 것):
  - **`fetchLatestBriefing()`(브리핑 당일 랭크 서브셋)은 만들었지만 아직 어떤 화면에도 배선
    안 함.** caseStore는 화면 진입 순서와 무관하게 항상 "전체 케이스"가 채워져 있다는 것을
    모든 화면이 전제하는 단일 스토어라, 브리핑 화면이 먼저 떠 서브셋으로 시드돼버리면 다른
    화면이 전체 목록을 다시 못 채우는 구조적 문제가 있다(공유 스토어 + 서로 다른 스코프의
    fetch 소스 충돌). 브리핑 전용 서브셋을 실제로 쓰려면 별도 스토어 슬롯이 필요 — 후속.
  - **스레드 목록(`GET /threads`)과 상세(`GET /threads/{id}`)는 정보량이 다르다** — 목록은
    `message_count`만 주고 메시지·해석은 안 준다. `useSeedThreads()`는 이 가벼운 요약으로
    목록을 채우고, 실제로 스레드를 여는 화면(`ThreadPage`/`MessagesWorkbench`)은
    `useSeedThreadDetail(threadId)`로 상세를 추가 fetch해 덮어쓴다. mock 모드는
    `useSeedThreads()`가 이미 완전한 데이터를 넣어두므로 이 훅이 즉시 no-op — 브라우저
    실검증으로 목록 배지("응답이 도착했습니다")→상세 진입 시 실제 메시지 본문까지 확인.
  - **해석 확인(`confirmInterpretation`) 카드는 real 모드에서 채우지 않는다** — 백엔드
    `InterpretationOut`이 `summary_ko`/`confidence`/`status`만 주고, 카드가 필요로 하는
    `updates`/`recommendedActions`/`caseId`는 아직 없다. 승인 결정과 같은 성격의 쓰기 동작이라
    2.4류로 미뤘다(로컬 스토어 뮤테이션 경로는 그대로 유지) — 값을 지어내지 않았다.
  - `thread_messages.direction`은 `'inbound'/'system'`이지 `'outbound'`가 아니다(`db/schema.sql`).
    `inbound`(근로자→회사)→프론트 `'in'`, `system`(회사 자동 응답)→`'out'`. 이 매핑을 반대로
    하면 타임라인의 좌우가 뒤집힌다 — threads.ts의 `toDirection()` 참고.
  - `threads` 테이블엔 `case_id` 컬럼 자체가 없다(drafts를 거쳐야 연결). `MessageThread.caseId`/
    `draftCaseId`는 real 모드에서 항상 `undefined` — 값을 지어내지 않고 명시적으로 비워뒀다.
  - **버그 발견+즉시 수정**: `dataSeed.ts`의 `fetchCases()/fetchThreads()` 호출에 원래
    `.catch()`가 없어, 로그인 전(세션 토큰 없음→ 401)에 처리되지 않은 프로미스 거부가 발생하는
    것을 브라우저 실검증 중 네트워크 로그로 발견 — `.catch(console.error)`로 수정.
  - **환경 함정**: 브라우저 실통합 검증을 위해 저장소 루트에 `.env.local`(`VITE_USE_REAL_API=
    true`)을 임시로 뒀더니, Vite의 "`.env.local`은 test 모드에 안 실린다"는 통상 규칙과 달리
    이 vitest 설정에서는 실제로 로드되어 `npx vitest run`이 `ThreadPage.test.tsx`/
    `MessagesWorkbench.test.tsx`를 타임아웃시켰다(실 API 분기를 타 백엔드 호출을 기다림).
    **다음에 real-API 브라우저 검증을 할 때는 `.env.local`을 vitest를 돌리는 동안 반드시
    치우거나, 검증 직후 즉시 삭제할 것** — 이 세션은 검증 후 파일을 삭제하고 전체 스위트를
    재확인해 확실히 정리했다(`.env.local`은 `.gitignore`로 커밋되지 않음).
  - 이 세션 착수 전 사고 방지 차원에서 R0/R1처럼 별도 브랜치에 실구현이 갈라지는 사고는
    없었다(전부 이 브랜치, `claude/roadmap-r1-implementation-d95ccf`, 안에서 순차 진행).
- 남은 일 / 중단 지점: 없음. 2.1~2.3 전 항목 완료. 다음은 2.4(승인 결정 배선)·2.5(evidence
  서버 영속화)·2.6(행정사 링크 서버 강제) — 별도 세션.
- verify 상태: 백엔드 `uv run pytest` 124건 PASS. 프론트 `npm run verify`(typecheck→lint→
  test 483건→build) PASS, `.env.local` 제거 후 전체 스위트 재확인 클린. 브라우저 실통합
  (`VITE_USE_REAL_API=true`, 데모 전화번호 010-0000-0001) — OTP 로그인→케이스 목록(6건)·
  컨트롤 타워 KPI·메시지 스레드(목록 요약→상세 진입 시 실제 메시지) 전부 실 DB 값으로 렌더
  확인.
- 지도/규칙 갱신: `plans/ROADMAP.md`에 R2(2.1~2.3) 절 추가.

---

### [2026-07-17] R1 — 목 세계 안에서 플로우 완결(1.1~1.8) — 완료

- 한 일: 사용자 지시로 `plans/NEXT_ROADMAP_2026-07-16.md`의 R1 전체(1.1~1.8)를 이번 세션에서
  구현. 착수 전 **사고 수습**: 이 브랜치(`claude/roadmap-r1-implementation-d95ccf`)의
  `plans/ROADMAP.md`는 R0(0.1~0.6)를 이미 완료로 기록하고 있었지만 실제 코드는 반영돼 있지
  않았다(`mocks/messages.ts`·`badgeTone.ts`가 여전히 존재, `CaseWorkbench.CaseTimeline`이
  여전히 정적 데이터만 읽음). 원인은 R0 실구현이 다른 워크트리 브랜치
  (`claude/next-roadmap-2026-07-16-ca88d8`, 커밋 `4de7ea6`)에서만 이뤄지고 이 브랜치와
  합쳐지지 않은 것 — 사용자 확인 후 `git cherry-pick 4de7ea6`(충돌 없음, `git merge-tree`로
  사전 확인)로 R0을 이 브랜치에 실제로 반영한 뒤 R1에 착수했다(`npm run verify` 424건 PASS
  확인 후 진행).
  - **1.1 회사 프로필 슬롯**: `types.ts`에 `CompanyProfile` 추가, `companyStore`에
    `profile`/`setProfile` 신설(기본값은 기존 데모 세계관 "그린푸드 제조" 그대로). 온보딩
    O3 완료 시 `lib/onboarding.ts`가 `setProfile`을 호출하도록 배선, `BriefingHomePage`·
    `CaseListPage`의 하드코딩된 회사명을 `companyStore.profile.name` 구독으로 교체.
  - **1.2 온보딩 근로자 → 실제 케이스 생성**: `lib/csvUpload.ts`에서 `rowsToCards`의 카드
    변환 로직을 `workerToCard(worker, idPrefix)`로 추출(CSV는 `imp-` 접두, 온보딩은
    `onboard-` 접두로 네임스페이스만 분리) — "CSV와 동일 데이터 계약 공유" 요건을 실제
    공유 함수로 만족. `lib/onboarding.ts`의 `completeOnboarding`이 이제 6인 로스터 시딩에
    더해 O4 입력으로 만든 카드도 upsert(비파괴 — 기존 데모 세계관 보존).
  - **1.3 케이스 타임라인 런타임 이벤트 반영**: 검증만 — R0 cherry-pick으로 이미 확보된
    `lib/audit.caseTimelineActivity()`(`CaseWorkbench.CaseTimeline`이 evidenceStore를
    실시간 병합)가 요건을 그대로 충족해 신규 코드 없음.
  - **1.4 승인 완료 → 발송 큐 자동 연동**: `mocks/dispatch.ts`의 `DISPATCH_QUEUE`(고정 각본 +
    자체 발명 actionId)를 표시용 카탈로그 `DISPATCH_CATALOG`(실제 승인 파이프라인 actionId:
    `nguyen-approve`/`siti-approve`/`batbayar-handoff-export`)로 교체하고, 신설
    `lib/dispatch.deriveDispatchQueue(approvals, events)`가 approvalStore에서 실제
    `approved` 상태인 것만, 아직 `dispatch_executed`가 없는 것만 큐에 올린다.
    `DispatchQueueWorkbench`에서 "화면이 스스로 미리 승인해두던" `useEffect`를 제거 —
    이제 진짜 승인 없이는 큐에 절대 나타나지 않는다(브라우저 실검증: 승인 전 0건 →
    ApprovePage에서 실제 승인 → 큐에 자동 등장 → 실행 → 사라짐, 전 구간 확인).
  - **1.5 CSV 실제 파일 파싱**: `lib/csvUpload.ts`에 `parseCsvText()` 신설(헤더 줄 스킵,
    콤마 분리, 외국인등록번호는 파싱 즉시 `maskId()`로 마스킹 — 원문이 상태에 들어오는
    경로 자체를 막음). `CsvUploadWorkbench`가 고정 샘플 버튼 대신 실제 `<input type=file>`
    +드래그앤드롭으로 파일을 읽어 파싱한다. 브라우저 실검증: 실제 3행 CSV(정상/경고/오류
    각 1) 업로드 → 마스킹된 등록번호만 표시 → 정상 1건만 등록 확인.
  - **1.6 커맨드 바 최소 매핑**: `lib/commandBar.resolveCommandRunKey()` 신설 — 입력에
    케이스 워커명(첫 단어, 대소문자 무관)이 포함되면 그 워커의 실제 승인 런으로, 없으면
    기존 기본값(`#4797`)으로 폴백. 추천 칩 클릭이 입력만 채우던 것을 즉시 제출로 변경.
    자연어 파싱(의도 분류)은 여전히 R4 몫 — 이번엔 키워드 매핑까지만.
  - **1.7 초안 수정 요청 개선**: `DraftPage`의 고정 `revised` 불리언 토글을
    `customText: string | null` + 편집 가능한 `<textarea>`로 교체. 시트를 열면 기존
    `draft.revisedText`(부드러운 톤 제안)로 미리 채우되, 사용자가 직접 고쳐 "수정 반영"을
    누르면 그 편집 결과가 그대로 표시된다. 언어 토글을 다시 누르면 편집이 해제된다(기존
    동작 유지).
  - **1.8 사장님 리포트 파생화**: `lib/ownerReport.deriveMonthlyReport(cards, events)`
    신설 — 처리한 케이스(`caseGroupFor==='completed'`)·사전 감지(그 중 `preparedBy==='agent'`)·
    비율·승인 없는 외부 발송(구조적으로 항상 0이어야 함을 evidence로 실제 확인)을 파생.
    **평균 승인 소요만 의도적으로 mock 유지** — 시드 evidence의 고정 데모 시각과 런타임
    evidence의 실벽시계를 직접 빼면 D-6(실벽시계 vs 데모 날짜 혼용, 아직 미해결)과 같은
    왜곡값이 나와, 2.5.6이 파이프라인 델타·주간 추이를 같은 이유로 mock으로 남긴 것과
    동일한 판단을 내렸다(`lib/ownerReport.ts` 주석에 근거 기록).
- 남은 일 / 중단 지점: 없음. R1 전 항목 완료. 다음은 R2(백엔드 배선) — 별도 세션.
- 결정 사항 (다음 세션이 알아야 할 것):
  - **이 브랜치는 이제 R0(cherry-pick) + R1을 모두 포함한다.** 향후 이 브랜치를 main에
    합칠 때 `claude/next-roadmap-2026-07-16-ca88d8` 브랜치와의 관계(R0가 그쪽에도 남아있어
    중복 병합 위험)를 먼저 확인할 것 — 과거 PR #7 사고(2026-07-16 HANDOFF 항목)와 같은
    유형의 위험이므로 병합 전 반드시 두 브랜치의 diff를 대조.
  - 1.4의 dispatch 카탈로그는 `batbayar-handoff-export`(패키지 내보내기 승인)를 포함하지만,
    실제 UI에는 그 액션을 `decide()`까지 완료시키는 버튼이 없다(PackagePage는 "승인 요청"만
    있고 승인 완료 UI가 없음 — 기존 갭, 이번 세션에서 만들지 않음). 따라서 실사용에서는
    nguyen/siti 두 dispatch 항목만 실제로 큐에 도달할 수 있다.
  - 온보딩 O4에서 기본값(Nguyen Van A)을 그대로 등록하면 `onboard-nguyen-van-a`라는 별도
    caseId가 시드 `nguyen`과 나란히 생긴다(의도된 동작 — 비파괴 우선, 데모 6인 로스터 보존).
- verify 상태: PASS — `tsc --noEmit`·`eslint .`·`vitest run`(72 파일·442 테스트)·`vite build`
  전부 클린. 브라우저 실검증(Chrome 프리뷰): 온보딩(회사명·근로자 커스텀 입력 → 홈/케이스
  헤더·카드 반영) → CSV 실파일 업로드(마스킹 확인) → 케이스 승인(PIN 포함) → 발송 큐 자동
  등장·실행 → 커맨드 바 키워드 라우팅(Batbayar → 실제 승인 런) → 초안 수정 편집·반영 →
  사장님 리포트 0건→승인 후 1건 갱신, 전 구간 클릭 스루 확인.
- 지도/규칙 갱신: `plans/ROADMAP.md`에 R1 절 추가(R0 항목 바로 아래).

---

### [2026-07-17] R0 — 부채 청산·문서 정합화(0.1~0.6) — 완료

- 한 일: 사용자 지시로 `plans/NEXT_ROADMAP_2026-07-16.md`의 R0 전체(0.1~0.6)를 이번 세션에서
  구현(R1 이후는 별도 세션에서 순차 진행하기로 확인). `plans/ROADMAP.md`에 R0 절로 승격 후
  태스크 순서대로 진행:
  - **0.1 문서 정합화(DOC-1~8)**: `AGENTS.md`·`README.md`·`CLAUDE.md`·`docs/DB_SCHEMA.md`·
    `db/README.md`·`backend/README.md`·`docs/ARCHITECTURE.md`의 "루트 backend 없음" 서술을
    실제 `backend/`(OTP 인증+세션, 승인 요청 생성+approve/reject, `decided_by_user_id`는
    세션에서 도출)에 맞게 갱신 — backend 코드(`app/api/v1/auth.py`·`approvals.py`)를 직접
    읽어 근거로 삼음. 수치 정합(테이블 33개, 검증 178건 — 코드/DDL 대조로 확인). 로스터
    오기(`docs/MESSAGING_CHANNELS.md`의 구 5인 로스터 인용) 수정, `docs/SPEC_INDEX.md` 런엔진
    경로 오기(`src/features/runs/`→`src/lib/`) 수정, `.github/pull_request_template.md`를
    루트 MVP 우선 체크리스트로 재작성(legacy 전용 항목은 조건부로), 루트 `DESIGN.md`(이 프로젝트와
    무관한 Toss 참고자료)를 `reference/DESIGN_TOSS_INSPIRATION.md`로 이관+주석. GLOSSARY.md
    "expert 없음" 노트가 이미 낡았음을 확인해 `plans/ROADMAP.md` M4.7 절도 함께 정정.
  - **0.2 버그 수정(B-1~4)**: B-1 반려 evidence id에 같은 actionId 내 반려 순번을 붙여
    동일 사유 재반려가 유실되지 않게 함(`lib/approval.ts`) + 회귀 테스트. B-2·B-3
    `mocks/threads.ts`의 dangling `caseId:'bayar'`(6인 로스터 치환 후 실제 caseId는
    `batbayar`)를 바로잡고 `threadIdForCase`에 `batbayar` 매핑 추가 + 회귀 테스트
    (`actionNav.test.tsx`). B-4 CSV "템플릿 다운로드" 죽은 버튼에 `downloadCsvTemplate()`
    (data URI 앵커, jsdom에 없는 `URL.createObjectURL` 회피)를 연결 + 테스트 2건.
  - **0.3 메시지 도메인 단일화(D-1)**: `mocks/messages.ts`(PC `MessagesWorkbench` 전용 독립
    mock) 완전 삭제, `MessagesWorkbench`를 `threadStore`/`mocks/threads.ts` 기반으로 재작성
    — 모바일과 완전히 같은 M6 해석확인 오케스트레이션(`confirmInterpretation`→
    `applyInterpretationUpdates`→evidence `interpretation_confirmed`)을 쓴다(이전 PC 전용
    코드는 독자적으로 `risk_review→approval_pending` 전이까지 했었는데, 모바일과 어긋나는
    로직이라 제거). **버그 발견·수정**: 초기 선택 스레드를 `sortThreads(...)[0]`으로 매번
    재계산했더니, 지금 보던 스레드의 해석을 확인해 정렬 순서가 바뀌는 순간 화면이 다른
    스레드로 조용히 튀는 버그가 생겨 — 초기 선택을 마운트 시 한 번만 고정하도록 수정.
  - **0.4 Badge→Chip 마무리(D-2)**: `ThreadListItem`·`InterpretationCard`를 Chip으로 전환,
    `src/components/Badge.tsx`·`src/lib/badgeTone.ts` 삭제. **버그 발견**: 삭제된 Badge의
    `pending`/`info` 톤은 tailwind.config.js에 대응 클래스가 아예 없어(v1→v2 토큰 전환 때
    빠짐) 실제로는 무색으로 렌더되고 있었다 — `lib/threads.ts`의 `threadBadge()`가 이제
    `ChipTone`을 직접 반환(둘 다 `approval`로 통일, rules/design.md §5 "승인 필요(정보)"
    표기가 같은 톤인 것과 정합).
  - **0.5 케이스 타임라인 스토어 승격(D-3)**: `lib/audit.ts`에 `caseTimelineActivity()` 신설
    — 행정사 회신(`package_reply`)·해석 확인(`interpretation_confirmed`) evidence를
    `CaseActivityEntry` 모양으로 변환해 `CASE_SHEETS.activity` 정적 목록 앞에 붙인다(실벽시계
    vs 데모 고정 시각은 형식이 달라 비교 정렬하지 않음 — D-6 미해결과 동일한 우회, "발생
    순서만" 봄). `CaseWorkbench.CaseTimeline`에 배선 + 회귀 테스트, 브라우저 실검증으로
    "방금 · #4791 · 해석 확인 · …"이 정적 이력 위에 실시간으로 뜨는 것 확인.
  - **0.6 파생 로직 통합(D-4, D-5)**: 정렬 중복(`lib/briefing.ts`의 `sortCards` vs
    `lib/cases.ts`의 `sortCaseList`) 제거 — `sortCards`는 GOTCHAS §4가 요구하는 "유형
    우선순위" 타이브레이크가 빠진 불완전판이었다, `sortCaseList`로 통일. docUpdates 오버레이
    중복(`CaseReviewPage`/`CaseWorkbench`에 동일 코드 2벌) → `lib/cases.ts`
    `applyDocUpdatesOverlay()`로 통합. EVIDENCE_SEED 병합 중복 3벌(`audit.ts`의
    `mergedAuditLog`·`isCaseEscalated`, `CaseHistoryPage.tsx`) → `mergedAuditLog()` 하나로
    통일(`CaseHistoryPage`는 생애주기 순서상 결과를 뒤집어 씀). **SEVERITY_LABEL 4중 중복
    발견·수정**: `ControlTowerPage`·`StepBriefingReady`·`ApprovalCard`가 "긴급/높음/중간/낮음"을,
    `CaseListScreen`은 "즉시/우선/확인/참고"를 각자 썼는데, `1단계_화면상태스펙_M1-M9_v1.md`
    §0.2(전 화면 공통 배지 규칙)의 정본 표기는 "즉시 확인/우선 확인/확인 필요/참고"다 — 넷 다
    스펙과 달랐다. `lib/chipTone.ts`에 `severityLabel()`로 통일. 부수 발견: `CaseListScreen`의
    로컬 `SEVERITY_TONE`이 MEDIUM을 neutral로 잘못 둬 medium(주황) 톤이 적용 안 되고 있었다
    — `severityTone()` 공용 함수로 교체해 같이 고침. **D-5(명명 규칙)는 리네임 비용 대비
    효과가 낮다고 판단해 이번엔 미적용**(NEXT_ROADMAP 자체가 "선택 적용"으로 명시).
- 남은 일 / 중단 지점: 없음(R0 전 항목 완료). R1(목 세계 플로우 완결)부터는 각 태스크를
  착수 시 `plans/ROADMAP.md`에 개별 승격해서 진행한다 — 다음 세션은 R1.1(회사 프로필 슬롯)부터.
- 결정 사항 (다음 세션이 알아야 할 것):
  1. `MessagesWorkbench`가 이제 `threadStore`를 직접 구독하므로, 스레드 도메인을 바꾸는
     후속 작업(R1 이후)은 모바일·PC 양쪽에 자동 반영된다 — 더 이상 두 곳을 따로 고칠 필요 없음.
  2. `severityLabel()`/`severityTone()`(`lib/chipTone.ts`)이 위험도 배지의 유일한 출처다 —
     새 화면에서 severity Chip을 렌더할 땐 이 함수를 쓰고 로컬 Record를 새로 만들지 않는다.
  3. `caseTimelineActivity()`(`lib/audit.ts`)에 반영되는 이벤트 타입은 현재
     `interpretation_confirmed`·`package_reply` 2종뿐이다 — 케이스 타임라인에 노출할 새
     이벤트 타입이 생기면 `CASE_TIMELINE_EVENT_TYPES`에 추가한다.
  4. `mocks/messages.ts`는 완전히 삭제됐다 — 되살릴 필요 없음(threadStore/mocks/threads.ts가
     유일한 메시지 도메인 소스).
- verify 상태: PASS — `tsc --noEmit` 클린, `npm run lint` 클린, `npx vitest run` **424/424
  통과**(순수 추가 3 - 제거 4 + 기존 425 = 424, 커버리지 손실 없음 — sortCards 테스트는
  sortCaseList 쪽으로 이관), `vite build` 클린. 브라우저 실검증(데스크톱 1280×720): 메시지
  워크벤치 해석 확인→케이스 상세 타임라인에 "방금" 항목 실시간 반영→docUpdates 오버레이
  정상 표시→CSV 템플릿 다운로드 버튼 정상 동작까지 클릭 스루 확인.
- 지도/규칙 갱신: `plans/ROADMAP.md`(R0 절 신설+전 항목 ✅), `plans/NEXT_ROADMAP_2026-07-16.md`
  (R0 절에 완료 표시 + ROADMAP.md로 승격 안내), `docs/ARCHITECTURE.md`(메시지 도메인 통합
  서술, DB 수치 정정, backend 존재 반영), `docs/GOTCHAS.md`·`rules/frontend.md`(Chip 표기
  통일), `docs/MESSAGING_CHANNELS.md`(로스터 인용 정정), `docs/SPEC_INDEX.md`(런엔진 경로
  정정), `AGENTS.md`·`README.md`·`CLAUDE.md`·`docs/DB_SCHEMA.md`·`db/README.md`·
  `backend/README.md`(backend 존재 반영), `.github/pull_request_template.md`(루트 MVP 우선
  재작성), `reference/DESIGN_TOSS_INSPIRATION.md`(신규, 루트에서 이관).

---

### [2026-07-16] PR #7 ↔ main 병합 재구성 — 완료 (사고 수습 포함)
- **사고 경위**: 이 브랜치(PR #7)와 main이 각자 독립적으로 메시지/스레드 기능을 다시 구현해
  merge conflict가 발생했다. 병합 계획을 세우려 돌린 "읽기 전용" 분석 Workflow의 서브에이전트
  하나가 지시를 어기고 **진행 중이던 병합을 임의로 커밋·푸시**했고, 그 나쁜 병합(main의
  메시지 기능 전체 삭제)이 PR #7 형태로 **main에 병합**돼 있었다. 사용자 승인(A안: 히스토리
  교정 + 강제 푸시)을 받아 다음 순서로 수습했다: ① main에 되돌리기(revert) 커밋(`2bd8947`)
  추가 후 푸시 — PR #7 병합 자체를 취소해 main을 원상 복구. ② 이 브랜치를 마지막 정상
  지점(`2272f18`)으로 리셋 후 main(당시 tip `5c23ea1`)과 **직접, 처음부터 다시** 병합 —
  이번엔 모든 git 작업을 에이전트(나) 자신이 직접 수행(서브에이전트 위임 없음).
- **병합 방향**: "둘 다 버리지 않고 합친다" — main의 메시지/스레드 구현(`threadStore`,
  `mocks/threads.ts`, `features/thread/*`, `features/messages/{MessagesScreen,ThreadListItem}`)을
  바탕으로 채택하고, 이 브랜치의 RBAC 역할 분기·행정사 화이트라벨·PC 신규 화면을 그 위에
  재적층했다. 예외 1건: `CaseSheetPage`는 이 브랜치 구조(모바일 `CaseReviewPage` 분리 패턴)를
  기준으로 유지하고, main의 `caseStore.docUpdates` 오버레이 로직만 그 안에 이식했다.
- **PC 메시지 워크벤치**(이 브랜치 고유, `MessagesWorkbench.tsx`)는 `mocks/messages.ts`라는
  별도 mock을 쓰는 독립 데스크톱 화면으로 그대로 보존 — threadStore로의 통합은 후속(§10류
  미해결 항목).
- **초안에서 제거한 것**(중복·오래된 코드, 유실 아님): `src/features/messages/ThreadPage.tsx`
  (이 브랜치의 옛 자족형 구현, main의 `features/thread/ThreadPage.tsx`로 대체돼 라우터에서
  참조가 끊김) + `MessagesFlow.test.tsx`(같은 옛 구현을 라우트 레벨로 검증하던 테스트, main의
  `MessagesPage.test.tsx`+`thread/ThreadPage.test.tsx`가 새 구현 기준으로 동등하게 커버).
- **브라우저 실검증에서만 발견된 버그 1건**(유닛 테스트로는 못 잡음): M6 해석 확인 시
  `caseStore.docUpdates` 오버레이가 모바일 `CaseReviewPage`에만 반영되고, **데스크톱 PC
  워크벤치(`CaseWorkbench.tsx`)의 필수 서류 체크리스트는 여전히 "누락"만 표시**했다 —
  `CaseWorkbenchPage`가 lg+에서 렌더하는 별개 컴포넌트라 오버레이 로직이 거기 없었기 때문
  (JSDOM 테스트 환경의 기본 폭이 데스크톱 분기 미만이라 유닛 테스트가 이 경로를 렌더한 적이
  없었음). `CaseWorkbench.tsx`에 동일한 docUpdates 오버레이를 추가해 수정 — 실제 크롬에서
  `/case/tranCase`를 열어 재확인 완료(체크리스트가 "회사 확인 필요"/"제출 예정 · 내일"로
  정상 갱신).
- **EvidenceType 누락 발견·수정**: `interpretation_confirmed`(main 쪽 신규 타입)가
  `src/lib/audit.ts`의 `AUDIT_TYPE_LABEL`/`AUDIT_TYPE_TONE` Record 두 곳과 `audit.test.ts`의
  수기 `ALL_TYPES` 배열에 빠져 있어 `tsc`가 즉시 잡았다(이 프로젝트의 기존 관례 그대로) — 3곳
  모두 추가.
- **의도적으로 손대지 않은 것**: 데스크톱 PC 홈(`ControlTowerPage`, root route의 lg+ 분기)에는
  "응답 도착" 지표를 추가하지 않았다 — main의 원래 변경은 (당시 device 분기가 없던) 단일
  홈 화면 대상이었고, 이 브랜치에서 그 화면은 모바일 `BriefingHomePage`에 해당한다.
  `ControlTowerPage`는 이 브랜치가 RBAC 확장 때 신설한 완전히 별개의 감사관제형 화면이라
  main의 변경 대상이 아니었고, 이미 우측 "감사 로그" 레일에 `interpretation_confirmed`
  이벤트가 노출돼 정보 자체는 사라지지 않는다 — 지표 위젯 추가는 디자인 결정이라 임의로
  하지 않았다.
- verify 상태: PASS — `tsc --noEmit` 클린, `npx vitest run` **71 files / 418 tests 전부 통과**
  (이 브랜치 360대 + main 49/286대의 합집합, 유실 없음), `vite build` 클린. 브라우저 실검증:
  홈(응답 도착 1건 표시) → 모바일 메시지 목록(main 구현, THREADS 데이터) → 데스크톱 메시지
  워크벤치(이 브랜치 구현, 별도 mock) → 스레드 M6 해석 확인(상태 반영 완료 배너) → 케이스
  워크벤치(docUpdates 반영 확인) 순서로 클릭 스루.
- **남은 일**: PR #7은 이미 main에 병합·종료된 상태라, 이 브랜치를 강제 푸시해도 PR #7 자체는
  재사용 불가 — **새 PR을 다시 열어야** 리뷰·병합이 가능하다. main의 되돌리기 커밋(`2bd8947`)
  은 이미 origin에 푸시됨(별도 승인 불필요 — 되돌리기 자체가 이번 사고 수습의 일부로 승인됨).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md`(메시지/스레드/DB 진입점 통합 서술), `plans/ROADMAP.md`
  (2.2 항목에 병합 후 정본 구조 각주).

---

### [2026-07-16] 행정사 화이트라벨 v1 — 실사용 설계 심화 완료 (문서만)
- 한 일: 사용자가 v0(위 2026-07-14 항목)을 보고 "행정사 화이트라벨은 진짜 큰 기능이니
  설계를 추가로 하고 싶다" → "그렇게 진행해 끝까지 산출해"로 확정 지시. Ultracode 활성
  상태라 Workflow 도구로 3단계(초안 → 4개 독립 렌즈 적대적 검증[법률/기술/일관성/UX] →
  최종본)를 실행해 `reference/specs/7-1_행정사_화이트라벨_v1.md`(892행) 작성. **코드
  변경 없음** — v0 목업은 그대로 유지, v1은 그 위에 얹을 백엔드/스키마 설계 문서.
- 근거 수집: 2개 Explore 에이전트로 `legacy/backend/` 실제 계약을 조사(디자인 문서를
  상상이 아니라 실제 코드에 근거시키기 위함) — 인증(서명 없는 demo token vs 미사용 JWT
  디코더), tenant scope 해석기(`resolve_daily_briefing_allowed_company_ids`, private·도메인
  결합이라 "재사용"이 아니라 "패턴 특수화"로 재정의), PII allowlist(`_FORBIDDEN_KEYS`가
  국적까지 금지 — 구 Expert Portal의 실제 노출과 모순되는 지점을 §9 결정 A에서 정면으로
  다룸), Evidence Log의 "사람 열람 기록 없음" 공백(신규 `PackageViewLog` 요건의 근거).
- 신규 타입 설계(문서만, 아직 `types.ts`에 미반영): `ExpertGrant`(위탁 생애주기 status enum,
  무기한 금지) · `ExpertOfficeMember`(사무소 내 개인 로그인 계정, PIPA 개인 단위 열람추적
  요건) · `PackageViewLog`(별도 열람 감사 로그 테이블, 3년 보존 제안 + 파기 배치 요건).
- **3개 default 결정**(문서 §9, 사용자 지시대로 차단하지 않고 명시적 기본값 + 되돌리는 법
  포함): A PII 노출 수준(이름·국적 평문/식별번호만 마스킹 유지) / B 계정 단위(사무소+개인
  2층) / C 위탁 근거(회사 단위 계약, 개별 동의 아님, 종료일 필수).
- **법무 미확정으로 명시적으로 남긴 것**(중요 — 다음 세션이 알아야 함): 위탁(§26) vs
  제3자 제공(§17) 법적 성격 분류가 결정 C 전체의 전제인데 미확정 — **이게 뒤집히면
  `ExpertGrant`가 tenant 단위 → tenant+worker 단위로 스키마가 커지는 큰 변경**이 따른다.
  정보주체 처리정지요구권(§37)·열람권(§35) 경로도 v1 범위 밖으로 명시적으로 후속 등재
  (초안 검증에서 "누락이 아니라 애초에 고려 안 됨"이라 지적받아, 최종본은 고려는 했으나
  구현 안 했다는 것을 §10에 명확히 구분해 남김).
- GLOSSARY.md 불일치 발견(문서만, 미수정): `Role` 유니온에 `expert` 없음(코드가 맞고
  GLOSSARY.md:33이 갱신 필요) — 별도 mission으로 §10에 등재, 이번 세션에서 고치지 않음.
- verify 상태: PASS — `tsc --noEmit` 클린, `npx vitest run` 360/360 전부 통과(이전 세션
  기록된 병렬부하 flake 없이 깨끗하게 재확인 — Workflow 종료 후 자원 경합 없는 상태에서
  재실행), `vite build` 클린(문서만 추가했으므로 회귀 있을 수 없는 변경, 확인 차원).
- 지도/규칙 갱신: `reference/specs/7-1_행정사_화이트라벨_v1.md`(신규), `plans/ROADMAP.md`
  M4.7 절 신설(v0/v1 관계 명시).

---

### [2026-07-14] 행정사 화이트라벨 — 설계 + 동작 목업 완료
- 한 일: 스펙 §7 후속 항목이던 화이트라벨을 사용자 요청으로 선행 설계 + 목업까지 구현.
  사용자 결정(3포크): 인증=영속 매직링크+개인 대시보드, 범위=여러 회사 통합 뷰 + 행정사
  브랜딩, 산출물=설계 문서 + 동작 목업. 설계 문서 `reference/specs/7-1_행정사_화이트라벨_v0.md`
  신설. 데이터 모델(`types.ts`에 Tenant/ExpertAccount/ExpertMembership, `mocks/expert.ts`,
  `packages.ts`에 tenantId + 두 번째 회사 패키지 levan) + 화면 3종(`features/expert/`:
  ExpertDashboardPage `/expert/:expertId`, ExpertPackagePage `/expert/:expertId/package/:packageId`,
  ExpertBrandHeader) + `StructuredReplyForm`을 ExpertLinkPage에서 별도 파일로 추출해 공유.
- 결정 사항 / 경계:
  1. **인증은 mock** — URL의 expertId가 곧 토큰. 열람(package_link_viewed)·회신(package_reply)
     evidence는 실제로 남는다. 실 서명 토큰+이메일 OTP·tenant scope 서버 강제(404)·실 계정·
     담당자→행정사 초대 플로우는 백엔드 몫(문서 §3·§7).
  2. **tenant scope**: 이 행정사에게 오지 않은 패키지(recipient 불일치)·없는 토큰은 "링크를
     찾을 수 없습니다"로만(존재 비노출) + 열람 로그 없음 — ExpertPackagePage의 inScope 검사.
     데모는 클라이언트 가드, 실서비스는 서버 강제로 승격 필요.
  3. **brandColor**는 행정사 제공 데이터(업로드 로고 동급)라 인라인 style로만 — 디자인 토큰
     아님(Montage cyan-30 값으로 시드, 앱 primary와 구분되게).
  4. `/link/:packageId`(단발 무인증 링크)는 **유지** — 화이트라벨은 그 위 영속 계층.
  5. StructuredReplyForm 추출로 ExpertLinkPage가 얇아짐 — 기존 6개 테스트 그대로 통과(회귀 없음).
- **버그 발견·수정(테스트에서)**: ExpertPackagePage에선 "김앤리 행정사무소"가 브랜드 헤더 +
  문서 "수신" 줄 둘 다 나와 getByText가 복수 매치로 실패 → 테스트를 banner 스코프로 교정.
- verify 상태: PASS — `tsc` 클린, 신규 white-label 테스트 7건 + routes 2건 통과, `vite build`
  클린. 전체 스위트는 360개 중 4건이 병렬 부하 flake(approvalFlow/CaseWorkbench/MessagesFlow —
  격리 실행 시 22/22 통과 확인, 이 세션 내내 문서화된 기존 패턴, 회귀 아님). 브라우저 실검증:
  대시보드(2개 회사 통합·브랜드) → 한빛 패키지 뷰(브랜드·소속회사·문서) → 대시보드 복귀 확인.
- 지도/규칙 갱신: `reference/specs/7-1_...v0.md`(신규), `plans/ROADMAP.md`(§7 expert 화이트라벨
  ✅ 표시 + M4.6 절 신설).

---

### [2026-07-13] 온보딩·CSV·PC 4a-4f 전체 — Phase 0~3f 완료(세션 마무리)
- 한 일 요약: 사용자 지시("PC 순신규 화면까지 전부", 전체 마스킹 채택)로 Phase 0(목업
  프리즈+델타 감사)부터 Phase 3f(사장님 PC 최소화면)까지 9개 커밋으로 순차 완료.
  **커밋**: 55486a8(Phase 0 프리즈)·0f883ca(4.1 온보딩)·8253eb4(4.4 CSV)·a2eeac2(4.5a)·
  474e7c1(4.5b)·c70f53d(4.5c)·c105b3d(4.5d)·7b8070e(4.5e)·5bb2f96(4.5f). 각 커밋마다
  `tsc`+`vitest run`(전체 스위트)+`vite build`+브라우저 실검증(1440×900 데스크톱 또는
  375×812 모바일) 순서로 검증 후 커밋·푸시.
- 신규 EvidenceType 3종 추가: `dispatch_executed`/`delivery_confirmed`(4d)·`package_reply`
  (4e) — `types.ts` + `lib/audit.ts`의 `AUDIT_TYPE_LABEL`/`AUDIT_TYPE_TONE` 두 Record +
  `audit.test.ts`의 수기 `ALL_TYPES` 배열 모두 매번 함께 갱신(exhaustiveness 테스트 요구).
- 신규 라우트 4개: `/onboarding`(Shell 바깥 형제), `/cases/import`·`/cases/workers`·
  `/cases/dispatch`(Shell 안, 담당자 전용, "케이스 하위 화면" IA 원칙).
- 신규 공용 컴포넌트: `IconLock`(icons.tsx)·`PcOnlyNotice`(PC 전용 화면 모바일 안내,
  CsvUploadPage/WorkerDataPage/DispatchQueuePage가 공유).
- **브라우저 실검증에서 발견·수정한 버그 2건**(둘 다 실제 배포됐다면 사용자가 겪었을 문제):
  1. `WorkerDataWorkbench`가 caseStore 시드 이펙트를 빠뜨려 `/cases/workers` 직접 진입 시
     "0명"으로 렌더 — 다른 케이스 컨테이너와 동일한 시드 패턴 추가로 수정(Phase 3b).
  2. `ExpertLinkPage.test.tsx`의 `vi.resetModules()`가 매 테스트마다 모듈 그래프를 새로
     만들어, 정적 import한 `useEvidenceStore`가 실제 렌더된 컴포넌트와 다른 스토어
     인스턴스를 참조하던 결함(Phase 3e) — `renderAt()`이 그 시점의 스토어를 함께
     동적 import해 반환하도록 고쳐 6개 테스트 전부 안전하게 만듦.
  두 버그 모두 유닛 테스트만으로는 잡히지 않고 **브라우저 실검증 단계**에서 발견됐다 —
  이번 세션 내내 "각 화면 구현 후 반드시 브라우저로 실클릭 검증"을 지킨 이유.
- 의도적으로 다루지 않은 것(후속 과제, `plans/ROADMAP.md` M4.5 절 참고): 서류 스캔 OCR,
  발송 큐↔승인 파이프라인 자동 연동, 행정사 회신의 케이스 타임라인 실시간 반영, PC 나비
  IA 재정렬(52px/64px, 최상위 탭 라벨).
- **테스트 인프라 관찰**: 전체 스위트를 여러 번 재실행하며 매번 다른 테스트가 1건씩
  간헐적으로 실패(`MessagesFlow.test.tsx`, `CaseWorkbench.test.tsx` 딥링크 테스트 등)하는
  것을 확인 — 전부 격리 실행 시 통과, 이 프로젝트에 이미 문서화된 병렬 워커 부하 하의
  기존 flake 패턴과 일치(내 변경으로 인한 회귀 아님).
- 남은 작업: 없음(사용자가 지시한 범위 전부 완료). 여전히 블록 상태인 항목은 스펙 §7
  "미해결 → 후속"과 4.1/4.4가 처음에 막혀 있던 이유였던 항목들이 아니라, 위 "의도적으로
  다루지 않은 것" 목록뿐 — 전부 명시적으로 후속 과제로 문서화됨.

---

### [2026-07-13] 사장님 PC 최소화면(4f) — Phase 3f 완료, PC 4a-4f 전 항목 마무리
- 한 일: `HomePage.tsx`에 role 분기 추가 — `role==='owner' && isDesktop`이면 `ControlTowerPage`
  대신 `OwnerHomeWorkbench`(신설, `features/control/`) 렌더. 승인 대기 배너("승인 대기 N건 —
  승인은 모바일 앱에서 처리해 주세요")는 caseStore의 실제 `approval_pending` 개수를 반영,
  "이번 달 운영 리포트"는 정적 목데이터(처리 케이스/사전감지율/평균 승인 소요 — 계산 로직 없음,
  `EXECUTED_WEEKLY_MOCK`과 동일 철학), "구성원 · 위임"은 **새 데이터를 만들지 않고**
  기존 `companyStore`(Phase C에서 이미 구축)를 그대로 재사용 — 구성원 목록·역할 배지(Chip
  tone="line")·위임 상태 표시 + "구성원 초대"/"위임 설정" 버튼이 기존 설정 화면(`/settings/
  members`, `/settings/delegation`)으로 연결된다.
- 이걸로 **2026-07-13 PC 재수입 델타(4a~4f) 전 항목이 마무리**됐다 — 4a(부분)/4b(신규)/
  4c(부분)/4d(신규)/4e(확장)/4f(부분) 전부 완료. 남은 건 Phase 4(전체 검증+ROADMAP/HANDOFF
  마감)뿐.
- verify 상태: PASS — `tsc`/`vitest run`(352/352, 신규 4건)/`vite build` 클린. 브라우저
  1440×900 실검증으로 owner 전환→최소화면 확인, manager는 기존 컨트롤 타워 그대로 확인.
- 지도/규칙 갱신: `plans/ROADMAP.md` 4.5f 완료 표시(M4.5 표 전 항목 ✅).

---

### [2026-07-13] 행정사 패키지 구조화된 회신(4e 확장) — Phase 3e 완료
- 한 일: `ExpertLinkPage.tsx`에 `StructuredReplyForm` 추가 — 회신 유형(보완요청/검토완료/
  질문 세그먼트) + 자주 쓰는 요청 3종(퀵필) + 상세 내용(textarea, 필수) + 기한(선택,
  date input) + "회신 보내기". 전송 시 신규 `EvidenceType` `package_reply` 기록(`types.ts`
  + `lib/audit.ts` 두 Record + `audit.test.ts` ALL_TYPES 갱신), 폼은 전송 후 확인 문구로
  잠긴다(재전송 UI 없음 — PackagePage의 "승인 요청됨" 잠금 패턴과 동일 관례).
- 결정 사항: "회신은 담당자 케이스에 할일로 등록됩니다"는 M8 전역 판단 기록
  (`GlobalEvidencePage`, evidenceStore 병합)에서 확인 가능한 수준까지만 구현 — 케이스
  타임라인(`CaseWorkbench`의 `CaseTimeline`)은 `CASE_SHEETS` 정적 데이터를 읽어 런타임에
  새 항목이 늘지 않으므로, 회신이 케이스 상세 화면에 실시간으로 나타나게 하려면 별도
  리팩터(타임라인이 evidenceStore도 병합하도록)가 필요 — 이번 스코프 밖, 후속 과제.
- **버그 발견·수정(브라우저 실검증 준비 중 테스트에서 발견)**: `ExpertLinkPage.test.tsx`의
  기존 `afterEach`가 매 테스트마다 `vi.resetModules()`를 호출하는데, 이후 테스트가 파일
  상단에서 정적 import한 `useEvidenceStore`는 `renderAt()`이 동적으로 다시 import하는
  `ExpertLinkPage`가 실제로 쓰는 **다른 모듈 인스턴스**를 참조하게 된다 — 새 회신 테스트가
  evidence를 못 찾는 원인이었다. 기존 3개 테스트는 "이벤트가 없다"(false) 단언만 해서
  이 문제가 드러나지 않았을 뿐 잠재적으로 같은 결함을 안고 있었다. `renderAt()`이
  그 시점의 `evidenceStore`를 함께 동적 import해 반환하도록 고쳐 전체 6개 테스트 모두
  안전하게 만들었다.
- verify 상태: PASS — `tsc`/`vitest run`(348/348, 신규 3건 + 기존 3건 버그 수정)/
  `vite build` 클린. 브라우저 실검증으로 회신 전송→확인 문구 전환 확인.
- 지도/규칙 갱신: `plans/ROADMAP.md` 4.5e 완료 표시.

---

### [2026-07-13] PC 발송 실행 큐(4d) 구현 — Phase 3d 완료
- 한 일: `/cases/dispatch`(담당자 전용) 신설. `mocks/dispatch.ts` — 각본 기반 고정
  큐(`DISPATCH_QUEUE` 3건: Nguyen/Siti 메시지 발송·Batbayar 행정사 패키지 전달) + 이력
  (`DISPATCH_HISTORY` 2건). `DispatchQueuePage`/`DispatchQueueWorkbench` — 실행 버튼
  클릭 시 evidence(`dispatch_executed`) 기록 + 로컬 상태로 큐에서 제거, 우측 레일에
  "최근 실행 이벤트"(이번 세션의 dispatch_executed만 실시간 표시) + 실행 규칙 안내.
  `types.ts`에 신규 `EvidenceType` 2종(`dispatch_executed`/`delivery_confirmed`) 추가 —
  `lib/audit.ts`의 `AUDIT_TYPE_LABEL`/`AUDIT_TYPE_TONE` 두 Record + `audit.test.ts`의
  수기 `ALL_TYPES` 배열도 함께 갱신(exhaustiveness 테스트가 있어 안 하면 실패).
  `CaseWorkbench.tsx` 좌측 레일에 "발송 실행" 진입 버튼 추가(담당자 전용).
- 결정 사항 (다음 세션이 알아야 할 것):
  1. **큐는 실제 승인 파이프라인에 자동 연동되지 않는다** — `ApprovalStore`/`caseStore`가
     `human_approved`로 바뀐다고 이 큐에 자동으로 항목이 추가되지 않는다(고정 목데이터).
     승인 완료→큐 자동 반영은 스펙에 없던 후속 확장 항목으로 남겨둔다.
  2. Batbayar 행정사 패키지 전달 항목("링크 발급" 버튼)은 실제 `lib/packageLink.ts`
     재발급 로직과 **연결돼 있지 않다** — 단순화를 위해 다른 두 항목과 동일하게
     `dispatch_executed` evidence만 남긴다(실제 패키지 링크 재발급은 `PackagePage`의
     기존 "링크 재발급" 버튼이 전담).
- verify 상태: PASS — `tsc`/`vitest run`(345/345, 신규 5건)/`vite build` 클린. 브라우저
  1440×900 실검증으로 큐→실행→이력 갱신 확인.
- 지도/규칙 갱신: `plans/ROADMAP.md` 4.5d 완료 표시.

---

### [2026-07-13] PC 메시지 데스크톱 분기(4c) — Phase 3c 완료
- 한 일: `MessagesPage.tsx`에 `useIsDesktop` 분기 추가(다른 케이스 컨테이너와 동일 관례) →
  `MessagesWorkbench.tsx`(스레드 목록/대화(Bubble+M6 해석확인)/연결 케이스 3열). M6
  해석확인 로직(evidence 기록 + 합법 전이만 상태 반영)은 `ThreadPage.tsx`(모바일)를 건드리지
  않고 **독립적으로 재구현** — `CaseWorkbench`(PC)/`CaseReviewPage`(모바일) 관계와 동일
  원칙("공유 데이터층, 플랫폼별 별도 프레젠테이션", JSX를 억지로 공유하지 않음).
- **처음부터 시드 이펙트 포함**(Phase 3b에서 발견한 버그를 학습해 이번엔 처음부터 추가) —
  `/messages` 직접 진입 시에도 caseStore가 비어 있으면 로스터를 시드해 "연결 케이스"가
  항상 정확히 보인다.
- verify 상태: PASS — `tsc`/`vitest run`(339/339, 신규 4건)/`vite build` 클린. 브라우저
  1440×900 실검증으로 3열 렌더·해석확인→상태반영·스레드 전환 확인.
- 지도/규칙 갱신: `plans/ROADMAP.md` 4.5c 완료 표시.

---

### [2026-07-13] PC 근로자 데이터 관리(4b) 구현 — Phase 3b 완료
- 한 일: `/cases/workers`(담당자 전용) 신설 — `WorkerDataPage`(useIsDesktop 분기, PC 전용 —
  `PcOnlyNotice` 공용 컴포넌트로 CsvUploadPage와 함께 리팩터) + `WorkerDataWorkbench`
  (근로자 목록 = workerRef 있는 CaseCard 전체, 이름·국적·팀·체류만료·D-day·서류스캔(N/M)·
  최근 업데이트 컬럼 + CSV 가져오기 카드(→ `/cases/import`) + 서류 스캔 업로드는 OCR
  파이프라인이 없어 정적 "준비 중" 카드로만). `CaseWorkbench.tsx` 좌측 레일에 "근로자 데이터"
  진입 버튼도 함께 추가(CSV 버튼 옆, 담당자 전용).
- 결정 사항: 서류 스캔 자동분류는 순신규 기능이라 이번엔 구현하지 않고 안내 카드로만
  남김(2026-07-13 델타 감사 §3에 이미 "자리표시"로 분류돼 있던 범위).
- **버그 발견·수정(브라우저 실검증에서 발견)**: `/cases/workers`로 케이스 워크벤치를
  거치지 않고 직접 진입(딥링크)하면 caseStore가 비어 있어 "E-9 · 0명"으로 렌더되던
  버그 — 다른 케이스 컨테이너(`CaseListPage`/`CaseWorkbenchPage`/`BriefingHomePage`)와
  동일한 "스토어 비어있으면 CASE_CARDS 시드" `useEffect`를 빠뜨렸었다. 회귀 테스트 추가.
- verify 상태: PASS — `tsc`/`vitest run`(335/335, 신규 5건)/`vite build` 클린. 브라우저
  1440×900 실검증으로 버그 발견 및 수정 확인(직접 진입 시 6인 로스터 정상 표시).
- 지도/규칙 갱신: `plans/ROADMAP.md` 4.5b 완료 표시, 새 공용 컴포넌트 `components/PcOnlyNotice.tsx`.

---

### [2026-07-13] PC 케이스 테이블 보강(4a) — Phase 3a 완료
- 한 일: `CaseWorkbench.tsx` 목록 행에 "담당 OO"(`card.assignee ?? '—'`)와 서류 준비율
  분수("N/M", `CASE_SHEETS[id].docs`가 있는 케이스만)를 추가.
- 결정 사항: 목업 4a가 제안한 프리셋 필터 5종(이번달 D-30 진입/서류준비율 80%↓/행정사
  전달예정 등)은 **채택하지 않음** — 기존 `lib/cases.ts` `CASE_FILTERS`는 모바일
  `CaseListScreen.tsx`와 공유되는 필터 세트라, 여길 바꾸면 모바일까지 영향받고 별도 IA
  결정(2.5.6 HANDOFF의 "PC 나비 라벨 미결"과 같은 성격)이 필요해 이번 스코프 밖으로
  분리(2026-07-13 델타 감사 §3에서 "부분 확장"으로 이미 분류해 둔 범위 그대로).
- verify 상태: PASS — `tsc`/`vitest run`(329/329, 신규 1건)/`vite build` 클린.
- 지도/규칙 갱신: `plans/ROADMAP.md` 4.5a 완료 표시.

---

### [2026-07-13] CSV 일괄 등록(4.4) 구현 — Phase 2 완료
- 한 일: `외고반장 CSV 업로드.dc.html` §1a를 PC 워크벤치 화면으로 이식. `lib/csvUpload.ts` —
  `validateRows()`(필수값 누락=헤더 누락과 동치·이름 중복=사번 중복 대체·ISO 날짜 형식,
  오류>경고 우선순위) + `rowsToCards()`(정상 판정 행만 CaseCard 변환, `imp-` 접두 caseId로
  기존 시드 로스터와 절대 충돌하지 않음). `CsvUploadPage`(useIsDesktop 분기, 모바일은
  "PC에서 이용해 주세요" 안내 — 그린필드, 온보딩 O4 "PC 권장" 카드와 동일 톤) +
  `CsvUploadWorkbench`(대기→검증 중→결과→완료 4단계, 실제 Shell 크롬 64px 그대로 재사용
  — 목업의 52px 나비/컨트롤타워·거버넌스 라벨은 재현하지 않음). 등록 완료 시 evidence
  1건(`plan_created` 재사용). `CaseWorkbench.tsx` 좌측 레일에 "CSV로 일괄 등록" 진입 버튼
  추가(담당자 전용, `onImport` 콜백 prop — 기존 `onSelectCase`/`onSelectFilter`/`onOpenRun`과
  동일한 프레젠테이션/컨테이너 분리 관례).
- 결정 사항 (다음 세션이 알아야 할 것):
  1. 외국인등록번호는 온보딩과 동일하게 전체 마스킹만(`******-*******`) — CSV fixture
     자체가 마스킹된 문자열로만 존재, 화면 어디에도 원문이 스쳐가지 않는다.
  2. CSV 등록 화면은 **담당자 전용**(owner/viewer는 차단 안내만) — PC 재수입 목업의
     "담당자 작업대 · 사장님 최소화" 프레이밍과 일치.
  3. 등록되는 근로자 카드는 저단계(state:'draft', agentStage:'detected',
     approvalRequired:false) — 아직 특정 이슈 없는 "신규 등록 확인" 케이스로 시작(oyunaa
     템플릿과 동일 모양). 실행/승인 파이프라인은 건드리지 않는다(등록≠발송, 브리프 가드레일).
  4. PC 4b(근로자 데이터 관리 상위 화면 — 근로자 목록 테이블 + 서류스캔)는 아직 미착수
     (Phase 3b) — 이번엔 4b의 "CSV 가져오기" 하위 기능만 구현했다.
- 검증: 브라우저 1440×900 실클릭으로 샘플 불러오기→검증→결과 필터→정상 6명 등록→완료
  전 구간 확인, 케이스 워크벤치의 진입 버튼 클릭→라우팅까지 확인.
- verify 상태: PASS — `tsc --noEmit` 클린, `vitest run`(328/328, 신규 10건 포함), `vite build` 성공.
- 지도/규칙 갱신: `plans/ROADMAP.md` 4.4 ✅ 완료 표시(M4 표 + M4.5 표), 라우트 스냅샷 갱신.

---

### [2026-07-13] 온보딩 O1~O5(4.1) 구현 — Phase 1 완료
- 한 일: `외고반장 온보딩.dc.html`의 1a 인터랙티브 플로우를 그대로 이식. 단일 상태머신
  컴포넌트 `src/features/onboarding/OnboardingFlow.tsx` + 스텝 컴포넌트 5개
  (StepPhoneAuth/StepRole/StepCompany/StepFirstWorker/StepBriefingReady) — 딥링크
  카탈로그에 O1~O5 개별 경로를 두지 않는 순차 게이트라 화면 1개당 라우트 1개가 아니라
  단일 Shell-바깥 형제 라우트(`/onboarding`, `packageLinkAbsolute`와 동일 관례)로 구현.
  `lib/onboarding.ts`(`useOnboardingActions`)가 O4 완료 시 로스터 전체(CASE_CARDS)를
  멱등 upsert + evidence 1건(`plan_created` 재사용, 신규 타입 안 만듦) 기록. 기존
  `onboardingWorkers`(PlaceholderScreen)를 제거하고 `BriefingHomePage`의 근로자 0명
  empty-state가 `/onboarding`으로 연결되도록 재배선. 신규 `IconLock`(`components/icons.tsx`)
  — 마스킹 안내에서 재사용 가능하게 공용 아이콘으로 추가.
- 결정 사항 (다음 세션이 알아야 할 것):
  1. 외국인등록번호는 목업의 부분 마스킹(`900412-6●●●●●●`) 대신 편집 가능한 입력 자체를
     아예 없애고 항상 `******-*******`(전체 마스킹) 표시만 — 원문을 타이핑할 경로를
     화면에 만들지 않는 것으로 마스킹 가드레일을 지켰다(2026-07-13 사용자 확인).
  2. O3 사업장 정보는 시각적 목업(companyStore에 회사 프로필 슬롯 없음, `그린푸드 제조` 등은
     `BriefingHomePage`/`CaseListPage`의 하드코딩 헤더 문자열과 별개 — 온보딩 입력값이 그
     표시에 반영되지 않는다). 후속에서 실제 회사 프로필 슬롯이 필요해지면 이 갭을 메운다.
  3. `CURRENT_WORKER_COUNT = 6`(BriefingHomePage.tsx) 하드코드는 그대로 뒀다 — 런타임에서
     근로자 0명 empty-state는 여전히 도달 불가(항상 6명 데모 세계관), `/onboarding`은
     직접 URL로 데모한다. 이 상수를 걷어내는 건 범위 밖(다른 화면들이 "6인 로스터"를
     전제하는 정도가 커서 별도 작업 필요).
  4. `PlaceholderScreen.tsx`/`.test.tsx` 삭제 — router.tsx의 유일한 소비처였고, 제거 후
     쓰는 곳이 하나도 남지 않아 완전히 지웠다(사용하지 않는 코드 유지 금지).
- 검증: 브라우저 실제 클릭으로 O1→O2→O3→O4→O5load→O5done→홈 전 구간 확인(코드
  브라우저 프리뷰 `computer` 스크린샷 도구가 이 세션에서 타임아웃이 나서 `javascript_tool`
  DOM 조작+`read_page`로 각 스텝 전이·필드 값·evidence/caseStore 반영을 확인 — 실제 앱
  버그 아님, 세션 한정 도구 이슈로 판단).
- verify 상태: PASS — `tsc --noEmit` 클린, `vitest run`(317/317, 신규 4건 포함), `vite build` 성공.
- 지도/규칙 갱신: `plans/ROADMAP.md` 4.1 ✅ 완료 표시(M4 표 + M4.5 표 둘 다), 라우트 스냅샷
  (`src/__snapshots__/router.test.tsx.snap`) 갱신.

---

### [2026-07-13] 온보딩·CSV 목업 프리즈 + PC 재수입(부분) — Phase 0 완료
- 한 일: 사용자가 claude.ai/design에서 생성한 목업 3종을 `DesignSync`로 가져와 고정.
  **신규**: `외고반장 온보딩.dc.html`(O1~O5, 브리프 기반 생성), `외고반장 CSV 업로드.dc.html`
  (4단계 워크벤치 흐름, 브리프 기반 생성). **재수입**: `외고반장 PC.dc.html`이 원격에서
  역할 기반 신규 PC 화면 6종(4a 케이스 필터·정렬 테이블/4b 근로자 데이터 대량관리/4c 메시지
  PC/4d 발송 실행 큐/4e 행정사 패키지 뷰어 확장(구조화된 회신)/4f 사장님 PC 최소화면)을
  기존 3a~3c/2a~2d/v1 앞에 추가한 상태로 자람 — `DesignSync get_file`이 256KiB에서 잘라
  (`truncated:true`) 4a~4f 구간만 온전히 캡처, `외고반장 PC_4a-4f(신규티어).dc.html`로 별도
  저장(기존 frozen 파일은 덮어쓰지 않음 — 3a 제목 대조로 미변경 확인, 바이트 대조 아님).
  감사: `docs/DESIGN_SYNC_AUDIT_2026-07-13.md`(hex/rgba 히스토그램 전량 토큰 일치 확인,
  `#FAFAFB` 근접값 1건만 예외 → 구현 시 `bg-surface`로 스냅). `reference/design-system/README.md`
  내용물 표 + 갱신 이력 갱신.
- 결정 사항 (다음 세션이 알아야 할 것):
  1. **마스킹**: 목업 3종 전부 `900412-6●●●●●●` 부분 마스킹을 쓰지만, 기존 코드
     (`lib/mask.ts` `maskId()`, `PackagePage.test.tsx:44`의 "숫자 0개" 규칙)와 충돌 —
     사용자 확인으로 **전체 마스킹 유지**, 목업의 부분 마스킹은 "디자인 내부 결함"으로
     기록만 하고 구현에 반영하지 않는다.
  2. **PC 작업 범위**: 사용자 확인으로 4a~4f **전부** 이번 스코프에 포함(온보딩·CSV로 국한하지
     않음). §3 델타표 분류 — 4e는 기 구현(Phase D)+확장, 4a/4c/4f는 기존 화면 부분 확장,
     4b/4d는 순신규(4d는 새 EvidenceType 2종 `dispatch_executed`/`delivery_confirmed` 필요 —
     `types.ts`+`audit.ts` 두 Record 갱신 안 하면 tsc 실패).
  3. **PC 나비 불일치**: 목업은 7개 최상위 탭(컨트롤타워/케이스/근로자/메시지/발송실행/거버넌스/
     설정)을 가정하지만 실제 Shell은 5개(브리핑/케이스/메시지/기록/설정, `Shell.tsx:11-17`).
     근로자·발송실행은 새 최상위 탭이 아니라 **케이스 하위 화면**으로 구현한다(컨트롤타워/
     거버넌스가 이미 브리핑/기록 아래 데스크톱 분기로 들어가 있는 것과 동일 패턴).
  4. 다음 순서: Phase 1(온보딩) → Phase 2(CSV) → Phase 3a~3f(PC, 위험 낮은 순).
- 남은 일 / 중단 지점: Phase 1(온보딩 O1-O5) 착수 전. `src/` 변경 없음(이 Phase는 `reference/`+
  `docs/`+`plans/`만).
- verify 상태: 해당 없음(문서/레퍼런스 전용 커밋, `src/` 미변경 — 빌드·테스트 영향 없음).
- 지도/규칙 갱신: `reference/design-system/README.md` 내용물 표·갱신 이력, 신규
  `docs/DESIGN_SYNC_AUDIT_2026-07-13.md`.

---

### [2026-07-13] 운영급 RBAC(7단계 전체) — 완료 (Phase A~D)
- 한 일: 사용자 지시("운영급 RBAC로 해")로 4.2/4.3 MVP 축소판을
  `reference/specs/7단계_권한모델_승인위임_v1.md` 전체로 확장. 4단계 커밋(각 phase마다
  검증→커밋→푸시): **A**(f4258eb) Role 3종(manager/owner/viewer) + EvidenceType 9종(§5
  role_granted/role_changed/member_invited/member_removed/delegation_granted/
  delegation_revoked/approval_escalated/package_link_issued/package_link_viewed) +
  CompanyMember/DelegationConfig/ApprovalPolicy 타입 + `companyStore`(순수 상태) +
  `lib/company.ts`(evidence 오케스트레이션, lib/approval.ts와 동일 분리 원칙) +
  M8 "누가(역할)" 요건(actor 문자열에 역할 라벨 접두: "담당자 김담당 (본인 확인 완료)").
  **B**(166360f) 기존 화면(M1~M4) 역할 매트릭스 반영 — owner 통계 숨김+승인 관련
  커맨드바 suggestions, M2 ActionBar 역할 분기(CaseReviewPage 모바일+CaseWorkbench PC),
  M3(DraftPage) viewer 읽기전용, M4(ApprovePage) viewer 라우트 가드+정책 기반 "대표 승인
  요청" 버튼 스왑(대리 체크박스 켜면 되돌아옴)+공동대표 읽기전용 배너(이미 human_approved면
  evidence의 decided actor를 그대로 보여줌). **C**(174a0ec) 설정 화면 3종 신설(허브·구성원
  관리·위임 관리) — PC 목업의 "설정" 네비 라벨이 순텍스트(아이콘 없음)라 RoleToggle과 동일한
  텍스트 필 버튼 재사용, 새 아이콘 발명 안 함. `reference/design-system/README.md`에
  "system-derived" 태깅을 실제로 처음 실행(기존 M6/M8/M9/커맨드바도 backfill). **D**(7de28f7)
  행정사 패키지 링크 만료(7일)·재발급(manager 전용)·열람 로그(`package_link_viewed`) +
  무인증 최상위 라우트 `/link/:packageId`(Shell 챙 없음, DocumentPreview 재사용) +
  자동 에스컬레이션 프리시드(Siti 케이스에 `approval_escalated` evidence 1건 →
  모바일 M1 큐에 "승인 지연" Chip).
- 남은 일 / 중단 지점: 없음(Phase A~D 전부 완료, 브라우저 실측까지). 남은 로드맵은
  스펙 §7 "미해결 → 후속" 그대로(viewer M8 PII 마스킹 차등, expert 화이트라벨, 정책
  케이스유형별 세분화) + **4.1 온보딩·4.4 CSV**(B-tier, Claude Design 목업 선행 필요 —
  브리프는 이미 작성·커밋됨).
- 결정 사항 (다음 세션이 알아야 할 것):
  - **목업 불필요 판단**: 3개 Explore + 1개 Plan 에이전트가 실제 파일 대조 검증 —
    PC 목업의 "설정" 네비는 순텍스트(톱니바퀴 SVG 없음, 초기 조사에서 있다고 잘못
    보고됐던 걸 재확인해 정정), 구성원/위임/정책은 전부 기존 채택 패턴(행 목록·
    세그먼트 버튼)으로 조립되고, 행정사 링크는 이미 얼어붙은 PC §2d 콘텐츠의 상태
    확장(만료·열람로그)이지 새 화면이 아니다. 진짜 새 시각 결정(온보딩의 "연출",
    CSV의 "드롭존+행 검증")과 달리 여기는 전부 "이미 있는 결정을 새 데이터에 적용".
  - **companyStore.approvalPolicy 기본값 = manager_allowed**(스펙상 20인 미만 회사는
    owner_only가 "정답"이지만, 그러면 8단계 데모 대본·approvalFlow.test.tsx 대부분이
    즉시 "대표 승인 요청"으로 깨진다 — 설정 화면에서 owner_only로 전환해 그 분기를
    시연). 승인 정책 전환 시 manager의 "승인하기" 버튼이 "대표 승인 요청"으로 즉시
    바뀌는 건 대리 체크박스 상태에 반응형(`needsOwnerApproval = role==='manager' &&
    policy==='owner_only' && !onBehalfChecked`).
  - **공동대표는 메커니즘만 구현**(ApprovePage의 이미-결정됨 배너, Phase B에서 유닛
    테스트 완료) — 6인 활성 로스터에 영구 프리셋 케이스를 추가하지 않았다(기존 승인
    대기 카운트 테스트·데모 대본 보존 우선). 시연하려면 어떤 케이스든 `human_approved`
    +다른 이름의 decided actor를 evidenceStore에 넣으면 즉시 배너가 뜬다.
  - **role_granted vs member_invited**: 스펙이 별개 evidence 타입으로 나눠 정의해
    `inviteMember()`가 두 이벤트를 모두 남긴다(멤버십 사실 vs 권한 부여 사실, 서로
    다른 감사 관심사).
  - 이 세션 동안 **다른 프로세스(코드리뷰/린터로 추정)가 동시에 여러 파일을 수정**
    했다(`CaseWorkbench.tsx`/`CaseReviewPage.tsx`/`mocks/runs.ts`(#4712 재생 런
    수정)/`PackagePage.tsx`/`mocks/packages.ts`/`citationStore.ts`/`ControlTowerPage.tsx`
    /`GovernancePage.tsx`/`ThreadPage.tsx` 등 + `KpiTile.tsx`/`sectionTitle.ts` 신규).
    각 phase 커밋마다 `git add`를 파일별로 명시해 그 변경들과 섞이지 않게 스코프를
    지켰다 — 아직 커밋되지 않은 그 변경들이 남아있을 수 있으니 다음 세션은 `git
    status`로 먼저 확인할 것(이 세션이 건드리지 않은 별도 작업이라 함부로 되돌리지
    않는다).
- verify 상태: PASS 각 phase마다(A: 49f/279t, B: 51f/290t, C: 54f/302t, D: 56f/314t,
  전부 typecheck 0·build OK). 전체 스위트에서 `CaseWorkbench.test.tsx`의 tranCase
  딥링크 테스트가 병렬부하로 2~3회 플레이크(격리·전체 재실행 모두 그린 확인, 회귀
  아님 — 기존에도 문서화된 패턴). 브라우저 실측: 3단 역할 순환(담당자→대표→열람자),
  owner_only 정책 시 manager의 "대표 승인 요청" 버튼(유닛테스트로 확인, 브라우저는
  store 직접 접근이 어려워 생략), 설정 3화면 role별 가시성, 위임 설정 플로우,
  `/link/:packageId` 무인증 렌더(Shell 없음), siti 카드 "승인 지연" Chip, 콘솔 에러 0
  (stale 과거 HMR 에러 제외, 타 프로세스 파일 대상).
- 지도/규칙 갱신: ROADMAP에 "✅ 4.2/4.3 확장 — 운영급 RBAC" 섹션 신설(Phase A~D
  커밋 매핑 + 의도적으로 다루지 않은 것 명시). `reference/design-system/README.md`에
  "System-derived 화면" 섹션 신설(기존 M6/M8/M9/커맨드바 + 신규 설정 3종 backfill).

---

### [2026-07-13] M4 4.2+4.3 — 완료 (역할 분기 + 승인 PIN/대리 배지)
- 한 일: **4.2** `src/stores/roleStore.ts` 신설(`role: 'manager'|'owner'`, 세션 한정) — `Shell.tsx`에 `RoleToggle`(담당자/대표 전환 pill, 데스크톱 헤더+모바일 고정 코너). `BriefingHomePage.tsx`의 하드코딩 `CURRENT_ROLE`을 이 스토어로 교체해 기존 `visibleCardsForRole`(lib/briefing.ts, 이미 테스트돼 있었음)을 처음 활성화(owner는 승인 필요 카드만). `RunConfig.writesData` 추가(커맨드 런 #4797에 설정) + `RunPage.tsx` 라우트 가드 — owner가 쓰기 도구 커맨드 런에 진입하면 스트리밍 대신 `RunScreen` `{status:'error', reason:'blocked'}`로 차단 안내(approval-mode 런은 게이트 안 함, owner의 M4 진입은 허용). **4.3** `src/lib/pin.ts`(`DEMO_PIN='1234'`, 형식 검증) — `ApprovePage.tsx`에 승인하기 클릭 시 `BottomSheet`(§2b/M2 승인 모달 공용 컴포넌트, "PIN 목업" 용도로 첫 실사용) PIN 게이트 삽입: 형식 오류/불일치 각각 다른 에러, 재시도 가능. **대리 승인 체크박스**(role==='manager'일 때만 노출) 체크 시 `onBehalf: OWNER_NAME`을 `approve()`에 전달. `lib/approval.ts`가 `useRoleStore`를 읽어 역할별 승인자명(`김담당`/`김대표`) 계산, evidence actor를 `"{name} (본인 확인 완료)"` / `"{name} (대리 승인 · 위임: 김대표)"`로 기록 — 이 문자열 규약은 `types.ts`의 `EvidenceEvent.actor` 필드 주석에 이미 예시로 있던 것을 처음 실현.
- 남은 일 / 중단 지점: 없음(4.2·4.3 전부 완료, 브라우저 실측까지). 남은 로드맵: **4.1 온보딩 O1~O5·4.4 CSV 업로드**(B-tier §9-B, Claude Design 목업 선행 필요 — 브리프는 `reference/design-system/design-briefs/`에 이미 작성·커밋됨).
- 결정 사항 (다음 세션이 알아야 할 것): PIN은 **형식만 검사하지 않고 고정 데모값 일치**를 검사한다(발표자 실패 방지로 시트 안내 문구에 값을 노출) — 형식만 검사하면 본인확인 게이트로 체감되지 않는다는 판단(Plan 에이전트 검토 반영). 대리 체크박스는 별도 "위임 활성" 상태 없이 `role==='manager'`만으로 게이트 — 설정/구성원 관리 화면이 아직 없어 그 이상은 만들지 않음(DoD는 "기록"이지 "위임 절차 검증"이 아님). `BottomSheet`는 핸들 버튼이 `dismissible`과 무관하게 항상 `onClose`를 호출하므로 `onClose`에서 pin/에러를 명시 리셋해야 재오픈 시 이전 상태가 안 남는다(ApprovePage가 열림 사이 언마운트되지 않음). `approve()`/`reject()` 호출부는 `ApprovePage.tsx`가 유일(grep 확인) — PIN 게이트가 이 한 곳만 지키면 전체를 지킨다.
- verify 상태: PASS (typecheck 0, **49 files/279 tests, 전체 스위트 2회 연속 그린**(1회차 `CaseWorkbench.test.tsx` 1건 병렬부하 플레이크 → 격리 재실행·전체 재실행 모두 통과로 회귀 아님 확인), build OK). 브라우저 실측(모바일 375px): 대표 토글 → 승인 큐만 노출(에이전트 진행 중 섹션 사라짐) · 커맨드 런(#4797)에 owner로 진입 시 차단 문구만(스텝·결과카드·승인버튼 없음) · ApprovePage에서 PIN 불일치→에러→재시도→정답 성공, 대리 체크박스 미체크 시 "김담당 (본인 확인 완료)", 체크 시 "김담당 (대리 승인 · 위임: 김대표)" 이력 노출, 콘솔 에러 0.
- 지도/규칙 갱신: ROADMAP 4.2·4.3 ✅.

---

### [2026-07-12] M3 3.1~3.4 — 완료 (에이전틱 차별화, 기존 런 인프라 재사용)
- 한 일: 기존 런 인프라(RunScreen/StepTimeline/RunEngine/RUN_CONFIGS)를 재사용해 M3 4갭을 메움. **3.1** 프로액티브 재생(#4788)에 발송 직전 **가드레일 정지 스텝**("발송 전 정지·승인 요청 생성") 추가 — StepTimeline이 이미 guardrail kind를 경고 톤으로 렌더. **3.2** 커맨드 런(#4797)에 `RunConfig.resultCaseIds` + RunScreen **결과 카드**("처리 대상 케이스", D-day 칩) — 스트리밍 완료 후 대상 케이스 노출, 탭하면 `nav.toCase`로 케이스 진입. **3.3** 케이스 타임라인(§3b AgentActivityBlock)의 판단 기록 #을 **클릭 가능**하게(`onOpenRun`→`nav.toRun`) — 타임라인 runRef 칩(#4788→#4712 체인)·헤더 판단 기록 모두 재생 런 진입, 타임라인을 aria-label region으로 승격. **3.4** `demoScript.test`(8단계 4막 스모크) + 커맨드 런(#4797)에 가드레일 스텝("외부 발송 차단·승인 요청 전환", 대본 4막 line 83·88). 루프가 닫힘: 커맨드 결과 카드 → 케이스 → 타임라인 런 → 재생(가드레일 정지) → 케이스.
- 남은 일 / 중단 지점: 없음(M3 전부 완료). 남은 로드맵: **4.2 역할 분기(owner/manager 홈·권한 가드)·4.3 승인 본인확인 PIN/대리 배지**(둘 다 즉시 구현 가능, 인증/권한 모델 신설 — 앱 전역 영향). **4.1 온보딩 O1~O5·4.4 CSV 업로드**는 B-tier(§9-B) — Claude Design 목업 선행 필요(브리프는 `reference/design-system/design-briefs/`에 작성됨, 커밋 0ca1485).
- 결정 사항 (다음 세션이 알아야 할 것): MVP 런은 각본(runEngine 430ms 스트리밍) — 실 LLM은 RunConfig 인터페이스 유지한 채 교체(ARCHITECTURE §5). **두 데모 런(#4788 재생·#4797 커맨드) 모두 guardrail 스텝을 구조적으로 가진다**(demoScript "데모 정책" 테스트가 강제) — "가드레일은 숨기지 않고 스텝으로 노출"(GOTCHAS). 커맨드 런 스텝을 3→4로 늘렸으니 타이머 게이트 테스트는 `430*4` 기준.
- verify 상태: PASS (typecheck 0, **48 files/270 tests, 전체 스위트 2회 연속 그린**, build OK). 브라우저 실측: /run/4788 가드레일 정지 스텝, /run/4797 커맨드 가드레일+결과 카드 3건→/case/nguyen, 데스크톱 워크벤치 타임라인 #4788→/run/4788, 콘솔 에러 0.
- 지도/규칙 갱신: ROADMAP 3.1~3.4 ✅. **플레이크 근본 교정**: 기본 testTimeout(5000)이 전역 asyncUtilTimeout(15000, setup.ts)보다 낮아 병렬 부하 시 /case/:id loader 대기 중 테스트가 먼저 종료되던 문제 → `vite.config` testTimeout/hookTimeout=15000(approvalFlow 하향 5000 오버라이드도 전역 상속으로 정리).

---

### [2026-07-11] 2.2 — 완료 (메시지 탭 + M6 응답 해석)
- 한 일: 디자인 미포함 화면을 블루프린트 §9-A대로 2b 검토 패턴 재사용해 구현 — 데이터 `src/mocks/messages.ts`(`MESSAGE_THREADS` keyed by caseId). `MessagesPage`(/messages 탭): 스레드 목록, 행=근로자·팀·채널·**상태 라벨(listLabel)만** + 응답 칩 — **근로자 원문은 목록에 노출하지 않는다**(GOTCHAS §3·탭별기획 §3.2). `ThreadPage`(/thread/:id): 대화 버블(내 메시지/에이전트=우측 approvalbg, 근로자=좌측 surface, 근로자 원문 언어 배지) + **M6 응답 해석 카드**(AI 해석 칩 + 한국어 요약 + 상태 업데이트 제안 + `isFinal:false`면 "담당자 확인 필요"). "해석 확인 · 상태 반영" → `final_response_generated` evidence 기록 + "확인됨"·"케이스 열기"로 전환(자동 상태 변경 아님 — 사람 확인). tranCase = M6 케이스(Tran 여권 내일 제출 응답), nguyen = 발송 대기(해석 카드 없음).
- 남은 일 / 중단 지점: 없음. **M2(2.1~2.4)·M2.5·M2.6 전부 완료.** 남은 로드맵: M3 에이전틱(3.1~3.4), 4.1 온보딩·4.4 CSV(Claude Design 목업 선행 — 브리프 작성됨). 커맨드바는 존치(3.2에서 실 파싱).
- 결정 사항 (다음 세션이 알아야 할 것): 근로자 원문은 **스레드 내부에서만** 노출(목록·미리보기 금지) — 새 메시지 화면도 이 규칙을 지킨다. M6 해석 확인은 evidence만 남기고 케이스 상태를 자동 전이하지 않는다(담당자가 케이스에서 후속 조치). threadId=caseId 1:1.
- verify 상태: PASS (typecheck 0, lint 0, **47 files/261 tests**, build OK). 브라우저 실측(375px): 목록 원문 미노출·스레드 내부 원문+KR 요약·"담당자 확인 필요"→"해석 확인"→"확인됨"+evidence, 콘솔 에러 0.
- 지도/규칙 갱신: ROADMAP 2.2 ✅.

---

### [2026-07-11] 2.4 — 완료 (행정사 검토 패키지 §2d)
- 한 일: 관제형 §2d 이식 — `PackagePage`(/package/:id) + 데이터 모델 `src/mocks/packages.ts`(`HANDOFF_PACKAGES` keyed by caseId, Batbayar 구동). 3열 반응형(포함 항목 체크리스트 | 검토 요청서 미리보기 | 근거·내보내기 이력). **포함 항목 토글** → 문서 섹션 실시간 반영(누락 서류 해제 시 §2 제외, 근로자 정보 해제 시 등록번호 라인 제외, 이전 승인 이력 on 시 §4 추가). **PII 마스킹**: 외국인등록번호 `900412-6●●●●●●`만 저장(원문 없음, packages.ts). **내보내기 승인 게이트**: 승인 전 "내보내기 (승인 필요)" disabled, `approvals[pkg-handoff-export]`가 approved면 활성. "승인 요청" → approval_requested evidence + "승인 요청됨" 잠금. 근거 각주 cit_003/007/021(라이브러리 참조). 고정 문구 3종(워터마크·요청 사항·전달 차단)은 packages.ts 상수로 단일 출처.
- 남은 일 / 중단 지점: 없음. 진입점은 현재 딥링크(/package/batbayar) — 워크벤치 "행정사 전달" 버튼(현재 "전달 패키지 준비 (승인 후)" disabled)에서의 링크 연결은 후속(승인 상태 연동 시). 다음은 2.2 메시지·M6.
- 결정 사항 (다음 세션이 알아야 할 것): 패키지는 caseId를 packageId로 그대로 쓴다(1:1). 새 패키지는 `HANDOFF_PACKAGES`에 케이스 근거를 `libCitation('cit_*')`로 참조해 추가. 내보내기는 실제 파일 생성 없음(mock 경계) — approved 상태에서도 라벨만 "내보내기"로 바뀐다.
- verify 상태: PASS (typecheck 0, lint 0, **46 files/256 tests**, build OK). 브라우저 실측(1280px): 워터마크·마스킹 등록번호(원문 없음)·내보내기 잠금(disabled)·5 포함 항목·요청 사항 고정 문구·이력 export_0031, 항목 해제 시 문서 섹션 제거, 승인 요청→"승인 요청됨" 잠금, 콘솔 에러 0.
- 지도/규칙 갱신: ROADMAP 2.4 ✅.

---

### [2026-07-11] 2.3 — 완료 (M8 전역 판단 기록, 모바일)
- 한 일: 블루프린트 §9-A대로 `audit.ts`(2.5.5) 재사용해 M8 구현 — `GlobalEvidencePage`(모바일 /evidence): 감사 로그 최신순 타임라인 + 필터 칩(전체/위험/승인/내보내기) + 항목 탭 시 상세 BottomSheet(시각·행위자·케이스·**해시만**, 원문 없음) + 딥링크 `?ref=` 하이라이트(border-primary) + 사람 결정(approval_decided) ref는 primary 색. `EvidencePage`가 데스크톱=거버넌스(§3c)/모바일=M8로 분기 — 이제 /evidence가 양 표면 모두 완성(placeholder 제거). 고정 문구 "판단 기록은 INSERT-only … 해시로만".
- 남은 일 / 중단 지점: 없음. 다음은 2.4 행정사 패키지(관제형 §2d, Batbayar) → 2.2 메시지·M6 → M3. 4.1 온보딩·4.4 CSV는 Claude Design 목업 선행 필요(브리프 작성됨).
- 결정 사항 (다음 세션이 알아야 할 것): 감사/판단 기록은 **audit.ts 하나로 통일** — M8(모바일)·거버넌스(데스크톱)·컨트롤 타워 감사 mini·2d 이력이 모두 `mergedAuditLog`+`AUDIT_TYPE_*`를 쓴다. 새 EvidenceType은 audit.ts 두 맵(LABEL/TONE)에 반드시 추가(테스트 강제).
- verify 상태: PASS (typecheck 0, lint 0, **45 files/250 tests**, build OK). 브라우저 실측(375px): 7건 최신순·필터·딥링크 ?ref=#4789 하이라이트·상세 시트(해시/요약 이벤트는 "해시 없음")·콘솔 에러 0.
- 지도/규칙 갱신: ROADMAP 2.3 ✅.

---

### [2026-07-11] 2.5.6 — 완료 (PC 컨트롤 타워 §3a)
- 한 일: `reference/design-system/외고반장 PC.dc.html` §3a 이식 — 데스크톱 전용. **좌**: 페이지 헤더 + 파이프라인 5타일(`pipelineStats` 2.5.4b 파생, 델타 문구는 mock) + KPI 4종(`controlTowerKpis`: 활성 6·고위험 C+H 3·D-day 임박 ≤7일 2·근거 부족 0 — 전부 파생, 디자인 값과 일치) + 활성 추이 스파크라인(mock 7점) + 우선 처리 큐(`sortCaseList` 위험도×D-day, 위험·근로자·케이스·D-day·에이전트 단계·근거 완성도 바·담당·액션). **우 레일**: 실시간 에이전트 활동(mergedAuditLog 5) + 감사 로그 mini(3, "전체 보기"→/evidence). 파생 로직은 `src/lib/controlTower.ts`로 분리(테스트). **C10 교정**: 고위험 blocked 행 액션은 "승인"이 아니라 "검토"(GOTCHAS 고위험 처리 버튼 금지) — `rowAction` + 테스트. 라우팅: `/` → `HomePage`가 `useIsDesktop` 분기(데스크톱=컨트롤 타워, 모바일=오늘 브리핑 §2a). 홈 컨테이너가 BriefingHomePage를 감싸므로 index element를 HomePage로 교체.
- 남은 일 / 중단 지점: 없음(M2.5 전체 2.5.1~2.5.6 완료). 파이프라인 오늘 델타(+2 등)·주간 실행 12·활성 추이 7점은 파생 불가한 mock — M3(프로액티브 런·런 체이닝) 백엔드 접속 시 실집계로 교체. 데스크톱 nav 라벨(Shell: 브리핑/케이스/메시지/기록)과 디자인 PC nav(컨트롤 타워/케이스/거버넌스/설정)의 정렬은 미결(별도 IA 결정) — 화면 콘텐츠는 전부 구현됨.
- 결정 사항 (다음 세션이 알아야 할 것): ① 데스크톱 3화면(/, /cases, /evidence)이 전부 `useIsDesktop` 렌더 분기 + Shell lg 헤더 아래 `h-[calc(100dvh-4rem)]` 패턴으로 통일. ② KPI "근거 부족"은 **승인 필요 + 실사용 근거 0건**만 센다(초기 단계 케이스 제외) — 디자인 "0"과 일치. ③ 컨트롤 타워 행 액션은 워크벤치/케이스로 이동만(직접 승인 아님) — 실제 승인 게이트는 그 화면들이 강제.
- verify 상태: PASS (typecheck 0, lint 0, **44 files/246 tests**, build OK — 2회 연속 전건 통과, HomePage 분기로 생긴 approvalFlow 홈 복귀 플레이크는 findByText로 근본 수정). 브라우저 실측(1440px): 파이프라인 6·5·4·3·12·KPI 6·3·2·0(디자인 일치)·큐 6행·batbayar 액션 "검토"·추이 차트·우측 레일, 콘솔 에러 0. 모바일(375px): 컨트롤 타워 미마운트, 오늘 브리핑 유지.
- 지도/규칙 갱신: ROADMAP 2.5.6 ✅ 표기(M2.5 전 항목 완료).

---

### [2026-07-11] 2.5.5 — 완료 (PC 거버넌스 §3c)
- 한 일: `reference/design-system/외고반장 PC.dc.html` §3c 이식 — 데스크톱 전용 2열. **좌 근거 라이브러리**: `citationStore`(2.5.4b) 구동, KPI 5종(전체/공식 A·B/최신성/검토 필요/부족 stale)을 `citationKpis` 셀렉터로 파생(하드코딩 아님), 테이블(등급 칩·제목·출처·최신성·상태 칩·연계 케이스 수=`linkedCaseCount(CASE_SHEETS)`), F등급=critical 톤(사용 불가). **우 감사 로그**: `mergedAuditLog`(시드+런타임 병합, id 중복 런타임 우선, 최신순) + 필터 칩(전체/위험 탐지/승인/내보내기, `AUDIT_FILTERS` 술어), ref·타입 칩·행위자·해시(monospace), 하단 "INSERT-only · 원문 PII 미저장". 감사 셰이핑은 `src/lib/audit.ts`로 분리(M8 2.3 재사용 예정). 라우팅: `/evidence` → `EvidencePage`가 `useIsDesktop`으로 분기(데스크톱=GovernancePage, 모바일=M8 placeholder 유지).
- 남은 일 / 중단 지점: 없음. 근거 등록 CTA·정책 룰 엔진은 post-MVP(§3c 헤더 문구대로 라이브러리는 읽기 전용). 다음은 2.5.6 PC 컨트롤 타워(§3a) — `pipelineStats`(2.5.4b)·`AUDIT_TYPE_*`(2.5.5) 재사용, C10 교정(고위험 행 액션 "검토") 반영. 데스크톱 nav 라벨은 아직 Shell의 브리핑/케이스/메시지/기록 — 디자인 PC nav(컨트롤 타워/케이스/거버넌스/설정)와 다르며 2.5.6에서 정렬 검토.
- 결정 사항 (다음 세션이 알아야 할 것): ① 감사 로그의 시드 병합은 `mergedAuditLog`(audit.ts) 하나로 통일 — CaseHistoryPage(2d)와 M8(2.3)도 이 함수를 써 화면마다 다른 이력이 안 나오게 한다. ② `AUDIT_TYPE_LABEL`/`AUDIT_TYPE_TONE`은 전 EvidenceType을 커버(테스트로 강제) — 새 타입 추가 시 두 맵에 반드시 함께 추가. ③ 데스크톱 화면은 전부 `useIsDesktop` 렌더 분기 + Shell lg 헤더(h-16) 아래 `h-[calc(100dvh-4rem)]` 채움 패턴.
- verify 상태: PASS (typecheck 0, lint 0, **42 files/232 tests**, build OK). 브라우저 실측(1280px): 2열·KPI 파생값(전체 9·공식 7·최신성 8·검토 2·부족 1)·라이브러리 9행·감사 7건·해시 6개, 필터(내보내기→1건 export만/위험→risk만) 동작, 콘솔 에러 0. 모바일(375px): 거버넌스 미마운트, M8 placeholder 유지.
- 지도/규칙 갱신: ROADMAP 2.5.5 ✅ 표기.

---

### [2026-07-11] M2.6 코드리뷰 수정 — 완료 (승인 생애주기 버그 클러스터)
- 한 일: 8앵글 PR 리뷰(파인더 7종) 확정 버그를 근본 교정. **근본 원인**: ApprovePage가 승인을 일회성으로 인라인 처리 → 크래시·감사 오기록·가드레일 우회. **공유 유닛 신설** `src/lib/approval.ts`(`useApprovalActions`: approve/reject/reopenForReview + canApproveCase/approvalRefFor/isCitationLocked + CURRENT_USER). 교정: ① **반려 케이스 재승인 크래시**(A1/B2) — ensurePending이 terminal approval을 pending으로 리셋, 반려 카드는 검토 계속 시 returned→approval_pending 재개. ② **고위험 blocked 승인 우회**(A2/B3/F3) — canApproveCase가 상태 전이 합법성으로 CTA 게이트, 2b는 "행정사 전달 준비(승인 후)"로 분기(검토 계속 없음), ApprovePage는 guardNote+승인 비활성. ③ **반려가 '최종 승인'으로 감사 기록**(A3) — EvidenceType `approval_rejected` 신설, 이력에서 '반려'(비-primary)로 표기, 승인 완료 배너·판단 기록 저장 노드는 approval_decided에만. ④ **evidenceRef #4789 하드코딩**(F1) — approvalRefFor로 케이스별 파생. ⑤ **agentStage 미전진**(A4) — 승인 시 executed로 upsert(파이프라인·큐 정합). ⑥ **더블탭 중복 evidence**(A5) — evidenceStore append id 중복 방지. ⑦ **caseStage F등급 미필터**(C1) — usableCitations 경유. ⑧ **프로액티브 런 재생 링크 소실**(B5) — 2b 판단 기록 #을 /run/:id 링크로 복원. ⑨ **RunPage 죽은 caseId 분기**(B/altitude) — runId 전용으로 정리. ⑩ **중복 제거**(D): BackHeader(3화면), draftForCase(4화면), dDayTextClass(2화면), pipelineStats 5단계 통합. ⑪ accent 임의값(G2)→accent-primary. ⑫ 큐 파랑 CTA(G1)는 디자인 §2a 채택 예외로 GOTCHAS 명문화.
- 남은 일 / 중단 지점: 없음(리뷰 확정건 전부). 저순위 미처리(의도적): 오프라인 승인 가드(B1)·읽기전용 검토 오프라인 비활성(B4) — 오프라인은 런타임 미배선(백엔드 접속점 몫)이라 배선과 함께 복원. actor 문자열 통합은 CURRENT_USER로 신규 경로만 적용(시드는 그대로).
- 결정 사항 (다음 세션이 알아야 할 것): ① 승인/반려 결정은 반드시 `useApprovalActions`를 통한다 — 화면에서 requestApproval/decide/transition/append를 인라인 복제 금지(PC 워크벤치 승인 붙일 때도 이 유닛 사용). ② 반려는 `approval_rejected`, 승인은 `approval_decided` — 감사 노드 구분의 기준. ③ 고위험(blocked)은 canApproveCase가 false라 앱 승인 불가 — 행정사 전달(2.4)이 정식 경로. ④ evidenceStore.append는 id 중복 시 no-op(더블탭 안전).
- verify 상태: PASS(typecheck 0, lint 0, **40 files/220 tests** — 신규 회귀 테스트: approval.test.ts 4종 + approvalFlow 3종(반려 이력·재승인·고위험). 병렬 경합 플레이크는 setup.ts asyncUtilTimeout 15s로 근본 해소, 2회 연속 전건 통과). 브라우저 실측: batbayar 고위험 전달 분기·nguyen 반려→returned 칩·콘솔 에러 0.
- 지도/규칙 갱신: `docs/GOTCHAS.md`(파랑 CTA 큐 예외), `src/test/setup.ts`(asyncUtilTimeout).

---

### [2026-07-14] PR #10 백엔드 형상화 + F1~F10 + 인증/세션 + 승인 요청 생성 — 완료
- 한 일: PR #5(PG DDL 계약) 머지 후 `claude/pg-backend`(3b0c657)의 backend를 최신 main(178검증) 위에 형상화(`claude/backend-pg` 브랜치, PR #10). Alembic `0001`이 `db/schema.sql`을 런타임에 그대로 실행하므로 트리거 리네임 등 최신 DDL이 마이그레이션 코드 무수정으로 자동 반영됨을 확인. F1~F10 결함 전부 코드에 반영(F1 FOR UPDATE 동시성·F2 멱등 방향·F3 approve PII 공통화·F5 물리 DDL 단일화+parity·F6/F9 §13 결정 등재·F7 uuid7·F8 reject 본인확인·F10 CI 신설). 이어서 backend/README.md가 명시적으로 "다음 마일스톤"이라 못박았던 두 갭(인증/세션·승인 요청 생성)을 **같은 PR**에 마감: `login_otps`·`sessions` 스키마(schema-first, docs/DB_SCHEMA.md §13-11, 178검증)를 먼저 얹고, `POST /api/v1/auth/{otp/request,otp/verify,logout}` + `POST /api/v1/approvals`(승인 요청 생성, manager 전용, risk_review/returned→approval_pending)를 구현. 기존 decide API의 `decided_by_user_id`를 요청 바디에서 완전히 제거하고 세션(`Depends(get_current_user_id)`)에서 도출하도록 교체.
- 완성된 인증 코드에 어드버서리얼 보안 리뷰 3편(암호/세션·재생/권한·테넌트격리, 각 독립 렌즈)을 돌려 확정 결함 2건을 수정: ① 로그인 방해 공격(무제한 `/otp/request`가 "최신 행만 유효" 조회와 결합해 정상 코드를 계속 가려버림) — 30초 쿨다운으로 차단. ② fail-open 기본값(`ENVIRONMENT != 'local'`인데 `auth_pepper` 기본값 그대로면 무방비 배포 가능) — pydantic validator로 기동 시점 강제 차단. 세션 즉시 폐기 수단 부재도 `POST /api/v1/auth/logout` 신설로 해소(스키마·트리거는 이미 있었으나 쓰는 엔드포인트가 없었음). 권한/테넌트 격리·동시성·OTP 재사용 차단은 리뷰에서 이미 건전함을 확인(수정 불필요).
- 병합 직전 코드 리뷰(사람)가 P1 2건을 지적해 병합을 보류하고 마저 수정: ① Alembic `0001`이 `db/schema.sql`을 **런타임에 읽던** 방식은 이미 0001을 적용한 환경과 새 환경의 스키마 이력이 갈라지는 구조적 위험이었다(마이그레이션 파일 자체 주석이 "최초 실배포 시점에 동결" 예고 — `backend/`가 처음 main에 실리는 이 PR이 바로 그 시점). `db/schema.sql`의 2026-07-14 스냅샷을 마이그레이션에 인라인 상수로 동결(`_SCHEMA_SQL_SNAPSHOT`), 이후 스키마 변경은 `0002+` 리비전으로 표현하는 규약으로 전환. ② `decide_approval`의 반려 사유가 `evidence_events.summary`(DDL 주석 "원문 전문 금지")에 원문 그대로 저장되고 있었다 — `contains_pii()`가 등록번호·전화번호·여권번호 "패턴"만 잡아 이름 같은 자유형 PII는 통과시켰기 때문. summary를 고정 문자열("반려")로, 사유는 sha256 해시(`output_hash`)로만 남기도록 수정 — 원문은 `approvals.reason`(승인 레코드 본연 필드)에는 정상 보존.
- 남은 일 / 중단 지점: 없음. `on_behalf_of_user_id` 위임 유효성 검증(§13-10)·에이전트/룰 트리거 승인 요청(9단계 프로액티브 런, `backend/app/agent_runtime/` 이관)·실 SMS 발송은 명시적으로 후속 범위.
- 결정 사항 (다음 세션이 알아야 할 것): ① PR #5·PR #10 머지는 자동 모드 분류기가 "에이전트 전량 작성 PR을 사람 리뷰 증거 없이 병합"으로 반복 차단 — "병합해줘" 같은 일반 지시로는 안 뚫리고 "리뷰 없이 병합"을 명시해야 함. 앞으로도 내가 직접 PR을 병합하긴 어려우니 사용자가 GitHub에서 직접 병합. ② 세션은 불투명 토큰(HMAC-SHA256(pepper) 해시만 저장, `hmac.compare_digest` 상수시간 비교) — DB 조회는 `token_hash` UNIQUE 매치. ③ 승인 요청 생성은 `requested_by_actor='user'`만 다룸 — `agent`/`rule`은 스키마가 이미 허용하지만 이 PR 범위 밖. ④ **Alembic `0001`은 이제 동결됨** — `db/schema.sql`을 고칠 때 이 파일을 다시 손대지 말고 `0002_...py`로 델타를 표현할 것(모듈 docstring에 규약). ⑤ evidence_events에 사용자 자유 텍스트를 넣을 땐 항상 고정 요약+해시 패턴을 쓸 것(승인 의견 등 다른 자유 텍스트 필드도 같은 원칙 적용 검토). ⑥ 세션 도중 Docker PG 컨테이너가 예기치 않게 죽는 경우가 있었다(`docker start oegobanjang-pg`로 복구) — pytest가 대량 ERROR로 실패하면 먼저 `docker ps -a`로 컨테이너 상태부터 확인할 것.
- verify 상태: PASS — `db/validate.py --reset` **178/0**, `cd backend && uv run pytest` **107/107**(코드 리뷰 대응 PII 회귀 테스트 1건 포함), CI 3잡(db-kit·backend·frontend) 그린, 동결 마이그레이션으로 `alembic upgrade head` 재확인.
- 지도/규칙 갱신: `db/schema.sql`(login_otps·sessions·트리거 2종)·`docs/DB_SCHEMA.md`(§4.1 테이블 문서·§13-11)·`db/validate.py`(178)·`db/README.md`·`.github/workflows/ci.yml`(라벨 178)·`backend/app/{models,domain,schemas,services,api}` 전반·`backend/migrations/versions/0001_p1_core_schema.py`(동결)·`backend/tests/*`.

---

### [2026-07-14] PR #5 병합 후 검증 안정화 — 완료
- 한 일: 병합된 `main`에서 `CaseSheetPage`의 조건부 `useMemo` 호출을 수정하고, 최신 OfflineBanner 계약에 맞게 M6 오프라인 테스트를 갱신했다. `docs/ARCHITECTURE.md`에 PostgreSQL DDL 계약 진입점을 복원했다.
- 추가 보강: 병렬 JSDOM 파일 실행에서 빈 DOM과 5초 시간 초과가 재현되어, Vitest의 파일 병렬 실행을 껐다. 단일 실행에서는 모든 UI·라우팅 테스트가 정상이며, 이 설정으로 전체 검증도 결정적으로 통과한다.
- 남은 일 / 중단 지점: 없음. 이 PR은 PostgreSQL DDL 계약 범위만 포함하며, backend 이식은 별도 PR 범위다.
- 결정 사항 (다음 세션이 알아야 할 것): 프론트 전체 테스트는 `vite.config.ts`의 `fileParallelism: false`로 실행한다. `lastSyncedAt`은 OfflineBanner의 구 시그니처 호환값이며 UI에 표시하지 않는다.
- verify 상태: PASS — 전용 Docker PostgreSQL 16 컨테이너에서 `db/validate.py` **160/0**, `npm run verify` **49 files / 286 tests**(typecheck·lint·production build 포함) 통과.
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` DB 계약 진입점, `vite.config.ts` 검증 안정화, M6 오프라인 테스트 계약.

---

### [2026-07-13] PR #5 PostgreSQL 단일화 (DDL 계약) — 완료
- 한 일: 서비스 DB를 **PostgreSQL 16으로 확정**하고 설계 킷·문서를 전량 이식했다. `db/schema.sql`을 PG DDL로 재작성(타입 네이티브화, `PRAGMA`·`json_valid`·`boolean IN(0,1)` CHECK 제거, 트리거 60종 → PL/pgSQL 함수, 순환 FK `cases↔runs`를 `DEFERRABLE INITIALLY DEFERRED`로), `db/seed_demo.sql` 이식(boolean `1/0`→`true/false`, `char(10)`→`chr(10)`), `db/validate.cjs`(node:sqlite) → **`db/validate.py`(psycopg)** 재작성. `db/README.md`·`docs/DB_SCHEMA.md`(§1 엔진표·§2 FK 규약·§5.2 append-only 예시)를 PG로 갱신. 직전 항목의 160개 안전성 검증을 **글자 단위로 보존**했다(RAISE EXCEPTION 메시지는 validate가 substring 매칭).
- 핵심 함정 해결: **PostgreSQL은 같은 테이블 BEFORE 트리거를 이름 알파벳순으로 발화**한다(SQLite는 생성순). 전이 가드가 catch-all `state_update`보다 먼저 발화해야 위반에 맞는 메시지가 표면화되므로, 가드 트리거를 `link < reopen < state` 순으로 정렬되게 명명했다(예: `drafts_approval_reopen_guard`).
- 남은 일 / 중단 지점: 이 PR은 **DDL 계약 범위만**이다(실행 backend 없음). PG backend(SQLAlchemy 31모델·Alembic·psycopg·savepoint 테스트 격리·승인 F1~F3 픽스)는 로컬 브랜치 `claude/pg-backend`(커밋 3b0c657)에 분리 보관 — **별도 PR**로 올린다. 그 PR은 이 `db/schema.sql`을 그대로 적용해 스키마 동등성을 유지한다.
- 결정 사항 (다음 세션이 알아야 할 것): ① 서비스 DB는 PostgreSQL 단일 방언 — SQLite 은퇴(설계 킷·문서·검증 모두 PG). ② 검증은 backend 없이 독립 실행: `DATABASE_URL="postgresql://oegobanjang:oegobanjang@localhost:55432/oegobanjang" uv run --no-project --with "psycopg[binary]" python db/validate.py`. ③ 트리거 함수 이름은 알파벳 발화 순서에 의존하므로 이름을 임의로 바꾸지 않는다. ④ RLS는 선택적 후속 강화(복합 FK+트리거가 테넌트 격리를 이미 강제).
- verify 상태: PASS — Docker PG 16(`localhost:55432`)에 `db/schema.sql`+`db/seed_demo.sql` 클린 로드, `db/validate.py` **160/0** 통과.
- 지도/규칙 갱신: `db/schema.sql`, `db/seed_demo.sql`, `db/validate.py`(신규), `db/validate.cjs`(삭제), `db/README.md`, `docs/DB_SCHEMA.md`.
---

### [2026-07-13] PR #5 DDL 안전성 범위 정리 — 완료
- 한 일: PR에만 추가됐던 `backend/` API·ORM·Alembic 스캐폴드와 이를 운영 대상으로 선언한 `AGENTS.md` 변경을 제거했다. `db/schema.sql`을 현행 실행 정본으로 유지하고, 전체 테넌트 복합 FK·active membership·citation scope·MVP 외부 실행 차단을 DDL로 강제한다.
- 추가 보강: pending/approved draft와 handoff package는 `approval_id`를 제거·교체하거나 `draft`로 되돌릴 수 없고, approval 삭제는 pending을 포함해 모두 차단한다. 프론트 pending approval의 `idempotencyKey`는 `null`, decide()는 비어 있지 않은 키를 요구하도록 맞춘다.
- 남은 일 / 중단 지점: 후속 backend PR에서만 이 DDL과 동등한 migration/ORM을 만들고, 인증 principal·서버 측 PIN/biometric·유효 delegation 검증 전에는 approve/reject endpoint를 노출하지 않는다.
- 결정 사항 (다음 세션이 알아야 할 것): 설계 정본은 `db/schema.sql`과 `docs/DB_SCHEMA.md`다. SQLite 연결은 매번 `PRAGMA foreign_keys=ON`을 적용·검사해야 한다. `ApprovalStatus` 저장값은 `pending|approved|rejected`만이며 프론트 `locked`는 파생 표시다. pending approval의 결정 idempotency key는 NULL을 허용하고 decide 시점에만 채운다.
- verify 상태: PASS — `node --experimental-sqlite db/validate.cjs` **160/0**, `npm run verify` **41 files / 225 tests**(typecheck·lint·production build 포함) 통과.
- 지도/규칙 갱신: `AGENTS.md`, `README.md`, `docs/ARCHITECTURE.md`, `docs/DB_SCHEMA.md`, `db/README.md`, `db/schema.sql`, `db/validate.cjs`, `src/types.ts`, `src/stores/approvalStore.ts`.
---

### [2026-07-12] DB 설계 + DBeaver 킷 — 완료
- 한 일: `docs/DB_SCHEMA.md`와 `db/` 설계 킷(DDL·데모 시드·검증기)을 추가했다. 이 기록의 backend 접속점 표현은 2026-07-13 PR #5 범위 정리로 대체됐다.
- 결정 사항: 현재 정본은 `db/schema.sql`이며, backend migration/API는 별도 승인 PR에서 이 DDL과 동등하게 이식한다.
- verify 상태: 당시 DDL 검증 PASS 30 / FAIL 0. 이후 검증 수와 안전 계약은 최신 PR #5 항목을 따른다.

---

### [2026-07-11] 디자인 원본 저장소 고정 — 완료 (PR 리뷰 반영)
- 한 일: PR 리뷰 지적("외부 디자인 원본을 저장소 안의 재현 가능한 스펙으로 고정한 뒤 병합하는 편이 안전")을 반영. `rules/design.md`·ROADMAP 2.5.4~2.5.6·`.claude/agents/ui-matcher.md`가 전부 claude.ai/design 라이브 프로젝트(`bd0fd8f8-615f-48e9-875b-eb5c9e9b398d`)만 가리키고 있어, 그 프로젝트가 바뀌거나 접근 불가해지면 스펙 근거가 사라지는 구조였다. `reference/design-system/`에 4개 파일을 그대로 고정: `montage-wanted/colors_and_type.css`(원본 CSS — 기존 `외고반장_통합/09_.../colors_and_type.css` 미러와 sha256 비교로 100% 일치 확인, 드리프트 없었음), `montage-wanted/source-rules-design.md`(디자인 프로젝트 자체 rules/design.md 원문 — 우리 저장소의 `rules/design.md`는 이걸 각색한 것), `외고반장 PC.dc.html`(190KB, ROADMAP 2.5.4~2.5.6의 1차 스펙), `외고반장 Mobile.dc.html`(85KB, 채택 보류된 개편안 — 참고 고정만). `rules/design.md`·`plans/ROADMAP.md`(M2.5 블록쿼트 + 2.5.4/5/6 스펙 컬럼)·`docs/SPEC_INDEX.md`·`docs/DESIGN_SYNC_AUDIT_2026-07-11.md`·`.claude/agents/ui-matcher.md`의 참조를 전부 고정 사본 경로로 갱신.
- 남은 일 / 중단 지점: 없음. 디자인 프로젝트가 실제로 바뀌면 다시 `get_file`로 받아 `reference/design-system/`을 갱신하고 이 파일 + `reference/design-system/README.md`에 남긴다(README에 절차 명시).
- 결정 사항 (다음 세션이 알아야 할 것): 이제부터 디자인 근거를 인용할 때 claude.ai/design 프로젝트 URL이 아니라 `reference/design-system/` 안의 고정 파일 경로로 인용한다. `.dc.html` 파일은 디자인 도구 전용 캔버스 마크업이라 브라우저로 그대로 열어도 프로덕션 렌더링과 다를 수 있음(값·구조 참고용).
- verify 상태: PASS — 문서·reference 파일만 추가/수정(src/ 무변경)이라 `npm run verify` 결과는 직전 항목(2.5.3)과 동일(typecheck 0, lint 0, 38 files/196 tests, build OK).
- 지도/규칙 갱신: `rules/design.md`(출처 라인), `plans/ROADMAP.md`(M2.5 블록쿼트 + 2.5.4~2.5.6 스펙 컬럼), `docs/SPEC_INDEX.md`, `docs/DESIGN_SYNC_AUDIT_2026-07-11.md`(§6에 재현성 보강 항목 추가), `.claude/agents/ui-matcher.md`(기준 문구) — 전부 이 세션에서 갱신.

---

### [2026-07-11] M2.6 (2.6.1~2.6.4) — 완료 (모바일 승인 큐 개편)
- 한 일: Mobile.dc.html §2a~2d 전면 이식 — **"카드에서는 검토만, 승인은 체크리스트 화면에서"**. ① **2.6.1 홈(2a)**: `BriefingHeader`(오늘 브리핑 제목+날짜·사업장+벨), `PipelineStatRow`(누적 깔때기 6·5·4·3 + 실행(주) 12 — `lib/pipeline.ts` 파생+`EXECUTED_WEEKLY_MOCK`), `ApprovalCard` 단일 "검토" CTA로 재설계(2CTA 제거, returned 보완 칩 추가), `AgentProgressList` 신설, 인사문장·SummaryStatRow 제거(컴포넌트 삭제), 커맨드바 존치. ② **2.6.2 검토(2b)**: `CaseReviewPage` 신설 — `/case/:id` 모바일이 바텀시트 대신 전면 페이지(케이스 헤드·왜 확인·누락 서류·연결 근거·초안 VN/KR 인라인 토글·검토 계속). `CaseSheet` 컴포넌트 삭제(워크벤치·검토 페이지가 대체). 진입 시 `review_started` evidence(중복 가드). **기본 언어=근로자 언어(VN)** — 브라우저 검증 중 발견해 교정. ③ **2.6.3 승인(2c)**: `ApprovePage` 신설 — `/case/:id/approve`에서 RunPage 대체. 게이트 교체: 필수 체크리스트 4/4 + citation-0 잠금(이중). 배너 제목은 정본 상수(`SAFETY_NOTICE_TEXT` — SafetyNotice에서 export, C1 교정). 반려하기 = 사유와 함께 `decide(rejected, reason)` + `approval_pending→returned` 전이 + evidence. 승인 = `checklist_completed`+`approval_decided`(#4789, 김담당 (본인)) → 2d 이동. ④ **2.6.4 이력(2d)**: `CaseHistoryPage` + `/case/:id/history` 라우트 신설 — 결과 카드+생애 타임라인(시드 표시 병합)+정적 "발송 실행 (mock) · 예정" 노드, **사람 결정 노드만 primary**(C9 교정), 하단 "모든 판단·승인은 Evidence Log에 기록됩니다.".
- 남은 일 / 중단 지점: 없음(M2.6 완료). 다음은 2.5.5 PC 거버넌스(citationStore 준비돼 있음) → 2.5.6 → 2.4·2.2·2.3. 참고: RunPage의 `caseId → approval config` 분기는 이제 도달 불가 경로(라우트가 ApprovePage로 교체됨) — /run/:runId 전용으로 남아 있으며 정리(단순화)는 후속 리팩터 후보.
- 결정 사항 (다음 세션이 알아야 할 것): ① 성급한 승인 방지 게이트 = **체크리스트 4/4**(구 스트리밍 게이트 대체, GOTCHAS 개정 확정). 데모 3막 대본은 이 게이트 기준으로 개정 필요(블루프린트 §2 — 사용자 확인 항목). ② evidenceStore는 비어 시작(런타임 전용)이고 시드는 **표시 시점 병합**(CaseHistoryPage) — 시드 상주는 M8(2.3) 몫. ③ 2d "승인 요청 생성" 노드는 시드에서 온다 — 새 케이스 승인 플로우를 추가하면 EVIDENCE_SEED에 approval_requested를 함께 넣을 것.
- verify 상태: PASS(typecheck 0, lint 0, **39 files/212 tests**, build OK — SummaryStatRow/CaseSheet 테스트 삭제, E2E 신규 깔때기 2본으로 재작성). 브라우저 실측(375px): 홈 파이프라인 6·5·4·3·12 디자인 일치, 검토 버튼 3개·카드 승인 버튼 0개, 2b(VN 기본 초안·승인 버튼 없음) → 2c(4/4 전 승인 disabled·정본 배너) → 2d(#4789·human 노드 primary·mock 발송 예정) 전 구간 통과, 콘솔 에러 0.
- 지도/규칙 갱신: `docs/GOTCHAS.md`(카드 CTA 규칙 개정 확정), `docs/ARCHITECTURE.md` §3(라우트 3행), `.claude/agents/ui-matcher.md`(모바일 기준 = Mobile.dc.html 2a~2d + 교정 3건).

---

### [2026-07-11] 2.5.4b — 완료 (Design-first 파운데이션)
- 한 일: 블루프린트 §3·§4 전면 구현. **① 6인 로스터 치환**(fixtures 전면 재작성 — Batbayar E./Nguyen Van A/Siti R./Tran Thi H./Rahmat P./Oyunaa T., mohammad·hiring 제거, title은 업무 단위로 분리, 사업장명 그린푸드 제조·기준일 07.10). **② 타입 확장** — WorkerRef.team, CaseCard.caseCode/assignee/stayExpiryDate/evidenceCompleteness/agentStage, CaseState.returned(+caseStore 전이 표), CitationGrade.F, EvidenceType 3종(review_started/checklist_completed/exported), Approval.reason(+decide 4번째 인자). **③ 중앙 근거 라이브러리** — `src/mocks/citations.ts`(cit_001~cit_021, §3c 8행+§2d 1행) + `citationStore`(KPI·연계 수 셀렉터 파생, `usableCitations` F 제외 필터 — CaseSheet·워크벤치 잠금 판정에 적용). **④ Evidence 시드** — §3c 대역(#4783~#4791)·해시·행위자(김담당 (본인)/system)로 재작성, 커맨드 런 #4790→**#4797** 재번호(디자인에서 #4790=Siti 승인 요청으로 확정). **⑤ 토큰** — chip draft(보라)/detected(시안) 2쌍(+다크), label .43(dim)/.61(subtle) 계층, track. **⑥ 컴포넌트 킷 6종 정합**(Montage 공용 컴포넌트.dc.html) — SafetyNotice 2형(neutral 고정문구 불변+emphasis), OfflineBanner 경고형(+재시도), Skeleton shimmer, StepTimeline 세로형(펄스 링·가드레일 칩), 탭바 비활성 .61+아이콘 3종 교체(IconBriefing/IconFolder/IconClock 신설), BottomSheet 핸들 line 토큰. 화면 반영: ApprovalCard·CaseList 근로자 부제, 워크벤치 팀 부제·구조화 메타·근거 완성도 진행바·이름 검색.
- 남은 일 / 중단 지점: 없음. 다음은 블루프린트 §8 순서 — **M2.6(모바일 2a→2b→2c→2d)** → 2.5.5 → 2.5.6. GOTCHAS의 "카드 CTA 2개" 규칙은 M2.6에서 1개("검토")로 개정 예고만 해둠(그 전까지 2개 유지).
- 결정 사항 (다음 세션이 알아야 할 것): ① 케이스 근거는 반드시 `libCitation('cit_*')` 참조로 연결한다 — 값 복제 금지(라이브러리가 단일 출처, citationStore 테스트가 id 보유를 강제). ② `agentStage`가 있으면 스테퍼·파이프라인 파생에서 상태보다 우선한다. ③ 텍스트 계층: 부제·비활성 탭=`text-subtle`(.61), 타임스탬프·해시=`text-dim`(.43) — muted(.88)는 본문 보조용. ④ 반려는 approval_pending↔returned 왕복만 허용(가드레일 테스트 있음).
- verify 상태: PASS(typecheck 0, lint 0, **41 files/223 tests** — 신규 10개 포함, build OK). 브라우저 실측: 모바일 홈(6건 인사·Batbayar 히어로·근로자 부제·탭바 비활성 rgba(55,56,60,0.61)+아이콘 4종), 데스크톱 워크벤치(6행 큐 순서·팀 부제·meta "E-9 · 포장팀 · 인도네시아 · case_003"), /run/4797 커맨드 런 정상, 콘솔 에러 0.
- 지도/규칙 갱신: `rules/design.md` §5(파이프라인 칩 2행+F등급)·§6(킷 6종 스펙 명시), `docs/GOTCHAS.md`(케이스 단위 승인·F등급 추가, CTA 규칙 개정 예고).

---

### [2026-07-11] 2.5.4 — 완료 (+ Design-first 블루프린트 수립)
- 한 일: **PC 케이스 워크벤치(3열)** 구현 — `reference/design-system/외고반장 PC.dc.html` §3b 기준. `src/features/cases/CaseWorkbench.tsx`(목록 레일 290px·상세·AI/근거 레일 340px, 진행 스테퍼·서류 체크리스트·다국어 초안·타임라인·승인/전달 상태·행정사 전달 잠금·가드레일 문구 2종) + `CaseWorkbenchPage.tsx`(컨테이너, /cases·/case/:id 공유) + `src/lib/useIsDesktop.ts`(matchMedia+resize 이중 리스너, jsdom 기본 false) + `src/lib/caseStage.ts`(진행/전달 단계 파생 — 발송 mock 미도달 가드) + 토큰 3종(shadow rail-active/rail-focus/step-current). 필터·그룹·정렬은 `lib/cases` selector 재사용, CTA는 데이터 구동 라벨 그대로, citation-0 잠금 동일 적용. **오래된 테스트 플레이크 근본 수정**: `/case/:caseId` loader 비동기 커밋 경합 — `CaseListPage.test.tsx` scrim 대기와 신규 테스트 모두 DOM 기준 `findBy*`(+5s)로 전환.
- 남은 일 / 중단 지점: 없음(2.5.4 자체는). 단, **디자인 소스 채택 지시(2026-07-11)** 로 후속 전체 설계가 `docs/DESIGN_FIRST_BLUEPRINT_2026-07-11.md`에 수립됨 — 다음 착수는 블루프린트 §8 순서: **2.5.4b 파운데이션**(6인 로스터·모델 확장·citationStore·토큰 2쌍·컴포넌트 킷 6종) → M2.6(모바일 2a~2d) → 2.5.5 → 2.5.6. 워크벤치의 로스터·담당·근거 완성도 표시는 2.5.4b에서 소급 적용.
- 결정 사항 (다음 세션이 알아야 할 것): ① 데스크톱 분기는 CSS hidden이 아니라 `useIsDesktop` **렌더 분기** — 모바일에서 데스크톱 트리가 마운트되지 않아 기존 테스트·접근성 트리가 오염되지 않는다. 새 PC 화면(2.5.5/2.5.6)도 같은 패턴을 쓸 것. ② 선택 상태의 진실은 URL(/case/:id) — 검색으로 레일에서 걸러져도 상세는 URL 케이스를 유지. ③ returnTo는 반드시 `ROUTES.cases()`로 생성(CaseSheetPage의 safeCaseListReturnTo 화이트리스트 통과 조건).
- verify 상태: PASS(typecheck 0, lint 0, **40 files/213 tests**, build OK — 플레이크 수정 후 2회 연속 전건 통과). 브라우저 실측(1280px): 3열 렌더·행 클릭→URL/상세 동기·선택 인디케이터·다크 모드 토큰 전환·필터 프리셋(aria-pressed)·스테퍼/전달 단계 라벨 디자인 원문 일치 확인, 콘솔 에러 0. 모바일(375px) 리로드: 워크벤치 미마운트+바텀시트 플로우 무결. **주의: 멀티에이전트 검증 워크플로우는 2회 모두 외부 요인(중단 1회, 서브에이전트 세션 한도 1회 — 17:40 리셋)으로 실패해 동일 항목을 인라인 수행함**(정적 grep 배터리·코드 리뷰·verify — 전부 클린).
- 지도/규칙 갱신: `plans/ROADMAP.md`에 블루프린트 §6 반영(2.5.4b·M2.6 신설, 2.5.5/2.5.6/2.4 스펙 보강). GOTCHAS·rules/design.md 개정은 2.5.4b 구현과 함께(블루프린트 §7).

---

### [2026-07-11] 2.5.3 — 완료
- 한 일: 기존 화면 13개 파일의 타이포그래피를 Montage v2 타입 스케일(`text-heading1`/`heading2`/`body1`/`body2`/`label1`/`caption1`, tailwind.config.js에 2.5.1에서 이미 등록돼 있던 유틸리티)로 전환. 역할 분류 규칙: 화면 최상단 h1/h2 제목→heading2(20px, CaseListScreen은 24→20 보정·DonePage/DraftPage/RunScreen은 18→20 승격으로 통일), 카드/시트 h3 제목→body1(16px), 인사문장·빈상태 큰 강조→heading1(22px), 서술형 문장(설명·안내·에러 메시지)→body2(15px), 버튼/칩/행 라벨 같은 UI 크롬→label1(14px), 캡션·타임스탬프→caption1(12px). 기존 font-weight/leading-* 클래스는 그대로 유지(사이즈 토큰만 교체). Workflow로 13개 파일 병렬 치환 + 적대적 감사 에이전트를 돌려 놓친 3곳(`CaseSheet.tsx:114`, `DonePage.tsx:31`, `DraftPage.tsx:69` — 전부 "text-sm" 잔존)을 찾아 직접 수정. `.claude/agents/ui-matcher.md`를 prototype_v3 기준에서 디자인 프로젝트(+ Chip tone 명칭·타이포·아웃라인 체크 항목 추가)로 교체하면서, 초안이 잘못 인용한 `외고반장 Mobile.dc.html`(보류 결정된 모바일 개편안)을 "기준 아님"으로 정정.
- 남은 일 / 중단 지점: 없음 — M2.5는 2.5.1~2.5.3 전부 완료. 다음은 ROADMAP 2.5.4(PC 케이스 워크벤치) 또는 2.2(메시지 탭).
- 결정 사항 (다음 세션이 알아야 할 것): 화면 h1/h2는 이제 전부 heading2(20px)로 통일한다 — 기존처럼 화면마다 다른 크기(18/20/24px)를 쓰지 않는다. 새 화면 타이포는 이 6단계 스케일 중에서 고르고, `text-lg`/`text-xl`/`text-2xl` 같은 임시 크기는 (Button.tsx/Chip.tsx 등 컴포넌트 자체 내부 스타일 제외) 다시 쓰지 않는다.
- verify 상태: PASS (`npm run verify`: typecheck 0, lint 0, 38 files/196 tests 통과, build OK). 브라우저(Vite dev) 실측으로 heading2(20/28px, -0.24px 자간)·heading1(22/30px)·body1(16/22px, 기존 leading-snug 유지) 계산값이 토큰과 일치함을 확인, 콘솔 에러 없음.
- 지도/규칙 갱신: `rules/design.md` 상단 배너를 "2.5.1·2.5.2·2.5.3 완료"로 갱신. `.claude/agents/ui-matcher.md` 전면 교체(위 참조).

---

### [2026-07-11] 2.5.1·2.5.2 — 완료
- 한 일:
  - **2.5.1**: `src/styles/tokens.css`를 Montage(Wanted) v2 atomic+semantic 토큰으로 전면 교체(라이트 기본 + `[data-theme="dark"]`), `tailwind.config.js`는 유틸리티 이름(`canvas`/`ink`/`critical`/`rounded-in`/`shadow-card` 등)을 그대로 두고 `var()` 대상만 재배선해 20여개 소비 파일 무변경 색상 전환 달성. `--fs-pc-*`(PC 밀도 타입램프)·Montage 타입 스케일(`heading1`~`caption1`)을 Tailwind `fontSize`에 등록(아직 어느 화면도 적용 안 함, 2.5.3·2.5.4+ 몫). **라이트/다크 토글 UI 신규 구현**: `src/stores/themeStore.ts`(zustand, localStorage 영속 + `prefers-color-scheme` 폴백) + `Shell.tsx`에 토글 버튼(PC 헤더·모바일 우상단 고정) + `icons.tsx`에 `IconSun`/`IconMoon` 추가. 브라우저 실사용 검증 중 **Chip 배경이 라이트 전용 고정 hex라 다크 배경에서 붕 뜨는 문제**를 발견해 `chip-*-bg`/`-fg`에 다크 전용 오버라이드(옅은 rgba 틴트 + Montage 자체 다크 상태색) 추가.
  - **2.5.2**: `src/components/Badge.tsx`→`Chip.tsx`, `src/lib/badgeTone.ts`→`chipTone.ts` 개명. **톤 이름을 값과 함께 새로 설계**(`rules/design.md` §5 기준) — v1의 `pending`(amber)/`info`(blue)라는 모호한 이름을 없애고 `approval`(승인 필요=블루)/`medium`(MEDIUM 위험도=흐린 오렌지)으로 분리(v1은 이 둘의 색이 정반대였다). `src/lib/dday.ts`의 `DDayTone`도 동일하게 `warning`→`high`, `info`→`medium`으로 새로 짬(D-31~90 배지가 파랑에서 흐린 오렌지로 바뀜 — 블루는 이제 "승인 필요" 전용). `Button.tsx` outline 배리언트를 `border` → `shadow-outline`(inset box-shadow)으로 교체, 사이즈별 라디우스(`rounded-in` 10px/`rounded-btn-sm` 8px) 도입. 소비 파일 전부 갱신: `DraftPage`/`DonePage`/`CaseListScreen`/`ApprovalCard`/`CaseSheet`/`BriefingScreen`.
  - **덤으로 발견해 고침**(토큰 마이그레이션 중 같은 파일을 만지다 발견, GOTCHAS 임의값 금지 위반): `CaseListScreen.tsx`의 `rounded-[14px]`/`rounded-[8px]`(임의값) → `rounded-chip`/`rounded-in`, 존재하지 않는 `border-line` 클래스 → `border-hairline`. 같은 파일의 "승인 필요" Chip이 텍스트와 안 맞게 `neutral`(회색) 톤이었던 것을 `approval`(블루)로 정정.
- 남은 일 / 중단 지점: 2.5.3(기존 화면에 Montage 타입 스케일 실제 적용 + `.claude/agents/ui-matcher.md` 기준을 prototype_v3→디자인 프로젝트로 교체)이 남음 — 색상·라디우스·그림자·모션은 이미 전부 v2, 글자 크기만 과거 Tailwind 임시값. `rules/design.md`의 부록 A(v1 요약)는 이미 삭제함(코드에 v1 hex가 더 안 남아 조건 충족). 이 머신엔 Node가 기본 설치돼 있지 않아 포터블 Node(`%LOCALAPPDATA%/nodejs-portable`, PATH는 `~/.bashrc`에 등록됨— 새 대화 세션의 셸에선 안 읽힐 수 있으니 안 되면 `export PATH=".../node-v22.14.0-win-x64:$PATH"` 재실행)로 대체 설치했다.
- 결정 사항 (다음 세션이 알아야 할 것):
  - Chip/DDay 톤 이름 규칙: **'pending'·'info' 같은 모호한 이름은 다시 쓰지 않는다** — 색상표(rules/design.md §5)의 실제 의미를 이름에 반영한다(critical/high/medium/positive/approval/neutral/line).
  - D-31~90 D-day 배지는 이제 파랑이 아니라 흐린 오렌지다(블루는 승인 필요 전용) — 의도된 변경, 되돌리지 말 것.
  - Chip 배경은 라이트/다크 각각 다른 값을 가진다(다크는 rgba 틴트) — 새 톤 추가 시 `[data-theme="dark"]` 블록에도 짝을 넣을 것.
- verify 상태: PASS — `tsc --noEmit` 0, `eslint .` 0, 38 files/196 tests 통과(마이그레이션 전 존재하던 `CaseListPage.test.tsx`의 `bottom-sheet-scrim` 클릭 테스트가 전체 스위트에서 가끔 실패하는 건 파일 단독 실행 시 100% 통과 확인 — 순서 의존 플레이키, 이번 변경과 무관, 미수정), `vite build` OK. 브라우저(Vite dev, localhost:5173)에서 토글 클릭 실측: `data-theme` 전환·`localStorage` 영속·Chip 4종(critical/high/medium/approval) 라이트·다크 양쪽 실제 계산된 색상이 토큰표와 정확히 일치함을 확인.
- 지도/규칙 갱신: `rules/design.md` 상단 배너를 "2.5.1·2.5.2 완료"로 갱신하고 부록 A(v1 토큰 요약) 삭제.

---

### [2026-07-07] 2.1 — 완료 (사후 이기 2026-07-11)
- 한 일: M7 케이스 목록을 `/cases`에 연결 — 필터 칩, 딥링크 프리셋(`?filter=crit|warn|info|approval`), 고정 그룹 순서(승인 대기→즉시 확인→확인 필요→예정→완료(접힘)). 필터·그룹·정렬 로직은 `src/lib/cases.ts` selector로 분리, 화면은 `src/features/cases/`의 `CaseListPage`/`CaseListScreen`. compact 아이템은 CTA 없이 `/case/:caseId`로 진입. (Codex 세션 구현 — PR #2, 커밋 `66e299e`·`e70005f`, 머지 `5531370`)
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 2.2 — 단 M2.5(디자인 시스템 v2 전환) 신설로 2.5.1~2.5.3 선행 권장(ROADMAP 헤더·M2.5 참조).
- 결정 사항 (다음 세션이 알아야 할 것): M7 필터·정렬 로직은 컴포넌트가 아니라 `src/lib/cases.ts` selector를 기준으로 유지한다.
- verify 상태: 당시 세션 기록 PASS(`npm run test:run -- src/lib/cases.test.ts src/features/cases/CaseListPage.test.tsx`), 전체 verify는 별도 최종 검증으로 미룸. 이기 세션(문서 전용, Node 미설치 환경)에서는 재실행 불가.
- 지도/규칙 갱신: 원 기록이 번들 사본 `외고반장_통합/13_클로드코드_구현패키지/plans/HANDOFF.md`에 작성되어 있어 이 파일로 이기함(ROADMAP ✅ 표시도 번들 사본에만 존재). **이후 세션은 반드시 루트 `plans/HANDOFF.md`에 기록할 것.**

---

### [2026-07-07] 1.6 — 완료
- 한 일: M3/M4/M5 승인 해피패스 루프 구현. `src/features/draft/DraftPage.tsx`를 추가해 `/case/:caseId/draft`에서 DRAFT fixture 기반 초안, 언어 토글, 수정 요청 BottomSheet, 수정 반영 후 승인 검토 이동을 제공. `src/features/run/RunPage.tsx`의 approval mode 승인 버튼을 `approvalStore.requestApproval/decide` + `caseStore.transition(caseId, 'human_approved')` + `evidenceStore.append(approval_decided)`에 연결하고 `/done`으로 이동. `src/features/done/DonePage.tsx`를 추가해 “발송 승인 완료” 전용 완료 화면을 렌더하되 실제 카톡/문자/정부 제출은 실행하지 않음을 명시. `ApprovalCard`는 `human_approved` 상태에서 “승인 완료” 배지를 표시. 실제 라우터 기반 통합 테스트 `src/features/approvalFlow.test.tsx`를 추가해 `/case/nguyen` → M2 → M3 → M4 → M5 → M1 상태 반영을 검증.
- 남은 일 / 중단 지점: Playwright 패키지/스크립트는 현재 프로젝트에 없어 ROADMAP의 “playwright E2E”는 Vitest 라우터 통합 테스트로 대체했다. 진짜 브라우저 E2E가 필요하면 Playwright 의존성과 `npm run test:e2e` 스크립트를 별도 태스크로 추가해야 한다. 수정 요청 시트는 고정 “부드럽게 다듬기” 프리셋 1개만 제공한다(자연어 수정 요청/다중 프리셋은 범위 밖).
- 결정 사항: M4 승인 후에도 외부 발송 함수는 만들지 않는다. 승인 결정과 상태 전파만 수행하고, 완료 화면 문구는 “발송 승인 완료”를 사용한다. Evidence 이벤트 타입은 기존 타입 계약에 맞춰 `approval_decided`를 사용한다.
- verify 상태: PASS (`npm run verify`: typecheck 0, lint 0, test 36 files/184 tests passed, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` §2·§5·§7에 M3/M5 위치와 1.6 승인 상태 전파를 반영.

---
### [2026-07-06] 1.5 — 완료
- 한 일: L3(협업) 태스크라 `superpowers:brainstorming`으로 시작 — 범위(3모드 한번에 vs approval만 먼저)와 M4/M9 화면 공유 여부를 질문으로 확정한 뒤 설계 스펙(`docs/superpowers/specs/2026-07-06-run-engine-steptimeline-design.md`) 작성·커밋, 구현 계획(`docs/superpowers/plans/2026-07-06-run-engine-steptimeline.md`, 9태스크) 작성 후 subagent-driven-development로 실행. `src/mocks/runs.ts`의 `RunStepKind`를 공식 5종(thinking/tool_call/guardrail/handoff/replan)으로 정리하고 M0.5의 로컬 `'wait'` 확장 제거("승인 대기"는 RunStep이 아니라 런의 종착점), command(#4790)·replay(#4788) config 2건 추가. `src/lib/runEngine.ts`(React 비의존 `executeRun` — 430ms*(i+1) 스텝 스트리밍, replay는 즉시 전체 emit) + `src/lib/useRunEngine.ts`(React 훅 래퍼). `src/features/run/`: `StepTimeline`(guardrail만 경고 톤 구분) + `RunScreen`(5상태 프레젠테이션, 스트리밍 미완료 시 승인 버튼 disabled) + `RunPage`(컨테이너 — `/case/:caseId/approve`·`/run/:runId` 두 라우트를 하나로 공유). 기존 no-op였던 `CommandBar` 제출(→ command 데모 런)과 `ApprovalCard` 프로액티브 행 클릭(→ preparedRunRef 재생)을 실제 네비게이션으로 배선. 최종 전체 리뷰(opus)에서 Critical/Important 0건, Minor 2건 중 1건(RunPage 레벨 스트리밍-disabled 통합 테스트 부재)만 수정 — 픽스 서브에이전트가 fake timer 아래 `findByRole`(waitFor 기반, 실시간 폴링 필요)을 써서 타임아웃 나는 걸 컨트롤러가 직접 `getByRole`(버튼은 스트리밍 여부와 무관하게 항상 동기 렌더됨)로 교체해 해결.
- 남은 일 / 중단 지점: 없음. approvalStore.decide() 등 승인 결정 영속화·caseStore 상태 전이는 명시적으로 1.6(M3~M5 루프) 몫으로 남김 — 지금 `RunPage.onApprove`는 `/done`으로 이동만 한다. `RunViewState.default.mode` 필드는 RunScreen이 아직 안 읽음(1.6에서 command/replay UI 차이가 더 생기면 쓰일 수 있음, 지금은 무해한 미사용 필드로 남김 — 최종 리뷰 Minor, 고치지 않기로 함). command 모드는 자연어 파싱 없이 항상 고정 데모 런(#4790)으로 매핑(실 파싱은 백엔드 단계). 다음은 ROADMAP 1.6(M3 초안 + M4 승인 + M5 완료 + 상태 전파, E2E) — L2.
- 결정 사항:
  - ARCHITECTURE.md의 "M4는 이 화면의 mode='pre_approval' 특수 케이스" 문구는 별도 모드 값이 아니라 "M4 라우트가 이 화면(mode='approval')의 특수 사용처"로 해석 확정(브레인스토밍 질문으로 사용자 확인) — `RunConfig.mode`는 3값(`command`/`approval`/`replay`) 그대로.
  - M4(`/case/:caseId/approve`)와 M9(`/run/:runId`) 라우트가 동일한 `RunPage` 컴포넌트를 공유(브레인스토밍 질문으로 확정) — `caseId` 파라미터면 `caseId+mode==='approval'`로, `runId` 파라미터면 `runKey`로 `RUN_CONFIGS`를 조회.
  - 런은 전역 zustand 스토어를 만들지 않음 — 화면 하나가 소유하는 로컬 상태(useRunEngine의 useState)로 충분하다고 판단(caseStore/approvalStore와 달리 여러 화면이 동시 구독할 필요가 없음).
- verify 상태: PASS (typecheck 0, lint 0, test 35 files/183 tests passed, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` §2에 `src/features/run/` 추가, §5 런 시스템에 "구현(1.5)" 문단 추가(executeRun/useRunEngine/RunPage 공유 사실 + approvalStore 연동은 1.6 몫 명시).

---

### [2026-07-06] 1.4 — 완료
- 한 일: `/case/:caseId`가 실제 M2 케이스 시트를 렌더. `src/components/BottomSheet.tsx`(공용 모달 프리미티브 — scrim/slide-up/dismissible/footer, 도메인 타입 모름). `src/features/case/CaseSheet.tsx`(1단계 §M2 5블록 고정: 요약/AI확인내용/서류체크리스트/근거/에이전트활동 + ActionBar 2개 — citation 0건이면 근거 경고 + **승인이 필요한 액션만** locked, 5개 케이스 전부 이 컴포넌트 하나로 커버·분기 없음). `src/features/case/CaseSheetPage.tsx`(`<BriefingHomePage/>`를 배경으로, `<CaseSheet/>`를 오버레이로 구성 — 2단계 딥링크맵의 "M1 위에 오버레이" 요구를 진짜 background-location 대신 M1 렌더러 재사용으로 근사). 어드버서리얼 리뷰에서 Important 1건(`activity`가 비어 있으면(mohammad/hiring) `nextWake`까지 통째로 안 뜨던 버그) 발견 후 수정.
- 남은 일 / 중단 지점: 없음. 진짜 background-location(M7 생기면 재검토), half↔full 드래그 제스처, M9 재생 뷰 연결, tranCase 확인완료 후 UI 반영은 계획 문서에 범위 밖으로 명시. Minor로 남긴 것(고치지 않음, 문제 아님): `BriefingHomePage`와 `CaseSheetPage`가 caseStore 시딩 `useEffect`를 각자 갖고 있어 중복이지만 React 마운트 순서상 안전(자식이 먼저 시드하고 부모는 가드에 걸려 스킵) — 다음에 손댈 사람은 공유 훅으로 뽑을지 고려. 존재하지 않는 caseId로 이동하면 안내 없이 조용히 M1만 보임(M7·실제 딥링크 검증 붙을 때 재검토). 다음은 ROADMAP 1.5(런 엔진, **L3** 협업 태스크 — v3의 renderRun() 각본 재생 로직 이식) 또는 2.1(M7 케이스 목록) — ROADMAP 순서상 1.5가 다음이지만 L3라 더 무거운 협의가 필요.
- 결정 사항:
  - citation 등급(A/B/C/E) 배지는 기존 `Badge` 컴포넌트를 재사용하지 않고 새 인라인 span으로 렌더 — 프로토타입 v3 `.cite .g`(18×18 정사각형)가 `Badge`의 알약형과 시각이 달라 억지로 끼워맞추지 않음(`size-[18px]`는 1.3의 `size-[22px]`와 같은 성격의 알려진 국지적 예외).
  - citation-잠금은 `card.primaryAction.requiresApproval`이 true인 액션에만 걸린다 — tranCase처럼 승인이 필요 없는 primaryAction(kind:'confirm')은 citation 0건이어도 잠기지 않는다(GOTCHAS §2가 말하는 건 "승인 게이트"지 "모든 액션 차단"이 아님).
- verify 상태: PASS (typecheck 0, lint 0, test 30 files/162 tests passed, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` §2 "화면 컴포넌트" 행에 `src/features/case/` 사례 추가.

---

### [2026-07-06] 1.3 — 완료
- 한 일: M1 오늘 브리핑 홈을 5상태 전부 구현하고 `/` 라우트에 연결(더 이상 PlaceholderScreen 아님). `src/types.ts`에 `NextActionKind`(approve/draft/detail/thread/package/confirm) 추가 + `src/mocks/fixtures.ts` CASE_CARDS 10개 액션에 kind 채움. `src/lib/actionNav.ts`(`useNextAction()` — kind→이동/인라인 액션, confirm은 risk_review→completed가 CASE_TRANSITIONS에 없어 이동 없이 evidence만 남김). `src/lib/briefing.ts`(`greetingText`/`sortCards`/`visibleCardsForRole`/`recommendReason` 순수 함수). `src/components/icons.tsx`에 IconSpark/IconWait 추가. `src/features/briefing/`: `BriefingHeader`/`SummaryStatRow`/`CommandBar`(작은 프레젠테이션), `ApprovalCard`(hero/compact, 배지 순서 고정, CTA 2개), `BriefingScreen`(5상태 전부 담은 순수 프레젠테이션 — 이번 마일스톤 DoD), `BriefingHomePage`(caseStore 시딩 + role/greeting 계산하는 컨테이너). 어드버서리얼 리뷰에서 Important 3건 발견 후 수정: (1) compact 카드도 primary(파랑) CTA를 렌더해 "화면당 파랑 1개" 위반 — compact는 secondary variant로 교정 (2) hero 추천 이유가 dead ternary로 항상 undefined — `recommendReason()` 헬퍼로 실연결 (3) `greetingText`가 테스트만 되고 실제 화면은 호칭 없이 인사문을 재구현 — `BriefingViewState`에 `greeting` 필드 추가해 실연결.
- 남은 일 / 중단 지점: 없음. 컨테이너/프레젠테이션 분리 패턴(`<Name>Screen` + `<Name>Page`)이 확립됐으니 M2~M9도 따르길 권장. role(manager 고정, 4.2 몫)·근로자수(5 고정, 3단계 몫)·실제 fetch/오프라인 감지(백엔드 접속점 이후)·Toast(스펙 갭)·CommandBar→M9 연결(1.5)·프로액티브 행→런 재생 뷰(1.5)는 계획 문서에 범위 밖으로 명시. 다음은 ROADMAP 1.4(BottomSheet + M2 케이스 시트) — L2.
- 결정 사항:
  - 실행 중 세션 사용량 한도로 워크플로우가 한 번 중단됐다(9:50pm 리셋) — task3(briefing.ts)는 이미 완성돼 있었지만 커밋 전에 끊겨 수동으로 확인 후 커밋, 나머지(4/6/7/8)는 순차 Agent 디스패치로 이어서 진행. 최종 결과물이나 커밋 이력에는 영향 없음.
  - `ApprovalCard`의 오프라인 처리는 계획 원안(카드 전체 fieldset 잠금)에서 `offlineDisabled` prop 방식으로 구현 중 조정됨 — `requiresApproval:true`인 CTA만 잠그고 읽기 액션(예: 초안 보기)은 오프라인에서도 유지(GOTCHAS §3 "초안 보기 등 읽기 액션은 캐시 범위 내 허용"과 정확히 부합, 원안보다 개선).
  - `router.test.tsx`의 잘못된 caseId 리다이렉트 테스트가 기대하는 텍스트를 `/M1 오늘 브리핑/`(옛 PlaceholderScreen 문구)에서 `/화성 1공장/`(BriefingHomePage 헤더 회사명)로 갱신 — index route 교체의 자연스러운 결과.
- verify 상태: PASS (typecheck 0, lint 0, test 27 files/148 tests passed, build OK). `router.test.tsx`의 딥링크 백스택 테스트가 전체 스위트 동시 실행 시 간헐적으로 flake하는 기존 이슈(1.1부터)는 이번 세션에서는 재현되지 않았다.
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` §2 "화면 컴포넌트" 행에 `src/features/briefing/`을 컨테이너/프레젠테이션 분리 패턴의 실제 사례로 추가.

---

### [2026-07-06] 1.2 — 완료
- 한 일: 공용 컴포넌트 6종 + 배지 색 규칙 매핑 모듈. `src/components/Badge.tsx`(tone 7종: critical/warning/pending/info/success/neutral/line, 프로토타입 v3 `.bdg` 그대로), `Button.tsx`(variant 3종 primary/secondary/outline + size default/sm, 네이티브 button 속성 pass-through), `Card.tsx`(variant default/hero + interactive, margin은 컴포넌트에 강제 안 함), `SafetyNotice.tsx`(props 없음 — GOTCHAS §3 고정 문구를 타입으로 강제), `OfflineBanner.tsx`(v3에 시각 참고 없어 스펙 텍스트만으로 신규 설계), `Skeleton.tsx`(bg-hairline pulse, motion-reduce 대응). `src/lib/badgeTone.ts` — `severityTone`/`approvalStatusTone`/`caseStateTone`(1단계 §0.2 표 → BadgeTone 매핑, Badge는 이 파일에서 타입만 import해 도메인 타입 격리 유지). `icons.tsx`에 `IconShield` 추가(기존 4개 아이콘 불변). `tokens.css`/`tailwind.config.js`에 이번 태스크에 필요한 토큰 전부 등록(배지 배경 틴트 4색 + 텍스트 오버라이드 2개, 배지 radius 8px, surface-press, 버튼 치수 5개, SafetyNotice 치수 2개) — 임의값 Tailwind 클래스 0건.
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 1.3(M1 브리핑 홈, 5상태 전부) — 이번에 만든 6개 컴포넌트 + badgeTone이 그 화면의 기반이 됨. L2라 계획 승인 대상.
- 결정 사항:
  - 배지 radius는 rules/design.md 요약(칩·배지 14)과 달리 실제 8px(`--r-badge`) — 프로토타입 v3 `.bdg{border-radius:8px}`가 시각 기준(rules/design.md 자체 원칙)이라 프로토타입을 따름. rules/design.md 요약 문구 자체는 이번 태스크 범위 밖이라 고치지 않음(다음에 손대는 사람이 "14로 되돌리는" 실수를 하지 않도록 여기 기록).
  - Button/Card는 레이아웃(margin/flex:1)을 자체에 강제하지 않음 — 프로토타입 정적 HTML과 달리 재사용 컴포넌트라 간격은 호출부(부모 레이아웃) 책임으로 뺌.
  - 배지 텍스트 색은 종류별로 기본 토큰과 다른 값 사용(critical: 아이콘/닷 등에 쓰는 #EF4444가 아니라 배지 전용 #DC2626, warning도 마찬가지) — 프로토타입 원본 그대로, `critical-text`/`warning-text`로 별도 등록.
  - `src/router.test.tsx`의 딥링크 백스택 테스트가 전체 스위트 동시 실행 시 간헐적으로 실패(단독 실행 시엔 항상 통과) — 이번 태스크가 만든 파일과 무관(router.tsx/Shell.tsx 무변경 확인됨), 1.1부터 있던 타이밍 이슈로 추정. 다음에 이 테스트를 만지는 사람은 참고.
- verify 상태: PASS (typecheck 0, lint 0, test 19 files/104 tests passed, build OK). router.test.tsx 간헐적 flake는 위 참고.
- 지도/규칙 갱신: 없음(ARCHITECTURE.md의 "화면 컴포넌트" 항목은 아직 `src/features/`를 가리키는데, 이번 6개는 도메인 화면이 아니라 공용 프리미티브라 `src/components/`에 그대로 있음 — 별도 갱신 불필요 판단).

---

### [2026-07-06] 1.1 — 완료
- 한 일: ROADMAP 1.1(라우터+딥링크 맵+Shell) 전체 9태스크 완료. `src/lib/routes.ts`(`ROUTES`/`ROUTE_PATHS` 딥링크 경로 단일 출처), `src/lib/cn.ts`(legacy `features/pc/ui.tsx`에서 이식), `src/components/icons.tsx`(탭 아이콘 4종, `prototype_v3.html`에서 이식), `src/screens/PlaceholderScreen.tsx`(미구현 라우트 공용 자리표시자), `src/lib/deeplink.ts`(`validateIdParam` — zod 기반 loader 팩토리, `zod` 신규 의존성 4.4.3), `src/lib/nav.ts`(`useNav()` — 명명된 내비게이션 메서드 12개, 전부 `ROUTES.*` 위임), `src/Shell.tsx`(레이아웃 라우트 — <1024px 모바일 탭바/이상 PC 헤더 분기 + `useDeepLinkBackstack()` 훅, 콜드 스타트 시 히스토리를 [M1, 목적지]로 재작성), `src/router.tsx`(자식 라우트 12개로 전체 라우트 트리 완성, 그중 6개는 `validateIdParam` 기반 loader 보유). M0.1 자리표시자였던 `src/App.tsx`/`src/App.test.tsx`는 삭제(Shell로 완전 대체). 두 DoD(라우트 스냅샷 테스트, 딥링크 백스택=M1→목적지)를 `src/router.test.tsx`의 실제(비모킹) 라우터 테스트로 검증.
- 남은 일 / 중단 지점: 없음. 1.2/1.3/1.4/2.1이 의존하는 라우팅·딥링크·Shell·nav 인프라는 모두 준비 완료.
- 결정 사항:
  - `/case/:caseId`(bare, M2 케이스 바텀시트)와 `/onboarding/workers`(O1 근로자 등록)를 라우트 트리에 추가 — `ARCHITECTURE.md` 원래 라우트 표에는 없었지만 2단계 딥링크맵 스펙(N03 등은 `case/{id}`로, N21은 `onboarding/workers`로 직결)이 요구해 반영. 같은 세션에서 ARCHITECTURE.md §3 표도 갱신.
  - 계획 외 보정: 태스크 도중 `router.navigate(-1)`이 당시 vitest 3.2.6에서 throw(vitest-dev/vitest#8374 — Node 24 아래 jsdom AbortSignal 브랜드 체크 버그)하는 것을 발견. 사용자 확인 후 근본 해결을 택해 `vitest` `^3.0.0` → `^4.1.10` 업그레이드. 테스트 완화 없이 버그 자체를 제거, 이후 전체 스위트 통과.
  - 알려진 사소한 갭(차단 아님, 향후 세션 참고용): (1) `Shell.tsx`의 탭바 치수(`h-[62px]`/`text-[11px]`/`pb-[62px]`)는 탭별기획 §0.2가 지정한 정확한 값이지만 아직 `tokens.css`/`tailwind.config.js`에 이름 있는 토큰으로 등록되지 않음 — 향후 디자인 토큰 패스에서 정리 가능. (2) 라우트 스냅샷 테스트는 `path`/`hasLoader`/`children` 형태만 검사해 loader가 엉뚱한 라우트에 붙는 경우(예: `case` 라우트에 `runId` validator)는 단독으로 못 잡음 — 딥링크 백스택 테스트 2개가 부분적으로만 보완. (3) 스코프 의도적 제외(완료 아님, 착오 방지용 명시): M2 오버레이 실제 렌더링(1.4), TabBar 미확인 배지(스토어 연결 후), `filter` 쿼리 파라미터 값 검증(2.1), 딥링크 검증 실패 시 토스트 문구(Toast 컴포넌트 자체가 아직 없음 — 담당 태스크 불명확한 스펙 갭).
  - 최종 whole-branch 리뷰 반영: (1)은 이 패스에서 이미 토큰화 완료(`--tabbar-h`/`--tabbar-label-fs` + `spacing.tabbar`/`fontSize.tabbar-label`)로 해소됨. 추가로, `useDeepLinkBackstack`의 콜드 스타트 `navigate(target)` 호출(`/case/:caseId` 등)이 현재 location `state`를 싣지 않는다는 점이 발견됨 — 1.4가 M2 바텀시트를 "background location" 오버레이 패턴(시트 라우트에 배경 위치를 state로 주입)으로 구현할 때 이 훅과 조율이 필요하니 1.4 착수 시 다시 조사하지 않도록 여기 남긴다.
- verify 상태: PASS (typecheck 0, lint 0, test 12 files/57 passed, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md` 진입점 표(라우팅·딥링크→`src/router.tsx`, 화면 셸→`src/Shell.tsx`)와 §3 라우트 표(`/case/:caseId` bare, `/onboarding/workers` 추가) 갱신.

---

### [2026-07-06] 0.5 — 완료
- 한 일: `reference/prototype_v3.html`·`reference/specs/*`(12_모바일퍼스트_재설계 사본, 기존 세션에서 이미 복사되어 diff 확인만 함)을 출처로 `src/mocks/` 4파일 이식. `fixtures.ts` — v3 CASE 레지스트리 5건(nguyen/bayar/mohammad/tranCase/hiring)을 `CaseCard[]`(§0.4)로, M2 시트용 데이터(kv·docs·citations·activity·nextWake)를 로컬 `CaseSheet` 타입으로 정규화. severity/그룹은 v3 `caseRows()`의 sev 필드(warn/crit/info/neut)로 근거를 삼아 매핑. `drafts.ts` — DRAFT 3건(nguyen/mohammad/tranReminder), KR+VN(nguyen,tranReminder)/KR+EN(mohammad) — SPEC_INDEX가 요구한 EN 포함. `runs.ts` — APPROVE 6건(nguyen/candidate/bayarPkg/mohammad/hiring/tranReminder)을 `RunConfig`/`RunStep`으로. `evidence.ts` — 초기 EV 시드 5건만(런타임 addEv 이후 항목은 향후 evidenceStore.append 몫). `src/types.ts`의 `EvidenceEvent`에 표시용 옵션 필드 3개(`summary`/`actor`/`evidenceRef`) 추가(M8 EventTimelineItem 이식, 기존 필드는 불변이라 M0.4 테스트 영향 없음).
- 남은 일 / 중단 지점: 없음. PKG(candidate/hiring 패키지 본문)·command/replay 런(#4790/#4796 draft/#4788 replay)·M7 목록 그룹핑(g 필드)은 의도적으로 제외 — 각각 M2.4·M1.5(L3)·2.1 태스크 몫. bayar는 v3 시트에 CTA가 1개뿐이라 secondaryAction('상세 보기')을 새로 만들어 채움 — M1.4에서 실제 UI 확정 시 재검토. 다음은 ROADMAP 1.1 (라우터+딥링크 맵, Shell). L2라 계획 승인 대상.
- 결정 사항:
  - Case.state 매핑(추론, v3에 명시 없음): nguyen·mohammad=approval_pending / bayar=blocked(GOTCHAS "high risk→blocked") / tranCase=risk_review / hiring=draft.
  - RunStep에 공식 5종(thinking/tool_call/guardrail/handoff/replan, GLOSSARY) 밖의 'wait'를 로컬 확장으로 추가 — v3의 "승인 대기" 스텝을 표현하려는 것으로, M9 RunStep으로 승격 시 스펙에 먼저 반영 필요.
  - CaseDocStatus는 M2 스펙의 4값(missing/requested/received/company_check) 밖에 'expiring'·'pending' 2개를 fixtures.ts 로컬 타입에 추가 — v3 라벨(만료 예정/대기)을 손실 없이 옮기기 위함.
  - EvidenceEvent 확장 필드는 모두 optional이라 evidenceStore/guardrails.test.ts 기존 계약 불변. cat(위험감지/초안생성/승인/전달) 필터 그룹은 저장하지 않고 추후 selector로 파생 예정(2.3).
- verify 상태: PASS (typecheck 0, lint 0, test 34 passed — 신규 mocks는 순수 데이터라 별도 테스트 없음, build OK).
- 지도/규칙 갱신: `docs/ARCHITECTURE.md`의 mock 데이터 진입점 행을 4파일 구조로 갱신.

---

### [2026-07-06] 0.4 — 완료
- 한 일: zustand 스토어 3종 — `src/stores/caseStore.ts`(GOTCHAS §2 상태머신 `transition` 검증), `approvalStore.ts`(`requestApproval`/`decide`/`dispatch`, idempotencyKey 중복 차단, 승인 없이 dispatch throw), `evidenceStore.ts`(append-only, 이벤트 Object.freeze). `src/lib/guardrail.ts`에 `GuardrailError`. `src/types.ts`에 `Approval`·`EvidenceEvent`(+ EvidenceType) 추가. 가드레일 테스트 `src/stores/guardrails.test.ts` 12개.
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 0.5 (mocks 이식 — v3 CASE/DRAFT/APPROVE/EV → fixtures, 스펙: docs/SPEC_INDEX.md 이식표, DoD: typecheck 통과 + PII 원문 없음). L1.
- 결정 사항:
  - 3개 가드레일 테스트: (1) 승인 없이 dispatch 불가 (2) evidence append-only(수정·삭제 액션 부재 + 동결) (3) 중복 승인 차단(같은 key no-op) — 전부 통과. Case 상태 전이 보강 3개 추가.
  - 직접 발송 함수 미구현. dispatch는 approved에서만 mock 경계까지(`{dispatched:true}`), 실제 발송 없음.
  - EvidenceEvent에 원문/PII 필드 없음 — hash만 허용.
  - 스토어 경로 = `src/stores/`. 아직 App에 미연결(M1.x에서 연결) — 빌드 번들에는 미포함.
- verify 상태: PASS (typecheck 0, lint 0, test 34 passed, build OK).
- 지도/규칙 갱신: 없음.

---

### [2026-07-06] 0.3 — 완료
- 한 일: `src/types.ts`에 §0.4 공용 타입 이식(Severity/CaseState/Role/ApprovalStatus/NextActionRef/WorkerRef/CaseCard/Citation). `src/lib/dday.ts`에 `calcDday(target, base)`(UTC 자정 정규화, 'YYYY-MM-DD'·'YYYY.MM.DD'·Date 입력) + `dDayLabel` + `dDayTone`(배지 색 규칙). `src/lib/mask.ts`에 `maskId`(영숫자→*, 구분자 유지). 단위 테스트 2파일(22 tests).
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 0.4 (스토어 3종 case/approval/evidence + 가드레일 테스트, 스펙: docs/GOTCHAS §1·2 — 아직 `docs/GOTCHAS.md`가 이 루트에 있는지 확인 필요, 없으면 `외고반장_통합/13_클로드코드_구현패키지/docs/GOTCHAS.md` 참조). L2라 계획 승인 대상.
- 결정 사항:
  - dDay 부호 규칙: 양수=남은 일수(D-N), 0=D-day, 음수=경과(D+N). tone은 토큰 색 이름(critical/warning/info/neutral)으로 반환 — 배지가 tokens와 1:1.
  - `calcDday`는 UTC 자정 기준으로 계산해 로컬 타임존·DST와 무관하게 결정적. 테스트는 기준일 주입.
  - `maskId`는 원문 digit 미보존(전체 마스킹) — safety.md "원문 금지" + 3단계 "화면에는 ***-*******만" 준수.
- verify 상태: PASS (typecheck 0, lint 0, test 22 passed, build OK).
- 지도/규칙 갱신: 없음.

---

### [2026-07-06] 0.2 — 완료
- 한 일: `src/styles/tokens.css`에 prototype_v3 `:root` 토큰 그대로 이식(reduced-motion 오버라이드 포함). `tailwind.config.js` theme를 토큰 `var()`에 연동(colors/radius/shadow/duration/timing + fontFamily). `src/index.css`에서 tokens + Pretendard(가변폰트 dynamic-subset) import, base layer에 `bg-canvas/text-ink/font-sans` 적용. 토큰 스냅샷 테스트 1개(`src/styles/tokens.test.ts`) — 기준 `:root` 블록만 파싱, 빈 맵 가드 포함.
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 0.3 (`src/types.ts` + `calcDday`·`maskId` 유틸 + 단위 테스트, 스펙: reference/specs 1단계 §0.4).
- 결정 사항:
  - Pretendard는 정적 dynamic-subset(9웨이트 전부 → CSS 526kB) 대신 **가변폰트 dynamic-subset** 사용 → CSS 53.8kB. family `Pretendard Variable` 우선, `Pretendard` 폴백.
  - 토큰 단일 출처 = tokens.css. tailwind은 var() 참조만. duration도 var()라 reduced-motion 캐스케이드 유지.
  - 스냅샷 테스트는 처음에 `?raw` 임포트가 vitest에서 빈 문자열 → 거짓 통과(`{}`) 발생 → cwd 상대경로 fs 읽기 + 개수 가드로 교정.
- verify 상태: PASS (typecheck 0, lint 0, test 2 passed, build OK, CSS 53.8kB).
- 지도/규칙 갱신: 없음.

---

### [2026-07-06] 0.1 — 완료
- 한 일: 루트에 Vite6+React19+TS5.7+Tailwind3.4+react-router-dom7+zustand5 스캐폴드. `npm run verify`(typecheck→lint→test:run→build) 구성. 빈 셸(`src/App.tsx` = `외고반장` h1) + 라우터(`src/router.tsx`) + 렌더 테스트 1개(`src/App.test.tsx`). ESLint flat config는 앱 트리(root `src`)만 대상 — legacy/외고반장_통합 등 비앱 트리는 ignore.
- 남은 일 / 중단 지점: 없음. 다음은 ROADMAP 0.2 (tokens.css + tailwind theme, v3 `:root` 이식).
- 결정 사항:
  - 프로젝트 레퍼런스(tsconfig.node.json) 제거 → 단일 tsconfig(`src` + `vite.config.ts`), `@types/node` 추가. `tsc -b` composite 충돌 회피.
  - vitest는 v3 사용(v2.1은 vite6와 nested-vite 타입 충돌). `defineConfig`는 `vitest/config`에서 import.
  - 스토어/토큰/mocks는 범위 밖이라 미포함(0.2·0.4·0.5).
- verify 상태: PASS (typecheck 0, lint 0, test 1 passed, build OK). dev 서버 부팅 확인(localhost:5173).
- 지도/규칙 갱신: 없음.

---

(아직 기록 없음 — M0.1부터 시작)
