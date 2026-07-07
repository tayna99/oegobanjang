from app.agent_runtime.rag.domain_splitters import split_domain_units


def test_law_text_splits_into_article_units() -> None:
    units = split_domain_units(
        "제1조(목적) 이 법은 외국인근로자의 고용에 관한 사항을 정한다.\n\n"
        "제2조(정의) 외국인근로자란 대한민국 국적을 가지지 아니한 사람을 말한다.",
        doc_type="law",
        source_id="foreign_worker_employment_act",
        source_path="data-pipeline/raw/laws/foreign_worker_employment_act.txt",
    )

    assert [unit.source_unit_type for unit in units] == ["law_article", "law_article"]
    assert units[0].unit_heading == "제1조(목적)"
    assert units[0].domain_unit_id == "foreign_worker_employment_act::law_article::0001"
    assert "제2조" in units[1].text


def test_procedure_text_splits_by_workforce_process_steps() -> None:
    units = split_domain_units(
        "내국인 구인노력\n사업주는 먼저 내국인 구인을 진행한다.\n\n"
        "고용허가 신청\n관할 고용센터에 고용허가 신청을 접수한다.\n\n"
        "근로계약 체결\n표준근로계약서를 작성한다.",
        doc_type="procedure",
        source_id="eps_employer_process",
        source_path="data-pipeline/raw/eps/employer_process.md",
    )

    assert [unit.source_unit_type for unit in units] == [
        "procedure_step",
        "procedure_step",
        "procedure_step",
    ]
    assert [unit.unit_heading for unit in units] == ["내국인 구인노력", "고용허가 신청", "근로계약 체결"]


def test_eps_employer_process_table_rows_split_into_workforce_process_steps() -> None:
    units = split_domain_units(
        "1. 내국인구인노력: 2. 외국인고용허가신청 | 사업주는 고용센터에 외국인고용허가 신청을 한다.\n"
        "1. 내국인구인노력: 3. 고용허가서 발급 | 고용센터는 요건 확인 후 고용허가서를 발급한다.\n"
        "1. 내국인구인노력: 4. 근로계약체결 | 사업주와 외국인근로자는 표준근로계약을 체결한다.\n"
        "1. 내국인구인노력: 5. 사증발급인정서 신청 및 발급 | 사증발급인정서 신청과 발급 절차를 진행한다.\n"
        "1. 내국인구인노력: 6. 외국인근로자 입국 및 취업교육 | 입국 후 취업교육을 이수한다.\n"
        "1. 내국인구인노력: 7. 사업장 배치, 사업장 고용 및 체류지원 | 사업장 배치 후 고용 및 체류지원을 관리한다.",
        doc_type="procedure",
        source_id="eps_employer_process",
        source_path="https://eps.hrdkorea.or.kr/e9/user/employment/employment.do?method=employProcessCompany",
    )

    headings = [unit.unit_heading for unit in units]

    assert len(units) == 6
    assert "외국인고용허가신청" in headings[0]
    assert "고용허가서 발급" in headings[1]
    assert "근로계약체결" in headings[2]
    assert "사증발급인정서 신청 및 발급" in headings[3]
    assert "외국인근로자 입국 및 취업교육" in headings[4]
    assert "사업장 배치" in headings[5]


def test_form_text_splits_into_form_sections() -> None:
    units = split_domain_units(
        "사업장 정보\n사업장명, 업종, 소재지를 기재한다.\n\n"
        "외국인 인적사항\n성명, 국적, 체류자격을 기재한다.\n\n"
        "제출기한\n정해진 기한 내 제출한다.",
        doc_type="form",
        source_id="employment_change_form",
        source_path="data-pipeline/raw/forms/employment_change_form.md",
    )

    assert [unit.source_unit_type for unit in units] == ["form_section", "form_section", "form_section"]
    assert units[1].unit_heading == "외국인 인적사항"


def test_unmatched_text_falls_back_to_general_low_confidence_unit() -> None:
    units = split_domain_units(
        "패턴이 명확하지 않은 일반 안내 문단입니다.",
        doc_type="general",
        source_id="unknown_doc",
        source_path="data-pipeline/raw/misc/unknown.md",
    )

    assert len(units) == 1
    assert units[0].source_unit_type == "general"
    assert units[0].unit_confidence == "low"


def test_allowed_industry_text_splits_as_allowed_industry_unit() -> None:
    units = split_domain_units(
        "E-9 제조업 허용 범위\n자동차부품 제조업은 제조업 허용 범위 검토 대상이다.",
        doc_type="allowed_industry",
        source_id="e9_allowed_industry",
        source_path="data-pipeline/raw/eps/e9_allowed_industry.md",
    )

    assert len(units) == 1
    assert units[0].source_unit_type == "allowed_industry"
    assert units[0].unit_heading == "E-9 제조업 허용 범위"


def test_candidate_readiness_text_splits_as_employer_requirement_unit() -> None:
    units = split_domain_units(
        "후보자 기본 확인 항목\n여권 보유 여부, 증명사진 제출 여부, 건강검진 확인 여부를 확인한다.",
        doc_type="candidate_readiness",
        source_id="candidate_readiness_checklist",
        source_path="data-pipeline/raw/templates/candidate_readiness_template.md",
    )

    assert len(units) == 1
    assert units[0].source_unit_type == "employer_requirement"
    assert units[0].unit_heading == "후보자 기본 확인 항목"
