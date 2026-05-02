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
  "evidence_grade": "B"
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

---

## 9. 검색 실패 처리

공식 근거를 찾지 못한 경우 다음 문구를 사용한다.

```txt
공식 근거를 찾지 못했습니다. 이 케이스는 행정사 또는 노무사 검토가 필요합니다.
```