# Mission 002: RAG Indexing

## Goal

외고반장 MVP에 필요한 공식 문서와 템플릿 데이터를 수집·전처리하고, RAG 검색에 사용할 chunk와 metadata 구조를 만든다.

RAG는 공식 근거와 절차를 찾기 위한 용도다.  
현재 직원 상태, 후보자 상태, 서류 보유 여부, D-day 계산은 DB 또는 Rule Base에서 처리한다.

---

## Required Reading

```txt
docs/RAG_STRATEGY.md
docs/TOOL_CONTRACT.md
docs/EVAL_HARNESS.md
docs/SECURITY_GUARDRAILS.md
```

---

## Target Files

```txt
data-pipeline/ingest.py

data-pipeline/crawlers/
data-pipeline/loaders/
data-pipeline/splitters/
data-pipeline/normalizers/

data-pipeline/seed/sample_policy_docs.jsonl
data-pipeline/seed/sample_required_docs.jsonl
data-pipeline/seed/document_requirements.csv

backend/app/agent_runtime/rag/retriever.py
backend/app/agent_runtime/rag/chunking.py
backend/app/agent_runtime/rag/citation.py

evals/datasets/rag_retrieval_cases.jsonl
```

---

## Scope

이번 mission에서 구현할 범위는 다음과 같다.

- 공식 문서 20~30개 수집 목록 작성
- `document_requirements.csv` 초안 작성
- RAG chunk metadata schema 정의
- 법령은 조문 단위 chunking
- 절차는 단계 단위 chunking
- 서식은 필드 단위 chunking
- 메시지 템플릿은 목적 단위 chunking
- Chroma 적재용 JSONL 생성
- retrieval eval 초안 작성

---

## Data Collection Targets

### 법령/서식

```txt
출입국관리법
출입국관리법 시행령
출입국관리법 시행규칙
외국인근로자의 고용 등에 관한 법률
외국인근로자의 고용 등에 관한 법률 시행령
외국인근로자의 고용 등에 관한 법률 시행규칙
외국인근로자 고용변동 등 신고서
고용사업장 정보변동 신고서
```

### 절차

```txt
EPS 고용허가제 소개
사업주 고용절차
고용/취업절차
허용업종 안내
고용허가 신청 관련 안내
체류기간 연장 민원 안내
```

### 안전/다국어

```txt
KOSHA 외국인 안전교육 자료
다국어 안전표지
외국인력상담센터 안내
```

---

## Metadata Required Fields

모든 chunk에는 아래 필드를 포함한다.

```json
{
  "source_id": "string",
  "title": "string",
  "publisher": "string",
  "source_type": "official_law | official_procedure | official_form | safety_guide | message_template | synthetic_case",
  "url": "string",
  "retrieved_at": "YYYY-MM-DD",
  "effective_date": "YYYY-MM-DD | null",
  "doc_type": "law | procedure | form | safety | template | case",
  "mission_agent": [],
  "visa_type": [],
  "country": [],
  "industry": [],
  "risk_level": "low | medium | high",
  "evidence_grade": "A | B | C | D | E | F"
}
```

---

## Evidence Grade Rules

| Grade | 의미 | 답변 근거 사용 |
|---|---|---|
| A | 법령/정부 공식 문서 | 가능 |
| B | 공공기관/공식 절차 안내 | 가능 |
| C | 공공데이터/통계 | 시장 분석용 |
| D | 센터 상담사례/참고자료 | 참고용 |
| E | 내부 템플릿 | 승인 템플릿으로 가능 |
| F | 합성 데이터 | 데모/평가용, 공식 근거 불가 |

---

## Out of Scope

이번 mission에서 구현하지 않는다.

- 모든 법령 자동 크롤링 완성
- 실시간 법령 변경 Watcher
- 고급 reranker
- fine-tuning
- 실제 법적 판단
- 개인정보가 포함된 상담 사례 원문 저장

---

## Acceptance Criteria

- `document_requirements.csv` 초안이 존재한다.
- `regulation_chunks.jsonl` 생성 구조가 정의된다.
- `procedure_chunks.jsonl` 생성 구조가 정의된다.
- `form_chunks.jsonl` 생성 구조가 정의된다.
- 모든 chunk에 `source_id`, `publisher`, `doc_type`, `evidence_grade`가 포함된다.
- Evidence Grade A/B/E만 답변 근거로 사용 가능하도록 필터링된다.
- `rag_retrieval_cases.jsonl` 평가 데이터를 실행할 수 있다.

---

## Verification Commands

```bash
python scripts/ingest_rag_docs.py
python scripts/run_evals.py --dataset rag_retrieval_cases
```

---

## Human Review Checklist

- [ ] 법령 chunk가 조문 단위인가?
- [ ] 절차 chunk가 단계 단위인가?
- [ ] 서식 chunk가 필드 단위인가?
- [ ] 합성 데이터가 공식 근거로 쓰이지 않도록 제한했는가?
- [ ] metadata가 누락되지 않았는가?
- [ ] 개인정보가 포함된 원문이 저장되지 않았는가?