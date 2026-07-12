# db/ 설계 킷

`docs/DB_SCHEMA.md`의 서비스 DB 계약을 SQLite에서 실행·검증하는 산출물이다.

| 파일 | 내용 |
|---|---|
| `schema.sql` | 테이블 31개, 파생 뷰 4개, 테넌트·승인·감사 가드레일 |
| `seed_demo.sql` | 6인 로스터와 판단 기록 데모 시드 |
| `validate.cjs` | 테넌트 격리, 승인 상태, 외부 실행 차단을 포함한 145개 회귀 검증 |
| `oegobanjang_design.sqlite3` | 재생성 가능한 Git 미추적 산출물 |

## DBeaver에서 열기

1. SQLite 연결을 만들고 `<repo>/db/oegobanjang_design.sqlite3`를 지정한다.
2. 파일이 없으면 `schema.sql`, `seed_demo.sql` 순서로 실행한다.
3. 연결별 Driver property에서 `foreign_keys=true`를 설정한다. SQLite FK 강제는 연결 단위이므로 이 설정이 꺼지면 복합 테넌트 FK가 작동하지 않는다.
4. 테이블을 선택해 **View Diagram**으로 ERD를 확인한다.

`evidence_events`의 수정·삭제, 타사 데이터 연결, 승인 없는 상태 전이, `sent`/`delivered` 알림, outbound 메시지, 외부 패키지 링크는 모두 실패해야 정상이다.

## 재생성·검증

```bash
node --experimental-sqlite db/validate.cjs
```

검증은 설계 DB를 재생성한 뒤 스키마와 시드를 실행한다. 마지막 줄은 `Result: PASS 145 / FAIL 0`이어야 한다. Node 23.4+에서는 `--experimental-sqlite` 없이도 실행할 수 있다.

## 편집 규칙

- 정본은 `docs/DB_SCHEMA.md`다. 스키마를 바꾸면 문서·DDL·시드·검증을 같은 PR에서 갱신한다.
- 모든 서비스 DB 연결은 생성 직후 `PRAGMA foreign_keys=ON`을 적용하고, 활성 상태를 검사한다. 실제 SQLAlchemy/Alembic 이관에서도 연결 훅으로 같은 계약을 유지한다.
- 시드 PK는 가독성을 위한 별칭이다. 실제 서비스 PK는 UUIDv7을 사용한다.
- `*.sqlite3` 산출물은 커밋하지 않는다.
