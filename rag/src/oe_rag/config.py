from __future__ import annotations

import os
from pathlib import Path

# src/oe_rag/config.py → parents[2] = rag/ 프로젝트 루트
RAG_ROOT = Path(__file__).resolve().parents[2]
# legacy와 동일한 data-pipeline/ 레이아웃 유지 — .md/.txt 원문의 source_id가
# root 기준 상대 경로(sha1)로 파생되므로 레이아웃이 곧 ID 계약이다.
DATA_PIPELINE_DIR = RAG_ROOT / "data-pipeline"
RAW_DIR = DATA_PIPELINE_DIR / "raw"
SEED_DIR = DATA_PIPELINE_DIR / "seed"
PROCESSED_DIR = DATA_PIPELINE_DIR / "processed"
CHUNKS_DIR = PROCESSED_DIR / "chunks"
EVALS_DIR = RAG_ROOT / "evals"
DATASETS_DIR = EVALS_DIR / "datasets"
REPORTS_DIR = EVALS_DIR / "reports"

# pgvector 연결 (전용 `rag` 스키마 사용 — 정본 db/schema.sql 비침범)
DEFAULT_PG_URL = "postgresql+psycopg://postgres:postgres@localhost:55433/oegobanjang_rag"


def pg_url() -> str:
    return os.getenv("RAG_PG_URL", DEFAULT_PG_URL)


def env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
