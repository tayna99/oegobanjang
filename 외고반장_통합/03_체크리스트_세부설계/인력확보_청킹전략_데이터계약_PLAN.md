# 인력확보 에이전트 데이터-정제-청킹 보강 계획

## Summary

맞습니다. 흐름은 **데이터 수집 → 문서 정제 → metadata 추론/정규화 → 업무 판단 단위 record 생성 → chunking/indexing → eval → agent 출력** 순서가 맞습니다.

단, 이미 있는 법령/절차 JSONL과 `domain_splitters.py`, `raw_ingest.py`, `ingest_rag_docs.py`를 버리고 다시 하는 게 아니라, 현재 파이프라인 위에 **인력확보 전용 데이터 계약**을 얹는 방식으로 갑니다.

핵심 방향은 이것입니다.

- RAG는 “사람 추천”이 아니라 **공식 절차·근거·템플릿 재료 검색**만 담당한다.
- DB/Rule은 **회사 상태, 후보 준비도, 서류 보유 여부, true/false 판단**을 담당한다.
- Workforce Agent는 내부적으로 `workforce_requirement_agent`와 `candidate_readiness_agent`로 나눈다.
- 최종 출력은 `신규 인력 요청서`, `제도상 확인 필요 항목`, `후보 준비도 비교표`, `송출회사/행정사 확인 질문` 4개로 고정한다.

## Key Changes

### 1. 데이터 소스 계약 재정의

RAG에 넣는 데이터와 DB/Rule로 남길 데이터를 명확히 분리합니다.

RAG 대상:
- 공식 절차 데이터: EPS, 고용24, HRDK, 고용노동부의 고용허가제 소개, 사업주 고용절차, E-9 허용업종, 고용허가 신청, 근로계약, 사증발급인정서, 취업교육.
- 법령/제도 데이터: 외국인근로자고용법, 시행령, 시행규칙, 출입국관리법, 관련 별지 서식. 단, 인력확보 화면에서는 보조 근거로 사용.
- 내부 템플릿: 신규 인력 요청서, 송출회사 확인 요청서, 행정사 검토 요청서, 후보 준비도 비교표, 추가 확인 질문 템플릿. `evidence_grade=E`.
- 합성/사례 데이터: demo/eval 전용. 공식 근거로 사용 금지.

DB/Rule 대상:
- 회사 정보: `company_id`, `industry`, `region`, `housing`, `shift_type`, `current_foreign_workers`.
- 후보 정보: `passport`, `photo`, `health_check`, `available_from`, `desired_role`, `understood_housing`, `understood_shift`.
- 체크리스트: `candidate_readiness_checklist.csv`. 이것은 Rule Checker의 기준표이며, 공식 근거가 아니다.

### 2. metadata 정규화 보강

현재 `source_unit_type`은 유지하고, 인력확보 전용 metadata를 추가합니다.

필수 추가 metadata:
```json
{
  "mission_agent": ["workforce_agent"],
  "sub_agent": ["workforce_requirement_agent"],
  "case_type": ["new_hiring"],
  "workflow_stage": "pre_hiring",
  "output_usage": ["requirement_check", "request_form", "handoff_question"],
  "source_unit_type": "procedure_step",
  "evidence_grade": "B"
}
```

허용 값:
- `sub_agent`: `workforce_requirement_agent`, `candidate_readiness_agent`
- `case_type`: `new_hiring`, `candidate_review`, `handoff_question`, `request_form`
- `workflow_stage`: `pre_hiring`, `candidate_readiness`, `handoff_preparation`, `post_arrival_preparation`
- `output_usage`: `requirement_check`, `request_form`, `handoff_question`, `readiness_check`, `candidate_readiness_table`, `additional_questions`
- `source_unit_type`: `law_article`, `procedure_step`, `allowed_industry`, `employer_requirement`, `form_section`, `template_purpose`, `case_record`, `general`

### 3. 문서 정제와 업무 단위 record 생성

현재 `raw_ingest.py`의 HTML/PDF/text/jsonl loader는 유지합니다. 보강할 부분은 “정제 후 어떤 업무 단위 record로 만들 것인가”입니다.

업무 단위 분리 기준:
- 절차 문서: 고용허가제 개요, 신청 전 확인사항, 내국인 구인노력, 고용허가 신청, 근로계약, 사증발급인정서, 입국/취업교육, 사업장 배치 후 관리.
- 허용업종: `visa_type=E-9`, `industry=manufacturing/agriculture/fishery/service/...` 단위.
- 사업주 요건: 업종, 지역, 필요 인원, 내국인 구인노력, 숙소, 근로조건, 표준근로계약서, 안전교육.
- 서식/문서: 사업장 정보, 필요 인원, 희망 직무, 숙소/근무조건, 송출회사 질문, 행정사 검토 항목.
- 후보 준비도: 여권, 사진, 건강검진, 근무 가능일, 희망 직무, 언어/안내, 기숙사/근무조건 이해 여부.

`chunking.py`는 계속 stable chunk id와 schema validation만 담당합니다. 업무 단위 분리는 `domain_splitters.py`와 raw 정규화 단계에서 처리합니다.

### 4. 인력확보 Agent 출력 계약

`HiringReadinessResult`를 정식 schema로 분리합니다.

필수 출력:
- `hiring_request_draft`: 사업장명, 업종, 지역, 필요 인원, 희망 언어, 근무 형태, 숙소 제공 여부, 기존 외국인 근로자 수, 요청 직무, 희망 입사 시점.
- `institutional_checklist`: E-9 허용업종 확인, 내국인 구인노력 확인, 고용허가 신청 가능성 검토, 표준근로계약서 준비, 숙소/근무조건 안내, 안전교육 자료.
- `candidate_readiness_table`: 후보별 제출 준비도와 추가 확인 필요 항목. 점수/추천 금지.
- `handoff_questions`: 송출회사/행정사에게 물어볼 질문 목록.
- `approval_required=true`.

`CandidateReadinessResult`를 새로 만듭니다.

필수 출력:
- 후보별 `passport/photo/health_check/available_from/desired_role_match/understood_housing/understood_shift`
- 상태 값은 `ready`, `missing_required_info`, `needs_confirmation`, `not_applicable` 정도로 제한.
- 금지 필드: `candidate_score`, `nationality_preference`, `reliability_score`, `absconding_prediction`, `final_eligibility_decision`.

### 5. 검색 흐름 보강

인력확보 검색은 RAG 결과를 최종 답변으로 쓰지 않고, LLM/Rule에 넘기는 재료로만 씁니다.

검색 흐름:
1. Query rewrite: `E-9 신규 고용 절차`, `사업주 고용절차`, `내국인 구인노력`, `고용허가 신청`, `제조업 허용업종`, `송출회사 확인 요청서`.
2. Metadata filter:
```json
{
  "mission_agent": "workforce_agent",
  "visa_type": "E-9",
  "case_type": "new_hiring"
}
```
3. Retrieval buckets:
- official procedure top 5
- allowed industry top 3
- internal template top 3
- candidate readiness checklist top 3
4. Rule Checker:
- 회사 필수값 누락
- 후보 서류 true/false
- 근무 가능일 누락
- 요청 직무와 희망 직무 일치 여부
- 금지 판단 차단
5. Generator:
- 4개 고정 출력물 생성
- 외부 전달 전 Human Approval 요구
- Evidence Log에 사용 근거와 rule 결과 저장

## Implementation Plan

1. Source inventory 보강
- 기존 raw/source를 다시 수집하지 않고, 현재 raw JSONL/MD/PDF/HTML에 `sub_agent`, `case_type`, `workflow_stage`, `output_usage`가 있는지 inventory report를 만든다.
- 부족한 항목은 `workforce_source_gap_report.json`으로 출력한다.
- Acceptance: report에서 공식 절차, 허용업종, 사업주 요건, 내부 템플릿, 후보 준비도 체크리스트의 coverage가 보인다.

2. Metadata normalizer 추가
- raw record metadata가 부족하면 title/path/content 기반으로 `sub_agent`, `case_type`, `workflow_stage`, `output_usage`를 추론한다.
- 추론 confidence가 낮으면 `unit_confidence=low`와 warning을 남긴다.
- Acceptance: `ingest_rag_docs.py --dry-run --report`에 workforce metadata coverage가 나온다.

3. Workforce templates와 checklist 추가
- `workforce_request_template.md`
- `handoff_questions_template.md`
- `candidate_readiness_checklist.csv`
- `candidate_readiness_template.md`
- Acceptance: 템플릿은 `evidence_grade=E`, `source_type=internal_template`, `mission_agent=workforce_agent`로 chunk된다.

4. Domain splitter 확장
- `allowed_industry`, `employer_requirement`, `form_section`, `template_purpose` 분리를 보강한다.
- `candidate_readiness` 항목은 사람 평가가 아니라 제출 준비도 항목으로만 분리한다.
- Acceptance: 허용업종/사업주 요건/후보 준비도 raw sample이 기대 `source_unit_type`으로 분리된다.

5. Workforce retrieval filter 추가
- `workforce_requirement_agent`는 official procedure, allowed industry, employer requirement, request template을 우선 검색한다.
- `candidate_readiness_agent`는 candidate readiness checklist/template과 관련 공식 절차만 검색한다.
- Acceptance: 후보 추천/성실도/국적 선호 query는 검색 전 guardrail에서 차단된다.

6. Agent schema 보강
- `HiringReadinessResult`와 `CandidateReadinessResult`를 분리한다.
- 기존 `build_hiring_readiness_result`는 4개 출력물 구조로 확장한다.
- Acceptance: 신규 고용 요청이 4개 출력물을 모두 반환하고, 후보 준비도는 점수 없이 상태와 누락 항목만 반환한다.

7. Eval dataset 재구성
- `workforce_rag_retrieval_cases.jsonl`을 다음 4개 묶음으로 확장한다.
- 신규 고용 준비 5개
- 허용업종/사업주 요건 5개
- 후보 준비도 5개
- 송출회사/행정사 질문/템플릿 5개
- Acceptance: seed/internal-only에 의존하지 않고 Hit@3 `>= 0.80`, 금지 판단 eval은 100% 차단.

## Test Plan

- `test_workforce_source_inventory.py`: raw source가 official procedure, allowed industry, templates, readiness checklist로 분류되는지 검증.
- `test_workforce_metadata_normalizer.py`: `sub_agent`, `case_type`, `workflow_stage`, `output_usage` 추론 검증.
- `test_domain_splitters.py`: 절차/허용업종/사업주 요건/서식/후보 준비도 단위 분리 검증.
- `test_workforce_rag_eval_dataset.py`: 20-case 이상이고 seed/template-only에 의존하지 않는지 검증.
- `test_workforce_retrieval_filters.py`: `new_hiring`과 `candidate_review`가 서로 다른 metadata filter를 쓰는지 검증.
- `test_hiring_readiness_result.py`: 4개 고정 출력물과 `approval_required=true` 검증.
- `test_candidate_readiness_result.py`: 후보 준비도는 누락/확인 필요만 표시하고 점수/추천 필드가 없는지 검증.
- `test_workforce_agent_guardrails.py`: 성실도, 이탈 가능성, 국적 선호, 후보 추천 요청 차단.

검증 명령:
```powershell
uv run pytest backend/tests/test_workforce_source_inventory.py backend/tests/test_workforce_metadata_normalizer.py backend/tests/test_domain_splitters.py -q
uv run pytest backend/tests/test_workforce_retrieval_filters.py backend/tests/test_hiring_readiness_result.py backend/tests/test_candidate_readiness_result.py backend/tests/test_workforce_agent_guardrails.py -q
uv run python scripts/ingest_rag_docs.py --dry-run --report --eval-dataset evals/datasets/workforce_rag_retrieval_cases.jsonl --min-hit-rate 0.80
uv run pytest backend/tests -q
```

## Assumptions

- 기존 raw 법령/절차 데이터는 재수집하지 않고, metadata와 업무 단위 정규화를 보강한다.
- 새로운 웹 크롤링은 이번 범위가 아니다. 부족한 데이터는 gap report로 먼저 드러낸다.
- 후보자/회사 상태는 RAG가 아니라 DB/CSV/Rule Checker에서 처리한다.
- `candidate_fit_agent`라는 이름은 쓰지 않고 `candidate_readiness_agent`로 고정한다.
- 후보 준비도 비교는 가능하지만 후보 추천, 순위, 점수화, 성실도 판단, 이탈 예측은 금지한다.
- 내부 템플릿은 `evidence_grade=E`로 사용 가능하지만 공식 법령/절차 근거처럼 표시하지 않는다.
