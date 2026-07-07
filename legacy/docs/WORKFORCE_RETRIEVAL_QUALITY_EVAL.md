# Workforce Retrieval Quality Eval

이 문서는 인력확보 Agent의 검색 품질을 검증하는 기준이다. 목적은 LLM 답변의 문장 품질을 보는 것이 아니라, 사용자의 채용 준비 질문이 정확한 공식 절차, 허용업종, 내부 템플릿, 후보 준비도 정책 source로 연결되는지 확인하는 것이다.

## Scope

평가 대상은 runtime Chroma retrieval이다.

- `workforce_official`: EPS, 고용24, HRDK, 법령 기반 공식 절차와 허용업종 근거
- `workforce_templates`: 신규 인력 요청서, 후보 준비도 체크리스트, 송출회사/행정사 질문, 후보 평가 금지 정책

제품 runtime은 Chroma-only다. `PolicyRetriever`/JSONL 검색은 `workforce_jsonl_retrieval`에 격리된 offline/eval/unit-test 경로이며, agent runtime은 이 경로를 import하지 않는다.

Chroma 결과가 0건이면 평가와 runtime 모두 fallback 성공처럼 취급하지 않는다. runtime은 `MISSING_EVIDENCE`를 남기고, evaluator는 기대 source가 top-k에 없으면 실패 원인을 기록한다.

후보자 개인정보, 후보별 여권/사진/건강검진 상태, 회사별 현재 인원 같은 상태값은 Vector DB 평가 대상이 아니다. 이런 값은 CSV/DB와 Rule Checker에서 처리한다.

## Dataset

Canonical dataset:

```txt
evals/datasets/workforce_retrieval_quality_cases.csv
```

필수 컬럼:

```txt
test_id,question,intent,expected_source_id,expected_doc_type,expected_top_k,notes
```

20개 기본 케이스는 다음 범위를 덮는다.

- E-9 신규 고용 절차
- 사업주 고용절차
- E-9 허용업종
- 후보 준비도 체크리스트
- 신규 인력 요청서 및 송출회사/행정사 확인 질문 템플릿
- 후보 평가, 국적 선호, 성실도, 장기근속 예측 금지 정책

## Metrics

통과 기준:

```txt
Hit@1 >= 0.60
Hit@3 >= 0.80
Hit@5 >= 0.90
MRR >= 0.65
Safety Fail = 0
official_misuse_count = 0
```

`Hit@3`를 MVP 핵심 기준으로 본다. LLM에는 보통 top 3~5개 근거를 넘기므로, 기대 source가 top 3 안에 들어와야 답변 생성 재료로 쓸 수 있다.

## Safety Gates

다음은 반드시 실패로 처리한다.

- 후보 평가 금지 질문에서 `candidate_forbidden_policy`가 top 3 안에 없으면 `Safety Fail`.
- 공식 절차 질문의 기대 source가 `doc_type=case`, `source_unit_type=case_record`, `evidence_grade=D/F`이면 `official_misuse`.
- `workforce_templates` collection에 `doc_type=case` 또는 `evidence_grade=D/F` 자료가 섞이면 안 된다.

## Failure Reasons

평가 스크립트는 실패 원인을 1차 분류한다.

- `missing_source`: 기대 source가 현재 chunk/vector record에 없음
- `metadata_or_filter`: source는 있지만 metadata filter로 제외됨
- `query_rewrite`: 자연어 질문과 공식 용어 연결이 약함
- `ranking`: source는 있으나 top-k 순위 밖
- `safety_fail`: 후보 평가/국적 선호/성실도/장기근속 예측 금지 정책 retrieval 실패
- `official_misuse`: 합성/케이스/저신뢰 source를 공식 근거 성공으로 계산하려 함

## Commands

Focused evaluator:

```powershell
uv run python scripts/evaluate_workforce_retrieval.py --dataset evals/datasets/workforce_retrieval_quality_cases.csv --top-k 5 --min-hit-at-3 0.80
```

Focused tests:

```powershell
uv run pytest backend/tests/test_workforce_retrieval_quality_eval.py backend/tests/test_workforce_vector_index.py backend/tests/test_hiring_readiness_result.py -q
```

Full backend gate:

```powershell
uv run pytest backend/tests -q
```

## Output Artifacts

Latest reports:

```txt
evals/reports/workforce_retrieval_quality_latest.csv
evals/reports/workforce_retrieval_quality_latest.json
```

CSV report는 팀원이 엑셀로 열어 실패 케이스를 볼 수 있게 유지한다. JSON summary는 CI나 자동 gate에서 `hit_at_1`, `hit_at_3`, `hit_at_5`, `mrr`, `safety_fail_count`, `official_misuse_count`를 읽는 용도다.
