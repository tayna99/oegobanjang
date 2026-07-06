from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any


DEFAULT_MAX_CHARS = 1000
DEFAULT_OVERLAP_CHARS = 150
RAG_DOMAIN = "multilingual_contact"
OWNER_AGENT = "multilingual_contact_agent"
NON_LEGAL_BASIS_SOURCE_TYPES = {
    "message_template",
    "public_case_reference",
    "synthetic_case",
    "interview_case_pattern",
}


def stable_id(*parts: str) -> str:
    raw = "::".join(part for part in parts if part)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def now_iso_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    pattern = re.compile(r".+?(?:니다\.|다\.|요\.|[.!?](?:\s+|$)|$)", re.DOTALL)
    sentences = [match.group(0).strip() for match in pattern.finditer(text)]
    return [sentence for sentence in sentences if sentence]


def _split_by_chars(text: str, max_chars: int) -> list[str]:
    return [text[i : i + max_chars].strip() for i in range(0, len(text), max_chars) if text[i : i + max_chars].strip()]


def _split_long_unit(unit: str, max_chars: int) -> list[str]:
    if len(unit) <= max_chars:
        return [unit]

    pieces: list[str] = []
    current = ""
    for sentence in split_sentences(unit):
        if len(sentence) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_split_by_chars(sentence, max_chars))
            continue

        separator = " " if current else ""
        if len(current) + len(separator) + len(sentence) <= max_chars:
            current = f"{current}{separator}{sentence}"
        else:
            if current:
                pieces.append(current)
            current = sentence
    if current:
        pieces.append(current)
    return pieces or _split_by_chars(unit, max_chars)


def _tail_overlap(text: str, overlap_chars: int) -> str:
    if overlap_chars <= 0:
        return ""
    if len(text) <= overlap_chars:
        return text
    return text[-overlap_chars:].strip()


def split_text(
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be smaller than max_chars")

    target_chars = max_chars if overlap_chars <= 0 else max_chars - overlap_chars - 2
    target_chars = max(1, target_chars)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    units: list[str] = []
    for paragraph in paragraphs:
        units.extend(_split_long_unit(paragraph, target_chars))

    chunks: list[str] = []
    current = ""

    for unit in units:
        if not current:
            current = unit
            continue

        separator = "\n\n" if "\n" in current or "\n" in unit else " "
        if len(current) + len(separator) + len(unit) <= target_chars:
            current = f"{current}{separator}{unit}"
        else:
            chunks.append(current)
            current = unit

    if current:
        chunks.append(current)

    if overlap_chars <= 0:
        return [chunk for chunk in chunks if chunk]

    overlapped: list[str] = []
    previous = ""
    for chunk in chunks:
        if not previous:
            overlapped.append(chunk)
            previous = chunk
            continue
        overlap = _tail_overlap(previous, overlap_chars)
        combined = f"{overlap}\n\n{chunk}" if overlap else chunk
        if len(combined) > max_chars:
            combined = combined[-max_chars:].strip()
        overlapped.append(combined)
        previous = chunk

    return [chunk for chunk in overlapped if chunk]


def to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        output: list[str] = []
        for item in value:
            output.extend(to_list(item))
        return output
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
        return [part for part in parts if part]
    return [str(value)]


def normalize_not_for_legal_basis(record: dict[str, Any]) -> bool:
    value = record.get("not_for_legal_basis")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    return bool(set(to_list(record.get("source_type"))).intersection(NON_LEGAL_BASIS_SOURCE_TYPES))


def format_list(value: Any) -> str:
    return ", ".join(to_list(value))


def build_context_prefix(metadata: dict[str, Any]) -> str:
    publisher = metadata.get("publisher") or "출처 미상"
    title = metadata.get("title") or "제목 없음"
    doc_type = metadata.get("doc_type") or "unknown"
    language = format_list(metadata.get("language"))
    page_number = metadata.get("page_number")
    file_type = metadata.get("file_type") or "document"

    if page_number not in (None, ""):
        location = f"PDF {page_number}페이지"
    else:
        location = f"{file_type} 문서"

    return (
        f"이 chunk는 {publisher}의 '{title}' {location}에서 추출되었다. "
        f"문서 유형은 {doc_type}이고, 언어는 {language or '미지정'}이며, "
        "multilingual_contact RAG에서 safety_notice, multilingual_contact, "
        "worker_support, rag 용도로 참고할 수 있다."
    )


def normalize_metadata(
    record: dict[str, Any],
    *,
    relative_path: str,
    page_number: int | None = None,
) -> dict[str, Any]:
    metadata = {
        "source_id": record.get("source_id") or stable_id(relative_path),
        "title": record.get("title", ""),
        "publisher": record.get("publisher", ""),
        "source_type": to_list(record.get("source_type")),
        "url": record.get("url", ""),
        "retrieved_at": record.get("retrieved_at") or now_iso_date(),
        "doc_type": record.get("doc_type", ""),
        "evidence_grade": (to_list(record.get("evidence_grade")) or [""])[0],
        "use_case": to_list(record.get("use_case")),
        "language": to_list(record.get("language")),
        "raw_path": record.get("raw_path") or relative_path,
        "file_type": record.get("file_type") or "",
        "rag_domain": RAG_DOMAIN,
        "owner_agent": OWNER_AGENT,
        "ingest_target": bool(record.get("ingest_target", True)),
        "not_for_legal_basis": normalize_not_for_legal_basis(record),
        "contains_personal_data": bool(record.get("contains_personal_data", False)),
        "source_path": relative_path,
    }
    if page_number is not None:
        metadata["page_number"] = page_number
    return metadata


def make_chunks(
    *,
    text: str,
    metadata: dict[str, Any],
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[dict[str, Any]]:
    chunks = split_text(text, max_chars=max_chars, overlap_chars=overlap_chars)
    if not chunks:
        return []

    output: list[dict[str, Any]] = []
    page_number = metadata.get("page_number")
    context = build_context_prefix(metadata)
    for index, chunk_text in enumerate(chunks):
        chunk_hash = stable_id(chunk_text)[:8]
        if page_number in (None, ""):
            chunk_id = f"{metadata['source_id']}_chunk_{index:04d}_{chunk_hash}"
        else:
            chunk_id = f"{metadata['source_id']}_page_{int(page_number):04d}_chunk_{index:04d}_{chunk_hash}"

        contextual_text = f"{context}\n\n{chunk_text}"
        output.append(
            {
                "chunk_id": chunk_id,
                "source_id": metadata["source_id"],
                "text": chunk_text,
                "context": context,
                "contextual_text": contextual_text,
                "metadata": {
                    **metadata,
                    "chunk_id": chunk_id,
                    "chunk_index": index,
                    "chunk_char_length": len(chunk_text),
                },
            }
        )

    return output


def validate_chunk(record: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    required_top = ("chunk_id", "source_id", "text", "context", "contextual_text", "metadata")
    for field in required_top:
        if field not in record:
            reasons.append(f"missing_{field}")

    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    for field in ("source_id", "title", "publisher", "doc_type", "evidence_grade", "raw_path"):
        if not metadata.get(field):
            reasons.append(f"missing_metadata_{field}")

    context = record.get("context")
    text = record.get("text")
    contextual_text = record.get("contextual_text")
    if not isinstance(contextual_text, str) or not contextual_text.strip():
        reasons.append("missing_contextual_text")
    elif isinstance(context, str) and isinstance(text, str):
        if context not in contextual_text or text not in contextual_text:
            reasons.append("contextual_text_invalid")
        if len(contextual_text) <= len(text):
            reasons.append("contextual_text_not_longer_than_text")
    else:
        reasons.append("contextual_text_invalid")

    if metadata.get("rag_domain") != RAG_DOMAIN:
        reasons.append("invalid_rag_domain")
    if metadata.get("owner_agent") != OWNER_AGENT:
        reasons.append("invalid_owner_agent")
    if not isinstance(metadata.get("not_for_legal_basis"), bool):
        reasons.append("invalid_metadata_not_for_legal_basis")
    if not isinstance(metadata.get("contains_personal_data"), bool):
        reasons.append("invalid_metadata_contains_personal_data")

    if set(to_list(metadata.get("source_type"))).intersection(NON_LEGAL_BASIS_SOURCE_TYPES):
        if metadata.get("not_for_legal_basis") is not True:
            reasons.append("non_legal_source_requires_not_for_legal_basis")

    if isinstance(text, str):
        if metadata.get("chunk_char_length") != len(text):
            reasons.append("invalid_chunk_char_length")

    return reasons
