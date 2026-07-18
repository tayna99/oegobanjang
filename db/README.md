# db/ 설계 킷

`docs/DB_SCHEMA.md`의 서비스 DB 계약을 **PostgreSQL**에서 실행·검증하는 산출물이다.
서비스 DB는 PostgreSQL 16+로 확정됐다(단일 방언 — SQLite 설계 킷은 은퇴). `db/schema.sql`이 정본
DDL이며, 루트 `backend/`의 Alembic 0001이 이 파일을 그대로 적용한다(`backend/README.md`).

| 파일 | 내용 |
|---|---|
| `schema.sql` | 테이블 33개, 파생 뷰 4개, PL/pgSQL 트리거 함수(테넌트·승인·감사 가드레일) |
| `seed_demo.sql` | 6인 로스터와 판단 기록 데모 시드 |
| `validate.py` | 테넌트 격리, 승인 상태머신, 외부 실행 차단을 포함한 **181개 회귀 검증**(psycopg) |

## 로컬 PostgreSQL (Docker)

```bash
docker run -d --name oegobanjang-pg \
  -e POSTGRES_USER=oegobanjang -e POSTGRES_PASSWORD=oegobanjang -e POSTGRES_DB=oegobanjang \
  -p 55432:5432 postgres:16
```

접속 URL: `postgresql://oegobanjang:oegobanjang@localhost:55432/oegobanjang`

> RAG 벡터 인덱스(`rag/`)는 이 서비스 DB와 분리된 전용 pgvector 컨테이너
> (`pgvector/pgvector:pg16`, 포트 55433, 스키마 `rag`)를 사용한다 — `rag/README.md` 참조.
> 인스턴스를 하나로 합치고 싶으면 위 이미지를 `pgvector/pgvector:pg16`으로 바꿔도
> 기존 사용에는 영향이 없다(상위호환).

## DBeaver에서 열기

1. PostgreSQL 연결을 만들고 Host `localhost` · Port `55432` · DB/User/PW `oegobanjang`를 입력한다.
2. 스키마가 비어 있으면 SQL 편집기에서 `schema.sql`, `seed_demo.sql`을 순서대로 실행한다
   (또는 아래 `psql`). PostgreSQL은 FK를 **항상** 강제하므로 SQLite 시절의 `foreign_keys`
   드라이버 속성 설정은 필요 없다.
3. `public` 스키마를 선택해 **View Diagram**으로 ERD를 확인한다.

`evidence_events`의 수정·삭제, 승인 삭제, 타사 데이터 연결, 승인 없는 상태 전이, `sent`/`delivered`
알림, outbound 메시지, PDF 기록 없는 export는 모두 실패해야 정상이다(트리거가 차단).

## psql로 로드

```bash
export DATABASE_URL="postgresql://oegobanjang:oegobanjang@localhost:55432/oegobanjang"
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/schema.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/seed_demo.sql
```

## 검증

`validate.py`는 backend와 무관하게 DDL 자체를 직접 검증하려고 uv 인라인 의존성(psycopg)으로 독립 실행한다:

```bash
DATABASE_URL="postgresql://oegobanjang:oegobanjang@localhost:55432/oegobanjang" \
  uv run --no-project --with "psycopg[binary]" python db/validate.py --reset
```

`--reset`을 명시한 경우에만 validate는 대상 스키마를 drop/recreate한 뒤 `schema.sql`·`seed_demo.sql`을 실행하고 181개 회귀를
검사한다. 마지막 줄은 `Result: PASS 178 / FAIL 0`이어야 한다. (Windows 콘솔에서 한글 출력이
깨지면 `PYTHONIOENCODING=utf-8`을 앞에 붙인다.)

## 편집 규칙

- 정본은 `docs/DB_SCHEMA.md`다. 스키마를 바꾸면 문서·DDL·시드·검증을 같은 PR에서 갱신한다.
- 안전성 규칙 중 FK/CHECK로 표현 못 하는 것은 트리거 함수로 강제한다(파일 하단). 트리거 함수의
  `RAISE EXCEPTION` 메시지는 검증 스크립트가 substring으로 매칭하므로 문구를 임의로 바꾸지 않는다.
  PostgreSQL은 BEGINNING 트리거를 이름 알파벳순으로 발화하므로(SQLite는 생성순), 가드 트리거는
  catch-all보다 먼저 발화하도록 이름을 지었다(link < reopen < state).
- 시드 PK는 가독성을 위한 별칭이다. 실제 서비스 PK는 UUIDv7을 사용한다.
- 루트 `backend/`(SQLAlchemy/Alembic)가 이 `db/schema.sql`을 그대로 적용해 스키마 동등성을
  유지한다(`backend/tests/test_ddl_parity.py`) — 스키마를 바꾸면 이 리포지토리도 함께 갱신·재검증한다.
