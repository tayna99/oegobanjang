# Mission 004: Chroma ↔ citations 동기화

## Goal

`legacy/backend/app/agent_runtime/rag/`에 있는 Chroma 벡터 저장소 인제스트·검색 자산을,
현행 `backend/`(PostgreSQL, `docs/DB_SCHEMA.md`)의 `citations` 테이블과 동기화되는 형태로
이관한다. 목표는 실 RAG 검색 API를 완성하는 것이 아니라, Chroma에 있는 근거 메타데이터가
`citations` 테이블(및 그 파생 뷰 `v_global_usable_citations`)과 어긋나지 않게 만드는
**동기화 파이프라인**이다.

이 mission은 `CLAUDE.md`의 "Agent Runtime 관련 코드는 복구/이관 mission이 명시된 경우에만
수정합니다(`legacy/backend/app/agent_runtime/`)" 게이트를 여는 문서다 — 이 문서 자체는
코드를 수정하지 않는다.

---

## Required Reading

```txt
CLAUDE.md
AGENTS.md
docs/DB_SCHEMA.md          §4.4(citations)·§8(프론트 계약 매핑)·§13-13/14(관련 결정 선례)
db/schema.sql              citations·case_citations 테이블 DDL, v_global_usable_citations 뷰
legacy/docs/RAG_STRATEGY.md
legacy/docs/DB_SCHEMA.md   (레거시 citations 설계 — 현행과 대조용)
```

---

## Context (왜 지금 이 mission을 여는가)

- `docs/DB_SCHEMA.md`가 명시: "Chroma(벡터 저장소)는 이 문서 범위 밖. service DB와의 접점은
  `citations` 한 테이블(§4.4)뿐이다." — 즉 스키마 설계는 이미 Chroma와의 접점을 `citations`
  하나로 좁혀뒀다. 이 mission은 그 접점을 실제로 채우는 작업이다.
- 현행 `backend/`(PostgreSQL, 승인/인증/읽기 API까지 구현됨)에는 RAG/Chroma 코드가 전혀 없다
  — `legacy/backend/app/agent_runtime/rag/`에만 존재하며 새 `backend/`로 이관된 적 없다.
- `citations` 테이블은 이미 시드 데이터(9건, `db/seed_demo.sql`)로 채워져 있고 `grade`
  (A/B/C/E/F)·`status`·`company_id`(NULL=전역) 컬럼으로 스코프된다 — Chroma 쪽 메타데이터가
  이 컬럼들과 대응돼야 "사용 가능 근거"(`grade != 'F'`) 판정이 두 시스템에서 일관된다.

---

## Target Files (제안 — mission 착수 시 재검토)

```txt
legacy/backend/app/agent_runtime/rag/vector_store.py            # 참고 — Chroma 클라이언트 초기화 패턴
legacy/backend/app/agent_runtime/rag/workforce_source_importer.py  # 참고 — import_workforce_sources 계열
legacy/backend/app/agent_runtime/rag/workforce_metadata.py      # 참고 — 메타데이터 스키마
legacy/scripts/index_workforce_chroma.py                        # 참고 — 인제스트 스크립트 구조

backend/app/services/citations_sync.py      # 신규 — Chroma 메타데이터 → citations upsert
backend/app/models/citation.py               # 기존(Citation, CaseCitation) — 필드 매핑 확인
backend/tests/test_citations_sync.py         # 신규
```

---

## Scope

- Chroma 컬렉션의 각 문서 메타데이터(출처·grade·title 등)를 `citations` 테이블 행으로
  upsert하는 동기화 스크립트/서비스 함수.
- 동기화는 **일방향**(Chroma → citations)으로 시작한다 — `citations`을 Chroma에 되쓰지 않는다.
- `grade`/`status`/`company_id` 매핑 규칙을 정의하고 문서화한다(`docs/DB_SCHEMA.md`에 반영).
- 멱등성: 같은 소스를 재실행해도 중복 행이 생기지 않아야 한다(자연키 또는 외부 id 기준 upsert).

## Out of Scope (명시적으로 이번엔 안 함)

- 실 RAG 검색 API(`/api/v1/citations/search` 류)는 별도 후속 mission.
- Chroma 인덱스 재구축·임베딩 모델 변경.
- `legacy/backend/app/agent_runtime/` 전체(그래프·에이전트 노드 등) 이관 — Mission 001 범위.
- 근로자 개인 메시지·RAG 응답 생성 — PII/안전 경계 밖.

## Acceptance Criteria

- 동기화 실행 후 `citations` 행 수·grade 분포가 예상과 일치한다(테스트로 검증).
- 재실행해도 결과가 안정적이다(멱등).
- `v_global_usable_citations`(grade≠'F')로 조회했을 때 Chroma의 "사용 가능" 판정과 어긋나지
  않는다.
- 기존 `db/validate.py`(178개)·backend pytest가 계속 통과한다(회귀 없음).

---

## Human Review Checklist

- [ ] Chroma→citations 매핑 규칙이 `docs/DB_SCHEMA.md`에 문서화됐는가?
- [ ] 동기화가 멱등한가(같은 소스 재실행 시 중복 없음)?
- [ ] `company_id` 스코프(전역 vs 자사)가 올바르게 매핑되는가?
- [ ] 원문(근로자 개인정보 등)이 citations에 섞여 들어가지 않는가?
- [ ] 기존 검증(validate.py·pytest)이 회귀 없이 통과하는가?
