# db/ — DBeaver 설계 킷

`docs/DB_SCHEMA.md`(설계 정본)를 DBeaver에서 바로 열어 검토·실험할 수 있게 내린 실행 산출물이다.

| 파일 | 내용 |
|---|---|
| `schema.sql` | 전체 DDL — 테이블 32개 + 파생 뷰 4개 + append-only 트리거. 문서 §4를 그대로 내린 것 |
| `seed_demo.sql` | 데모 시드 — 디자인 세계관(6인 로스터·그린푸드 제조·판단 기록 #4712~#4797) |
| `validate.cjs` | 스키마+시드 실행 후 가드레일 30항목 검증(트리거·CHECK·부분 유니크·파생 뷰) |
| `oegobanjang_design.sqlite3` | 생성 산출물 — **git 미추적**(재생성 가능). 없으면 아래 재생성 |

## DBeaver에서 열기

1. **데이터베이스 → 새 데이터베이스 연결 → SQLite**
2. Path에 `<repo>/db/oegobanjang_design.sqlite3` 지정 (파일이 없으면 아래 "재생성" 먼저, 또는 DBeaver가 만든 빈 파일에 SQL 편집기로 `schema.sql` → `seed_demo.sql` 순서 실행)
3. **연결 편집 → Driver properties → `foreign_keys` = `true`** — SQLite FK 강제는 연결 단위라 이 설정이 없으면 참조 무결성이 꺼진 채 열린다
4. ERD: 연결 트리에서 데이터베이스(또는 Tables) 우클릭 → **View Diagram**
5. 편하게 실험해도 된다 — 단, `evidence_events`는 append-only 트리거 때문에 그리드에서 행 수정·삭제가 **실패하는 것이 정상**이고, `drafts.sent_at` 채우기·일괄 승인 같은 조작도 CHECK가 막는다(설계가 곧 가드레일)

## 재생성·검증

```bash
node --experimental-sqlite db/validate.cjs
```

DB 파일을 새로 만들고(기존 파일 삭제) 스키마·시드를 실행한 뒤 30개 항목을 검사한다. 마지막 줄이 `PASS 30 / FAIL 0`이어야 한다.
이 저장소 개발 머신에는 Node가 포터블로 설치돼 있다(`%LOCALAPPDATA%/nodejs-portable/node-v22.14.0-win-x64` — plans/HANDOFF.md 2.5.1 기록). Node 23.4+는 플래그 없이 실행된다.

## 편집 규칙

- **정본은 `docs/DB_SCHEMA.md`다.** DBeaver나 이 파일들에서 실험한 변경을 확정하려면 문서 §4와 `schema.sql`을 **같은 PR에서 함께** 고치고 `validate.cjs`를 다시 통과시킨다.
- 시드의 PK는 가독성용 슬러그(`cs_nguyen` 등)다 — 실서비스 PK는 UUIDv7(문서 §2).
- `*.sqlite3`는 커밋하지 않는다(.gitignore 등재).
