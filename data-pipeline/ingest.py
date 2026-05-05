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


def load_chunks_from_raw(raw_dir: Path = RAW_DIR) -> list[Document]:
  """Load 729 chunks from raw/{laws,eps,gov24_hikoska,safety}/*.jsonl"""
  documents = []

  for jsonl_file in sorted(raw_dir.rglob("*.jsonl")):
    with open(jsonl_file, "r", encoding="utf-8") as f:
      for line in f:
        if not line.strip():
          continue
        data = json.loads(line)
        doc = Document(
          page_content=data.get("content", ""),
          metadata={
            "source_id": data.get("source_id", ""),
            "title": data.get("title", ""),
            "publisher": data.get("publisher", ""),
            "source_type": data.get("source_type", ""),
            "doc_type": data.get("doc_type", ""),
            "evidence_grade": data.get("evidence_grade", ""),
            "visa_type": data.get("visa_type"),
            "mission_agent": data.get("mission_agent"),
            "retrieved_at": data.get("retrieved_at", ""),
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
