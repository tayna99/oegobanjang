# RAG Strategy

## 1. 핵심 원칙

외고반장의 RAG는 답변을 그럴듯하게 만들기 위한 검색이 아니다.  
공식 근거와 절차를 찾아서 안전한 다음 행동을 제안하기 위한 근거 검색 시스템이다.

```txt
RAG = 공식 근거와 절차를 찾는 곳
SQL/DB = 현재 직원·후보자 상태를 저장하는 곳
Rule Base = 날짜 계산과 true/false 판단을 하는 곳
LLM = 자연어 구조화, 요약, 메시지 생성, 설명을 하는 곳
Human Approval = 발송·제출·전달 전 최종 승인 지점
```

---

## 2. RAG에 넣는 데이터

### 공식 법령/절차 데이터

- 출입국관리법
- 출입국관리법 시행령
- 출입국관리법 시행규칙
- 외국인근로자의 고용 등에 관한 법률
- 외국인근로자의 고용 등에 관한 법률 시행령
- 외국인근로자의 고용 등에 관한 법률 시행규칙
- 관련 별지 서식
- EPS 고용허가제 자료
- 고용24 자료
- 한국산업인력공단 자료
- 정부24 체류기간 연장 안내
- HiKorea 체류 관련 안내

### 다국어/안전/생활 안내 데이터

- 다국어 안전표지
- 외국인 기초안전보건교육 자료
- 외국인 근로자 생활 안내
- 상담센터 안내
- 의료/은행/통신/교통 안내

### 템플릿 데이터

- 여권 사본 요청 메시지
- 외국인등록증 요청 메시지
- 증명사진 요청 메시지
- 기숙사 안내 메시지
- 안전교육 안내 메시지
- 급여명세서 설명 메시지
- 행정사 전달 패키지 템플릿

---

## 3. RAG에 넣지 않는 데이터

아래 데이터는 RAG 검색 대상이 아니라 DB 또는 Rule Base에서 관리한다.

- 직원명
- 체류만료일
- 계약종료일
- 외국인등록번호
- 여권번호
- 서류 보유 여부
- D-day 계산 결과
- 승인 상태
- 메시지 발송 이력

---

## 4. 저장 구조

```txt
data-pipeline/
├─ raw/
│  ├─ laws/
│  ├─ eps/
│  ├─ gov24_hikorea/
│  ├─ safety/
│  ├─ templates/
│  └─ synthetic_cases/
├─ processed/
│  └─ chunks/
└─ seed/
   ├─ companies.csv
   ├─ employees.csv
   ├─ candidates.csv
   ├─ document_requirements.csv
   ├─ visa_lookup.csv
   └─ country_lookup.csv
```

---

## 5. Metadata Schema

모든 chunk는 아래 메타데이터를 가져야 한다.

```json
{
  "source_id": "eps_employer_process_001",
  "title": "사업주를 위한 고용허가제 안내",
  "publisher": "한국산업인력공단 EPS",
  "source_type": "official_procedure",
  "url": "",
  "retrieved_at": "2026-04-29",
  "effective_date": null,
  "doc_type": "procedure",
  "mission_agent": ["workforce_agent", "visa_document_agent"],
  "visa_type": ["E-9"],
  "country": ["ALL"],
  "industry": ["manufacturing"],
  "risk_level": "medium",
  "evidence_grade": "B",
  "source_unit_type": "procedure_step",
  "domain_unit_id": "eps_employer_process_001::procedure_step::0001",
  "unit_heading": "내국인 구인노력",
  "unit_index": 1,
  "splitter_version": "domain_splitters_v1",
  "unit_confidence": "high"
}
```

---

## 6. Evidence Grade

| Grade | 의미 | 답변 근거 사용 |
|---|---|---|
| A | 법령/정부 공식 문서 | 가능 |
| B | 공공기관/공식 절차 안내 | 가능 |
| C | 공공데이터/통계 | 시장 분석용 |
| D | 센터 상담사례/참고자료 | 참고용 |
| E | 내부 템플릿 | 승인 템플릿으로 가능 |
| F | 합성 데이터 | 데모/평가용, 공식 근거 불가 |

---

## 7. Chunking 전략

### 구현 책임 분리

도메인 의미 단위는 `chunking.py`가 추론하지 않는다.

```txt
raw domain splitter = 법령/절차/서식/안전/템플릿을 의미 단위 record로 분리
chunking.py = 이미 정리된 JSONL의 14필드 metadata 검증, paragraph split, stable chunk_id 생성
```

따라서 “법령은 조문, 절차는 단계, 서식은 필드 단위”라는 기준은 raw 수집/정규화 단계의 계약이다.
`chunking.py`는 이 경계를 다시 AI처럼 추론하지 않고, 입력 record의 schema와 citation 재현성을 안정화한다.

인력확보 Agent는 후보 추천기가 아니라 신규 고용 준비상태 점검 Agent이므로, RAG는 `신규 고용 절차`, `내국인 구인노력`, `고용허가 신청`, `표준근로계약`, `사증발급인정서`, `취업교육`, `서식 항목`을 바로 인용 가능한 단위로 제공해야 한다.

### 법령

조문 단위로 자른다.

예시:

- 출입국관리법 제18조
- 외국인근로자고용법 제17조
- 시행규칙 별지 제12호서식

### 절차 안내

절차 단계 단위로 자른다.

예시:

- 내국인 구인노력
- 고용허가서 발급
- 근로계약 체결
- 사증발급인정서 신청
- 입국 및 취업교육

### 서식

필드 단위로 자른다.

예시:

- 사업장 정보
- 외국인 인적사항
- 신고 사유
- 제출기한
- 유의사항

---

## 8. 검색 전략

MVP에서는 다음 구조를 사용한다.

```txt
1차 검색: BM25 + Dense Hybrid
2차 필터: visa_type, doc_type, mission_agent, country, industry
3차 재정렬: MVP에서는 생략 가능
```

### 인력확보 Agent Vector DB

인력확보 Agent의 Vector DB는 후보자 검색용이 아니다.
신규 채용 준비에 필요한 공식 절차와 내부 템플릿을 찾는 근거 저장소다.

```txt
workforce_official = EPS/고용24/HRDK/법령 기반 공식 절차와 허용업종 근거
workforce_templates = 신규 인력 요청서, 후보 준비도 체크리스트, 송출회사/행정사 질문 템플릿
case_examples = 합성/상담 사례 참고자료, 공식 근거나 template collection에 섞지 않음
```

`workforce_templates`에는 `evidence_grade=E` 내부 템플릿만 들어간다.
`doc_type=case`, `source_unit_type=case_record`, `evidence_grade=D/F` 자료는 공식 판단 근거나 템플릿 검색 재료로 노출하지 않는다.

운영 임베딩은 아래처럼 구분한다.

```txt
local/dev = deterministic embedding
production = WORKFORCE_RAG_EMBEDDING_PROVIDER=openai + OPENAI_API_KEY + text-embedding-3-small
```

색인과 runtime query는 같은 embedding provider를 사용해야 한다. 서로 다른 provider로 색인/검색하면 벡터 차원이 맞지 않거나 검색 품질이 깨진다.

### Runtime Retrieval Boundary

인력확보 Agent의 제품 runtime 검색 경로는 `workforce_runtime_retriever` 하나로 고정한다. 이 경로는 Chroma collection인 `workforce_official`, `workforce_templates`만 조회한다.

`PolicyRetriever`와 JSONL 기반 `workforce_jsonl_retrieval`은 eval, unit test, 로컬 debugging 전용이다. Chroma collection이 없거나 검색 결과가 0건이어도 runtime에서 JSONL로 조용히 fallback하지 않는다.

검색 결과가 0건이면 `rag_retrieved` 이벤트에 `retrieved_count=0`, `jsonl_fallback_used=false`를 남기고, `MISSING_EVIDENCE` risk와 `risk_flagged` 이벤트를 생성한다. 이 상태는 “근거 없음”으로 보고 담당자/행정사 검토가 필요하다고 표시한다.

검색 품질 검증 계획과 통과 기준은 `docs/WORKFORCE_RETRIEVAL_QUALITY_EVAL.md`에 고정한다.
현재 canonical dataset은 `evals/datasets/workforce_retrieval_quality_cases.csv`이며, 결과는 `evals/reports/workforce_retrieval_quality_latest.csv`와 `.json`에 기록한다.

### 고용24 본문 추출 경계

고용24 일부 상세 URL은 서버 응답만으로 의미 있는 본문이 비어 있는 shell HTML을 반환할 수 있다.
현재 MVP는 정확한 상세 URL을 manifest에 고정하고, 직접 fetch 본문이 비어 있을 때 `fallback_text`로 수동 검토된 curated source를 사용한다.

브라우저 렌더링 기반 수집은 운영 crawler/importer hardening 단계에서 붙인다. 그 전까지는 “빈 본문을 그대로 chunk로 넣기”보다 “수동 curated fallback + source_fetch_method 기록”을 우선한다.

---

## 9. 검색 실패 처리

공식 근거를 찾지 못한 경우 다음 문구를 사용한다.

```txt
공식 근거를 찾지 못했습니다. 이 케이스는 행정사 또는 노무사 검토가 필요합니다.
```
