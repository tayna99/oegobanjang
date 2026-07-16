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

### [2026-07-16] PR 후속(Tranche 3) — PIN 실검증·읽기 API·기준일·mockApi 어댑터 — 완료
- 한 일: PR #10(F1~F10·인증/세션·승인요청) 이후 남은 갭을 `claude/api-integration` 브랜치(base=`claude/backend-pg`, 스택 PR)에서 마감. ① PIN 본인확인 실검증 — `POST /api/v1/auth/pin` 신설, `decide_approval`이 `identity_method='pin'`을 `users.pin_hash`와 실제 대조(`secrets_match`, 기존 `hash_secret` 재사용). biometric은 `users.biometric_registered` 등록 여부까지만 확인(신뢰 경계 명시, §13-12). checklist는 `trg_approvals_update_guard`(pending 승인의 모든 UPDATE에 status 전이 요구) 때문에 전용 PATCH 없이 decide 요청에 동반 제출·병합. ② 읽기 API 신설 — `get_current_membership`(active membership 1개=스코프, 0개=403, 2+=400), `GET /api/v1/approvals`(status/case_id 필터), `GET /api/v1/cases`(`base_date` 기준일 주입 — 미지정 시 회사 timezone 오늘; `v_case_derived`는 `CURRENT_DATE` 고정이라 이 계약에 안 씀, 서비스 계층에서 `(due_date - base_date)` 계산). ③ 프론트 `src/lib/api.ts` 어댑터 신설 — `VITE_API_BASE_URL` 플래그(미설정 시 100% 기존 mockApi), dev 전용 자동 로그인+고정 PIN(실 로그인 화면 M4 이전 대역, 명시 주석), `caseCode`로 케이스→승인 id 상관관계 해석(프론트 픽스처 id·시드 id가 전부 달라 유일 공유 리터럴). `RunPage.approve()`를 "서버 확정 후 반영"으로 배선(성공 후에만 로컬 스토어 체인, 실패 시 인라인 에러). ④ `legacy/missions/active/004-chroma-citations-sync.md` 신설 — Chroma↔citations 동기화 mission 문서(코드 무수정, CLAUDE.md의 agent_runtime 게이트를 여는 스코프 문서만).
- 구현 중 발견한 함정: checklist 대입과 `approval.status` 대입 사이에 `db.get(User,...)` 같은 SELECT가 끼면 SQLAlchemy autoflush가 checklist만 담긴 UPDATE를 status 변경보다 먼저 내보내 `trg_approvals_update_guard`("must transition ... to a decision")에 걸린다 — 두 필드 대입을 같은 지점(커밋 직전)으로 모아서 해결. 앞으로 `approvals` UPDATE에 필드를 추가할 때 이 순서 규칙을 유지할 것.
- 병합 전 코드 리뷰(사람, PR #12)가 P1 3건을 지적해 마저 수정: ① **CORS 미들웨어 부재** — 프론트(다른 origin)의 JSON+Bearer 요청이 브라우저 preflight에서 전부 막혔다(내가 앞서 curl로만 검증해서 못 잡았던 것 — curl은 CORS를 강제 안 함). `CORSMiddleware` 추가, `environment=local`이면 `localhost`/`127.0.0.1` 정규식만 기본 허용·그 외는 명시 설정 전까지 전면 차단(`auth_pepper`와 동일 fail-safe 원칙). ② **PIN 재설정이 세션만으로 가능** — 세션 탈취자가 재확인 없이 PIN을 덮어쓰면 본인확인 게이트 전체가 무력화됐다. 로그인(`verify_otp`)·PIN 등록(`set_pin`) 공용 `_consume_otp` 헬퍼로 리팩터 — PIN 등록/변경은 이제 **방금 새로 발급받은 OTP**로 전화 소지를 재확인해야 한다(로그인용 OTP는 이미 소비돼 재사용 불가). ③ **biometric이 실서명 검증 없이 통과** — `users.biometric_registered`는 등록 여부일 뿐 실제 생체 서명 증명이 아니라서 세션만 있으면 누구나 주장해서 통과할 수 있었다. WebAuthn 등 실서명 검증이 붙기 전까지 `identity_method='biometric'`을 승인 API에서 전면 거부(422)하도록 변경 — 컬럼·CHECK는 미래를 위해 스키마에 유지.
- 남은 일 / 중단 지점: 없음(계획한 5 Phase + P1 3건 전부 완료). 다음 자연스러운 순서는 `GET /cases` 응답을 실제 케이스 목록 화면(현재 mockApi 기반)에 연결하는 것 — 지금은 승인 decide 루프만 연결됨. 후속으로 고려할 것: 로그아웃/세션 폐기 시 PIN 재확인 정책, biometric 실서명(WebAuthn) 도입 시점.
- 결정 사항 (다음 세션이 알아야 할 것): ① B-13/B-14/B-15/B-16 번호는 세션 초반 구두로 전달된 "구현 착수 결정사항" 목록 기준이며 저장소에 커밋된 원본 파일이 없다 — 번호가 다시 언급되면 사용자에게 원문 재확인을 요청할 것(이번에 한 번 번호를 잘못 짚었었음). ② PIN은 6자리 숫자로 확정(스펙에 명시 없어 엔지니어링 결정, §13-12). ③ 계약 동기화는 수동+어댑터 매핑으로 확정 — OpenAPI codegen은 엔드포인트가 두 자릿수 중반을 넘으면 재검토(§8). ④ 이 세션의 Browser pane에서 클릭 자동화가 전혀 반응하지 않는 환경 문제가 있었다(네비게이션 링크 클릭도 무효) — 스크린샷도 타임아웃. 재현되면 curl로 프론트 어댑터와 동일한 API 시퀀스를 재현해 대체 검증할 것(이번에 그렇게 했고 완전히 성공함 — 단, **curl은 CORS를 강제하지 않으므로 CORS 관련 회귀는 못 잡는다**는 걸 이번에 직접 겪었다. CORS는 `curl -X OPTIONS -H "Origin: ..."`로 preflight를 직접 재현해서 확인할 것). ⑤ `.claude/launch.json`의 `web` 설정에 `autoPort:true`를 추가함 — 다른 세션이 5173을 점유해도 실패하지 않고 자동으로 다른 포트를 쓴다. ⑥ **PIN 등록/변경은 항상 "방금 받은 새 OTP"가 필요** — 로그인에 쓴 OTP는 이미 소비돼 재사용 불가. 프론트 어댑터(`src/lib/api.ts`)는 로그인용 1회 + PIN 등록용 1회, 총 2회 `/otp/request`를 호출한다.
- verify 상태: PASS — backend pytest **129/129**(P1 수정 후 최종치: CORS 3건·PIN 재확인 3건·biometric 2건 포함), `db/validate.py --reset` **178/0**, frontend `npm run verify` **290/290**(P1 수정 후 재확인, 2회 연속 그린). 1차 Phase 6 실행 중 5건 실패는 기존 문서화된 병렬 실행 간헐적 flake로 확인(단독 재실행 7/7). **실 E2E(최종)**: Docker PG 클린 시드 → uvicorn → curl로 CORS preflight 직접 확인(허용 origin=`access-control-allow-origin` 헤더 있음, 비허용 origin=400+헤더 없음) + 로그인 OTP 재사용 PIN 재설정 거부 확인(P1-2 핵심 시나리오) + 신선한 OTP로 PIN 등록 성공 + 새 PIN으로 실제 승인 완주(`status=approved`, `case_state=human_approved`).
- 지도/규칙 갱신: `docs/DB_SCHEMA.md`(§13-12 정정 + §13-13/14/15 신설), `backend/README.md`(전면 갱신 + P1 대응), `plans/ROADMAP.md`·`docs/ARCHITECTURE.md`(백엔드 접속점 게이트 정합), `legacy/missions/active/004-chroma-citations-sync.md`(신규), `backend/app/{config.py,main.py}`(CORS), `backend/app/{services/auth.py,schemas/auth.py,api/v1/auth.py}`(PIN 재확인), `backend/app/{domain/exceptions.py,services/approvals.py,api/v1/approvals.py}`(biometric 차단), `src/lib/api.ts`(2단계 OTP).

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
