from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel


ROOT_DIR = Path(__file__).resolve().parents[4]
DEFAULT_PERSIST_DIR = ROOT_DIR / "data-pipeline" / "index" / "chroma" / "multilingual_contact"
DEFAULT_COLLECTION_NAME = "multilingual_contact_docs"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

RAG_DOMAIN = "multilingual_contact"
OWNER_AGENT = "multilingual_contact_agent"
SUPPORTED_INTENTS = {"counseling", "safety", "life", "notice"}
EXCLUDED_KEYWORDS = (
    "worker_replies",
    "synthetic_cases",
    "public_cases",
    "templates",
    "synthetic_worker_reply",
    "public_case_patterns",
    "interview_case_patterns",
    "not_for_legal_basis",
)

COUNSELING_BOOST_KEYWORDS = (
    "1577-0071",
    "외국인력상담센터",
    "EPS",
    "HRDK",
    "한국산업인력공단",
    "상담센터",
    "고충",
    "국내취업생활",
    "사업장 적응",
)

INTENT_KEYWORDS = {
    "counseling": (
        "상담센터",
        "상담",
        "고충",
        "문제",
        "연락처",
        "전화번호",
        "1577",
        "외국인력상담센터",
    ),
    "safety": ("안전", "안전교육", "KOSHA", "보호구", "교육", "산업안전"),
    "life": ("생활", "기숙사", "의료", "병원", "은행", "통신", "교통"),
    "notice": ("고용", "신청", "접수", "절차", "사업주", "외국인력지원"),
}

LANGUAGE_KEYWORDS = {
    "vi": ("베트남", "베트남어", "Vietnamese", "vi"),
    "id": ("인도네시아", "인도네시아어", "Indonesian", "id"),
}


class RetrievedContext(BaseModel):
    chunk_id: str
    source_id: str
    title: str
    publisher: str
    doc_type: str
    evidence_grade: str
    language: str
    raw_path: str
    page_number: int | None = None
    context: str
    text: str
    distance: float
    citation_label: str
    not_for_legal_basis: bool | None = None
    use_case: str | None = None
    file_type: str | None = None
    rank: int | None = None
    matched_intent: str | None = None
    matched_language: str | None = None


def load_env(path: Path | None = None) -> None:
    env_path = path or (ROOT_DIR / ".env")
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue

        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def infer_intent(query: str, intent: str | None = None) -> str | None:
    if intent:
        normalized = intent.strip().lower()
        return normalized if normalized in SUPPORTED_INTENTS else normalized

    for candidate, keywords in INTENT_KEYWORDS.items():
        if any(keyword.lower() in query.lower() for keyword in keywords):
            return candidate

    return None


def infer_language_code(query: str, language_code: str | None = None) -> str | None:
    if language_code:
        return language_code.strip().lower()

    for candidate, keywords in LANGUAGE_KEYWORDS.items():
        if any(keyword.lower() in query.lower() for keyword in keywords):
            return candidate

    return None


def build_where_filter(doc_types: list[str] | None = None) -> dict[str, Any]:
    base_filters: list[dict[str, Any]] = [
        {"rag_domain": RAG_DOMAIN},
        {"owner_agent": OWNER_AGENT},
        {"ingest_target": True},
    ]

    if doc_types:
        if len(doc_types) == 1:
            base_filters.append({"doc_type": doc_types[0]})
        else:
            base_filters.append({"doc_type": {"$in": doc_types}})

    if len(base_filters) == 1:
        return base_filters[0]

    return {"$and": base_filters}


def _is_truthy_true(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def _normalize_optional_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if value is True or value is False:
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return bool(value)


def _metadata_text(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key, "")
    if value is None:
        return ""
    return str(value)


def _metadata_int(metadata: dict[str, Any], key: str) -> int | None:
    value = metadata.get(key)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _haystack(metadata: dict[str, Any]) -> str:
    return "\n".join(
        [
            _metadata_text(metadata, "title"),
            _metadata_text(metadata, "publisher"),
            _metadata_text(metadata, "source_id"),
            _metadata_text(metadata, "raw_path"),
            _metadata_text(metadata, "context"),
            _metadata_text(metadata, "text"),
        ]
    )


def is_safe_result(metadata: dict[str, Any], document: str = "") -> bool:
    if metadata.get("evidence_grade") == "F":
        return False

    if _is_truthy_true(metadata.get("not_for_legal_basis")):
        return False

    if metadata.get("rag_domain") != RAG_DOMAIN:
        return False

    if metadata.get("owner_agent") != OWNER_AGENT:
        return False

    if metadata.get("ingest_target") is not True:
        return False

    combined = "\n".join([_haystack(metadata), document])
    return not any(keyword in combined for keyword in EXCLUDED_KEYWORDS)


def _language_matches(metadata: dict[str, Any], language_code: str | None) -> bool:
    if not language_code:
        return False

    language = _metadata_text(metadata, "language").lower()
    values = {value.strip() for value in language.split(",") if value.strip()}
    return language_code.lower() in values


def compute_boosted_score(
    *,
    distance: float,
    metadata: dict[str, Any],
    intent: str | None,
    language_code: str | None,
) -> float:
    score = distance
    doc_type = _metadata_text(metadata, "doc_type")

    if intent and _doc_type_matches_intent(doc_type, intent):
        score -= 0.25

    if _language_matches(metadata, language_code):
        score -= 0.6

    if intent == "counseling":
        text = _haystack(metadata)
        keyword_hits = sum(1 for keyword in COUNSELING_BOOST_KEYWORDS if keyword in text)
        score -= min(keyword_hits * 0.08, 0.48)

    return score


def _doc_type_matches_intent(doc_type: str, intent: str) -> bool:
    if intent == "counseling":
        return doc_type == "counseling"
    if intent == "safety":
        return doc_type == "safety"
    if intent == "life":
        return doc_type in {"life", "counseling"}
    if intent == "notice":
        return doc_type == "notice"
    return False


def make_citation_label(metadata: dict[str, Any]) -> str:
    publisher = _metadata_text(metadata, "publisher") or "unknown publisher"
    title = _metadata_text(metadata, "title") or "untitled"
    page_number = _metadata_int(metadata, "page_number")

    if page_number is not None:
        return f"{publisher}, {title}, p.{page_number}"

    return f"{publisher}, {title}"


def _create_embedding(query: str, model: str, api_key: str) -> list[float]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(model=model, input=query)
    return response.data[0].embedding


def _resolve_persist_dir() -> Path:
    value = os.getenv("CHROMA_PERSIST_DIR")
    if not value:
        return DEFAULT_PERSIST_DIR

    path = Path(value)
    if path.is_absolute():
        return path

    return (ROOT_DIR / path).resolve()


def _fallback_doc_type_groups(intent: str | None) -> list[list[str] | None]:
    if intent == "counseling":
        return [["counseling"], ["counseling", "life"], None]
    if intent == "safety":
        return [["safety"], ["safety"], None]
    if intent == "life":
        return [["life", "counseling"], ["life", "counseling"], None]
    if intent == "notice":
        return [["notice"], ["notice", "life", "counseling"], None]
    return [None]


def _query_collection(
    *,
    collection: Any,
    query_embedding: list[float],
    doc_types: list[str] | None,
    n_results: int,
) -> list[tuple[str, dict[str, Any], float]]:
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=build_where_filter(doc_types),
        include=["documents", "metadatas", "distances"],
    )
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    return [
        (document or "", metadata or {}, float(distance))
        for document, metadata, distance in zip(documents, metadatas, distances)
    ]


def _to_retrieved_context(
    metadata: dict[str, Any],
    distance: float,
    *,
    rank: int,
    intent: str | None,
    language_code: str | None,
) -> RetrievedContext:
    return RetrievedContext(
        chunk_id=_metadata_text(metadata, "chunk_id"),
        source_id=_metadata_text(metadata, "source_id"),
        title=_metadata_text(metadata, "title"),
        publisher=_metadata_text(metadata, "publisher"),
        doc_type=_metadata_text(metadata, "doc_type"),
        evidence_grade=_metadata_text(metadata, "evidence_grade"),
        language=_metadata_text(metadata, "language"),
        raw_path=_metadata_text(metadata, "raw_path"),
        page_number=_metadata_int(metadata, "page_number"),
        context=_metadata_text(metadata, "context"),
        text=_metadata_text(metadata, "text"),
        distance=distance,
        citation_label=make_citation_label(metadata),
        not_for_legal_basis=_normalize_optional_bool(
            metadata.get("not_for_legal_basis")
        ),
        use_case=_metadata_text(metadata, "use_case") or None,
        file_type=_metadata_text(metadata, "file_type") or None,
        rank=rank,
        matched_intent=intent,
        matched_language=language_code if _language_matches(metadata, language_code) else None,
    )


def search_multilingual_contact_docs(
    query: str,
    top_k: int = 5,
    language_code: str | None = None,
    intent: str | None = None,
) -> list[RetrievedContext]:
    load_env()

    query = query.strip()
    if not query:
        return []

    resolved_intent = infer_intent(query, intent)
    resolved_language = infer_language_code(query, language_code)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for multilingual contact retrieval.")

    import chromadb

    collection_name = os.getenv("CHROMA_COLLECTION_NAME", DEFAULT_COLLECTION_NAME)
    embedding_model = os.getenv(
        "MULTILINGUAL_CONTACT_EMBEDDING_MODEL",
        DEFAULT_EMBEDDING_MODEL,
    )
    client = chromadb.PersistentClient(path=str(_resolve_persist_dir()))
    collection = client.get_collection(collection_name)
    query_embedding = _create_embedding(query, embedding_model, api_key)

    n_results = max(top_k * 40, 200)
    deduped: dict[str, tuple[float, dict[str, Any], float]] = {}

    for doc_types in _fallback_doc_type_groups(resolved_intent):
        for document, metadata, distance in _query_collection(
            collection=collection,
            query_embedding=query_embedding,
            doc_types=doc_types,
            n_results=n_results,
        ):
            if not is_safe_result(metadata, document):
                continue

            score = compute_boosted_score(
                distance=distance,
                metadata=metadata,
                intent=resolved_intent,
                language_code=resolved_language,
            )
            chunk_id = _metadata_text(metadata, "chunk_id")
            current = deduped.get(chunk_id)
            if current is None or score < current[0]:
                deduped[chunk_id] = (score, metadata, distance)

        if len(deduped) >= top_k:
            break

    ranked = sorted(
        deduped.values(),
        key=lambda item: (
            item[0],
            item[1].get("doc_type", ""),
            item[1].get("source_id", ""),
            item[1].get("chunk_id", ""),
        ),
    )

    return [
        _to_retrieved_context(
            metadata,
            distance,
            rank=index,
            intent=resolved_intent,
            language_code=resolved_language,
        )
        for index, (_, metadata, distance) in enumerate(ranked[:top_k], start=1)
    ]
