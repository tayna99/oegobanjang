# RAG Seed 제거/실제 20개 데이터 기준 전환 플랜

## Current State
| 항목 | 현재 상태 | 판단 |
|---|---|---|
| `sample_policy_docs.jsonl` | 2,927 bytes, 5 records | 2개는 `F synthetic_case`, 3개는 `E message_template`라서 “실제 공식 RAG 근거”가 아니다 |
| `sample_required_docs.jsonl` | 0 bytes, 0 records | placeholder이며 실제 데이터 역할이 없다 |
| `document_requirements.csv` | 22 rows | 내부 서류 체크리스트라 `E` 근거로는 가능하지만 공식 법령/절차 근거는 아니다 |
| `data-pipeline/raw/` | 58 files, `.jsonl` 19개 + `.md` 39개 | 실제 raw 기반 RAG 소스는 이미 존재한다 |
| raw JSONL rows | 729 rows | 실제 법령/절차/안전/정부24/HiKorea 계열 데이터가 seed보다 훨씬 크다 |
| dry-run ingest | 768 raw records, 918 chunks 생성 | 새 raw loader 기준으로는 실제 raw가 들어오고 있다 |
| 현재 processed chunks | 27 chunks only | 아직 `all_chunks.jsonl`은 seed + internal checklist 중심이라 실제 raw 결과가 반영되지 않았다 |
| 현재 eval dataset | 20 rows | 20개로 늘었지만 대부분 seed/template/internal checklist 기준이라 “실제 공식 20-case eval”은 아니다 |

## Summary
지금부터는 seed를 “RAG 주 데이터”가 아니라 “CI/demo fallback”으로 낮춰야 한다. 실제 기준선은 `data-pipeline/raw/`의 공식/준공식 source에서 나온 최소 20개 eval case로 다시 잡는다.

핵심 전환은 이거다: `sample_policy_docs.jsonl`로 검색이 되는지 보는 단계는 끝났고, 이제는 raw 공식 데이터로 ingest → chunk → retrieval eval이 통과해야 한다.

## Key Changes
| 작업 | 변경 방향 | 완료 기준 |
|---|---|---|
| Seed 역할 분리 | `sample_policy_docs.jsonl`, `sample_required_docs.jsonl`은 demo/CI fallback으로만 사용 | 기본 ingest에서 seed가 공식 eval 결과를 떠받치지 않는다 |
| Raw-first ingest | 기본 실행은 raw official/source docs + `document_requirements.csv` 중심으로 chunk 생성 | processed `all_chunks.jsonl`에 raw 기반 chunks가 들어간다 |
| Seed flag 추가 | seed는 `--include-demo-seed` 또는 `DAILY_BRIEFING_INCLUDE_DEMO_SEED=true`일 때만 포함 | 운영/공식 eval 경로에서 `seed_*` source가 빠진다 |
| Eval dataset 분리 | smoke eval과 official eval을 분리 | smoke는 seed/template 확인용, official은 실제 20-case Hit@3 gate |
| Official 20-case 재작성 | `rag_retrieval_cases.jsonl`을 실제 raw source_id 기반으로 재구성 | expected_source_ids가 `seed_*` 또는 `document_requirement_*`에 의존하지 않는다 |
| Ingest report 강화 | report에 `seed_records`, `raw_records`, `official_records`, `synthetic_records`를 표시 | seed가 얼마나 섞였는지 한눈에 보인다 |
| Processed 재생성 게이트 | raw ingest 결과로 temp chunks 생성 후 official eval 통과 시 processed 갱신 | 정제/인제스천 때문에 retrieval 품질이 떨어지면 write하지 않는다 |

## Implementation Plan
| 순서 | 작업 | 상세 |
|---|---|---|
| 1 | 현재 seed 계약 고정 | seed 파일은 삭제하지 않고 `demo fallback`으로 명시한다 |
| 2 | ingest 옵션 추가 | `scripts/ingest_rag_docs.py`에 `--include-demo-seed`를 추가하고 기본값은 false로 둔다 |
| 3 | raw source inventory 생성 | raw JSONL과 MD에서 source_id, title, source_type, evidence_grade, doc_type을 추출하는 inventory 함수를 만든다 |
| 4 | official eval 후보 20개 선정 | 법령, 시행령/시행규칙, EPS 절차, HiKorea/정부24 서식, 안전/상담 안내에서 20개 source_id를 고른다 |
| 5 | eval dataset 재구성 | `rag_retrieval_cases.jsonl`은 official 20-case로 바꾸고, 기존 seed/template/internal case는 smoke dataset으로 분리한다 |
| 6 | temp chunk eval gate 추가 | processed overwrite 전에 temp `all_chunks.jsonl`을 만들고 official eval을 먼저 실행한다 |
| 7 | processed chunks 갱신 | official eval 통과 후에만 `data-pipeline/processed/chunks/*.jsonl`을 갱신한다 |
| 8 | 테스트 강화 | seed 미포함 기본값, seed flag 포함, official eval 20개, raw source_id 존재 여부를 테스트한다 |

## Test Plan
| 테스트 | 검증 내용 |
|---|---|
| seed default exclusion test | 기본 ingest에서 `seed_*` source_id가 포함되지 않는다 |
| seed flag inclusion test | `--include-demo-seed`를 켜면 기존 5개 seed가 포함된다 |
| official eval dataset test | `rag_retrieval_cases.jsonl`이 20개 이상이고 `seed_*`, `document_requirement_*`에 의존하지 않는다 |
| raw source coverage test | eval의 모든 `expected_source_ids`가 raw source inventory에 존재한다 |
| ingest report test | report에 seed/raw/official/synthetic count가 나온다 |
| temp eval gate test | official Hit@3가 기준 이하이면 processed write가 차단된다 |
| regression test | raw HTML/PDF/JSONL cleaner 테스트와 기존 RAG indexing 테스트가 계속 통과한다 |

권장 검증 명령은 다음으로 고정한다.

```powershell
uv run pytest backend/tests/test_raw_ingest_cleaning.py backend/tests/test_rag_ingest_quality_gate.py backend/tests/test_rag_eval_dataset.py backend/tests/test_rag_indexing.py -q
uv run python scripts/ingest_rag_docs.py --dry-run --report
```

공식 20-case gate는 별도 명령으로 둔다.

```powershell
uv run python scripts/ingest_rag_docs.py --dry-run --report --eval-dataset evals/datasets/rag_retrieval_cases.jsonl
```

## Acceptance Criteria
| 기준 | 완료 조건 |
|---|---|
| seed 격리 | 기본 ingest/eval에서 `sample_policy_docs.jsonl`이 공식 성능을 떠받치지 않는다 |
| 실제 20개 기준 | official eval 20개가 모두 raw source 기반이다 |
| processed 반영 | `all_chunks.jsonl`이 27개 seed/internal 중심이 아니라 raw 기반 chunks를 포함한다 |
| 안전한 fallback | 빈 raw 환경에서는 seed fallback이 명시 flag 없이는 자동 사용되지 않는다 |
| retrieval gate | official Hit@3가 기준 미만이면 processed write를 막는다 |
| 설명 가능성 | report만 봐도 seed/raw/synthetic/official 비중을 알 수 있다 |

## Assumptions
| 항목 | 기본 결정 |
|---|---|
| seed 파일 삭제 여부 | 삭제하지 않고 demo fallback으로 유지한다 |
| official eval 기준 | 1차 기준은 Hit@3 `>= 0.80`, smoke eval은 `100%` 유지 |
| 내부 checklist | `document_requirements.csv`는 업무 체크리스트로 유지하되 official eval source로 쓰지 않는다 |
| synthetic 데이터 | `F` grade는 demo/테스트에는 가능하지만 공식 답변 근거와 official eval 기준선에서는 제외한다 |
| raw source 우선순위 | 법령/시행령/시행규칙, EPS 절차, HiKorea/정부24 서식, 안전/상담 안내 순서로 20-case를 구성한다 |
