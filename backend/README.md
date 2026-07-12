# backend/ — 외고반장 서비스 API (백엔드 접속점)

정본은 [`docs/DB_SCHEMA.md`](../docs/DB_SCHEMA.md)다. 여기는 그 설계를 FastAPI+SQLAlchemy+Alembic으로 구현한 것 — **P1 코어 18테이블**(문서 §10)만 우선 구현됐다. P2·P3(소통·패키지·알림·에이전틱)는 해당 마일스톤 착수 시 이관한다.

`legacy/backend/`는 이전 FastAPI 서버(Agent Runtime·RAG 포함, 아카이브)다. 이 디렉터리는 그것을 되살린 게 아니라 `docs/DB_SCHEMA.md` 설계를 새로 구현한 것이며, 레거시의 구조적 결함 20건(문서 §12)을 의도적으로 피한다 — 특히: 런타임 `ALTER TABLE`/산재한 `create_all()` 없음(Alembic이 유일한 스키마 생성 경로), 모든 논리적 관계는 실제 FK, 날짜·불리언·JSON은 네이티브 타입.

## 세팅

```bash
cd backend
uv sync
```

## 마이그레이션

```bash
uv run alembic upgrade head        # 최신 스키마 적용
uv run alembic revision --autogenerate -m "설명"   # 모델 변경 후 리비전 생성(생성물은 수기 검토 필수)
```

`DATABASE_URL` 환경변수(기본 `sqlite:///./data/oegobanjang.sqlite3`)로 대상 DB 지정 — `app/config.py` 참조.

## 테스트

```bash
uv run pytest
```

테스트는 `create_all()`을 쓰지 않는다 — 매 세션 임시 SQLite 파일에 `alembic upgrade head`를 실제로 실행해 만든 DB로 검증한다(`tests/conftest.py`). 순환 FK(`cases.prepared_run_id` ↔ `runs.id`)가 `Base.metadata.create_all()`에서 위상정렬 실패를 일으키는 것도 이 방식으로 피한다.

## API

현재 구현된 엔드포인트:

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/v1/approvals/{approval_id}/approve` | 승인 결정 — §5.3 게이트 8개 강제(citation-0 잠금·본인확인·high risk handoff 전용 등) |
| POST | `/api/v1/approvals/{approval_id}/reject` | 반려 결정 — 사유 필수 + PII 패턴 차단, 케이스 `returned` 전이 |
| GET | `/health` | 헬스체크 |

승인/반려는 액션(케이스) 단위 단건 처리만 존재한다 — **일괄 승인 엔드포인트는 만들지 않는다**(GOTCHAS §3). 두 엔드포인트 모두 상태 전이 + evidence append를 한 트랜잭션으로 묶고(`app/services/approvals.py`), `idempotency_key` 재호출은 멱등 replay(같은 결과 재반환), 다른 키로 이미 결정된 승인을 재호출하면 409다.

인증은 아직 없다 — `decided_by_user_id`를 요청 바디로 직접 받아 `memberships` 조회로 권한만 확인한다(세션/토큰 기반 인증은 별도 마일스톤).

## 구조

```txt
app/
  main.py           FastAPI 앱 진입점 + 라우터 등록
  config.py         pydantic-settings, DATABASE_URL 등
  db/base.py        단일 DeclarativeBase(레거시 §12-17 "Base 이중 정의" 결함 교정)
  db/session.py     엔진·세션 팩토리, PRAGMA foreign_keys=ON 강제
  models/           18개 P1 테이블, 파일당 스키마 §4 소분류 단위로 그룹
  domain/
    case_transitions.py  src/stores/caseStore.ts CASE_TRANSITIONS와 동일한 상태 전이 화이트리스트
    exceptions.py        승인 도메인 예외(§5.3 게이트별 1:1 대응) — 라우터가 HTTP 상태로 변환
    pii.py               반려 사유 등 자유 텍스트의 PII 패턴 차단(rules/safety.md)
  schemas/approval.py  요청/응답 Pydantic 모델
  services/approvals.py  승인 결정 트랜잭션 — 게이트 검증 + 케이스 전이 + evidence append
  api/v1/approvals.py    라우터 — 도메인 예외 → HTTP 상태 매핑, batch 엔드포인트 없음
migrations/
  versions/0001_p1_core_schema.py   유일한 리비전 — 테이블 18개+뷰 4개+append-only 트리거 2개
tests/
  conftest.py                pytest fixture: 임시 DB에 alembic upgrade head 실행
  test_schema_ddl_parity.py  실제 생성된 DDL이 docs/DB_SCHEMA.md §4/§10 P1 정의와 일치하는지 검증
  test_guardrails.py         db/validate.cjs와 동일한 가드레일(append-only·CHECK·부분 유니크)을 pytest로 재검증
  test_api_approvals.py     승인 decide 엔드포인트 — 게이트 8개·멱등성·high risk·PII 차단
```

## 알려진 스코프 경계 (의도적)

- `drafts.thread_id`는 컬럼만 있고 FK 제약이 없다 — 참조 대상 `threads`가 P2 테이블이라 아직 없다. P2 마이그레이션에서 FK를 추가한다(문서 §4.7 주석).
- 인증·세션 관리는 아직 없다 — `decided_by_user_id`를 신뢰된 값으로 받는다(다음 마일스톤).
- 승인 "요청" 생성 엔드포인트(`requestApproval` 대응)는 아직 없다 — 지금은 시드 데이터로 pending 승인을 만든다. 다음으로 붙일 엔드포인트 후보.
- `checklist`(M2.6 §2c)·delegation(위임) 흐름은 게이트 로직은 있으나 그것을 채우는 화면/엔드포인트가 아직 없다.
