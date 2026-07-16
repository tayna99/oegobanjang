"""청킹 통합 모듈.

- 14필드 메타 계약·JSONL 유틸: legacy rag/chunking.py 이식 (계약 유지)
- doc_type별 분할 전략(law 800/procedure 600/form 400/safety 300):
  legacy rag_hyunwook/chunking.py 흡수
- chunk_hash: legacy rag_hyunhee의 내용 해시 ID 방식 흡수 (멱등 upsert용)
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .ingest.domain_splitters import (
    FORM_HEADING_RE,
    LAW_HEADING_RE,
    PROCEDURE_HEADING_RE,
    SAFETY_HEADING_RE,
)

REQUIRED_METADATA_FIELDS = (
    "source_id",
    "title",
    "publisher",
    "source_type",
    "url",
    "retrieved_at",
    "effective_date",
    "doc_type",
    "mission_agent",
    "visa_type",
    "country",
    "industry",
    "risk_level",
    "evidence_grade",
)

# 법령 조문 내 항 번호 패턴 (①②③ 또는 ⑴⑵ 등)
_LAW_CLAUSE_RE = re.compile(r"(?m)^(?=[①②③④⑤⑥⑦⑧⑨⑩]|[⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽])")

_LAW_MAX = 800
_PROCEDURE_MAX = 600
_FORM_MAX = 400
_SAFETY_MAX = 300
_DEFAULT_MAX = 600


def chunk_hash(text: str) -> str:
    """청크 내용 기반 안정 해시 — chunk_id 접미사로 써서 멱등 upsert를 가능하게 한다."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def load_policy_documents(path: str | Path) -> list[dict[str, Any]]:
    source_path = Path(path)
    records: list[dict[str, Any]] = []

    with source_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {source_path}:{line_no}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Invalid JSONL at {source_path}:{line_no}: row must be an object")
            records.append(record)

    return records


def validate_document(document: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_METADATA_FIELDS if field not in document]
    if missing:
        source_id = document.get("source_id", "<unknown>")
        raise ValueError(
            f"Missing metadata for source_id={source_id}: {', '.join(sorted(missing))}"
        )

    content = document.get("content")
    if not isinstance(content, str) or not content.strip():
        source_id = document.get("source_id", "<unknown>")
        raise ValueError(f"Missing content for source_id={source_id}")


def split_text(text: str) -> list[str]:
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    if blocks:
        return blocks
    return [line.strip() for line in text.splitlines() if line.strip()]


def build_chunks(documents: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    for document in documents:
        validate_document(document)
        source_id = str(document["source_id"])
        metadata = {field: document[field] for field in REQUIRED_METADATA_FIELDS}

        for index, text in enumerate(split_text(str(document["content"])), start=1):
            chunks.append(
                {
                    "chunk_id": f"{source_id}__{index:04d}",
                    "source_id": source_id,
                    "title": document["title"],
                    "text": text,
                    "metadata": metadata,
                }
            )

    return chunks


def write_chunks_jsonl(chunks: Iterable[dict[str, Any]], path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    return output_path


def _preamble_chunks(text: str, first_start: int, max_chars: int) -> list[str]:
    """첫 헤딩 매치 이전의 서두 텍스트 보존.

    legacy 구현은 spans[0].start() 이전 텍스트를 조용히 버려 절차/법령 문서의
    도입부(예: 제출 서류 목록 1~4번)가 유실됐다. 이식하면서 수정한다.
    """
    preamble = text[:first_start].strip()
    if not preamble:
        return []
    return _split_default(preamble, max_chars)


def _split_by_pattern(text: str, pattern: re.Pattern, max_chars: int) -> list[str]:
    spans = list(pattern.finditer(text))
    if not spans:
        return _split_default(text, max_chars)

    chunks: list[str] = _preamble_chunks(text, spans[0].start(), max_chars)
    for i, match in enumerate(spans):
        start = match.start()
        end = spans[i + 1].start() if i + 1 < len(spans) else len(text)
        block = text[start:end].strip()
        if not block:
            continue
        if len(block) <= max_chars:
            chunks.append(block)
        else:
            chunks.extend(_split_default(block, max_chars))
    return chunks


def _split_default(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chars,
        chunk_overlap=0,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )
    return [doc.page_content for doc in splitter.create_documents([text])]


def _split_law_article(text: str) -> list[str]:
    spans = list(LAW_HEADING_RE.finditer(text))
    if not spans:
        return _split_default(text, _LAW_MAX)

    chunks: list[str] = _preamble_chunks(text, spans[0].start(), _LAW_MAX)
    for i, match in enumerate(spans):
        start = match.start()
        end = spans[i + 1].start() if i + 1 < len(spans) else len(text)
        article = text[start:end].strip()
        if not article:
            continue
        if len(article) <= _LAW_MAX:
            chunks.append(article)
        else:
            # 항 단위 2차 분리
            sub_spans = list(_LAW_CLAUSE_RE.finditer(article))
            if sub_spans:
                chunks.extend(_split_by_pattern(article, _LAW_CLAUSE_RE, _LAW_MAX))
            else:
                chunks.extend(_split_default(article, _LAW_MAX))
    return chunks


def _split_procedure_step(text: str) -> list[str]:
    spans = list(PROCEDURE_HEADING_RE.finditer(text))
    if not spans:
        return _split_default(text, _PROCEDURE_MAX)

    chunks: list[str] = _preamble_chunks(text, spans[0].start(), _PROCEDURE_MAX)
    prev_heading = ""
    for i, match in enumerate(spans):
        start = match.start()
        end = spans[i + 1].start() if i + 1 < len(spans) else len(text)
        block = text[start:end].strip()
        if not block:
            prev_heading = match.group("head").strip()
            continue
        if len(block) <= _PROCEDURE_MAX:
            chunks.append(block)
        else:
            sub_blocks = _split_default(block, _PROCEDURE_MAX)
            # 첫 서브블록 외에는 앞 단계 제목을 오버랩으로 prepend
            for j, sub in enumerate(sub_blocks):
                if j > 0 and prev_heading:
                    chunks.append(f"{prev_heading}\n{sub}")
                else:
                    chunks.append(sub)
        prev_heading = match.group("head").strip()
    return chunks


def _split_form_section(text: str) -> list[str]:
    return _split_by_pattern(text, FORM_HEADING_RE, _FORM_MAX)


def _split_safety_section(text: str) -> list[str]:
    return _split_by_pattern(text, SAFETY_HEADING_RE, _SAFETY_MAX)


def chunk_document(text: str, doc_type: str, metadata: dict | None = None) -> list[str]:
    """doc_type에 따라 소스별 청킹 전략을 선택해 텍스트를 분리한다."""
    if doc_type == "law":
        return _split_law_article(text)
    if doc_type == "procedure":
        return _split_procedure_step(text)
    if doc_type == "form":
        return _split_form_section(text)
    if doc_type == "safety":
        return _split_safety_section(text)
    return _split_default(text, _DEFAULT_MAX)
