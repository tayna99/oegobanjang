from __future__ import annotations

import re

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.agent_runtime.rag.domain_splitters import (
    FORM_HEADING_RE,
    LAW_HEADING_RE,
    PROCEDURE_HEADING_RE,
    SAFETY_HEADING_RE,
)

MAX_CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# 법령 조문 내 항 번호 패턴 (①②③ 또는 ⑴⑵ 또는 1. 2. 등)
_LAW_CLAUSE_RE = re.compile(r"(?m)^(?=[①②③④⑤⑥⑦⑧⑨⑩]|[⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽])")

_LAW_MAX = 800
_PROCEDURE_MAX = 600
_FORM_MAX = 400
_SAFETY_MAX = 300
_DEFAULT_MAX = 600


def _split_by_pattern(text: str, pattern: re.Pattern, max_chars: int) -> list[str]:
    spans = list(pattern.finditer(text))
    if not spans:
        return _split_default(text, max_chars)

    chunks: list[str] = []
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

    chunks: list[str] = []
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

    chunks: list[str] = []
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


def maybe_split(doc: Document) -> list[Document]:
    doc_type = (doc.metadata or {}).get("doc_type", "")
    chunks = chunk_document(doc.page_content, doc_type, doc.metadata)
    if len(chunks) == 1 and chunks[0] == doc.page_content:
        return [doc]
    return [Document(page_content=c, metadata=doc.metadata) for c in chunks if c.strip()]
