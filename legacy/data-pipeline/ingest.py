from __future__ import annotations

import json
import sys
from pathlib import Path
from langchain_core.documents import Document

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agent_runtime.rag_hyunwook.embeddings import get_embedding_model
from app.agent_runtime.rag_hyunwook.chunking import maybe_split
from app.agent_runtime.rag_hyunwook.vector_store import get_chroma_store


RAW_DIR = ROOT_DIR / "data-pipeline" / "raw"

VISA_SOURCE_DIRS = ["eps", "laws", "안전", "정부24_hikorea"]


def load_chunks_from_raw(raw_dir: Path = RAW_DIR) -> list[Document]:
  """Load visa-agent source docs from raw/{eps,laws,안전,정부24_hikorea}/*.jsonl"""
  documents = []

  for subdir in VISA_SOURCE_DIRS:
    subdir_path = raw_dir / subdir
    if not subdir_path.exists():
      continue
    for jsonl_file in sorted(subdir_path.rglob("*.jsonl")):
      with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
          if not line.strip():
            continue
          data = json.loads(line)
          # 필드가 최상위 또는 중첩 metadata 안에 있을 수 있음
          meta = data.get("metadata") or {}
          def _field(key: str) -> str:
            return data.get(key) or meta.get(key) or ""
          visa_type_raw = data.get("visa_type") or meta.get("visa_type")
          visa_type = visa_type_raw[0] if isinstance(visa_type_raw, list) else (visa_type_raw or "")
          mission_agent_raw = data.get("mission_agent") or meta.get("mission_agent")
          mission_agent = ",".join(mission_agent_raw) if isinstance(mission_agent_raw, list) else (mission_agent_raw or "")
          doc = Document(
            page_content=data.get("content", ""),
            metadata={
              "source_id": _field("source_id"),
              "title": _field("title"),
              "publisher": _field("publisher"),
              "source_type": _field("source_type"),
              "doc_type": _field("doc_type"),
              "evidence_grade": _field("evidence_grade"),
              "visa_type": visa_type,
              "mission_agent": mission_agent,
              "retrieved_at": _field("retrieved_at"),
            }
          )
          documents.append(doc)

  return documents


def split_long_documents(documents: list[Document]) -> list[Document]:
  """Split documents longer than 800 chars using maybe_split"""
  result = []
  for doc in documents:
    result.extend(maybe_split(doc))
  return result


def ingest_to_chroma() -> dict[str, object]:
  """Load chunks, split if needed, embed, and store in Chroma"""

  # Load
  documents = load_chunks_from_raw()
  initial_count = len(documents)

  # Split
  split_docs = split_long_documents(documents)
  split_count = len(split_docs)

  # Embed & Store
  embeddings = get_embedding_model()
  store = get_chroma_store()

  # Add documents to Chroma (batch processing)
  store.add_documents(split_docs)

  return {
    "initial_chunks": initial_count,
    "after_split": split_count,
    "embedded_and_stored": split_count,
    "chroma_collection": store._collection.name if hasattr(store, "_collection") else "foreign_hiring",
  }


if __name__ == "__main__":
  result = ingest_to_chroma()
  print(result)
