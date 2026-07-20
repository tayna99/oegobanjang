# backend/ — 외고반장 서비스 API (백엔드 접속점)

이 디렉터리는 `docs/DB_SCHEMA.md` 설계를 **PostgreSQL 16+**로 구현한 서비스 API다.
[`db/schema.sql`](../db/schema.sql)이 스키마 정본이며, **Alembic 0001이 그 파일을 그대로 적용**하므로
설계 킷과 백엔드 스키마는 구조적으로 동일하다(드리프트 원천 차단 — `tests/test_ddl_parity.py`가 보증).

`legacy/backend/`는 이전 FastAPI 서버(Agent Runtime·RAG 포함, 아카이브)다. 이 디렉터리는 그것을
되살린 게 아니라 새로 구현한 것이며, 레거시의 구조적 결함 20건(문서 §12)을 의도적으로 피한다 —
런타임 `ALTER TABLE`/산재한 `create_all()` 없음(Alembic이 유일한 스키마 생성 경로), 모든 논리적
관계는 실제 FK, 타입은 PG 네이티브(jsonb·boolean·timestamptz).

## 세팅

로컬 PostgreSQL(Docker)은 `db/README.md` 참조. 접속 URL 기본값은
`postgresql+psycopg://oegobanjang:oegobanjang@localhost:55432/oegobanjang`(`DATABASE_URL`로 재정의).

```bash
cd backend
uv sync
```

## 마이그레이션

```bash
uv run alembic upgrade head        # db/schema.sql을 대상 DB에 적용
```

0001 리비전은 `db/schema.sql`을 `exec_driver_sql`로 실행한다(트리거 함수 34종·복합 FK·뷰 포함).
스키마를 바꾸려면 `db/schema.sql`(+`docs/DB_SCHEMA.md`)을 고치고 `db/validate.py`·backend pytest를
다시 통과시킨다. **미배포 스캐폴드 규약**: 최초 실배포 시점에 0001의 SQL을 그 시점 내용으로 인라인
동결하고, 이후 스키마 변경은 0002+ ALTER 리비전으로만 한다(migrations/versions/0001 주석 참조).

## 테스트

```bash
uv run pytest
```

`create_all()`을 쓰지 않는다 — 세션 1회 전용 테스트 DB(`ogb_test`)에 `alembic upgrade head`로 스키마를
구축하고(=db/schema.sql 적용), 테스트별로는 커넥션 외곽 트랜잭션 + savepoint 롤백으로 격리한다
(`tests/conftest.py`). 서비스 코드의 `db.commit()`은 SAVEPOINT 릴리스로 흡수된다. DB 레벨 가드레일
(테넌트 격리·승인 상태머신·참조 시드 불변식·발송 대기열 승인 게이트·행정사 화이트라벨 등)은
`db/validate.py`가 담당하며, 이 pytest는 서비스 계층에 집중한다.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/v1/auth/otp/request` | 전화번호로 OTP 요청(로컬 환경에서만 `debug_code` 응답에 포함) |
| POST | `/api/v1/auth/otp/verify` | OTP 검증 → 세션 토큰 발급 |
| GET | `/api/v1/auth/me` | 세션 사용자 + 활성 멤버십(회사별 역할) 조회(R2.2 — 프론트 roleStore가 새로고침 후에도 세션에서 role을 다시 파생) |
| POST | `/api/v1/auth/logout` | 세션 폐기(멱등 — 이미 무효한 토큰도 204) |
| GET | `/api/v1/cases` | 케이스 목록(R2.3) — 회사 스코프 |
| GET | `/api/v1/cases/{case_id}` | 케이스 상세(R2.4, SD-6 확장) — 목록 필드 + `usable_citation_count`·`guard_note`·`pending_approval`(id·action_id·checklist) + `checked_items`·`next_wake`(cases 컬럼 그대로)·`documents`(worker_documents, worker_id 없으면 빈 배열). ApprovePage/CaseReviewPage/CaseWorkbench가 real 모드에서 mock CASE_SHEETS 대신 쓴다 |
| GET | `/api/v1/cases/{case_id}/draft` | 케이스의 가장 최근 살아있는(non-rejected/superseded) 초안(SD-5) — `draft_id`·`channel`·`purpose`·`status`·`langs`(draft_variants, `is_revised` 포함). 초안이 아예 없으면 404. DraftPage가 real 모드에서 mock DRAFTS 대신 쓴다 |
| POST | `/api/v1/approvals` | 승인 요청 생성(`action_id` 기준, manager 세션 전용) |
| POST | `/api/v1/approvals/{approval_id}/approve` | 승인 결정 — 게이트 강제(citation-0 잠금·**PIN 서버 검증**·checklist 제출 반영·**위임 유효성 검증**·high risk handoff 전용·manager 정책 등, R2.4) |
| POST | `/api/v1/approvals/{approval_id}/reject` | 반려 결정 — 사유·PIN 본인확인 필수 + PII 패턴 차단, 케이스 `returned` 전이. evidence type은 `approval_rejected`(R2.4 — 이전엔 승인과 동일하게 `approval_decided`로 오기록됐다) |
| GET | `/api/v1/delegations/mine` | 현재 세션 사용자가 delegate인 유효 위임(R2.4) — 없으면 200 + `null`(에러 아님) |
| POST | `/api/v1/evidence` | 일반 판단 기록 기록(R2.5) — 인증 필요, PII 패턴 차단, `case_id` 제공 시 같은 회사 소속인지 검증. `action_id`/`approval_id`/`run_id`는 받지 않음(아래 §알려진 스코프 경계) |
| GET | `/api/v1/evidence` | 판단 기록 목록(R2.5) — 인증 필요, 자기 회사만, `case_id` 쿼리로 필터 |
| POST | `/api/v1/packages/{case_id}/link` | 행정사 패키지 열람 링크 발급/재발급(R2.6) — manager/owner 인증 + 케이스의 `create_handoff` 승인 완료 필요, 7일 유효기간 갱신, 응답에 회전된 `link_token` 포함 |
| GET | `/api/v1/packages/link/{link_token}` | 행정사 패키지 열람 링크 검증(R2.6) — **무인증**(ExpertLinkPage 전용). `case_id`가 아니라 발급/재발급마다 회전하는 `link_token`으로만 조회(코드리뷰 지적 — `case_id`는 PK라 불변이라 비밀로 쓰면 재발급으로 기존 유출 링크를 회수할 수 없었다). 미발급·만료·대상없음 전부 404 |
| POST | `/api/v1/expert/grants` | 행정사 위탁 발급(R5.1, owner/manager 내부 세션) — 사업자등록번호 일치 시 기존 사무소 재사용, 아니면 신규 사무소 + 최초 사무소 구성원(담당자, isOfficeAdmin) 부트스트랩. `until` 필수(무기한 위탁 금지, 결정 C) |
| POST | `/api/v1/expert/grants/{grant_id}/authorize` | 위탁계약 근거 확인(invited→company_authorized, owner/manager) |
| POST | `/api/v1/expert/grants/{grant_id}/revoke` | 위탁 철회(→revoked, **owner 전용** — manager는 초대까지만) |
| GET | `/api/v1/expert/grants` | 회사의 위탁 목록(owner/manager) — 조회 시 `until` 경과 grant를 지연 평가로 `expired` 전이 |
| POST | `/api/v1/expert/auth/otp/request` | 화이트라벨 세션 로그인 — 이메일로 OTP 요청(로컬 환경에서만 `debug_code` 응답 포함) |
| POST | `/api/v1/expert/auth/otp/verify` | OTP 검증 → 화이트라벨 세션 토큰 발급. 이 사무소의 `company_authorized` grant를 전부 `active`로 전이(spec §5.1 "최초 로그인") |
| GET | `/api/v1/expert/office-members` | 자기 사무소 구성원 로스터 조회(화이트라벨 세션) |
| POST | `/api/v1/expert/office-members` | 사무소 구성원 등록/재활성화(**isOfficeAdmin 전용**) |
| PATCH | `/api/v1/expert/office-members/{member_id}` | 구성원 상태(active/suspended)·admin 권한 변경(**isOfficeAdmin 전용**) |
| GET | `/api/v1/expert/packages/{package_id}` | 화이트라벨 세션 패키지 조회(R5.1, spec §4.2) — tenant scope + 사무소(`expert_account_id`) 일치 + 케이스 `human_approved` 이상 3중 체크, 실패 시 전부 동일 404. 성공 시 `PackageViewLog` 1행 기록(evidence_events가 아님 — 목적이 다른 별도 감사 로그, spec §6). 문서 콘텐츠는 반환하지 않음(R2.6과 동일 스코프 경계) |
| POST | `/api/v1/outbox` | 발송 "실행 확인"(R3 — MESSAGING_CHANNELS.md §1 각주²) — manager 세션 전용. 승인된(`status='approved'`) `send_message` 액션에만 outbox 1행을 만들고, 발송 창(21:00~08:30, CRITICAL 22:00)이 아니면 즉시 ChannelAdapter로 처리한다 |
| GET | `/api/v1/outbox` | 발송 대기열 목록(R3) — 인증 필요, 회사 스코프 |
| GET | `/api/v1/response-link/{token}` | 근로자 응답 링크 조회(R3) — **무인증**. 발신 메시지 본문(모국어)·버튼 선택지를 내려준다. 만료·미발급 전부 404 |
| POST | `/api/v1/response-link/{token}` | 근로자 응답 제출(R3) — **무인증**. 버튼 선택/자유입력 → 인바운드 정규화 + N02(`worker_reply_received`) + M6 Interpretation(proposed) |
| POST | `/api/v1/webhooks/zalo` | Zalo OA 인바운드 webhook(R3 stage ④) — 공유 시크릿(`X-Webhook-Secret` 헤더) 게이팅, 미설정 시 항상 503 |
| GET | `/health` | 헬스체크 |

승인/반려·생성은 액션(케이스) 단위 단건 처리만 존재한다 — **일괄 승인 엔드포인트는 만들지 않는다**(GOTCHAS §3).
동시 결정은 대상 행을 `SELECT ... FOR UPDATE`로 잠가 직렬화한다(F1). `idempotency_key` 재호출은 멱등
replay(같은 결정 방향일 때만 같은 결과 재반환), 방향이 다르거나 다른 키로 이미 결정된 승인을 재호출하면
409. blocked(고위험) 케이스의 handoff 승인은 승인만 확정되고 케이스는 blocked로 유지된다(행정사 이관).

**PIN 검증(R2.4)**: `identity_method='pin'`이면 결정자의 `users.pin_hash`와 요청 바디 `pin`을
`app.domain.auth_tokens.secrets_match`(HMAC-SHA256+pepper, OTP·세션 토큰과 동일 원리)로 대조한다.
미등록·불일치는 422. **위임 검증(R2.4)**: `on_behalf_of_user_id`가 있으면 유효한 `delegations`
행(scope='approval'·미철회·결정 시각이 기간 내·delegator가 활성 owner)이 있어야 하며, 없으면
403 — DB 트리거(`trg_approvals_decider_role`)가 최종 방어선으로 동일 조건을 다시 검사한다.

인증은 전화 OTP + Bearer 세션 토큰이다 — `approvals` 라우터는 `decided_by_user_id`를 요청 바디로 받지
않고 `Authorization: Bearer <session_token>` → `get_current_user_id`(세션 조회)로만 도출한다.

## 구조

```txt
app/
  main.py                  FastAPI 앱 진입점 + 라우터 등록
  config.py                pydantic-settings, DATABASE_URL(PostgreSQL)
  db/base.py               단일 DeclarativeBase
  db/session.py            엔진·세션 팩토리(lock_timeout)
  db/ids.py                new_id() = UUIDv7 발급 단일 지점
  db/counters.py           case_seq·evidence_seq 원자 증가 단일 지점
  models/                  41테이블 ORM 매핑(컬럼만 — FK/CHECK/트리거/뷰는 DB 소유). outbox는 R3부터,
    expert 화이트라벨 7종은 R5.1부터
  domain/
    case_transitions.py    src/stores/caseStore.ts CASE_TRANSITIONS와 동일한 전이 화이트리스트
    auth_tokens.py          세션 토큰 발급·해시·검증
    auth_exceptions.py      인증 도메인 예외 — 라우터가 HTTP 상태로 변환
    exceptions.py            승인 도메인 예외 — 라우터가 HTTP 상태로 변환
    outbox_exceptions.py    발송 대기열 도메인 예외(R3)
    response_link_exceptions.py  응답 링크 도메인 예외(R3)
    webhook_exceptions.py   인바운드 webhook 도메인 예외(R3)
    pii.py                 자유 텍스트 PII 패턴 차단(rules/safety.md)
    expert_exceptions.py   행정사 화이트라벨 도메인 예외(R5.1) — 라우터가 HTTP 상태로 변환
  schemas/approval.py, auth.py, evidence.py, package.py, delegation.py, expert.py, outbox.py, response_link.py, webhook.py   요청/응답 Pydantic 모델
  services/approvals.py    승인 요청·결정 트랜잭션 — 게이트(PIN·checklist·위임 포함, R2.4)·FOR UPDATE·전이·evidence append.
    usable_citation_count는 services/cases.py도 재사용(get_case_detail_out)
  services/auth.py         OTP 발급/검증, 세션 발급/조회/폐기
  services/cases.py        케이스 목록/상세 조립(R2.3·R2.4) — get_case_detail_out이 pending approval·근거수·guard_note를 얹는다
  services/delegations.py  현재 세션 사용자의 유효 위임 조회(R2.4)
  services/evidence.py     일반 판단 기록 기록/조회(R2.5) + next_event_no(evidence_seq 원자 증가, approvals.py도 재사용)
  services/packages.py     행정사 패키지 링크 발급/재발급/열람(R2.6) + view_expert_package(R5.1, 화이트라벨
    세션 3중 체크 + PackageViewLog 기록) — 문서 콘텐츠는 다루지 않음
  services/expert.py       위탁(Grant) 생애주기·사무소 구성원 CRUD·email+OTP 화이트라벨 세션(R5.1)
  services/channels/       ChannelAdapter 5종(Sms/Alimtalk/Zalo/Email + base 계약, R3) — 자격 증명 게이팅
  services/outbox.py       발송 대기열 오케스트레이션(R3) — 승인 게이트·발송 창·리마인드 쿨다운·48h 재발송·알림톡→SMS fallback
  services/response_link.py  응답 링크 조회/제출 + 인바운드 정규화 단일 지점(`ingest_inbound_reply`, R3)
  services/webhooks.py     Zalo OA webhook 인바운드(R3 stage ④) — 공유 시크릿 검증 + response_link.ingest_inbound_reply 재사용
  api/v1/approvals.py      라우터 — 도메인 예외 → HTTP 상태 매핑, batch 엔드포인트 없음
  api/v1/auth.py           라우터 — OTP 요청/검증/me/로그아웃
  api/v1/cases.py          라우터 — GET 목록(R2.3)/상세(R2.4)
  api/v1/delegations.py    라우터 — GET /api/v1/delegations/mine(R2.4)
  api/v1/evidence.py       라우터 — POST/GET /api/v1/evidence(R2.5, 인증 필요)
  api/v1/packages.py       라우터 — POST(인증) /api/v1/packages/{case_id}/link · GET(무인증) /api/v1/packages/link/{link_token}(R2.6)
  api/v1/expert.py         라우터 — /api/v1/expert/*(위탁 CRUD·사무소 구성원 CRUD·email OTP 로그인·패키지 조회, R5.1)
  api/v1/outbox.py         라우터 — POST/GET /api/v1/outbox(R3, 인증 필요)
  api/v1/response_link.py  라우터 — GET/POST /api/v1/response-link/{token}(R3, 무인증)
  api/v1/webhooks.py       라우터 — POST /api/v1/webhooks/zalo(R3, 공유 시크릿)
  api/deps.py              get_current_user_id/get_current_membership — Bearer 세션 토큰에서 신원·소속 도출
  api/expert_deps.py       get_current_expert_member — 화이트라벨 세션 토큰에서 ExpertOfficeMember 도출(R5.1)
migrations/
  versions/0001_p1_core_schema.py   실배포(PR #10) 동결 스냅샷 — 더 이상 손대지 않는다
  versions/0002_r2_5_evidence_and_r2_6_package_links.py   evidence_events.type CHECK 확장 +
    handoff_packages.link_issued_at/link_expires_at 추가(ALTER 리비전)
  versions/0003_r2_4_delegated_approval_decider.py   trg_approvals_decider_role에 위임 OR-arm 추가
    (ALTER 리비전)
  versions/0004_r3_outbox_and_response_link.py   outbox 테이블(+트리거 3종) + thread_messages
    response_token/response_token_expires_at 컬럼(ALTER 리비전)
  versions/0005_r5_1_expert_whitelabel.py   행정사 화이트라벨 v1 신규 테이블 7개 + handoff_packages.
    expert_account_id + evidence_events.type CHECK 확장(ALTER 리비전, down_revision=0004로 병합 시
    재정렬 — 병렬 작업 중 두 브랜치가 독립적으로 0003을 down_revision으로 잡았던 것을 병합 후
    0004→0005로 체인). 다음 스키마 변경은 0006+
tests/
  conftest.py              전용 테스트 DB + savepoint 격리
  test_ddl_parity.py       모델 ↔ 마이그레이션된 DB 컬럼/타입/nullable 대조
  test_api_approvals.py    승인 decide 엔드포인트 — 게이트(PIN·checklist·위임 포함)·멱등성·high risk·PII 차단
  test_api_approval_requests.py  승인 요청 생성 엔드포인트
  test_api_auth.py         OTP 요청/검증/세션/로그아웃
  test_api_cases.py        케이스 목록(R2.3)/상세(R2.4) — 근거수·guard_note·pending_approval·테넌트 격리
  test_api_delegations.py  위임 조회 — 유효·만료·철회·본인 소유 위임 제외(R2.4)
  test_api_evidence.py     일반 판단 기록 기록/조회 — 허용 타입·PII 차단·테넌트 격리(R2.5)
  test_api_packages.py     행정사 패키지 링크 발급/재발급/열람 — 권한·만료·404(R2.6)
  test_api_expert.py       행정사 화이트라벨 v1 — 위탁 생애주기·사무소 CRUD·email OTP 로그인·패키지
    3중 체크(cross-tenant·cross-office 격리 포함, R5.1)
  test_services_channels.py  채널 어댑터 자격 증명 게이팅 — 미설정→스텁(실 HTTP 0건)·설정→respx 요청 형태 검증(R3)
  test_api_outbox.py       발송 대기열 — 승인 게이트·idempotency·발송 창·리마인드 쿨다운·48h 재발송·알림톡 fallback(R3)
  test_api_response_link.py  응답 링크 조회/제출 — 만료·인바운드 정규화·원문 미노출(R3)
  test_api_webhooks.py     Zalo webhook — 시크릿 게이팅·인바운드 정규화(R3)
```

## 알려진 스코프 경계 (의도적)

- 인증·세션 관리(OTP + Bearer 세션 토큰 + 세션·멤버십 조회 `GET /me`), 승인 요청 생성·결정
  (PIN 서버 검증·checklist 제출·위임 유효성 검증 포함, R2.4), 케이스 읽기(목록+상세)·판단
  기록·행정사 패키지 링크까지 구현돼 있다. `decided_by_user_id`는 요청 바디가 아니라 세션에서
  도출된다.
- `POST /api/v1/evidence`(R2.5)는 `action_id`/`approval_id`/`run_id`를 받지 않는다 —
  `evidence_events`의 DB 트리거(`trg_evidence_context_match`)가 그 값들이 실제 존재하는 행을
  가리키길 요구하는데, 이 범용 엔드포인트를 쓰는 화면들은 여전히 그 참조 도메인(런 등, M3)이
  real 모드로 안 붙어 있어 `case_id`만 받는다(R2.3부터 real 모드 caseId는 항상 진짜 DB 행이라
  안전). 승인 결정 자체는 `services/approvals.py`가 자기 트랜잭션에서 직접 evidence를 남긴다
  (R2.4로 이제 real 모드가 붙었다).
- 위임 **관리**(발급/철회 UI·엔드포인트)는 여전히 범위 밖(P3) — `GET /api/v1/delegations/mine`은
  조회만 하고, 위임 레코드 자체는 시드나 직접 INSERT로만 생긴다.
- `POST /api/v1/packages/{case_id}/link`(발급/재발급, 인증) · `GET /api/v1/packages/link/{link_token}`
  (열람, 무인증)(R2.6)는 링크의 유효성(발급·만료·열람 로그)만 다룬다 — 패키지 문서 콘텐츠(검토
  요청서 본문·항목 토글)는 여전히 프론트 mock이며, 행정사 화이트라벨 개인 계정
  (`/expert/:expertId/...`, M-11 나머지)도 이번 범위 밖이다. GET의 조회 키가 `case_id`가
  아니라 회전하는 `link_token`인 이유·POST의 승인 전제조건은 위 API 표 참조(코드리뷰 지적).
- 프론트(`src/lib/api/`)는 R2.1~2.4까지 배선됐다 — `VITE_API_MODE=real`일 때만 이 backend를
  호출한다(기본값 mock, `src/lib/api/config.ts`). 브리핑·메시지 배선은 R2.3 범위(이미 완료),
  나머지 화면별 real 모드 배선은 화면이 필요해지는 순서대로 진행한다(`plans/ROADMAP.md`).
- **R3(메시징 채널, 2026-07-20)**: `outbox`+`SmsAdapter`/`AlimtalkAdapter`/`ZaloAdapter`(+
  fallback)+응답 링크+Zalo webhook까지 구현됐다(`docs/MESSAGING_CHANNELS.md` §5 ②~④). 자격
  증명이 없는 이 환경에서는 모든 어댑터가 스텁으로만 동작한다(`services/channels/` 모듈
  docstring 참고). `EmailAdapter`는 완성됐지만 `services/packages.py`에는 자동 배선하지
  않았다 — 행정사 이메일 주소를 저장할 컬럼/테이블이 스키마에 없다(`docs/MESSAGING_CHANNELS.md`
  §5-1). 리마인드 24h 쿨다운·48h 재발송 규칙은 서비스 함수로 구현됐지만 이를 주기적으로
  트리거하는 스케줄러는 없다 — 사람/후속 자동화가 `event_type='reminder'|'resend'`로
  `POST /api/v1/outbox`를 호출해야 실제로 발동한다.
