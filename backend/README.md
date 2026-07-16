# backend/ — 외고반장 서비스 API (백엔드 접속점)

이 디렉터리는 `docs/DB_SCHEMA.md` 설계를 **PostgreSQL 16+**로 구현한 서비스 API다.
[`db/schema.sql`](../db/schema.sql)이 스키마 정본이며, **Alembic 0001이 그 파일의 동결
스냅샷을 적용**하므로 설계 킷과 백엔드 스키마는 구조적으로 동일하다(드리프트 원천 차단 —
`tests/test_ddl_parity.py`가 보증).

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
uv run alembic upgrade head        # 0001 동결 스냅샷을 대상 DB에 적용
```

**동결 규약(중요)**: `migrations/versions/0001_p1_core_schema.py`는 `db/schema.sql`을 더 이상
런타임에 읽지 않는다 — backend/가 처음 실린 시점(PR #10)의 내용을 `_SCHEMA_SQL_SNAPSHOT` 상수로
인라인 동결했다. **이후 `db/schema.sql`을 바꿀 때 이 파일을 다시 손대지 않는다** — 그 변경분을
표현하는 새 리비전을 `0002_...py` 형태로 추가한다(0001 모듈 docstring 참조). `db/schema.sql`은
설계 킷(`db/validate.py`가 빈 스키마에 그대로 적용해 검증하는 논리적 계약)의 단일 정본으로 계속
남고, Alembic 리비전들은 그 계약과 최종 상태가 동일하도록 유지하는 배포 경로다.

## 테스트

```bash
uv run pytest
```

`create_all()`을 쓰지 않는다 — 세션 1회 전용 테스트 DB(`ogb_test`)에 `alembic upgrade head`로 스키마를
구축하고(=동결된 0001 적용), 테스트별로는 커넥션 외곽 트랜잭션 + savepoint 롤백으로 격리한다
(`tests/conftest.py`). 서비스 코드의 `db.commit()`은 SAVEPOINT 릴리스로 흡수된다. DB 레벨 가드레일
(테넌트 격리·승인 상태머신 178건)은 `db/validate.py`가 담당하며, 이 pytest는 서비스 계층에 집중한다.

## 트랜잭션 경계 규약

서비스 함수(`app/services/*.py`)가 트랜잭션을 **소유**한다 — 라우터(`app/api/v1/*.py`)는
`db.commit()`을 호출하지 않는다. 함수 하나가 커밋 1회로 끝나며, "상태 전이 + evidence append는
같은 트랜잭션" 불변식(§0-4)은 커밋 전 마지막 `db.add(EvidenceEvent(...))`까지 한 함수 안에서
끝내는 방식으로 지킨다. 실패하면 예외가 전파되고 아무 것도 반영되지 않는다(트랜잭션 롤백은
FastAPI 예외 핸들러가 아니라 `try/except IntegrityError: db.rollback()` 처럼 서비스 함수 자신이
필요한 지점에서 명시적으로 한다).

데코레이터나 별도 unit-of-work 프레임워크는 도입하지 않았다 — 서비스 함수가 `approvals.py`·
`auth.py` 두 모듈, 함수 6개 수준이라 추상화 비용이 이득보다 크다(과설계). 서비스 모듈이 늘어나
같은 트랜잭션 관리 코드가 반복되기 시작하면 그때 재검토한다.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/v1/auth/otp/request` | phone+OTP 로그인 1단계 — OTP 발급(mock 발송, local 환경만 응답에 코드 노출) |
| POST | `/api/v1/auth/otp/verify` | phone+OTP 로그인 2단계 — 코드 검증, 세션 토큰 발급 |
| POST | `/api/v1/auth/pin` | 승인 본인확인 PIN 등록/변경(6자리) |
| POST | `/api/v1/auth/logout` | 세션 폐기(멱등) |
| GET | `/api/v1/cases` | 케이스 목록 읽기 모델 v1 — `?base_date=` 기준일 주입, 세션 사용자 회사로 스코프 |
| GET | `/api/v1/approvals` | 승인 목록 — `?status=`·`?case_id=` 필터, 세션 사용자 회사로 스코프 |
| POST | `/api/v1/approvals` | 승인 요청 생성 — manager 역할만, `risk_review`/`returned` → `approval_pending` |
| POST | `/api/v1/approvals/{approval_id}/approve` | 승인 결정 — 게이트 강제(citation-0 잠금·본인확인 실검증·high risk handoff 전용·manager 정책 등) |
| POST | `/api/v1/approvals/{approval_id}/reject` | 반려 결정 — 사유·본인확인 실검증 필수 + PII 패턴 차단, 케이스 `returned` 전이 |
| GET | `/health` | 헬스체크 |

승인 요청/결정은 액션(케이스) 단위 단건 처리만 존재한다 — **일괄 승인 엔드포인트는 만들지 않는다**
(GOTCHAS §3). 동시 결정은 대상 행을 `SELECT ... FOR UPDATE`로 잠가 직렬화한다(F1). `idempotency_key`
재호출은 멱등 replay(같은 결정 방향일 때만 같은 결과 재반환), 방향이 다르거나 다른 키로 이미
결정된 승인을 재호출하면 409. blocked(고위험) 케이스의 handoff 승인은 승인만 확정되고 케이스는
blocked로 유지된다(행정사 이관).

인증된 세션(`Authorization: Bearer <session_token>`)에서 신원을 도출한다 —
`decided_by_user_id`/`requested_by_user_id`는 더 이상 요청 바디로 받지 않는다. `identity_method`
(pin/biometric)는 실검증된다: pin은 `users.pin_hash`와 HMAC 상수시간 비교, biometric은
`users.biometric_registered` 등록 여부만 확인한다(실제 생체 검증은 기기 몫, §13-12).

## 구조

```txt
app/
  main.py                  FastAPI 앱 진입점 + 라우터 등록
  config.py                pydantic-settings, DATABASE_URL·auth_pepper(비-local 필수 검증)
  db/base.py               단일 DeclarativeBase
  db/session.py            엔진·세션 팩토리(lock_timeout)
  db/ids.py                new_id() = UUIDv7 발급 단일 지점
  models/                  33테이블 ORM 매핑(컬럼만 — FK/CHECK/트리거/뷰는 DB 소유)
  domain/
    case_transitions.py    src/stores/caseStore.ts CASE_TRANSITIONS와 동일한 전이 화이트리스트
    exceptions.py          승인 도메인 예외 — 라우터가 HTTP 상태로 변환
    auth_exceptions.py     인증 도메인 예외(OTP·세션)
    auth_tokens.py         OTP 코드·세션 토큰 생성/해시(HMAC-SHA256 pepper) — PIN도 재사용
    pii.py                 자유 텍스트 PII 패턴 차단(rules/safety.md) + mask_phone
  schemas/                 요청/응답 Pydantic 모델(approval.py·auth.py·case.py)
  services/
    approvals.py           승인 요청/결정 트랜잭션 — 게이트·FOR UPDATE·전이·evidence append·본인확인 실검증
    auth.py                OTP 발급/검증·세션 발급/폐기·PIN 등록
  api/
    deps.py                get_current_user_id(세션)·get_current_membership(테넌트 해석)
    v1/approvals.py        라우터 — 도메인 예외 → HTTP 상태 매핑, batch 엔드포인트 없음
    v1/auth.py              로그인·PIN·로그아웃 라우터
    v1/cases.py             케이스 목록 읽기 라우터 — 기준일 주입
migrations/
  versions/0001_p1_core_schema.py   유일한 리비전 — db/schema.sql 2026-07-14 스냅샷 동결 실행
tests/
  conftest.py              전용 테스트 DB + savepoint 격리
  test_ddl_parity.py       모델 ↔ 마이그레이션된 DB 컬럼/타입/nullable/server_default 대조
  test_api_auth.py         OTP·세션·로그아웃
  test_api_approvals.py    승인 decide 엔드포인트 — 게이트·멱등성·high risk·PII 차단·PIN 실검증·checklist
  test_api_approval_requests.py  승인 요청 생성 — 역할·상태 게이트
  test_api_reads.py        GET /cases·GET /approvals — 테넌트 격리·기준일 주입
```

## 알려진 스코프 경계 (의도적)

- `checklist`(M2.6 §2c) 단독 UPDATE는 DB 트리거(`approvals_update_guard`)가 막는다 — decide
  요청에 동반 제출하는 방식으로만 갱신한다(§13-12). 전용 화면(M2.6)이 생겨도 같은 계약을 쓴다.
- delegation(위임) 유효성 검증은 `delegations` 테이블(§4.1, P3)이 화면·엔드포인트와 함께
  배선되는 시점으로 미룬다(§13-10 미결) — 현재는 활성 멤버 여부까지만 확인.
- 읽기 API(`GET /cases`)는 CaseCard 전체 계약(§8)이 아니라 목록 화면 최소 모델 v1이다 — 액션
  카드·preparedRunRef 등 전체 매핑은 화면이 실제로 붙는 시점.
- 다중 회사 소속 사용자의 회사 선택 UI는 없다 — `get_current_membership`이 active membership
  2개 이상이면 400을 반환한다(§13-13).
- 에이전트/룰이 트리거하는 승인 요청(`requested_by_actor IN ('agent','rule')`, 9단계 프로액티브
  런)은 `backend/app/agent_runtime/` 이관이 필요한 별도 범위 — CLAUDE.md가 mission 문서 없이는
  그 경로 수정을 금지한다.
