# db/ 설계 킷

`docs/DB_SCHEMA.md`의 서비스 DB 계약을 **PostgreSQL**에서 실행·검증하는 산출물이다.
서비스 DB는 PostgreSQL 16+로 확정됐다(단일 방언 — SQLite 설계 킷은 은퇴). `db/schema.sql`이 정본
DDL이며, 루트 `backend/`의 Alembic 0001이 이 파일을 그대로 적용한다(`backend/README.md`).

| 파일 | 내용 |
|---|---|
| `schema.sql` | 테이블 41개(R3 outbox·R5.1 행정사 화이트라벨 7종·R5.4 알림 확장 포함), 파생 뷰 4개, PL/pgSQL 트리거 함수(테넌트·승인·감사 가드레일) |
| `seed_reference.sql` | **전역 참조 시드(모든 환경 필수)** — 전역 A/B 근거·`document_requirements`. 빈 DB에서도 승인 근거 게이트·룰 엔진이 동작하려면 반드시 있어야 한다 |
| `seed_demo.sql` | 6인 로스터·판단 기록 **데모 시드(로컬·데모만)** — `seed_reference.sql` 뒤에 로드 |
| `load.py` | `schema → reference → demo`를 순서대로 로드하는 러너(psql 없이 uv 인라인 psycopg) |
| `validate.py` | 테넌트 격리, 승인 상태머신, 외부 실행 차단, 참조 시드 불변식을 포함한 **211개 회귀 검증**(psycopg) |

## 로드 순서 계약 (중요)

시드는 세 단계로, 이 순서를 반드시 지킨다:

1. `schema.sql` — 모든 환경.
2. `seed_reference.sql` — **모든 환경 필수**. 전역 A/B 근거·`document_requirements`(회사에 매이지 않는 전역 참조). 이게 비면 근거 라이브러리가 비고 승인 citation-lock이 항상 잠기며, 룰 엔진이 서류 요건 0으로 공전한다.
3. `seed_demo.sql` — **데모·로컬만**. 6인 로스터·케이스·승인 등 테넌트 데이터. `seed_reference.sql`이 넣은 전역 근거(cit_001~011)에 FK로 물린다.

> 시드는 Alembic 마이그레이션 **밖**이다(Alembic=스키마 단일 진실). 환경별로 데모 유무를 고를 수 있게 하기 위함이다 — 프로덕션은 1·2단계만, 로컬·데모는 3단계까지.

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
2. 스키마가 비어 있으면 SQL 편집기에서 `schema.sql`, `seed_reference.sql`, `seed_demo.sql`을
   순서대로 실행한다(또는 아래 `db/load.py`/`psql`). PostgreSQL은 FK를 **항상** 강제하므로
   SQLite 시절의 `foreign_keys` 드라이버 속성 설정은 필요 없다.
3. `public` 스키마를 선택해 **View Diagram**으로 ERD를 확인한다.

`evidence_events`의 수정·삭제, 승인 삭제, 타사 데이터 연결, 승인 없는 상태 전이, `sent`/`delivered`
알림, outbound 메시지, PDF 기록 없는 export는 모두 실패해야 정상이다(트리거가 차단).

## 로드 (`db/load.py` — psql 불필요, 권장)

Windows 로컬에 psql 클라이언트가 없어도 되도록 uv 인라인 psycopg로 순서대로 로드한다:

```bash
export DATABASE_URL="postgresql://oegobanjang:oegobanjang@localhost:55432/oegobanjang"
# 프로덕션 부트스트랩 근사 (schema + reference)
uv run --no-project --with "psycopg[binary]" python db/load.py --reset --reference-only
# 로컬·데모 (schema + reference + demo)
uv run --no-project --with "psycopg[binary]" python db/load.py --reset --with-demo
```

## psql로 로드 (대안)

```bash
export DATABASE_URL="postgresql://oegobanjang:oegobanjang@localhost:55432/oegobanjang"
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/schema.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/seed_reference.sql   # 전 환경 필수
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/seed_demo.sql        # 데모·로컬만
```

## 검증

`validate.py`는 backend와 무관하게 DDL 자체를 직접 검증하려고 uv 인라인 의존성(psycopg)으로 독립 실행한다:

```bash
DATABASE_URL="postgresql://oegobanjang:oegobanjang@localhost:55432/oegobanjang" \
  uv run --no-project --with "psycopg[binary]" python db/validate.py --reset
```

`--reset`을 명시한 경우에만 validate는 대상 스키마를 drop/recreate한 뒤 `schema.sql`·`seed_reference.sql`·
`seed_demo.sql`을 실행하고 211개 회귀를 검사한다. 마지막 줄은 `Result: PASS 211 / FAIL 0`이어야 한다.
(Windows 콘솔에서 한글 출력이 깨지면 `PYTHONIOENCODING=utf-8`을 앞에 붙인다.)

> **주의**: validate는 대상 DB의 `public` 스키마를 drop한다. dev 컨테이너(`oegobanjang-pg`의
> `oegobanjang` DB)의 시드 데이터를 보존하려면 별도 disposable DB를 쓴다 —
> `docker exec oegobanjang-pg createdb -U oegobanjang ogb_seed_validate` 후 그 DB로 `DATABASE_URL`을 지정.

## alembic_version 드리프트 복구 (dev 컨테이너)

이전 세션의 미완료 마이그레이션 흔적으로 dev 컨테이너(`oegobanjang-pg:55432`)의
`alembic_version`이 실제 스키마와 어긋날 수 있다(예: 커밋된 적 없는 `'0002'` 미아).
그대로 `alembic upgrade head`를 돌리면 revision 문자열이 우연히 겹쳐 "이미 최신"으로
오판돼 실제 ALTER가 적용 안 될 위험이 있다. 복구 절차:

1. **현재 상태 확인**: `SELECT version_num FROM alembic_version;`
2. **실스키마 지표 대조**(리비전이 실제 적용됐는지):
   - `0002`(R2.5/2.6): `evidence_events` CHECK에 `approval_rejected`·`dispatch_executed`가 있고
     `handoff_packages`에 `link_issued_at`·`link_expires_at` 컬럼이 있는가.
   - `0003`(R2.4): `trg_approvals_decider_role` 함수 소스에 delegation OR-arm이 있는가.
3. **불일치 시 재구축이 정본**(dev 데이터는 시드가 전부라 stamp 조작보다 재구축이 안전·저렴):
   `db/load.py --reset --with-demo` → 필요 시 `alembic stamp head`.
   실서버(운영) DB에는 이 재구축을 절대 쓰지 않는다 — 운영은 `alembic upgrade`만.

## 편집 규칙

- 정본은 `docs/DB_SCHEMA.md`다. 스키마를 바꾸면 문서·DDL·시드·검증을 같은 PR에서 갱신한다.
- 안전성 규칙 중 FK/CHECK로 표현 못 하는 것은 트리거 함수로 강제한다(파일 하단). 트리거 함수의
  `RAISE EXCEPTION` 메시지는 검증 스크립트가 substring으로 매칭하므로 문구를 임의로 바꾸지 않는다.
  PostgreSQL은 BEGINNING 트리거를 이름 알파벳순으로 발화하므로(SQLite는 생성순), 가드 트리거는
  catch-all보다 먼저 발화하도록 이름을 지었다(link < reopen < state).
- 시드 PK는 가독성을 위한 별칭이다. 실제 서비스 PK는 UUIDv7을 사용한다.
- 루트 `backend/`(SQLAlchemy/Alembic)가 이 `db/schema.sql`을 그대로 적용해 스키마 동등성을
  유지한다(`backend/tests/test_ddl_parity.py`) — 스키마를 바꾸면 이 리포지토리도 함께 갱신·재검증한다.
