from app.agent_runtime.rag.chunking import build_chunks


def _document() -> dict:
    return {
        "source_id": "foreign_worker_employment_act_제8조",
        "title": "외국인근로자의 고용 등에 관한 법률 제8조",
        "publisher": "고용노동부",
        "source_type": "official_law",
        "url": "https://www.law.go.kr",
        "retrieved_at": "2026-05-03",
        "effective_date": None,
        "doc_type": "law",
        "mission_agent": ["workforce_agent"],
        "visa_type": ["E-9"],
        "country": ["ALL"],
        "industry": ["ALL"],
        "risk_level": "high",
        "evidence_grade": "A",
        "content": "제8조(외국인근로자 고용허가) ① 고용허가를 신청한다.\n\n② 유효기간을 확인한다.",
    }


def test_chunking_keeps_strict_metadata_and_stable_chunk_ids() -> None:
    chunks = build_chunks([_document()])

    assert [chunk["chunk_id"] for chunk in chunks] == [
        "foreign_worker_employment_act_제8조__0001",
        "foreign_worker_employment_act_제8조__0002",
    ]
    assert chunks[0]["metadata"]["source_id"] == "foreign_worker_employment_act_제8조"
    assert chunks[0]["metadata"]["evidence_grade"] == "A"


def test_chunking_rejects_missing_contract_metadata() -> None:
    document = _document()
    document.pop("publisher")

    try:
        build_chunks([document])
    except ValueError as exc:
        assert "publisher" in str(exc)
    else:
        raise AssertionError("Expected strict metadata validation to fail")
