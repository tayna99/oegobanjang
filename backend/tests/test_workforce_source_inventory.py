from app.agent_runtime.rag.workforce_metadata import build_workforce_source_inventory


def test_workforce_source_inventory_reports_coverage_and_gaps() -> None:
    inventory = build_workforce_source_inventory(
        [
            {
                "title": "고용허가서 발급 절차",
                "source_type": "official_procedure",
                "doc_type": "procedure",
                "text": "내국인 구인노력 후 고용허가 신청을 진행한다.",
                "raw_metadata": {"source_unit_type": "procedure_step"},
            },
            {
                "title": "E-9 제조업 허용 범위",
                "source_type": "official_procedure",
                "doc_type": "procedure",
                "industry": ["manufacturing"],
                "text": "자동차부품 제조업 허용 범위를 확인한다.",
            },
            {
                "title": "신규 E-9 고용 전 사업주 확인 항목",
                "source_type": "internal_checklist",
                "doc_type": "form",
                "text": "업종, 지역, 필요 인원, 숙소, 근무 형태를 확인한다.",
            },
            {
                "title": "후보 제출 준비도 비교표 템플릿",
                "source_type": "internal_template",
                "doc_type": "template",
                "evidence_grade": "E",
                "text": "여권, 사진, 건강검진, 근무 가능일을 확인한다.",
            },
        ]
    )

    assert inventory["coverage"]["official_procedure"] == 1
    assert inventory["coverage"]["allowed_industry"] == 1
    assert inventory["coverage"]["employer_requirement"] == 1
    assert inventory["coverage"]["candidate_readiness_template"] == 1
    assert "candidate_readiness_checklist" in inventory["missing_categories"]


def test_workforce_source_inventory_accepts_candidate_readiness_checklist() -> None:
    inventory = build_workforce_source_inventory(
        [
            {
                "title": "candidate_readiness_checklist.csv",
                "source_type": "internal_checklist",
                "doc_type": "form",
                "text": "candidate_review,passport,true,boolean,여권 보유 여부",
                "raw_metadata": {
                    "source_unit_type": "employer_requirement",
                    "sub_agent": ["candidate_readiness_agent"],
                    "case_type": ["candidate_review"],
                    "output_usage": ["readiness_check"],
                },
            }
        ]
    )

    assert inventory["coverage"]["candidate_readiness_checklist"] == 1
