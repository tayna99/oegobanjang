"""다국어 컨택 로더 — HTML 정제·품질 게이트.

legacy 조사(2026-07-17)로 원본 corpus의 47%가 HTML 태그 잔재로 오염돼 있음을 발견했다
(레거시 인제스트 스크립트가 raw_ingest.clean_html_document()를 쓰지 않고 자체 재구현하며
정제를 누락). 이 테스트는 이식본의 정제 파이프라인이 실제로 오염을 제거하는지 검증한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from oe_rag.multilingual import (
    build_multilingual_vector_records,
    load_multilingual_contact_records,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _base_metadata(**overrides: object) -> dict:
    metadata = {
        "source_id": "demo_source",
        "title": "데모 안내",
        "publisher": "demo",
        "doc_type": "counseling",
        "evidence_grade": "B",
        "raw_path": "data-pipeline/raw/demo.html",
        "rag_domain": "multilingual_contact",
        "owner_agent": "multilingual_contact_agent",
        "ingest_target": True,
        "not_for_legal_basis": False,
        "language": ["ko", "vi"],
        "use_case": ["multilingual_contact"],
    }
    metadata.update(overrides)
    return metadata


def test_strips_html_boilerplate_and_keeps_real_content(tmp_path: Path) -> None:
    path = tmp_path / "all_chunks.jsonl"
    _write_jsonl(
        path,
        [
            {
                "chunk_id": "demo_chunk_0000",
                "source_id": "demo_source",
                "text": "<nav><ul><li><a href='#'>메뉴</a></li></ul></nav>",
                "context": "이 chunk는 데모 문서에서 추출되었다.",
                "metadata": _base_metadata(),
            },
            {
                "chunk_id": "demo_chunk_0001",
                "source_id": "demo_source",
                "text": "<article><h1>상담센터 안내</h1><p>대표번호는 1577-0071이다.</p></article>",
                "context": "이 chunk는 데모 문서에서 추출되었다.",
                "metadata": _base_metadata(),
            },
        ],
    )

    records, quarantined = load_multilingual_contact_records(path)

    assert len(records) == 1
    assert records[0].id == "demo_chunk_0001"
    assert "1577-0071" in records[0].text
    assert "<" not in records[0].text
    assert len(quarantined) == 1
    assert quarantined[0]["reason"] == "empty_after_html_cleanup"


def test_strips_unterminated_script_and_table_fragments_at_chunk_boundary(tmp_path: Path) -> None:
    """청크 경계에서 <script>/<td>가 끊겨도(전체 문서가 아니라 파편이므로) 새어나오면 안 된다."""
    path = tmp_path / "all_chunks.jsonl"
    _write_jsonl(
        path,
        [
            {
                "chunk_id": "demo_chunk_table",
                "source_id": "demo_source",
                "text": "<td>12월 31일</td>\n<td>정기 안전점검</td>\n<tr><td>실적 요약</td>",
                "context": "표 조각",
                "metadata": _base_metadata(),
            },
        ],
    )

    records, quarantined = load_multilingual_contact_records(path)
    # 표 조각 텍스트는 태그만 제거된 채 내용이 남을 수 있고, 없을 수도 있다 — 어느 쪽이든
    # 살아남은 레코드에 원시 태그 마커는 절대 없어야 한다는 것이 핵심 불변식이다.
    for record in records:
        assert "<" not in record.text and ">" not in record.text


def test_quarantines_pure_javascript_residue_without_tag_markers(tmp_path: Path) -> None:
    path = tmp_path / "all_chunks.jsonl"
    _write_jsonl(
        path,
        [
            {
                "chunk_id": "demo_chunk_js",
                "source_id": "demo_source",
                "text": (
                    "hasItem: function (sKey) {\n"
                    "return (new RegExp(sKey)).test(document.cookie);\n"
                    "},\n"
                    "var _srcDoc = window.srcDoc;\n"
                ),
                "context": "스크립트 잔재",
                "metadata": _base_metadata(),
            }
        ],
    )

    records, quarantined = load_multilingual_contact_records(path)

    assert records == []
    assert quarantined[0]["reason"] == "script_residue"


def test_quality_gate_rejects_low_evidence_grade_and_non_ingest_target(tmp_path: Path) -> None:
    path = tmp_path / "all_chunks.jsonl"
    _write_jsonl(
        path,
        [
            {
                "chunk_id": "demo_f_grade",
                "source_id": "demo_source",
                "text": "합성 케이스 예시입니다.",
                "context": "합성",
                "metadata": _base_metadata(evidence_grade="F"),
            },
            {
                "chunk_id": "demo_not_ingest",
                "source_id": "demo_source",
                "text": "인제스트 대상이 아닌 참고 텍스트입니다.",
                "context": "참고",
                "metadata": _base_metadata(ingest_target=False),
            },
        ],
    )

    records, quarantined = load_multilingual_contact_records(path)

    assert records == []
    reasons = {q["reason"] for q in quarantined}
    assert reasons == {"low_evidence_grade", "not_ingest_target"}


def test_build_multilingual_vector_records_tags_collection(tmp_path: Path) -> None:
    path = tmp_path / "all_chunks.jsonl"
    _write_jsonl(
        path,
        [
            {
                "chunk_id": "demo_chunk_0000",
                "source_id": "demo_source",
                "text": "상담센터 대표번호는 1577-0071이다.",
                "context": "이 chunk는 데모 문서에서 추출되었다.",
                "metadata": _base_metadata(),
            }
        ],
    )

    records, _ = load_multilingual_contact_records(path)
    vector_records = build_multilingual_vector_records(records)

    assert vector_records[0]["metadata"]["collection"] == "multilingual_contact"
    assert "1577-0071" in vector_records[0]["text"]
    assert "이 chunk는 데모 문서에서 추출되었다" in vector_records[0]["text"]  # contextual prefix 보존


def test_real_corpus_snapshot_is_fully_clean() -> None:
    """rag/data-pipeline/processed/chunks/multilingual_contact/all_chunks.jsonl(legacy 스냅샷)
    전건이 정제 후 태그 잔재 없이 로드되는지 회귀 검증한다."""
    records, quarantined = load_multilingual_contact_records()

    assert len(records) > 0
    assert len(records) + len(quarantined) == 1022
    for record in records:
        assert "<" not in record.text
        assert "function(" not in record.text
        assert "document.addEventListener" not in record.text
