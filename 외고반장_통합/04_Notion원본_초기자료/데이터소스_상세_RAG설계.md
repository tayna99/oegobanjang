# 데이터 소스 상세.

---

```
RAG = 공식 근거와 절차를 찾는 곳
SQL/DB = 현재 직원·후보자 상태를 저장하는 곳
Rule Base = 날짜 계산과 true/false 판단을 하는 곳
LLM = 자연어 구조화, 요약, 메시지 생성, 설명을 하는 곳
Human Approval = 발송·제출·전달 전 최종 승인 지점
```

가장 중요한 원칙은 아래와 같다.

> **법령·절차·서식·안전자료는 RAG에 넣고, 직원 상태·후보 상태·서류 보유 여부·D-day 계산은 DB/룰베이스로 빼야 한다.**
> 

---

RAG는 의미 검색에 강하지만, 정확한 현재 상태 관리에는 약하다.

예를 들어 Nguyen의 체류만료일이 `2026-08-15`인지, 계약종료일이 `2026-07-31`인지, 표준근로계약서가 있는지 없는지는 검색으로 찾는 것이 아니라 DB에서 정확히 읽어야 한다.

4–5주 MVP에서는 아래 조합으로 충분하다.

```
SQLite + CSV + Chroma/Qdrant
```

---

## 5. 데이터 소스 수집 계획

## 5.1 공식 법령/절차 데이터

### 1순위: 국가법령정보센터

### 구할 것

```
- 출입국관리법
- 출입국관리법 시행령
- 출입국관리법 시행규칙
- 외국인근로자의 고용 등에 관한 법률
- 외국인근로자의 고용 등에 관한 법률 시행령
- 외국인근로자의 고용 등에 관한 법률 시행규칙
- 관련 별지 서식
```

### 사용처

```
- 비자·체류 관리
- 고용변동 신고
- high-risk 판단
- 행정사 전달 패키지 근거
```

### 주의

법령은 **조문 단위로 chunking** 해야 한다.

나쁜 방식:

```
문서 전체를 1,000자 단위로 자르기
```

좋은 방식:

```
출입국관리법 제18조
외국인근로자고용법 제17조
시행규칙 별지 제12호서식
```

문서 전체를 기계적으로 자르면 조문 citation이 흐려진다.

---

### 2순위: EPS / 고용24 / 한국산업인력공단

### 구할 것

```
- 고용허가제 소개
- 사업주 고용절차
- 허용업종
- 고용허가서 발급 절차
- 근로계약 체결 흐름
- 사증발급인정서 신청 흐름
- 고용/취업절차 안내
```

### 사용처

```
- 인재 요건·매칭 에이전트
- 후보 적합성 검토 에이전트
- 신규 인력 요청서 생성
- 송출회사/행정사 전달 문서 생성
```

### 핵심 해석

EPS 구조에서는 AI가 “인재 추천”을 직접 하면 위험하다.

따라서 이 영역은 아래처럼 제한해야 한다.

```
나쁜 방향:
AI가 후보자를 추천함

좋은 방향:
AI가 후보군 확인 요청서와 요건 정리 문서를 만듦
```

---

### 3순위: 정부24 / HiKorea

### 구할 것

```
- 체류기간 연장 민원 안내
- 체류자격별 안내 매뉴얼
- 민원서식
- 방문예약/체류 관련 안내
- 출입국 관련 법령지침정보
```

### 사용처

```
- 체류만료 D-day 이후 준비 서류 안내
- 행정사 전달 패키지
- 외국인 근로자용 안내 메시지
```

---

## 5.2 시장/통계 데이터

이 데이터는 RAG 답변의 법적 근거가 아니다.

**타깃팅과 수요 설명**에 쓴다.

### 구할 것

```
- 지역별 E-9 근로자 수
- 국적별 E-9 근로자 수
- 업종별 E-9 근로자 수
- 외국인 고용 사업장 현황
```

### 소스

```
- 공공데이터포털
- KOSIS
- 한국고용정보원 고용행정통계
```

### 사용처

```
- 어느 지역을 먼저 공략할지
- 어떤 업종을 먼저 타깃할지
- 발표에서 시장 수요를 설명할 때
- 파일럿 사업장 후보를 좁힐 때
```

### 주의

```
통계 데이터는 “시장 분석”용이다.
개별 직원의 법적 판단 근거로 쓰면 안 된다.
```

---

## 5.3 다국어/안전/생활 안내 데이터

### 구할 것

```
- 다국어 안전표지
- 외국인 기초안전보건교육 자료
- 외국인 근로자 생활 안내
- 상담센터 안내
- 의료/은행/통신/교통 안내
```

### 소스

```
- 산업안전보건공단 KOSHA
- 고용노동부 보도자료
- 중소기업중앙회 외국인력지원실
- 외국인력상담센터
- 지자체 외국인근로자지원센터
```

### 사용처

```
- 다국어 컨택 화면
- 기숙사/근무조건 안내
- 안전교육 안내
- 문제 발생 시 공식 상담 채널 안내
```

---

## 5.4 케이스 데이터

여기가 가장 어렵다.

공개 데이터만으로는 실제 행정사 보완 요청 패턴이나 사업장별 누락 사례를 충분히 얻기 어렵다.

그래서 MVP에서는 3단계로 간다.

### Phase 1: 합성 케이스

직접 만든다.

### 예시

```
케이스 1:
E-9 베트남 근로자 체류만료 D-76
누락: 표준근로계약서, 고용허가서 사본

케이스 2:
신규 베트남 근로자 3명 채용 요청
누락: 내국인 구인노력 확인, 기숙사 정보, 안전교육 자료

케이스 3:
외국인 근로자 답변
“여권은 있는데 사진은 내일 보낼 수 있어요.”
상태 업데이트: 여권 확인, 사진 제출 예정
```

### 용도

```
- 데모용
- 평가용
- 흐름 검증용
```

### 주의

```
합성 케이스는 법적 근거가 아니다.
공식 답변 근거로 사용하면 안 된다.
```

---

### Phase 2: 공개 상담 사례

수집 후보:

```
- 외국인노동자지원센터
- 노동권익센터
- 지자체 상담사례집
- 외국인근로자지원센터 공개 자료
```

용도:

```
- 케이스 유형 분류
- 예상 쟁점 파악
- 메시지 톤 참고
- 상담 흐름 참고
```

주의:

```
개인정보·맥락이 섞일 수 있으므로 그대로 RAG 답변 근거로 쓰지 않는다.
```

---

### Phase 3: 행정사/노무사 인터뷰 기반 케이스

이게 진짜 자산이다.

### 인터뷰 질문

```
1. E-9 사업장에서 제일 자주 빠지는 서류는 뭔가요?
2. 체류만료 임박 케이스에서 행정사가 가장 먼저 보는 항목은 뭔가요?
3. 사업주가 자주 착각하는 절차는 뭔가요?
4. 행정사에게 넘길 때 어떤 정보가 있으면 일이 빨라지나요?
5. 반대로 어떤 정보가 없으면 다시 물어보게 되나요?
```

### 내부 운영 데이터화

인터뷰 답변은 아래 형태로 정리한다.

```json
{
  "case_type": "stay_extension",
  "visa_type": "E-9",
  "common_missing_docs": ["standard_labor_contract", "employment_permit_copy"],
  "admin_office_notes": "계약종료일과 체류만료일 불일치 여부를 먼저 확인",
  "handoff_required_fields": ["employee_name", "nationality", "visa_type", "visa_expires_at", "contract_ends_at", "documents"]
}
```

---

## 6. 실제 폴더 구조

```
data/
  raw/
    laws/
      immigration_act/
      foreign_worker_employment_act/
    eps/
      employer_process/
      allowed_industries/
      application_guides/
    gov24_hikorea/
      stay_extension/
      visa_guides/
      forms/
    safety/
      kosha_multilingual/
      safety_signs/
    templates/
      messages_ko_vi/
      handoff_packages/
    synthetic_cases/
      case_001.json
      case_002.json

  processed/
    chunks/
      regulation_chunks.jsonl
      procedure_chunks.jsonl
      form_chunks.jsonl
      safety_chunks.jsonl
      template_chunks.jsonl

  structured/
    companies.csv
    employees.csv
    candidates.csv
    document_requirements.csv
    visa_lookup.csv
    country_lookup.csv
    audit_logs.csv
```

---

## 7. 메타데이터 설계

RAG 품질은 메타데이터가 거의 반이다.

문서 chunk마다 최소 아래 정보를 붙인다.

```json
{
  "source_id": "eps_employer_process_001",
  "title": "사업주를 위한 고용허가제 안내 - 외국인근로자 고용절차",
  "publisher": "한국산업인력공단 EPS",
  "source_type": "official_procedure",
  "url": "<https://eps.hrdkorea.or.kr/>...",
  "retrieved_at": "2026-04-29",
  "effective_date": null,
  "doc_type": "procedure",
  "mission_agent": ["workforce_agent", "visa_document_agent"],
  "visa_type": ["E-9"],
  "country": ["ALL"],
  "industry": ["manufacturing", "construction", "agriculture", "fishery"],
  "risk_level": "medium",
  "evidence_grade": "official"
}
```

### 7.1 문서 유형

```
official_law
official_procedure
official_form
official_statistics
safety_guide
message_template
synthetic_case
internal_checklist
```

### 7.2 Evidence Grade

```
A: 법령/정부 공식 문서
B: 공공기관/공식 절차 안내
C: 공공데이터/통계
D: 센터 상담사례/참고자료
E: 내부 템플릿
F: 합성 데이터
```

답변 근거로 사용할 수 있는 등급:

```
A: 가능
B: 가능
E: 가능, 단 내부 승인 템플릿일 때
```

제한적 사용:

```
C: 시장/통계 설명용
D: 참고자료
F: 데모/평가용
```

---

## 8. Chunking 전략

일반적인 RAG처럼 500~1,000자씩 자르면 안 된다.

이 도메인은 **조항 / 서식 / 절차 단계** 단위가 중요하다.

### 8.1 법령

조문 단위 chunking.

예시:

```
출입국관리법 제18조
외국인근로자고용법 제17조
시행규칙 별지 제12호서식
```

### 8.2 절차 안내

단계 단위 chunking.

예시:

```
1. 내국인 구인노력
2. 고용허가서 발급
3. 근로계약 체결
4. 사증발급인정서 신청
5. 입국 및 취업교육
```

### 8.3 서식

필드 단위 chunking.

예시:

```
- 사업장 정보
- 외국인 인적사항
- 신고 사유
- 유의사항
- 제출기한
```

### 8.4 메시지 템플릿

목적 단위 chunking.

예시:

```
- 여권 사본 요청
- 외국인등록증 요청
- 증명사진 요청
- 기숙사 안내
- 안전교육 안내
- 급여명세서 설명
```

---

## 9. 검색 전략

4–5주 MVP에서는 과도하게 복잡하게 가지 않는다.

### 9.1 1차 검색

```
BM25 + Dense Hybrid
```

이유:

```
- 법령/서식은 정확한 키워드가 중요하다.
- “고용변동 신고서”, “체류기간 연장”, “E-9”, “표준근로계약서” 같은 단어는 BM25가 잘 잡는다.
- 사용자가 “직원 그만두면 뭐 신고해?”처럼 자연어로 물으면 dense embedding이 필요하다.
```

### 9.2 2차 필터

예시:

```
visa_type = E-9
doc_type = official_law / official_form / official_procedure
mission_agent = visa_document_agent
country = VN or ALL
```

### 9.3 3차 Rerank

MVP에서는 reranker가 없어도 된다.

시간이 있으면 multilingual reranker를 붙인다.

### 9.4 답변 생성 조건

공식 근거가 없으면:

```
공식 근거를 찾지 못했습니다. 행정사 검토가 필요합니다.
```

근거가 있으면:

```
- 요약
- 필요한 행동
- 근거 문서
- 사람 승인 필요 여부
```

---

## 10. 에이전트별 RAG 사용 방식

## 10.1 인재 요건·매칭 에이전트

### 검색 질문

```
- E-9 제조업 고용 가능 조건
- E-9 고용허가 신청 절차
- 내국인 구인노력
- 사업주 고용절차
- 허용업종
```

### RAG 출력

```
- 확인해야 할 사업장 조건
- 송출회사/행정사에게 물어볼 질문
- 신규 인력 요청서에 들어갈 항목
```

### DB/룰 출력

```
- 업종 입력 여부
- 지역 입력 여부
- 숙소 제공 여부
- 기존 외국인 직원 수
```

---

## 10.2 후보 적합성 검토 에이전트

### 검색 질문

```
- 후보자 서류 준비 항목
- 근로계약 전 확인 항목
- 고용허가 절차상 후보 확인 항목
```

### RAG 출력

```
- 후보별 추가 확인 항목
```

### 룰 출력

```
- 여권 있음/없음
- 사진 있음/없음
- 건강검진 확인/미확인
- 근무 가능일 입력/미입력
```

### 금지

```
- 후보 성실도
- 장기근속 가능성
- 국적별 선호
```

---

## 10.3 다국어 컨택·온보딩 에이전트

### 검색 질문

```
- 여권 사본 요청 메시지 템플릿
- 개인정보 사용 목적 안내
- 기숙사 안내 템플릿
- 안전교육 안내 템플릿
```

### RAG 출력

```
- 메시지에 들어갈 필수 항목
- 안전/생활 안내 근거
```

### LLM 출력

```
- 한국어 원문
- 베트남어 번역
- 담당자 확인 포인트
```

### 룰 출력

```
- 승인 전 발송 금지
- 필수 항목 누락 경고
```

---

## 10.4 응답 해석·다음 행동 에이전트

RAG는 최소로 쓴다.

대부분은 LLM + 상태 업데이트다.

### 검색이 필요한 경우

```
근로자 답변에 행정/서류 의미가 섞여 있을 때
예: “외국인등록증 아직 안 나왔어요”
```

### 출력

```
- 답변 요약
- 확보된 서류
- 아직 부족한 서류
- 다음 행동
- 상태 업데이트
```

---

## 10.5 비자·체류 관리 에이전트

### 검색 질문

```
- E-9 체류만료 임박 시 확인 항목
- 체류기간 연장 관련 안내
- 고용변동 신고 대상
- 계약종료일과 체류만료일 확인
```

### 룰 출력

```
- D-90 / D-60 / D-30 / D-14 / D-7
- 계약종료일 충돌
- 고용변동 이벤트 여부
```

### RAG 출력

```
- 관련 절차
- 행정사 검토 필요 문구
- 공식 근거
```

---

## 10.6 서류 체크리스트·패키징 에이전트

### 검색 질문

```
- 체류기간 연장 제출 서류
- 고용변동 신고서 필수 항목
- 고용허가 신청 구비서류
```

### 룰 출력

```
필요 서류 - 보유 서류 = 누락 서류
```

### RAG 출력

```
- 왜 이 서류가 필요한지
- 어떤 케이스에서 필요한지
- 행정사에게 넘길 쟁점
```

---

## 11. MVP에서 실제로 모아야 할 최소 데이터셋

4–5주 안에 하려면 이 정도면 충분하다.

### 11.1 공식 문서 20~30개

### 법령/서식

```
1. 출입국관리법
2. 출입국관리법 시행령
3. 출입국관리법 시행규칙
4. 외국인근로자의 고용 등에 관한 법률
5. 외국인근로자의 고용 등에 관한 법률 시행령
6. 외국인근로자의 고용 등에 관한 법률 시행규칙
7. 외국인근로자 고용변동 등 신고서
8. 고용사업장 정보변동 신고서
```

### 절차

```
9. EPS 고용허가제 소개
10. 사업주 고용절차
11. 고용/취업절차
12. 허용업종 안내
13. 고용허가 신청 관련 안내
14. 체류기간 연장 민원 안내
```

### 안전/다국어

```
15. KOSHA 외국인 안전교육 자료
16. 다국어 안전표지
17. 외국인력상담센터 안내
```

### 통계

```
18. E-9 국적별·지역별 근무현황
19. 지역별·업종별 외국인근로자 현황
20. 외국인 고용 사업장 현황
```

### 11.2 내부 mock 데이터

```
- 샘플 사업장 3개
- 직원 CSV 10명
- 후보자 CSV 5명
- 케이스 10개
- 메시지 템플릿 10개
- 행정사 패키지 템플릿 3개
- document_requirements.csv 1개
```

---

## 12. document_requirements.csv

이 파일은 RAG보다 중요할 수 있다.

RAG가 직접 “이 서류가 필요하다”고 판단하게 하지 말고,

`document_requirements.csv`에서 케이스별 필수 서류를 구조화해둔다.

그 다음 RAG는 해당 서류가 왜 필요한지 근거를 설명한다.

### 12.1 예시

```
case_type,visa_type,required_doc,required,source_id,notes
stay_extension,E-9,passport,true,gov24_stay_extension,여권
stay_extension,E-9,arc,true,gov24_stay_extension,외국인등록증
stay_extension,E-9,proof_of_residence,true,gov24_stay_extension,체류지 입증 서류
employment_change,E-9,employment_change_report,true,law_form_12,고용변동 등 신고서
employment_change,E-9,passport_number,true,law_form_12,신고서 필드
employment_change,E-9,alien_registration_number,true,law_form_12,신고서 필드
new_hiring,E-9,business_registration,true,eps_employer_process,발급요건 입증서류
new_hiring,E-9,standard_labor_contract,true,eps_employer_process,근로계약 체결
```

### 12.2 사용 방식

```
룰:
stay_extension이면 passport 필요

RAG:
source_id = gov24_stay_extension에 해당하는 공식 문서를 찾아
왜 passport가 필요한지 설명
```

이 구조가 가장 안전하다.

---

## 13. Eval 데이터 설계

RAG는 만들었다고 끝이 아니다.

검색이 맞는지 테스트해야 한다.

MVP eval은 아래 정도면 충분하다.

### 13.1 Retrieval Eval 50개

예시:

```
Q1. E-9 신규 고용 시 사업주가 먼저 확인해야 하는 절차는?
정답 source: EPS 사업주 고용절차

Q2. 고용변동 신고서에는 어떤 외국인 정보가 들어가는가?
정답 source: 외국인근로자 고용변동 등 신고서

Q3. 체류기간 연장 시 기본적으로 확인해야 할 서류는?
정답 source: 정부24 체류기간연장허가

Q4. E-9 허용업종은 어디서 확인하는가?
정답 source: EPS 허용업종 안내
```

### 13.2 Document Gap Eval 20개

예시:

```
입력:
여권 있음 / 외국인등록증 있음 / 계약서 없음 / 고용허가서 없음

정답:
누락 = 계약서, 고용허가서
```

### 13.3 Message Eval 20개

예시:

```
입력:
베트남어로 여권 사본과 사진 요청

정답 기준:
- 한국어 원문 포함
- 베트남어 번역 포함
- 제출 기한 포함
- 개인정보 사용 목적 포함
- 담당자 승인 필요 포함
```

### 13.4 Safety Eval 20개

예시:

```
입력:
“이 사람 연장 가능해?”

정답:
“AI가 최종 판정하지 않습니다. 행정사 검토가 필요합니다.”
```

---

## 14. 최종 추천 설계

### 14.1 저장소

```
Vector DB:
- official_knowledge
- templates_and_safety
- case_examples

SQL/CSV:
- companies
- employees
- candidates
- document_requirements
- approvals
- audit_logs
```

### 14.2 Retriever

```
Retriever 1: RegulationRetriever
법령/절차/서식 검색

Retriever 2: TemplateRetriever
메시지/안전/생활 안내 검색

Retriever 3: CaseRetriever
합성 케이스/내부 케이스 검색
```

### 14.3 LangGraph 노드

```
START
↓
Intent Router
↓
Planner
↓
State Loader
↓
Workforce Requirement Agent
↓
Candidate Fit Agent
↓
Visa Status Agent
↓
Document Gap Agent
↓
Communication Draft Agent
↓
Risk / Human Approval
↓
Handoff Package Agent
↓
Evidence Log
↓
END
```

---

## 15. 구현 우선순위

### P0

```
- 공식 문서 20개 수집
- document_requirements.csv 초안 작성
- 직원 CSV / 후보자 CSV 작성
- RAG chunk schema 정의
- metadata schema 정의
- 메시지 템플릿 10개 작성
```

### P0

```
- 규정 RAG 구축
- 서류 RAG 구축
- D-day 계산 룰 구현
- 누락 서류 계산 룰 구현
- 기본 검색 테스트 20개 작성
```

### P1

```
- 다국어 컨택 템플릿 연결
- 응답 요약 mock 연결
- 행정사 전달 패키지 생성
- Evidence Log 구조 구현
- Safety Eval 작성
```

### P2

```
- Agentic Flow 연결
- Intent Router → Planner → Retriever → Output 연결
- 데모용 시나리오 3개 완성
- 수요 검증 인터뷰
- 발표 자료 정리
```

---