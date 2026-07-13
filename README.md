# 외고반장

외고반장은 외국인 고용 사업장의 체류, 고용, 서류, 다국어 소통, 비자 갱신 업무를 하나의 흐름으로 관리하는 외국인 고용 운영 OS입니다.

이 프로젝트는 비자 신청을 대행하거나 법률 판단을 자동화하지 않습니다. 공식 근거, 현재 상태, 누락 정보, 메시지 초안, 전문가 검토 패키지를 정리해 담당자가 안전하게 판단하도록 돕습니다.

## 현재 MVP

루트의 운영 대상은 모바일 우선 Vite + React MVP입니다. 화면은 목업 데이터와 안전 가드레일을 사용하며, 실제 외부 발송·전달·정부 제출은 하지 않습니다.

- `src/` — 화면, 라우팅, 상태, 데모 런 엔진
- `db/` — 현행 DB 설계 DDL, 데모 시드, 독립 검증기
- `docs/`, `plans/`, `rules/` — 사양, 로드맵, 작업 규칙
- `legacy/` — 이전 백엔드·Agent Runtime·평가 자산 보관 영역

루트에는 실행 backend API 또는 migration이 없습니다. `legacy/backend/`는 보존용이며 현재 MVP의 production import 대상이 아닙니다.

## 실행과 검증

```bash
npm install
npm run dev
```

전체 프론트 MVP 검증:

```bash
npm run verify
```

## DB 설계 검증

`db/schema.sql`이 현행 실행 가능한 설계 정본입니다. 검증기는 별도의 SQLite 산출물(`db/oegobanjang_design.sqlite3`, Git 미추적)을 재생성한 뒤 DDL과 시드를 실행합니다.

```bash
node --experimental-sqlite db/validate.cjs
```

세부 규칙과 DBeaver 사용법은 [docs/DB_SCHEMA.md](docs/DB_SCHEMA.md), [db/README.md](db/README.md)를 참고합니다.

## 안전 경계

- AI는 비자 가능 여부를 확정하거나 법률·노무 자문을 하지 않습니다.
- 메시지 발송, 전문가 전달, 케이스 완료, 대외 제출용 export는 사람의 승인 전에는 실행하지 않습니다.
- MVP DB 설계는 outbound 메시지, 외부 패키지 링크, 실제 notification delivery 상태를 저장하지 않습니다.
- 승인 결정은 `pending → approved|rejected` 단방향이며, 승인 기록과 승인에 연결된 초안·패키지는 되돌리거나 교체할 수 없습니다.

## 후속 backend 이식

backend API·ORM·migration은 별도 승인 PR에서 이 DDL과 동등하게 구현합니다. 인증된 principal, 서버 측 PIN/biometric 검증, 유효한 delegation 검증이 준비되기 전에는 approve/reject endpoint를 노출하지 않습니다.
