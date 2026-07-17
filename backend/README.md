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
(테넌트 격리·승인 상태머신 등 178건)은 `db/validate.py`가 담당하며, 이 pytest는 서비스 계층에 집중한다.

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/v1/auth/otp/request` | 전화번호로 OTP 요청(로컬 환경에서만 `debug_code` 응답에 포함) |
| POST | `/api/v1/auth/otp/verify` | OTP 검증 → 세션 토큰 발급 |
| GET | `/api/v1/auth/me` | 세션 사용자 + 활성 멤버십(회사별 역할) 조회(R2.2 — 프론트 roleStore가 새로고침 후에도 세션에서 role을 다시 파생) |
| POST | `/api/v1/auth/logout` | 세션 폐기(멱등 — 이미 무효한 토큰도 204) |
| POST | `/api/v1/approvals` | 승인 요청 생성(`action_id` 기준) |
| POST | `/api/v1/approvals/{approval_id}/approve` | 승인 결정 — 게이트 강제(citation-0 잠금·본인확인·high risk handoff 전용·manager 정책 등) |
| POST | `/api/v1/approvals/{approval_id}/reject` | 반려 결정 — 사유·본인확인 필수 + PII 패턴 차단, 케이스 `returned` 전이 |
| GET | `/health` | 헬스체크 |

승인/반려·생성은 액션(케이스) 단위 단건 처리만 존재한다 — **일괄 승인 엔드포인트는 만들지 않는다**(GOTCHAS §3).
동시 결정은 대상 행을 `SELECT ... FOR UPDATE`로 잠가 직렬화한다(F1). `idempotency_key` 재호출은 멱등
replay(같은 결정 방향일 때만 같은 결과 재반환), 방향이 다르거나 다른 키로 이미 결정된 승인을 재호출하면
409. blocked(고위험) 케이스의 handoff 승인은 승인만 확정되고 케이스는 blocked로 유지된다(행정사 이관).

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
  models/                  33테이블 ORM 매핑(컬럼만 — FK/CHECK/트리거/뷰는 DB 소유)
  domain/
    case_transitions.py    src/stores/caseStore.ts CASE_TRANSITIONS와 동일한 전이 화이트리스트
    auth_tokens.py          세션 토큰 발급·해시·검증
    auth_exceptions.py      인증 도메인 예외 — 라우터가 HTTP 상태로 변환
    exceptions.py            승인 도메인 예외 — 라우터가 HTTP 상태로 변환
    pii.py                 자유 텍스트 PII 패턴 차단(rules/safety.md)
  schemas/approval.py, auth.py   요청/응답 Pydantic 모델
  services/approvals.py    승인 요청·결정 트랜잭션 — 게이트·FOR UPDATE·전이·evidence append
  services/auth.py         OTP 발급/검증, 세션 발급/조회/폐기
  api/v1/approvals.py      라우터 — 도메인 예외 → HTTP 상태 매핑, batch 엔드포인트 없음
  api/v1/auth.py           라우터 — OTP 요청/검증/me/로그아웃
  api/deps.py              get_current_user_id — Bearer 세션 토큰에서 신원 도출
migrations/
  versions/0001_p1_core_schema.py   유일한 리비전 — db/schema.sql을 그대로 적용
tests/
  conftest.py              전용 테스트 DB + savepoint 격리
  test_ddl_parity.py       모델 ↔ 마이그레이션된 DB 컬럼/타입/nullable 대조
  test_api_approvals.py    승인 decide 엔드포인트 — 게이트·멱등성·high risk·PII 차단
  test_api_approval_requests.py  승인 요청 생성 엔드포인트
  test_api_auth.py         OTP 요청/검증/세션/로그아웃
```

## 알려진 스코프 경계 (의도적)

- 인증·세션 관리(OTP + Bearer 세션 토큰 + 세션·멤버십 조회 `GET /me`)와 승인 "요청" 생성
  엔드포인트(`POST /api/v1/approvals`)는 구현돼 있다 — `decided_by_user_id`는 요청 바디가
  아니라 세션에서 도출된다.
- `checklist`(M2.6 §2c)·delegation(위임) 흐름은 게이트/트리거는 있으나 그것을 채우는 화면/엔드포인트가
  아직 없다 — **위임 유효성 검증은 아직 구현되지 않았다**(`docs/DB_SCHEMA.md` §13-10 미결, `plans/ROADMAP.md` R2.4).
- API 라우터는 인증·승인까지만 — 케이스 목록/상세·브리핑·메시지 등 read API는 화면이 백엔드에 붙는
  순서대로 추가한다(`plans/ROADMAP.md` R2.3).
- 프론트(`src/lib/api/`)는 R2.1~2.2(인증)까지 배선됐다 — `VITE_API_MODE=real`일 때만 이 backend를
  호출한다(기본값 mock, `src/lib/api/config.ts`). 케이스/브리핑/스레드/승인/evidence 배선은
  R2.3~2.6에서 순차 진행한다(`plans/ROADMAP.md`).
