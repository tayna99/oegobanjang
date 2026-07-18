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
(테넌트 격리·승인 상태머신 등 181건)은 `db/validate.py`가 담당하며, 이 pytest는 서비스 계층에 집중한다.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/v1/auth/otp/request` | 전화번호로 OTP 요청(로컬 환경에서만 `debug_code` 응답에 포함) |
| POST | `/api/v1/auth/otp/verify` | OTP 검증 → 세션 토큰 발급 |
| GET | `/api/v1/auth/me` | 세션 사용자 + 활성 멤버십(회사별 역할) 조회(R2.2 — 프론트 roleStore가 새로고침 후에도 세션에서 role을 다시 파생) |
| POST | `/api/v1/auth/logout` | 세션 폐기(멱등 — 이미 무효한 토큰도 204) |
| GET | `/api/v1/cases` | 케이스 목록(R2.3) — 회사 스코프 |
| GET | `/api/v1/cases/{case_id}` | 케이스 상세(R2.4) — 목록 필드 + `usable_citation_count`·`guard_note`·`pending_approval`(id·action_id·checklist). ApprovePage가 real 모드에서 mock CASE_SHEETS 대신 쓴다 |
| POST | `/api/v1/approvals` | 승인 요청 생성(`action_id` 기준, manager 세션 전용) |
| POST | `/api/v1/approvals/{approval_id}/approve` | 승인 결정 — 게이트 강제(citation-0 잠금·**PIN 서버 검증**·checklist 제출 반영·**위임 유효성 검증**·high risk handoff 전용·manager 정책 등, R2.4) |
| POST | `/api/v1/approvals/{approval_id}/reject` | 반려 결정 — 사유·PIN 본인확인 필수 + PII 패턴 차단, 케이스 `returned` 전이. evidence type은 `approval_rejected`(R2.4 — 이전엔 승인과 동일하게 `approval_decided`로 오기록됐다) |
| GET | `/api/v1/delegations/mine` | 현재 세션 사용자가 delegate인 유효 위임(R2.4) — 없으면 200 + `null`(에러 아님) |
| POST | `/api/v1/evidence` | 일반 판단 기록 기록(R2.5) — 인증 필요, PII 패턴 차단, `case_id` 제공 시 같은 회사 소속인지 검증. `action_id`/`approval_id`/`run_id`는 받지 않음(아래 §알려진 스코프 경계) |
| GET | `/api/v1/evidence` | 판단 기록 목록(R2.5) — 인증 필요, 자기 회사만, `case_id` 쿼리로 필터 |
| POST | `/api/v1/packages/{case_id}/link` | 행정사 패키지 열람 링크 발급/재발급(R2.6) — manager/owner 인증 + 케이스의 `create_handoff` 승인 완료 필요, 7일 유효기간 갱신, 응답에 회전된 `link_token` 포함 |
| GET | `/api/v1/packages/link/{link_token}` | 행정사 패키지 열람 링크 검증(R2.6) — **무인증**(ExpertLinkPage 전용). `case_id`가 아니라 발급/재발급마다 회전하는 `link_token`으로만 조회(코드리뷰 지적 — `case_id`는 PK라 불변이라 비밀로 쓰면 재발급으로 기존 유출 링크를 회수할 수 없었다). 미발급·만료·대상없음 전부 404 |
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
  models/                  33테이블 ORM 매핑(컬럼만 — FK/CHECK/트리거/뷰는 DB 소유)
  domain/
    case_transitions.py    src/stores/caseStore.ts CASE_TRANSITIONS와 동일한 전이 화이트리스트
    auth_tokens.py          세션 토큰 발급·해시·검증
    auth_exceptions.py      인증 도메인 예외 — 라우터가 HTTP 상태로 변환
    exceptions.py            승인 도메인 예외 — 라우터가 HTTP 상태로 변환
    pii.py                 자유 텍스트 PII 패턴 차단(rules/safety.md)
  schemas/approval.py, auth.py, evidence.py, package.py, delegation.py   요청/응답 Pydantic 모델
  services/approvals.py    승인 요청·결정 트랜잭션 — 게이트(PIN·checklist·위임 포함, R2.4)·FOR UPDATE·전이·evidence append.
    usable_citation_count는 services/cases.py도 재사용(get_case_detail_out)
  services/auth.py         OTP 발급/검증, 세션 발급/조회/폐기
  services/cases.py        케이스 목록/상세 조립(R2.3·R2.4) — get_case_detail_out이 pending approval·근거수·guard_note를 얹는다
  services/delegations.py  현재 세션 사용자의 유효 위임 조회(R2.4)
  services/evidence.py     일반 판단 기록 기록/조회(R2.5) + next_event_no(evidence_seq 원자 증가, approvals.py도 재사용)
  services/packages.py     행정사 패키지 링크 발급/재발급/열람(R2.6) — 문서 콘텐츠는 다루지 않음
  api/v1/approvals.py      라우터 — 도메인 예외 → HTTP 상태 매핑, batch 엔드포인트 없음
  api/v1/auth.py           라우터 — OTP 요청/검증/me/로그아웃
  api/v1/cases.py          라우터 — GET 목록(R2.3)/상세(R2.4)
  api/v1/delegations.py    라우터 — GET /api/v1/delegations/mine(R2.4)
  api/v1/evidence.py       라우터 — POST/GET /api/v1/evidence(R2.5, 인증 필요)
  api/v1/packages.py       라우터 — POST(인증) /api/v1/packages/{case_id}/link · GET(무인증) /api/v1/packages/link/{link_token}(R2.6)
  api/deps.py              get_current_user_id/get_current_membership — Bearer 세션 토큰에서 신원·소속 도출
migrations/
  versions/0001_p1_core_schema.py   실배포(PR #10) 동결 스냅샷 — 더 이상 손대지 않는다
  versions/0002_r2_5_evidence_and_r2_6_package_links.py   evidence_events.type CHECK 확장 +
    handoff_packages.link_issued_at/link_expires_at 추가(ALTER 리비전)
  versions/0003_r2_4_delegated_approval_decider.py   trg_approvals_decider_role에 위임 OR-arm 추가
    (ALTER 리비전). 다음 스키마 변경은 0004+
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
