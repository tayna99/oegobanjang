# 데이터 생성 및 파이프라인 구조 보고서

**기준일**: 2026-05-06
**상태**: Phase 1 운영 seed + Phase 2 법령/RAG 초안 + 다국어 Contact 데이터셋 반영

---

## 1. 현재 데이터 폴더 구조

```txt
data-pipeline/
├─ crawlers/
│  ├─ law_crawler.py
│  ├─ eps_crawler.py
│  ├─ gov24_crawler.py
│  └─ hrd_crawler.py
├─ loaders/
├─ metadata/
│  └─ multilingual_source_registry.jsonl
├─ normalizers/
├─ processed/
│  └─ chunks/
│     ├─ all_chunks.jsonl
│     ├─ case_chunks.jsonl
│     ├─ chroma_records.jsonl
│     ├─ form_chunks.jsonl
│     ├─ general_chunks.jsonl
│     ├─ policy_chunks.jsonl
│     ├─ procedure_chunks.jsonl
│     ├─ regulation_chunks.jsonl
│     ├─ safety_chunks.jsonl
│     ├─ template_chunks.jsonl
│     └─ multilingual_contact/
├─ raw/
│  ├─ laws/
│  ├─ public_cases/
│  ├─ synthetic_cases/
│  └─ templates/
│     ├─ messages/
│     │  ├─ id/
│     │  └─ vi/
│     └─ worker_replies/
│        ├─ id/
│        └─ vi/
├─ seed/
└─ splitters/
```

로컬 생성물로 `data-pipeline/index/chroma/multilingual_contact/`가 존재하지만, Chroma 인덱스는 재생성 가능한 산출물이므로 `.gitignore` 대상이다.

---

## 2. Seed 데이터

`data-pipeline/seed/`

| 파일 | 라인 수 | 설명 |
|---|---:|---|
| `companies.csv` | 6 | 사업장 seed |
| `workers.csv` | 31 | 근로자 seed |
| `visas.csv` | 31 | 비자/체류 상태 seed |
| `worker_documents.csv` | 45 | 근로자별 서류 상태 seed |
| `document_requirements.csv` | 23 | 케이스/비자별 필수 서류 기준 |
| `visa_lookup.csv` | 6 | 비자 유형 lookup |
| `country_lookup.csv` | 3 | MVP 언어 범위. `vi` end-to-end, `id` message demo |
| `counseling_centers.csv` | 4 | 상담센터 seed |
| `message_templates.csv` | 23 | 다국어 Contact Agent용 상세 메시지 템플릿 |
| `message_templates.jsonl` | 6 | 기본 메시지 템플릿 JSONL |
| `public_case_patterns.jsonl` | 19 | 공개/참고 사례 패턴 |
| `interview_case_patterns.jsonl` | 9 | 인터뷰성 사례 패턴 |
| `synthetic_cases.jsonl` | 22 | 합성 평가/데모 사례 |
| `sample_policy_docs.jsonl` | 5 | RAG 샘플 정책 문서 |
| `sample_required_docs.jsonl` | 0 | placeholder |

### 현재 MVP 언어 범위

```txt
Vietnam / vi      = end_to_end
Indonesia / id   = message_generation_demo
```

기존의 다국가 전체 확장 데이터보다, 현재는 다국어 Contact MVP 검증을 위해 `vi`, `id` 중심으로 축소되어 있다.

---

## 3. Raw 데이터

### 3.1 법령 raw

`data-pipeline/raw/laws/`

| 파일 | 라인 수 | 설명 |
|---|---:|---|
| `출입국관리법.jsonl` | 188 | 법령 raw |
| `출입국관리법_시행령.jsonl` | 185 | 시행령 raw |
| `출입국관리법_시행규칙.jsonl` | 191 | 시행규칙 raw |
| `외국인근로자고용법.jsonl` | 44 | 법령 raw |
| `외국인근로자고용법_시행령.jsonl` | 43 | 시행령 raw |
| `외국인근로자고용법_시행규칙.jsonl` | 32 | 시행규칙 raw |

### 3.2 다국어 Contact raw

| 경로 | 파일 수 | 설명 |
|---|---:|---|
| `raw/templates/messages/id/` | 5 | 인도네시아어 메시지 템플릿 원문 |
| `raw/templates/messages/vi/` | 5 | 베트남어 메시지 템플릿 원문 |
| `raw/templates/worker_replies/id/` | 10 | 인도네시아어 근로자 답변 샘플 |
| `raw/templates/worker_replies/vi/` | 10 | 베트남어 근로자 답변 샘플 |
| `raw/public_cases/` | 4 | 공개/참고 사례 md |
| `raw/synthetic_cases/` | 5 | 합성 end-to-end 사례 md |

`raw/life_guides/`, `raw/safety/`는 수집 원본 캡처 성격이 강해 현재 `.gitignore` 대상이다. 커밋에는 processed chunks와 metadata 중심으로 남긴다.

---

## 4. Processed chunks

### 4.1 기본 RAG chunks

`data-pipeline/processed/chunks/`

| 파일 | 라인 수 | 설명 |
|---|---:|---|
| `all_chunks.jsonl` | 27 | 기본 RAG 전체 chunk |
| `policy_chunks.jsonl` | 10 | 정책/절차성 chunk |
| `form_chunks.jsonl` | 22 | 서식/필드성 chunk |
| `template_chunks.jsonl` | 3 | 메시지 템플릿 chunk |
| `case_chunks.jsonl` | 2 | 사례 chunk |
| `chroma_records.jsonl` | 10 | Chroma 적재용 record |
| `general_chunks.jsonl` | 0 | placeholder |
| `procedure_chunks.jsonl` | 0 | placeholder |
| `regulation_chunks.jsonl` | 0 | placeholder |
| `safety_chunks.jsonl` | 0 | placeholder |

### 4.2 다국어 Contact chunks

`data-pipeline/processed/chunks/multilingual_contact/`

| 파일 | 라인 수 | 설명 |
|---|---:|---|
| `all_chunks.jsonl` | 1022 | 다국어 Contact 전체 chunk |
| `counseling_chunks.jsonl` | 327 | 상담센터/지원기관 안내 |
| `safety_chunks.jsonl` | 450 | 안전교육/안전 안내 |
| `notice_chunks.jsonl` | 157 | 고용/공지/절차 안내 |
| `life_chunks.jsonl` | 88 | 생활 안내 |
| `general_chunks.jsonl` | 0 | placeholder |

다국어 Contact RAG는 `rag_domain=multilingual_contact`, `owner_agent=multilingual_contact_agent`, `ingest_target=true` 메타데이터를 기준으로 필터링한다.

---

## 5. Metadata

`data-pipeline/metadata/multilingual_source_registry.jsonl`

- 다국어 Contact RAG source registry.
- source별 `source_id`, `publisher`, `doc_type`, `evidence_grade`, `language`, `use_case`, `ingest_target` 등을 관리한다.
- 합성/공개 사례와 템플릿은 공식 법적 근거로 쓰지 않도록 `not_for_legal_basis` 또는 낮은 evidence grade를 사용한다.

---

## 6. Scripts / Crawlers

### Crawlers

| 파일 | 상태 |
|---|---|
| `data-pipeline/crawlers/law_crawler.py` | 구현됨. 법령 JSONL 수집용 |
| `data-pipeline/crawlers/eps_crawler.py` | placeholder |
| `data-pipeline/crawlers/gov24_crawler.py` | placeholder |
| `data-pipeline/crawlers/hrd_crawler.py` | placeholder |

### Scripts

| 파일 | 설명 |
|---|---|
| `scripts/ingest_rag_docs.py` | 기본 RAG 문서 ingest |
| `scripts/ingest_multilingual_contact_rag.py` | 다국어 Contact raw/metadata 기반 chunk 생성 |
| `scripts/index_multilingual_contact_chroma.py` | 다국어 Contact Chroma index 생성 |
| `scripts/query_multilingual_contact_chroma.py` | 다국어 Contact Chroma 질의 확인 |
| `scripts/run_evals.py` | eval dataset 구조 검증 |
| `scripts/eval_runner.py` | Phase 3 eval runner |

---

## 7. Ignore / 커밋 제외 대상

아래는 로컬 생성물 또는 재생성 가능한 산출물이라 커밋하지 않는다.

```txt
data-pipeline/cache/
data-pipeline/index/
evals/reports/*.json
data-pipeline/raw/life_guides/
data-pipeline/raw/safety/
backend/data/*.sqlite3
backend/data/*.sqlite
backend/data/*.db
```

현재 로컬에는 `data-pipeline/index/chroma/multilingual_contact/`와 `backend/data/oegobanjang.sqlite3`가 있을 수 있지만, 둘 다 ignore 대상이다.

---

## 8. 현재 검증 상태

최근 확인된 주요 검증:

```bash
uv run pytest backend/tests
# 44 passed

uv run python scripts/run_evals.py --dataset safety_guardrail_cases
uv run python scripts/run_evals.py --dataset message_generation_cases
uv run python scripts/run_evals.py --dataset workflow_e2e_cases
# Total issues: 0
```

SQLite 저장 기능을 쓰는 로컬 환경에서는 backend 기준으로 migration을 먼저 적용한다.

```bash
cd backend
uv run python -m alembic upgrade head
```

---

## 9. 완료 체크리스트

- [x] 운영 seed CSV 생성
- [x] 기본 메시지 템플릿 JSONL 생성
- [x] 다국어 Contact 메시지 템플릿 CSV 생성
- [x] 베트남어/인도네시아어 메시지 raw template 생성
- [x] 베트남어/인도네시아어 worker reply 샘플 생성
- [x] 법령 raw JSONL 수집
- [x] 기본 RAG chunk 생성
- [x] 다국어 Contact chunk 생성
- [x] 다국어 Contact source registry 생성
- [x] Chroma index 생성 스크립트 작성
- [x] 로컬 Chroma index는 ignore 처리
- [x] 로컬 SQLite DB는 ignore 처리

---

## 10. 다음 단계

1. `eps_crawler.py`, `gov24_crawler.py`, `hrd_crawler.py` 실제 수집 구현
2. `procedure_chunks.jsonl`, `regulation_chunks.jsonl`, `safety_chunks.jsonl` 기본 RAG chunk 보강
3. 다국어 Contact RAG source registry의 공식 URL/effective date 보강
4. workers 테이블/조회 API와 `worker_name → worker_id` lookup 연결
5. approval approve/reject API endpoint 연결

---

## 11. 주의사항

- RAG는 공식 근거와 절차를 찾는 용도이며, 비자 가능 여부를 확정하지 않는다.
- 합성 데이터와 public case pattern은 데모/평가/패턴 참고용이며 공식 법적 근거로 사용하지 않는다.
- Evidence Log에는 메시지 전문, worker reply 원문, 민감정보 원문을 저장하지 않는다.
- `persist_result=true` 저장 결과도 발송/상태 확정이 아니라 approval pending 또는 approved/rejected 상태 전환까지만 다룬다.
