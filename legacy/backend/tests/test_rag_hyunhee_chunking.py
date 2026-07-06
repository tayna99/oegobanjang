from __future__ import annotations

import re

from app.agent_runtime.rag_hyunhee.chunking import (
    OWNER_AGENT,
    RAG_DOMAIN,
    make_chunks,
    normalize_metadata,
    normalize_not_for_legal_basis,
    normalize_text,
    split_text,
    validate_chunk,
)


def _metadata(**overrides):
    base = normalize_metadata(
        {
            "source_id": "safety_vi",
            "title": "Safety Guide",
            "publisher": "KOSHA",
            "source_type": "official_notice",
            "doc_type": "safety",
            "evidence_grade": "B",
            "language": "vi",
            "use_case": "safety_notice,multilingual_contact",
        },
        relative_path="data-pipeline/raw/safety/safety_vi.pdf",
    )
    base.update(overrides)
    return base


def test_normalize_text_collapses_spaces_and_extra_blank_lines():
    text = "  첫 문장   입니다.\r\n\r\n\r\n둘째\t문장입니다.  "

    assert normalize_text(text) == "첫 문장 입니다.\n\n둘째 문장입니다."


def test_split_text_keeps_chunks_under_max_chars():
    text = "\n\n".join(f"{index}번 문장입니다." * 8 for index in range(10))

    chunks = split_text(text, max_chars=80, overlap_chars=0)

    assert chunks
    assert all(len(chunk) <= 80 for chunk in chunks)


def test_split_text_adds_overlap_between_chunks():
    text = " ".join(f"문장{index}입니다." for index in range(40))

    chunks = split_text(text, max_chars=90, overlap_chars=20)

    assert len(chunks) > 1
    assert chunks[0][-20:].strip() in chunks[1]
    assert all(len(chunk) <= 90 for chunk in chunks)


def test_long_paragraph_prefers_sentence_boundaries():
    text = "첫 번째 안전교육 안내 문장입니다. 두 번째 보호구 안내 문장입니다. 세 번째 작업 전 점검 안내 문장입니다."

    chunks = split_text(text, max_chars=45, overlap_chars=0)

    assert len(chunks) >= 2
    assert all(chunk.endswith(("입니다.", "다.", "요.", ".", "?", "!")) for chunk in chunks)


def test_source_type_list_sets_not_for_legal_basis():
    record = {"source_type": ["official_notice", "synthetic_case"]}

    assert normalize_not_for_legal_basis(record) is True


def test_message_template_sets_not_for_legal_basis():
    record = {"source_type": "message_template"}

    assert normalize_not_for_legal_basis(record) is True


def test_make_chunks_builds_contextual_text_and_metadata():
    chunks = make_chunks(
        text="안전교육에 참석해 주세요.",
        metadata=_metadata(),
        max_chars=100,
        overlap_chars=0,
    )

    chunk = chunks[0]
    assert chunk["text"] == "안전교육에 참석해 주세요."
    assert chunk["context"]
    assert chunk["context"] in chunk["contextual_text"]
    assert chunk["text"] in chunk["contextual_text"]
    assert chunk["metadata"]["rag_domain"] == RAG_DOMAIN
    assert chunk["metadata"]["owner_agent"] == OWNER_AGENT
    assert chunk["metadata"]["chunk_char_length"] == len(chunk["text"])


def test_chunk_id_contains_stable_hash_suffix():
    chunk = make_chunks(
        text="안전교육에 참석해 주세요.",
        metadata=_metadata(source_id="source-1"),
        max_chars=100,
        overlap_chars=0,
    )[0]

    assert re.match(r"source-1_chunk_0000_[0-9a-f]{8}$", chunk["chunk_id"])


def test_validate_chunk_accepts_valid_chunk():
    chunk = make_chunks(
        text="안전교육에 참석해 주세요.",
        metadata=_metadata(),
        max_chars=100,
        overlap_chars=0,
    )[0]

    assert validate_chunk(chunk) == []


def test_validate_chunk_reports_missing_context_or_text():
    chunk = make_chunks(
        text="안전교육에 참석해 주세요.",
        metadata=_metadata(),
        max_chars=100,
        overlap_chars=0,
    )[0]
    chunk.pop("context")
    chunk["contextual_text"] = "context only"

    issues = validate_chunk(chunk)

    assert "missing_context" in issues
    assert "contextual_text_invalid" in issues


def test_validate_chunk_reports_invalid_domain_and_owner():
    chunk = make_chunks(
        text="안전교육에 참석해 주세요.",
        metadata=_metadata(rag_domain="workforce", owner_agent="other_agent"),
        max_chars=100,
        overlap_chars=0,
    )[0]

    issues = validate_chunk(chunk)

    assert "invalid_rag_domain" in issues
    assert "invalid_owner_agent" in issues
