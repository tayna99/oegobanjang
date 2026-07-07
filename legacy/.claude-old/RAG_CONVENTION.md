# RAG 구현 경로 규칙

## 핵심 규칙

**모든 RAG 관련 구현은 `backend/app/agent_runtime/rag_hyunwook/` 안에서만 한다.**

```
backend/app/agent_runtime/
├─ rag/              ← 팀 공유 원본. 절대 수정하지 않는다.
└─ rag_hyunwook/     ← 우리 RAG 구현. 여기에만 작업한다.
```

## 이유

- `rag/`는 팀 원격 main에 이미 올라가 있는 기존 구현(로컬 오프라인 임베딩 기반)이다.
- pull/rebase 시 충돌 방지를 위해 `rag/`는 건드리지 않는다.
- 우리 구현(OpenAI text-embedding-3-small + Chroma 벡터 검색)은 `rag_hyunwook/`에 유지한다.

## import 경로

```python
# 올바른 경로
from app.agent_runtime.rag_hyunwook.retriever import RAGRetriever
from app.agent_runtime.rag_hyunwook.embeddings import get_embedding_model
from app.agent_runtime.rag_hyunwook.citation import build_citations
from app.agent_runtime.rag_hyunwook.chunking import maybe_split
from app.agent_runtime.rag_hyunwook.vector_store import get_chroma_store

# 금지
from app.agent_runtime.rag.retriever import ...  # ← rag/ 직접 참조 금지
```

## rag_hyunwook/ 파일 구성

| 파일 | 역할 |
|---|---|
| `embeddings.py` | OpenAI text-embedding-3-small 싱글턴 |
| `vector_store.py` | Chroma 연결 (`.chroma/foreign_hiring`) |
| `retriever.py` | RAGRetriever — confidence ≥ 0.5 필터 |
| `citation.py` | LangChain Document → Citation 변환 |
| `chunking.py` | 800자 초과 chunk 재분할 |

## 새 파일 추가 시

`rag_hyunwook/` 안에 추가하고 `rag_hyunwook/__init__.py`에 export를 등록한다.
`rag/`에는 어떤 파일도 추가하지 않는다.
