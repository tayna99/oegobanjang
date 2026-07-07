from app.agent_runtime.rag.workforce_jsonl_retrieval import (
    build_workforce_retrieval_filters,
    retrieve_workforce_materials,
)


def test_new_hiring_retrieval_filters_target_requirement_materials() -> None:
    filters = build_workforce_retrieval_filters(
        case_type="new_hiring",
        sub_agent="workforce_requirement_agent",
        visa_type="E-9",
    )

    assert filters["official_procedure"]["mission_agent"] == "workforce_agent"
    assert filters["official_procedure"]["sub_agent"] == "workforce_requirement_agent"
    assert filters["official_procedure"]["case_type"] == "new_hiring"
    assert filters["official_procedure"]["visa_type"] == "E-9"
    assert filters["internal_template"]["output_usage"] == "request_form"


def test_candidate_review_retrieval_filters_target_readiness_materials() -> None:
    filters = build_workforce_retrieval_filters(
        case_type="candidate_review",
        sub_agent="candidate_readiness_agent",
        visa_type="E-9",
    )

    assert filters["readiness_checklist"]["sub_agent"] == "candidate_readiness_agent"
    assert filters["readiness_checklist"]["case_type"] == "candidate_review"
    assert filters["readiness_checklist"]["output_usage"] == "readiness_check"


def test_retrieve_workforce_materials_returns_bucketed_results_without_candidate_scoring() -> None:
    chunks = [
        {
            "chunk_id": "official_001",
            "source_id": "FORM_EMP_PERMIT_OVERVIEW",
            "title": "고용허가서 발급 절차",
            "text": "내국인 구인노력 이후 고용허가 신청을 진행한다.",
            "metadata": {
                "title": "고용허가서 발급 절차",
                "publisher": "고용노동부",
                "source_type": "official_procedure",
                "doc_type": "procedure",
                "mission_agent": ["workforce_agent"],
                "sub_agent": ["workforce_requirement_agent"],
                "visa_type": ["E-9"],
                "case_type": ["new_hiring"],
                "output_usage": ["requirement_check"],
                "evidence_grade": "B",
            },
        },
        {
            "chunk_id": "template_001",
            "source_id": "WORKFORCE_REQUEST_TEMPLATE",
            "title": "신규 인력 요청서 템플릿",
            "text": "사업장명, 업종, 지역, 필요 인원, 숙소, 근무 형태를 정리한다.",
            "metadata": {
                "title": "신규 인력 요청서 템플릿",
                "publisher": "internal",
                "source_type": "internal_template",
                "doc_type": "template",
                "mission_agent": ["workforce_agent"],
                "sub_agent": ["workforce_requirement_agent"],
                "visa_type": ["E-9"],
                "case_type": ["new_hiring"],
                "output_usage": ["request_form"],
                "evidence_grade": "E",
            },
        },
    ]

    result = retrieve_workforce_materials(
        "E-9 3명 신규 고용 준비",
        chunks=chunks,
        case_type="new_hiring",
        sub_agent="workforce_requirement_agent",
        visa_type="E-9",
    )

    assert result["official_procedure"][0]["source_id"] == "FORM_EMP_PERMIT_OVERVIEW"
    assert result["internal_template"][0]["source_id"] == "WORKFORCE_REQUEST_TEMPLATE"
    assert "candidate_score" not in str(result)
