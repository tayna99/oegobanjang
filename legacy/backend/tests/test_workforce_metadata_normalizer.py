from app.agent_runtime.rag.workforce_metadata import normalize_workforce_metadata


def test_normalizes_new_hiring_procedure_metadata_for_requirement_agent() -> None:
    metadata = normalize_workforce_metadata(
        {
            "title": "고용허가서 — 개요 및 발급 절차",
            "source_type": "official_procedure",
            "doc_type": "procedure",
            "visa_type": ["E-9"],
            "industry": ["ALL"],
            "text": "내국인 구인노력 이후 고용허가 신청과 근로계약 체결을 진행한다.",
            "raw_metadata": {"source_unit_type": "procedure_step"},
        },
        source_path="data-pipeline/raw/정부24_hikorea/고용허가서_안내.jsonl",
    )

    assert metadata["mission_agent"] == ["workforce_agent"]
    assert metadata["sub_agent"] == ["workforce_requirement_agent"]
    assert metadata["case_type"] == ["new_hiring"]
    assert metadata["workflow_stage"] == "pre_hiring"
    assert metadata["source_unit_type"] == "procedure_step"
    assert set(metadata["output_usage"]) >= {"requirement_check", "request_form", "handoff_question"}


def test_preserves_domain_splitter_source_unit_type_for_official_procedure() -> None:
    metadata = normalize_workforce_metadata(
        {
            "title": "사업주 고용절차 — 외국인근로자 입국 및 취업교육",
            "source_type": "official_procedure",
            "doc_type": "procedure",
            "visa_type": ["E-9"],
            "industry": ["ALL"],
            "text": "외국인근로자는 입국 후 취업교육을 이수하고 건강검진 결과 확인 후 사업장에 배치된다.",
            "raw_metadata": {"source_unit_type": "procedure_step"},
        },
        source_path="https://eps.hrdkorea.or.kr/e9/user/employment/employment.do?method=employProcessCompany",
    )

    assert metadata["source_unit_type"] == "procedure_step"
    assert metadata["sub_agent"] == ["workforce_requirement_agent"]


def test_normalizes_candidate_readiness_template_metadata() -> None:
    metadata = normalize_workforce_metadata(
        {
            "title": "후보 제출 준비도 비교표 템플릿",
            "source_type": "internal_template",
            "doc_type": "template",
            "evidence_grade": "E",
            "text": "여권 보유 여부, 증명사진, 건강검진, 근무 가능일, 숙소 안내 여부를 확인한다.",
        },
        source_path="data-pipeline/raw/templates/candidate_readiness_template.md",
    )

    assert metadata["mission_agent"] == ["workforce_agent"]
    assert metadata["sub_agent"] == ["candidate_readiness_agent"]
    assert metadata["case_type"] == ["candidate_review"]
    assert metadata["workflow_stage"] == "candidate_readiness"
    assert metadata["source_unit_type"] == "template_purpose"
    assert set(metadata["output_usage"]) >= {"readiness_check", "candidate_readiness_table", "additional_questions"}


def test_normalizes_allowed_industry_metadata() -> None:
    metadata = normalize_workforce_metadata(
        {
            "title": "E-9 제조업 허용 범위",
            "source_type": "official_procedure",
            "doc_type": "procedure",
            "visa_type": ["E-9"],
            "industry": ["manufacturing"],
            "text": "자동차부품 제조업 등 제조업 허용 범위를 확인한다.",
        },
        source_path="data-pipeline/raw/eps/e9_allowed_industry.md",
    )

    assert metadata["source_unit_type"] == "allowed_industry"
    assert metadata["industry"] == ["manufacturing"]
    assert metadata["case_type"] == ["new_hiring"]
    assert "requirement_check" in metadata["output_usage"]
