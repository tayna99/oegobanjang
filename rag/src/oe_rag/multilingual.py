"""다국어 컨택 RAG — legacy rag_hyunhee 이식.

legacy 조사 결과(2026-07-17 Understand 워크플로) 반영한 설계 차이:
- 원본 raw HTML(life_guides/safety)이 .gitignore로 소실돼 재수집 불가 — 사전 빌드된
  legacy/data-pipeline/processed/chunks/multilingual_contact/all_chunks.jsonl(1022건)을
  유일한 정본 입력으로 삼는다(이 파일을 rag/data-pipeline/processed/chunks/multilingual_contact/에
  그대로 복사). "복사·정제해 이식" 원칙에 따라 로드 시 정제(clean)한다.
- **버그 발견 및 수정**: 원본 text 필드의 47%(477/1022)가 HTML 태그 잔재로 오염돼 있었다
  (레거시 인제스트 스크립트가 raw_ingest.clean_html_document()를 쓰지 않고 자체 재구현하며
  HTML 정제를 누락함). 로드 시 clean_html_document()로 재정제하고, 정제 후 내용이 사라지는
  순수 네비게이션 잔재 청크(예: <nav>/<div class="gnb"> 메뉴 조각)는 품질 게이트로 제외한다.
- metadata 스키마는 workforce 14필드 계약과 다르다(rag_domain/owner_agent/not_for_legal_basis/
  contains_personal_data/language/use_case 등) — 별도 도메인 계약으로 그대로 유지, 별도
  pgvector 컬렉션(multilingual_contact)을 쓴다(workforce_official과 통합하지 않음 — 이식
  근거 문서가 rag_hyunwook과 달리 통합을 권고하지 않았음).
- compute_boosted_score의 "distance 차감" 방식은 legacy Chroma든 pgvector든 동일하게
  "거리가 작을수록 유사"라는 척도라 그대로 이식 가능하다(비자 RAG의 0.4 confidence-threshold와
  달리 척도 변환 문제가 없음).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import PROCESSED_DIR
from .ingest.raw_ingest import clean_html_document, normalize_whitespace

MULTILINGUAL_COLLECTION = "multilingual_contact"
DEFAULT_MULTILINGUAL_CHUNKS_PATH = (
    PROCESSED_DIR / "chunks" / "multilingual_contact" / "all_chunks.jsonl"
)

RAG_DOMAIN = "multilingual_contact"
OWNER_AGENT = "multilingual_contact_agent"
MIN_CLEANED_CHARS = 10

_RESIDUAL_TAG_RE = re.compile(r"<[^>]+>")
# 청크 경계에서 태그 속성값이 잘려 닫는 `>`가 다음 청크에 있는 경우(예: <option value="...
# 잘림) — 문자열 끝의 미완성 태그 시작 부분만 남는다. 이런 경우 안전하게 통째로 잘라낸다.
_TRAILING_OPEN_TAG_RE = re.compile(r"<[^>]*$")
# 청크 경계에서 <script>/<style>/<!--가 닫히지 않고 잘릴 수 있어(문서 전체가 아니라
# 파편 단위라서) 닫는 태그가 없으면 문자열 끝까지로 대체 매칭한다 — 안 그러면 JS 코드
# 본문이 그대로 corpus에 노출된다.
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?(?:</\1\s*>|$)", re.IGNORECASE | re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?(?:-->|$)", re.DOTALL)

SUPPORTED_INTENTS = frozenset({"counseling", "safety", "life", "notice"})
INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "counseling": ("상담", "고충", "상담센터", "1577", "카운슬링"),
    "safety": ("안전", "보건", "사고", "산재", "위험"),
    "life": ("생활", "주거", "은행", "병원", "교통", "숙소"),
    "notice": ("공지", "안내문", "발표", "보도", "고시"),
}
LANGUAGE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "vi": ("vi", "베트남어", "tiếng việt", "tieng viet"),
    "id": ("id", "인도네시아어", "bahasa indonesia"),
}

_DOC_TYPE_INTENT_MATCH: dict[str, frozenset[str]] = {
    "counseling": frozenset({"counseling"}),
    "safety": frozenset({"safety"}),
    "life": frozenset({"life", "counseling"}),
    "notice": frozenset({"notice"}),
}

_FALLBACK_DOC_TYPE_GROUPS: dict[str, list[list[str] | None]] = {
    "counseling": [["counseling"], ["counseling", "life"], None],
    "safety": [["safety"], None],
    "life": [["life"], ["life", "counseling"], None],
    "notice": [["notice"], None],
}

_COUNSELING_BOOST_KEYWORDS = ("1577-0071", "상담센터", "hrdk", "고충")


@dataclass(frozen=True)
class MultilingualRecord:
    id: str
    source_id: str
    text: str
    context: str
    contextual_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def load_multilingual_contact_records(
    path: Path = DEFAULT_MULTILINGUAL_CHUNKS_PATH,
) -> tuple[list[MultilingualRecord], list[dict[str, Any]]]:
    """청크 JSONL을 읽고 HTML 잔재를 정제한다.

    Returns (accepted, quarantined) — quarantined는 정제 후 내용이 남지 않은
    순수 boilerplate 청크(예: 네비게이션 메뉴 조각)의 {chunk_id, reason} 목록.
    """
    accepted: list[MultilingualRecord] = []
    quarantined: list[dict[str, Any]] = []

    if not path.exists():
        return accepted, quarantined

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            row = json.loads(raw)
            metadata = dict(row.get("metadata") or {})

            if str(metadata.get("evidence_grade", "")).upper() in {"D", "F"}:
                quarantined.append({"chunk_id": row.get("chunk_id"), "reason": "low_evidence_grade"})
                continue
            if metadata.get("ingest_target") is not True:
                quarantined.append({"chunk_id": row.get("chunk_id"), "reason": "not_ingest_target"})
                continue

            raw_text = str(row.get("text", ""))
            cleaned = clean_html_document(raw_text) if _looks_like_html(raw_text) else normalize_whitespace(raw_text)
            # clean_html_document()는 완결된 문서 기준으로 설계돼 있어, 청크 경계에서
            # 열림/닫힘 태그가 어긋나면(예: <table> 없이 <td>만 남은 조각, <head> 없이
            # <meta>만 남은 조각) 태그가 새어나올 수 있다 — 태그 종류를 전부 화이트리스트로
            # 열거하는 대신 무조건 마지막에 범용 정규식 스트립을 한 번 더 돌려 방어한다.
            cleaned = _strip_residual_tags(cleaned)
            if len(cleaned) < MIN_CLEANED_CHARS:
                quarantined.append(
                    {"chunk_id": row.get("chunk_id"), "reason": "empty_after_html_cleanup"}
                )
                continue
            if _looks_like_script_residue(cleaned):
                quarantined.append({"chunk_id": row.get("chunk_id"), "reason": "script_residue"})
                continue

            context = str(row.get("context", ""))
            contextual_text = f"{context}\n\n{cleaned}".strip()
            accepted.append(
                MultilingualRecord(
                    id=str(row["chunk_id"]),
                    source_id=str(row.get("source_id", "")),
                    text=cleaned,
                    context=context,
                    contextual_text=contextual_text,
                    metadata={
                        **metadata,
                        "chunk_char_length": len(cleaned),
                    },
                )
            )

    return accepted, quarantined


_JS_SIGNAL_RE = re.compile(
    r"\bfunction\s*\(|=>\s*\{|\bdocument\.\w|\bwindow\.\w|\.prototype\b|"
    r"\btypeof\s+\w|\breturn\s+[\w.'\"(]|\bvar\s+\w+\s*=|\bconst\s+\w+\s*="
)


def _looks_like_script_residue(text: str) -> bool:
    """<script> 태그가 청크 경계 밖에서 열리고 닫혀 태그 마커 없이 순수 JS 코드만
    남은 청크를 잡아낸다(태그 기반 정규식으로는 감지 불가) — 예: hwaseong_.../chunk_0040-0043."""
    return len(_JS_SIGNAL_RE.findall(text)) >= 2


_HTML_SNIFF_RE = re.compile(
    r"<\s*/?\s*(html|body|div|nav|article|p|table|a|li|ul|meta|script|style|head|title|dl|dt|dd|span)\b",
    re.IGNORECASE,
)


def _looks_like_html(text: str) -> bool:
    # 청크 조각 어디에나 태그가 있을 수 있어 앞부분만 보지 않고 전체를 스캔한다
    # (닫는 태그 `</div>`처럼 `<` 다음 `/`가 오는 경우도 잡아야 함).
    return bool(_HTML_SNIFF_RE.search(text))


def _strip_residual_tags(text: str) -> str:
    text = _HTML_COMMENT_RE.sub(" ", text)
    text = _SCRIPT_STYLE_RE.sub(" ", text)
    text = _RESIDUAL_TAG_RE.sub(" ", text)
    text = _TRAILING_OPEN_TAG_RE.sub(" ", text)
    return normalize_whitespace(text)


def build_multilingual_vector_records(
    records: list[MultilingualRecord],
) -> list[dict[str, Any]]:
    """oe_rag.cli.load_collection_records()가 기대하는 {id,text,embedding,metadata} 이전 단계.

    embedding은 CLI의 index-multilingual 커맨드가 provider에 맞춰 나중에 채운다.
    """
    output: list[dict[str, Any]] = []
    for record in records:
        metadata = dict(record.metadata)
        metadata["collection"] = MULTILINGUAL_COLLECTION
        output.append(
            {
                "id": record.id,
                "text": record.contextual_text,
                "metadata": metadata,
            }
        )
    return output


# --- 런타임 검색 (legacy rag_hyunhee/retriever.py 이식) ---------------------------------


def infer_intent(query: str, intent: str | None = None) -> str | None:
    if intent:
        return intent
    lowered = query.lower()
    for candidate, keywords in INTENT_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return candidate
    return None


def infer_language_code(query: str, language_code: str | None = None) -> str | None:
    if language_code:
        return language_code
    lowered = query.lower()
    for candidate, keywords in LANGUAGE_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return candidate
    return None


def _is_safe_result(metadata: dict[str, Any]) -> bool:
    if str(metadata.get("evidence_grade", "")).upper() in {"D", "F"}:
        return False
    if metadata.get("not_for_legal_basis") is True:
        return False
    if metadata.get("rag_domain") != RAG_DOMAIN or metadata.get("owner_agent") != OWNER_AGENT:
        return False
    if metadata.get("ingest_target") is not True:
        return False
    return True


def _doc_type_matches_intent(doc_type: str, intent: str) -> bool:
    return doc_type in _DOC_TYPE_INTENT_MATCH.get(intent, frozenset())


def compute_boosted_score(
    distance: float,
    metadata: dict[str, Any],
    intent: str | None,
    language_code: str | None,
) -> float:
    score = distance
    doc_type = str(metadata.get("doc_type", ""))
    if intent and _doc_type_matches_intent(doc_type, intent):
        score -= 0.25
    if language_code:
        languages = metadata.get("language")
        language_values = languages.split(",") if isinstance(languages, str) else _as_list(languages)
        if language_code in language_values:
            score -= 0.6
    if intent == "counseling":
        haystack = str(metadata.get("title", "")) + " " + str(metadata.get("publisher", ""))
        hits = sum(1 for keyword in _COUNSELING_BOOST_KEYWORDS if keyword in haystack)
        score -= min(hits * 0.08, 0.48)
    return score


def _fallback_doc_type_groups(intent: str | None) -> list[list[str] | None]:
    if intent and intent in _FALLBACK_DOC_TYPE_GROUPS:
        return _FALLBACK_DOC_TYPE_GROUPS[intent]
    return [None]


def search_multilingual_contact_docs(
    query: str,
    *,
    top_k: int = 5,
    language_code: str | None = None,
    intent: str | None = None,
    provider: str | None = None,
) -> list[dict[str, Any]]:
    """다국어 컨택 근거 검색 — intent/언어 부스팅 + doc_type 그룹 fallback + dedup."""
    from .embeddings import embed_query, resolve_embedding_provider
    from .store.pgvector_store import ManifestMismatchError, PgVectorIndex, read_manifest

    resolved_provider = resolve_embedding_provider(provider)
    manifest = read_manifest(MULTILINGUAL_COLLECTION)
    if manifest is None:
        return []
    if manifest.provider != resolved_provider:
        raise ManifestMismatchError(
            f"multilingual_contact indexed with provider '{manifest.provider}' "
            f"but query uses '{resolved_provider}'."
        )

    index = PgVectorIndex(
        MULTILINGUAL_COLLECTION,
        provider=manifest.provider,
        model=manifest.model,
        dimensions=manifest.dimensions,
    )
    try:
        total = index.count()
        if total == 0:
            return []

        resolved_intent = infer_intent(query, intent)
        resolved_language = infer_language_code(query, language_code)
        embedding = embed_query(query, provider=resolved_provider)

        candidate_count = max(min(total, top_k * 40), min(total, 200))
        hits = index.query(embedding, top_k=candidate_count)

        best_by_chunk: dict[str, tuple[float, dict[str, Any]]] = {}
        for doc_type_group in _fallback_doc_type_groups(resolved_intent):
            for hit in hits:
                metadata = dict(hit.metadata or {})
                if not _is_safe_result(metadata):
                    continue
                if doc_type_group is not None and str(metadata.get("doc_type", "")) not in doc_type_group:
                    continue
                score = compute_boosted_score(hit.distance, metadata, resolved_intent, resolved_language)
                existing = best_by_chunk.get(hit.id)
                if existing is None or score < existing[0]:
                    best_by_chunk[hit.id] = (score, {"id": hit.id, "text": hit.text, "metadata": metadata, "distance": hit.distance})
            if len(best_by_chunk) >= top_k:
                break

        ranked = sorted(
            best_by_chunk.values(),
            key=lambda item: (
                item[0],
                str(item[1]["metadata"].get("doc_type", "")),
                str(item[1]["metadata"].get("source_id", "")),
                str(item[1]["id"]),
            ),
        )
        results = []
        for rank, (score, result) in enumerate(ranked[:top_k], start=1):
            results.append(
                {
                    **result,
                    "score": score,
                    "rank": rank,
                    "matched_intent": resolved_intent,
                    "matched_language": resolved_language,
                }
            )
        return results
    finally:
        index.close()
