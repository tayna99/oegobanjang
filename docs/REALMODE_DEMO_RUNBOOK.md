# real 모드 데모 런북 (VITE_API_MODE=real)

> 목적: mock이 아닌 **실제 backend + PostgreSQL + rag 서비스**로 8단계 데모 대본을 재현하기
> 위한 사전 절차. 기본 데모는 mock 모드(`npm run dev`만)로 충분하다 — 이 런북은 영속성·인증·
> 서버 강제(행정사 링크 만료 등)를 실제로 보여줘야 할 때만 쓴다.
>
> 시드 정본: `db/seed_reference.sql`(전역 근거·서류 요건, 전 환경 필수) + `db/seed_demo.sql`
> (6인 로스터·케이스·승인, 데모만). 로드 순서·드리프트 복구는 `db/README.md` 참조.

## 0. 전제
- Docker(로컬 PostgreSQL `oegobanjang-pg:55432`), `uv`, Node 22(포터블 경로는 메모리 참조).
- 세 프로세스를 각각 띄운다: PostgreSQL(55432) · backend(8000) · rag(8100) · frontend(vite).

## 1. DB 준비 (스키마 + 시드)
```bash
# 컨테이너가 없으면 db/README.md의 docker run으로 먼저 띄운다.
cd backend
uv run alembic upgrade head            # db/schema.sql 적용 + alembic_version 스탬프
# 시드 로드(스키마는 이미 있으므로 --reset 없이 reference→demo만):
cd ..
DATABASE_URL="postgresql://oegobanjang:oegobanjang@localhost:55432/oegobanjang" \
  uv run --no-project --with "psycopg[binary]" python db/load.py --with-demo
```
> dev 컨테이너의 `alembic_version`이 실제 스키마와 어긋나면(과거 미완료 마이그레이션 흔적)
> 위 `upgrade head`가 "이미 최신"으로 오판할 수 있다 — `db/README.md`의 **드리프트 복구 절차**로
> 먼저 대조/재구축한 뒤 진행한다.

## 2. rag 서비스 기동 (4막 커맨드 런에 필요)
4막의 커맨드 바 런은 `POST /api/v1/runs/stream`이고, 이는 backend가 rag `/intent`·`/graph/run`을
호출하는 2-phase다(`plans/BACKEND_CONNECT.md` B3'). rag가 없으면 그 런은 `failed`가 된다.
```bash
cd rag
uv run python -m oe_rag.cli index --embedding-provider deterministic --reset   # 최초 1회 색인
uv run uvicorn oe_rag.api:app --port 8100
curl http://127.0.0.1:8100/health      # {"status":"ok"} 확인
```

## 3. backend 기동
```bash
cd backend
uv run uvicorn app.main:app --port 8000
```

## 4. frontend (real 모드)
```bash
cp .env.example .env.local             # 그리고 VITE_API_MODE=real 로 바꾼다
npm run dev
```
> `.env.local`은 vitest에는 새어들지 않도록 `config.ts`가 `MODE!=='test'` 가드를 둔다 — 테스트는
> 항상 mock이다(R2.1 노트). 즉 이 파일이 있어도 `npm run verify`는 mock 세계관으로 돈다.

## 5. 로그인 (시드 계정 OTP)
데모 계정(`db/seed_demo.sql`): 전화번호 → 역할
- `010-0000-0001` 김담당(manager) · `010-0000-0002` 박주임(manager)
- `010-0000-0003` 김대표(owner) · `010-0000-0004` 이대표(owner) · `010-0000-0005` 최감사(viewer)

OTP는 로컬 모드에서 요청 응답에 `debug_code`가 담긴다(`backend/app/api/v1/auth.py`, `is_local`).
승인 PIN은 세 결정자(김담당·박주임·김대표·이대표) 모두 데모값 **`1234`**(pin_hash 시드).
최감사는 viewer라 승인 불가(pin_hash NULL) — viewer 라우트 가드 데모용.

## 6. 행정사 링크 (시드가 아니라 발급 API를 대본 스텝으로)
링크 토큰은 발급마다 회전하므로 시드하지 않는다(R2.6 원칙). 대신 대본에서 직접 발급한다 —
전제조건(케이스의 `create_handoff` 승인)은 시드 `apv_batbayar_export`(approved)가 이미 충족한다.
```bash
# manager/owner 세션 토큰으로:
curl -X POST http://localhost:8000/api/v1/packages/cs_batbayar/link \
  -H "Authorization: Bearer <session_token>"
# 응답의 link_token으로 무인증 열람 화면 진입: /link/<link_token>
```
`/link/<token>`은 real 모드에서 서버 만료 판정을 따른다(만료·미발급·대상없음 모두 404 — 존재 비노출).

## 7. 이번 시드로 재현되는 것 / 여전히 mock으로 남는 것
- **재현됨**: 로그인·세션·역할 파생(김담당 manager, 최감사 viewer 가드), 케이스/브리핑/스레드
  읽기(서버), 승인/반려 결정(PIN 서버 검증), evidence 서버 영속화, 행정사 링크 서버 만료.
- **mock 유지(문서화된 경계)**: 케이스 상세 콘텐츠(`CASE_SHEETS`), 초안 본문(`DRAFTS`), 런 각본
  (`RUN_CONFIGS` — replay는 영구 mock), 발송 실행(mock 어댑터), 패키지 문서 콘텐츠, 행정사
  구조화된 회신(엔드포인트 없음 — real 모드는 "준비 중" 안내), 화이트라벨 개인 계정,
  KPI 필러(평균 승인 소요·주간 실행). 이들은 SD-3~SD-7 배선 트랙 몫이다(`plans/ROADMAP.md` SD 트랙).
