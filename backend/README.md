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

## 구조

```txt
app/
  main.py       FastAPI 앱 진입점(현재 헬스체크만 — 라우터는 각 화면 마일스톤에서 추가)
  config.py     pydantic-settings, DATABASE_URL 등
  db/base.py    단일 DeclarativeBase(레거시 §12-17 "Base 이중 정의" 결함 교정)
  db/session.py 엔진·세션 팩토리
  models/       18개 P1 테이블, 파일당 스키마 §4 소분류 단위로 그룹
migrations/
  versions/0001_p1_core_schema.py   유일한 리비전 — 테이블 18개+뷰 4개+append-only 트리거 2개
tests/
  conftest.py                pytest fixture: 임시 DB에 alembic upgrade head 실행
  test_schema_ddl_parity.py  실제 생성된 DDL이 docs/DB_SCHEMA.md §4/§10 P1 정의와 일치하는지 검증
  test_guardrails.py         db/validate.cjs와 동일한 가드레일(append-only·CHECK·부분 유니크)을 pytest로 재검증
```

## 알려진 스코프 경계 (P1 한정, 의도적)

- `drafts.thread_id`는 컬럼만 있고 FK 제약이 없다 — 참조 대상 `threads`가 P2 테이블이라 아직 없다. P2 마이그레이션에서 FK를 추가한다(문서 §4.7 주석).
- API 라우터·인증·승인 엔드포인트는 이번 스캐폴드 범위 밖이다 — 스키마·마이그레이션·가드레일 테스트까지가 이 작업의 완료 기준이었다(구현 착수 결정 #9·#10).
