# Raw HTML/PDF 인제스천 안정화 플랜

## Summary
진짜 `raw/` 데이터에 HTML, PDF, 표가 들어와도 RAG 청크가 조용히 망가지지 않도록, “정제 로직”보다 먼저 “회귀 검증 게이트”를 세운다. 현재 20-case retrieval eval을 기준선으로 삼고, 정제 전후 Hit@3가 떨어지면 병합하지 않는 구조로 간다.

핵심 원칙은 이거다: HTML/PDF를 더 많이 읽되, 품질 검증 없이 processed chunk에 넣지 않는다.

## Key Changes
| 작업 | 구현 방향 | 이유 |
|---|---|---|
| Raw loader 통합 | `scripts/ingest_rag_docs.py`의 확장자 처리를 `.txt`, `.md`, `.html`, `.htm`, `.pdf`, `.jsonl`로 확장 | 지금은 `.pdf`가 무시되고 `.jsonl` 경로가 분리돼 있어 데이터 흐름이 헷갈린다 |
| JSONL 경로 명시 | `.jsonl`은 “이미 청크화된 curated source”로 다루고 HTML/PDF cleaner를 태우지 않는다 | `raw/laws/*.jsonl` 같은 기존 crawler 산출물과 새 raw 문서 처리를 구분해야 한다 |
| HTML 정제 | `script/style/nav/footer/header/aside/form` 제거, `main/article` 우선 추출, 없으면 body 기반 추출 | 실제 HTML이 들어와도 `<script>`, `<div>` 태그가 청크에 섞이지 않게 한다 |
| 표 처리 | table을 row-preserving text로 변환: `컬럼명: 값 | 컬럼명: 값` 형태 유지 | “기간 / 30일” 같은 의미가 셀 분리로 깨지는 것을 막는다 |
| PDF 처리 | PDF를 page 단위로 텍스트 추출하고 `page_number`, `source_path`, `source_hash` 메타데이터 유지 | PDF를 조용히 무시하지 않고 citation 추적 가능한 chunk로 만든다 |
| Quality gate | chunk 생성 후 HTML tag residue, 너무 짧은 chunk, parser warning, missing source metadata를 검사 | 정제 실패가 RAG 품질 저하로 조용히 들어가는 것을 막는다 |
| Quarantine | 파싱 실패/품질 실패 문서는 processed에 넣지 않고 quarantine report에 기록 | “대충 넣기”보다 “막고 이유 남기기”가 안전하다 |
| Ingestion report | run마다 입력 파일 수, 확장자별 처리 수, 생성 chunk 수, warning, quarantined 문서 수 출력 | 운영자가 raw 데이터 품질을 볼 수 있어야 한다 |
| Eval before/after | 기존 20-case Hit@3 baseline 저장 후 새 cleaner 적용 결과와 비교 | 정제 때문에 retrieval 성능이 떨어지는지 바로 확인한다 |

## Implementation Plan
| 순서 | 작업 | 완료 기준 |
|---|---|---|
| 1 | 현재 `scripts/ingest_rag_docs.py`의 raw walker와 supported extension 계약을 정리한다 | `.jsonl`과 raw document 처리 경로가 문서/코드에서 분리된다 |
| 2 | 공용 raw document cleaner를 추가한다 | HTML, PDF, txt/md, jsonl이 같은 품질 검사 인터페이스를 통과한다 |
| 3 | HTML cleaner를 붙인다 | 샘플 HTML에서 script/style/div 태그가 최종 chunk에 남지 않는다 |
| 4 | Table serializer를 붙인다 | table header와 row value가 같은 chunk에서 의미 있게 보존된다 |
| 5 | PDF loader를 붙인다 | 샘플 PDF가 page metadata와 함께 chunk로 생성된다 |
| 6 | Quality gate와 quarantine report를 추가한다 | 품질 실패 문서는 processed output에 들어가지 않는다 |
| 7 | 20-case retrieval eval을 ingest gate로 연결한다 | 새 인제스천 결과의 Hit@3가 baseline보다 낮으면 실패 처리한다 |
| 8 | 기존 crawler JSONL 경로는 보존한다 | `raw/laws/*.jsonl` 같은 기존 데이터가 중복 정제되지 않는다 |

## Acceptance Criteria
| 항목 | 기준 |
|---|---|
| HTML tag leak 방지 | 최종 chunk에 `<script>`, `<style>`, `<div>`, `<td>`, `<tr>` 같은 원본 태그가 남지 않는다 |
| PDF 처리 | `.pdf` 파일이 walker에서 무시되지 않고 page 단위 chunk로 처리된다 |
| JSONL 호환 | 기존 `raw/**/*.jsonl` curated chunks는 기존 의미를 유지한다 |
| 표 의미 보존 | 표 row는 header-value 형태로 변환되어 검색 가능한 텍스트가 된다 |
| 품질 실패 차단 | parser 실패 또는 tag residue 발생 문서는 quarantine 처리된다 |
| Eval 회귀 방지 | 기존 20-case retrieval eval의 Hit@3가 baseline보다 떨어지면 실패한다 |
| 보고 가능성 | ingest report에 processed, skipped, quarantined, warning count가 남는다 |

## Test Plan
| 테스트 | 내용 |
|---|---|
| HTML cleaner unit test | script/style/nav/footer 제거, 본문 추출, 태그 잔류 없음 검증 |
| Table serializer test | header와 row value가 함께 보존되는지 검증 |
| PDF loader test | page별 텍스트와 page metadata 생성 검증 |
| JSONL compatibility test | curated jsonl record가 raw cleaner로 오염되지 않는지 검증 |
| Quality gate test | tag residue가 있는 chunk를 실패 처리하는지 검증 |
| Ingest integration test | 샘플 raw dir을 ingest해서 chunk/report/quarantine 결과 검증 |
| Retrieval regression test | 20-case Hit@3 baseline 대비 하락 없음 검증 |

권장 검증 명령은 다음으로 고정한다.

```powershell
uv run pytest backend/tests/test_rag_eval_dataset.py backend/tests/test_rag_indexing.py
uv run pytest backend/tests/test_raw_ingest_cleaning.py backend/tests/test_rag_ingest_quality_gate.py
```

추가로 ingestion 결과 비교용 명령을 하나 둔다.

```powershell
uv run python scripts/ingest_rag_docs.py --dry-run --report
```

## Assumptions
- MVP에서는 사이트별 CSS selector를 무리하게 만들지 않고, generic cleaner를 먼저 적용한다.
- Readability/Trafilatura 같은 본문 추출기는 바로 기본값으로 쓰지 않고, eval 통과 후 optional fallback으로 둔다.
- PDF table extraction은 완전한 표 복원이 아니라 page text + row-preserving fallback부터 시작한다.
- 기존 crawler가 만든 `.jsonl`은 신뢰된 curated source로 보고, 새 raw document cleaner와 분리한다.
- processed chunk overwrite는 dry-run report와 20-case eval gate가 통과한 뒤에만 허용한다.
