# 외고반장 RAG 인제스천 파이프라인

문서 수집 → 파싱/전처리 → 청킹 → 메타 검증 → pgvector 적재 → LangChain 1.x/LangGraph 검색 연동.
`legacy/backend/app/agent_runtime/rag*` 자산을 복사·정제해 이식한 독립 uv 프로젝트입니다 (legacy는 읽기 전용 소스).

## 요구사항

- Python 3.12~3.13 (`backend/`의 3.14 핀과 분리 — langchain 스택 호환)
- uv
- pgvector PostgreSQL (인덱싱/검색 시): `docker run -d --name oegobanjang-rag-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=oegobanjang_rag -p 55433:5432 pgvector/pgvector:pg16`

## 사용법

```bash
cd rag
uv sync --python 3.13

# 1) 수집·청킹 (data-pipeline/raw + seed → processed/chunks/*.jsonl)
uv run python -m oe_rag.pipeline --report

# 2) 인덱싱 (pgvector 적재, 기본 provider=deterministic)
uv run python -m oe_rag.cli index --embedding-provider deterministic --reset

# 3) 검색 평가 게이트 (hit@3 >= 0.80)
uv run python -m oe_rag.cli eval

# 4) 오프라인 스모크 (FakeChatModel)
uv run python -m oe_rag.cli chat --offline

# 5) 다국어 컨택 컬렉션 인덱싱 (사전 빌드 청크 → HTML 정제 → pgvector)
uv run python -m oe_rag.cli index-multilingual --embedding-provider deterministic --reset
uv run python -m oe_rag.cli query-multilingual "상담센터 전화번호가 뭐예요?" --intent counseling

# 테스트
uv run pytest
```

## 3개 검색 도메인

| 도메인 | 컬렉션 | 도구(@tool) | 코퍼스 |
|---|---|---|---|
| 신규 인력 확보(워크포스) | `workforce_official`/`workforce_templates` | `retrieve_workforce_materials` | `data-pipeline/raw/**` (법령·EPS 절차·서식) |
| 비자서류·체류 절차 | `workforce_official`(재사용) | `search_policy_documents` | 별도 코퍼스 없음 — 워크포스 컬렉션을 visa_type/evidence_grade로 재필터링(legacy 조사 결과 rag_hyunwook에 별도 원천 없음 확인) |
| 다국어 컨택 | `multilingual_contact` | `search_multilingual_contact_materials` | `data-pipeline/processed/chunks/multilingual_contact/*.jsonl` (사전 빌드 스냅샷 — 원본 raw HTML은 legacy에서 이미 소실, `oe_rag/multilingual.py`가 로드 시 HTML 태그 잔재를 재정제) |

## 계약 (legacy/docs/RAG_STRATEGY.md 정본 유지)

- 14필드 메타 + `evidence_grade` A~F (F=합성 — 답변 근거 사용 금지, D/F는 워크포스 컬렉션 제외)
- `chunk_id = {source_id}_chunk_{index:04d}_{내용해시8}` — 멱등 upsert
- 임베딩 provider: `WORKFORCE_RAG_EMBEDDING_PROVIDER=deterministic|openai|auto` (색인과 질의는 반드시 동일 provider)
- 검색 0건 시 JSONL fallback 금지 — `MISSING_EVIDENCE`로 응답
- `rag_retrieved` 이벤트에 청크 원문·민감정보 저장 금지 (질의 해시·source_id·등급만)

## 데이터 레이아웃

`data-pipeline/{raw,seed,processed}` — legacy와 동일 레이아웃 유지.
`.md`/`.txt` 원문의 source_id가 루트 기준 상대 경로 sha1로 파생되므로 레이아웃이 곧 ID 계약입니다.
HWP/DOCX 파서는 범위 밖 — 정부 서식 HWP는 txt/pdf로 변환해 `data-pipeline/raw/`에 투입하세요.
