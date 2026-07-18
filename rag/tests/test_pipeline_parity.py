"""이식 패리티·무손실 검증.

검수 결과 legacy 커밋 산출물(2026-05, all_chunks.jsonl 964청크)은
① doc_type 청킹 전략 도입 이전(구 split_text(1200) 방식)이고
② seed CSV 데이터도 이후 수정되어(document_requirements.csv 등)
텍스트 단위 비교 대상이 될 수 없다. 또한 legacy 청킹 코드에는 첫 헤딩 매치 이전
서두를 버리는 콘텐츠 유실 버그가 있어 이식 시 수정했다(chunking._preamble_chunks).

따라서 이 테스트는 다음을 검증한다:
1. baseline 대비 source_id 집합 패리티 — 수집 완전성 (데이터 소스 누락 없음)
2. 입력 대비 무손실 — 모든 입력 레코드의 각 줄이 산출 청크에 보존됨
3. 결정성 — 같은 입력에서 두 번 빌드 시 동일 산출
4. 재생성 기준 수치 고정 — 회귀 감지용
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from oe_rag import pipeline
from oe_rag.config import RAG_ROOT

LEGACY_BASELINE = (
    RAG_ROOT.parent / "legacy" / "data-pipeline" / "processed" / "chunks" / "all_chunks.jsonl"
)

def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.fixture(scope="module")
def built() -> tuple[list[dict], dict]:
    chunks, report = pipeline.build_all_chunks()
    return chunks, report


def test_parity_source_id_sets_match_legacy_baseline(built: tuple[list[dict], dict]) -> None:
    if not LEGACY_BASELINE.exists():
        pytest.skip("legacy baseline all_chunks.jsonl not present")
    baseline_ids = {chunk["source_id"] for chunk in _load_jsonl(LEGACY_BASELINE)}
    new_ids = {chunk["source_id"] for chunk in built[0]}

    missing = sorted(baseline_ids - new_ids)
    added = sorted(new_ids - baseline_ids)
    assert not missing and not added, f"source_id drift — missing: {missing[:10]}, added: {added[:10]}"


def test_no_content_loss_from_inputs(built: tuple[list[dict], dict]) -> None:
    """모든 입력 레코드의 각 줄(정규화)이 해당 소스의 청크 연결에 보존돼야 한다.

    legacy 청킹의 서두 유실 버그(첫 헤딩 이전 텍스트 폐기) 회귀를 막는 불변식.
    """
    chunks, _ = built
    concat_by_source: dict[str, str] = {}
    ordered: dict[str, list[tuple[int, str]]] = {}
    for chunk in chunks:
        ordered.setdefault(chunk["source_id"], []).append(
            (chunk["metadata"]["chunk_index"], chunk["text"])
        )
    for source_id, items in ordered.items():
        concat_by_source[source_id] = _norm("".join(text for _, text in sorted(items)))

    source_records = pipeline.load_document_requirements() + pipeline.load_candidate_readiness_checklist()
    raw_records = [record for record, _ in pipeline.load_raw_text_documents()]

    lost: list[str] = []
    for record in [*source_records, *raw_records]:
        text = pipeline.normalize_text(str(record.get("text") or record.get("content") or ""))
        if not text:
            continue
        metadata = pipeline.normalize_metadata(record, str(record.get("source_path") or "") or None)
        concat = concat_by_source.get(str(metadata["source_id"]), "")
        for line in text.splitlines():
            normalized_line = _norm(line)
            if normalized_line and normalized_line not in concat:
                lost.append(f"{metadata['source_id']}: {line[:80]}")

    assert not lost, f"{len(lost)} lost lines, first 10: {lost[:10]}"


def test_build_is_deterministic(built: tuple[list[dict], dict]) -> None:
    chunks, _ = built
    chunks_again, _ = pipeline.build_all_chunks()

    def key(rows: list[dict]) -> list[tuple[str, str]]:
        return [(row["chunk_id"], row["text"]) for row in rows]

    assert key(chunks) == key(chunks_again)


def test_regenerated_counts_are_pinned(built: tuple[list[dict], dict]) -> None:
    """회귀 감지용 고정 수치 — 데이터셋·청킹 전략 변경 시 의도적으로 갱신할 것."""
    chunks, _ = built
    collections = pipeline.build_workforce_collection_records(chunks)

    assert len(chunks) == 2033
    assert len(collections["workforce_official"]) == 945
    assert len(collections["workforce_templates"]) == 38


def test_chunk_ids_are_unique_and_hash_suffixed(built: tuple[list[dict], dict]) -> None:
    chunks, _ = built
    ids = [chunk["chunk_id"] for chunk in chunks]
    assert len(ids) == len(set(ids)), "chunk_id must be unique for idempotent upsert"
    assert all(re.search(r"_chunk_\d{4}_[0-9a-f]{8}$", chunk_id) for chunk_id in ids)
