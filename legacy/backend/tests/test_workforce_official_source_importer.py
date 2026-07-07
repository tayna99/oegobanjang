from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agent_runtime.rag.workforce_source_importer import (
    DEFAULT_ALLOWED_DOMAINS,
    FetchResponse,
    SourceDomainNotAllowed,
    import_workforce_sources,
)


def _write_manifest(path: Path, url: str) -> None:
    path.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "eps_employer_process_live",
                        "title": "EPS 사업주 고용절차",
                        "url": url,
                        "publisher": "EPS/고용24",
                        "source_type": "official_procedure",
                        "doc_type": "procedure",
                        "evidence_grade": "B",
                        "mission_agent": ["workforce_agent"],
                        "sub_agent": ["workforce_requirement_agent"],
                        "visa_type": ["E-9"],
                        "country": ["ALL"],
                        "industry": ["ALL"],
                        "case_type": ["new_hiring"],
                        "workflow_stage": "pre_hiring",
                        "output_usage": ["requirement_check", "request_form", "handoff_question"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_importer_uses_manifest_fallback_text_when_rendered_page_has_no_body_units(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    output_dir = tmp_path / "raw" / "workforce_official"
    manifest_path.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "work24_employment_permit_application",
                        "title": "고용24 외국인 고용허가 신청 안내",
                        "url": "https://www.work24.go.kr/cm/c/d/0180/retrieveSiteEasyHpcm.do?tabIndex=tab-panel-01&tabSubIndex=ul_p06",
                        "publisher": "고용24/고용노동부",
                        "source_type": "official_procedure",
                        "doc_type": "procedure",
                        "evidence_grade": "B",
                        "mission_agent": ["workforce_agent"],
                        "sub_agent": ["workforce_requirement_agent"],
                        "visa_type": ["E-9"],
                        "country": ["ALL"],
                        "industry": ["ALL"],
                        "case_type": ["new_hiring"],
                        "workflow_stage": "pre_hiring",
                        "output_usage": ["requirement_check", "handoff_question"],
                        "fallback_text": "외국인 고용허가 신청은 채용 지원의 외국인고용 메뉴에서 진행한다.\n\n발급신청 전 내국인 구인노력 선행 여부와 발급요건 충족 여부를 확인한다.",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = import_workforce_sources(
        manifest_path=manifest_path,
        output_dir=output_dir,
        fetch_enabled=True,
        fetcher=lambda url, *_args: FetchResponse(
            url=url,
            content_type="text/html;charset=UTF-8",
            body="<html><body><main>고객센터 이용가이드 챗봇 맨위로 가기</main></body></html>".encode("utf-8"),
        ),
    )

    rows = [
        json.loads(line)
        for line in (output_dir / "workforce_official_imported.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert report["written_records"] >= 1
    assert any("외국인 고용허가 신청" in row["content"] for row in rows)
    assert all(row["metadata"]["source_fetch_method"] == "official_source_url_with_manifest_fallback" for row in rows)


def test_importer_fetches_html_and_writes_workforce_jsonl_units(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    output_dir = tmp_path / "raw" / "workforce_official"
    _write_manifest(manifest_path, "https://www.eps.go.kr/eo/EmployJobProc.eo")

    def fake_fetcher(url: str, timeout_seconds: int, max_bytes: int) -> FetchResponse:
        assert url == "https://www.eps.go.kr/eo/EmployJobProc.eo"
        assert timeout_seconds > 0
        assert max_bytes > 0
        return FetchResponse(
            url=url,
            content_type="text/html; charset=utf-8",
            body="""
            <html><body><main>
              <h1>사업주 고용절차</h1>
              <script>tracking()</script>
              <h2>고용허가제 4대보험안내</h2>
              <p>채용정보<br>구직자정보<br>귀국자 네트워크<br>구직표 등록<br>자주 쓰는 외국어DB 안내<br>영상자료<br>홍보자료<br>사업주를 위한</p>
              <h2>내국인 구인노력</h2>
              <p>외국인근로자 고용을 원하는 사용자는 우선 관할 고용센터에 내국인 구인신청을 해야 합니다.</p>
              <h2>고용허가 신청</h2>
              <p>내국인 구인노력 이후에도 채용하지 못한 경우 고용허가서 발급을 신청합니다.</p>
              <p>개인정보 처리방침<br>이용약관<br>Copyrightⓒ2009 All rights reserved.</p>
            </main></body></html>
            """.encode("utf-8"),
        )

    report = import_workforce_sources(
        manifest_path=manifest_path,
        output_dir=output_dir,
        fetch_enabled=True,
        fetcher=fake_fetcher,
        fetched_at="2026-05-09T13:00:00+09:00",
    )

    output_path = output_dir / "workforce_official_imported.jsonl"
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert report["fetched_sources"] == 1
    assert report["written_records"] >= 1
    assert {row["metadata"]["source_unit_type"] for row in rows} == {"procedure_step"}
    assert all(row["metadata"]["mission_agent"] == ["workforce_agent"] for row in rows)
    assert all(row["metadata"]["sub_agent"] == ["workforce_requirement_agent"] for row in rows)
    assert all(row["metadata"]["source_fetch_method"] == "official_source_url" for row in rows)
    assert all(row["metadata"]["source_hash"] for row in rows)
    assert all("<script" not in row["content"] for row in rows)
    assert all("자주 쓰는 외국어DB" not in row["content"] for row in rows)
    assert all("개인정보 처리방침" not in row["content"] for row in rows)
    assert any("내국인 구인노력" in row["content"] for row in rows)


def test_importer_prunes_address_footer_lines(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    output_dir = tmp_path / "raw" / "workforce_official"
    _write_manifest(manifest_path, "https://www.eps.go.kr/eo/EmployJobProc.eo")

    def fake_fetcher(url: str, timeout_seconds: int, max_bytes: int) -> FetchResponse:
        return FetchResponse(
            url=url,
            content_type="text/html; charset=utf-8",
            body="""
            <html><body><main>
              <h2>내국인 구인노력</h2>
              <p>사업주는 내국인 구인노력을 확인한 뒤 외국인고용허가 신청을 준비한다.</p>
              <p>(우)44538 울산광역시 중구 종가로 345 한국산업인력공단</p>
            </main></body></html>
            """.encode("utf-8"),
        )

    report = import_workforce_sources(
        manifest_path=manifest_path,
        output_dir=output_dir,
        fetch_enabled=True,
        fetcher=fake_fetcher,
        fetched_at="2026-05-09T13:00:00+09:00",
    )

    rows = [json.loads(line) for line in (Path(report["output_path"])).read_text(encoding="utf-8").splitlines()]

    assert rows
    assert all("(우)44538" not in row["content"] for row in rows)


def test_importer_does_not_fetch_without_explicit_enable(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, "https://www.eps.go.kr/eo/EmployJobProc.eo")

    def forbidden_fetcher(url: str, timeout_seconds: int, max_bytes: int) -> FetchResponse:
        raise AssertionError("fetcher should not be called when disabled")

    report = import_workforce_sources(
        manifest_path=manifest_path,
        output_dir=tmp_path / "raw",
        fetch_enabled=False,
        fetcher=forbidden_fetcher,
    )

    assert report["status"] == "disabled"
    assert report["skipped_sources"] == 1
    assert not (tmp_path / "raw" / "workforce_official_imported.jsonl").exists()


def test_importer_blocks_non_allowlisted_domains(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, "https://example.com/not-official.html")

    with pytest.raises(SourceDomainNotAllowed):
        import_workforce_sources(
            manifest_path=manifest_path,
            output_dir=tmp_path / "raw",
            fetch_enabled=True,
            fetcher=lambda *_args: FetchResponse(
                url="https://example.com/not-official.html",
                content_type="text/plain",
                body=b"should not be fetched",
            ),
        )


def test_default_workforce_source_manifest_uses_official_allowlisted_domains() -> None:
    manifest_path = Path("data-pipeline/source_manifests/workforce_official_sources.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = manifest["sources"]

    assert {source["source_id"] for source in sources} >= {
        "eps_employer_process",
        "eps_employment_permit_system_intro",
        "work24_employment_permit_application",
        "hrdk_entry_employment_education",
    }
    for source in sources:
        host = source["url"].split("/")[2].lower()
        assert host in DEFAULT_ALLOWED_DOMAINS
        assert source["mission_agent"] == ["workforce_agent"]
        assert source["visa_type"] == ["E-9"]
