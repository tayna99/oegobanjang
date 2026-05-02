# Missions

이 폴더는 외고반장 프로젝트의 작업 단위를 관리한다.

mission은 사람 개발자와 AI Agent가 같은 범위 안에서 작업하도록 만드는 작업 지시서다.

---

## 1. 폴더 구조

```txt
missions/
├─ README.md
├─ active/
└─ completed/
```

---

## 2. active

현재 진행 중이거나 앞으로 진행할 작업을 둔다.

각 mission은 가능하면 하나의 PR 단위로 작업한다.

---

## 3. completed

완료된 mission을 보관한다.

완료된 mission은 필요하면 `active/`에서 `completed/`로 이동한다.

---

## 4. mission 작성 형식

모든 mission은 아래 형식을 따른다.

```md
# Mission XXX: 제목

## Goal

## Required Reading

## Target Files

## Scope

## Out of Scope

## Acceptance Criteria

## Verification Commands

## Human Review Checklist
```

---

## 5. 작업 원칙

- mission의 Scope 밖 파일은 수정하지 않는다.
- 구현 전 관련 docs를 먼저 읽는다.
- 금지 작업과 승인 필요 작업을 구분한다.
- 테스트 또는 eval 기준을 포함한다.
- Evidence Log 영향이 있으면 명시한다.

---

## 6. 현재 Mission 목록

| 파일 | 목적 |
|---|---|
| `001-agent-runtime-skeleton.md` | Agent Runtime 최소 실행 흐름 |
| `002-rag-indexing.md` | RAG 데이터 수집/전처리/인덱싱 |
| `003-approval-evidence-log.md` | 승인 흐름과 Evidence Log |
| `004-backend-core-api.md` | FastAPI 핵심 API |
| `005-frontend-dashboard.md` | 관리자 대시보드 |