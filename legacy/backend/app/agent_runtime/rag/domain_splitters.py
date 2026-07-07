from __future__ import annotations

import re
from dataclasses import dataclass


SPLITTER_VERSION = "domain_splitters_v1"

LAW_HEADING_RE = re.compile(
    r"(?m)^(?P<head>(?:제\s*\d+\s*조(?:의\s*\d+)?(?:\([^)\n]+\))?|부칙|별표\s*\d*|별지\s*제\s*\d+\s*호\s*서식))"
)
PROCEDURE_HEADING_RE = re.compile(
    r"(?m)^(?P<head>(?:(?:\d+\.\s*[^:\n]+:\s*)?\d+\.\s*)?"
    r"(?:내국인\s*구인노력|외국인고용허가신청|고용허가(?:서)?(?: 발급| 신청)?|근로계약(?:\s*체결|체결)?|"
    r"사증발급인정서(?: 신청 및 발급| 신청)?|외국인근로자 입국 및 취업교육|입국(?: 및 취업교육)?|"
    r"사업장 배치(?:[^|\n]*)?|취업교육|신청|접수|처리|제출|구비서류|허용업종|사업주 고용절차)[^|\n]*)"
)
FORM_HEADING_RE = re.compile(
    r"(?m)^(?P<head>(?:\[[^\]\n]+\]|사업장 정보|외국인 인적사항|신고 사유|제출기한|유의사항|신청인 정보|기재 항목|필수 기재 항목|첨부서류|구비서류)[^\n]*)"
)
SAFETY_HEADING_RE = re.compile(
    r"(?m)^(?P<head>(?:안전교육|안전표지|상담센터|긴급 연락처|생활 안내|권리 안내|의무 안내|의료·건강)[^\n]*)"
)
TEMPLATE_HEADING_RE = re.compile(
    r"(?m)^(?P<head>(?:신규 인력 요청서 템플릿|송출회사 확인 질문|행정사 검토 요청 항목|후보 제출 준비도 비교표 템플릿|후보 준비도 설명 원칙|여권 사본 요청|외국인등록증 요청|증명사진 요청|기숙사 안내|안전교육 안내|급여명세서 설명|행정사 전달|handoff package)[^\n]*)",
    re.IGNORECASE,
)
ALLOWED_INDUSTRY_HEADING_RE = re.compile(
    r"(?m)^(?P<head>(?:E-9\s*)?(?:제조업|농축산업|어업|서비스업|건설업)?\s*(?:허용업종|허용 범위|허용 직종)[^\n]*)",
    re.IGNORECASE,
)
EMPLOYER_REQUIREMENT_HEADING_RE = re.compile(
    r"(?m)^(?P<head>(?:신규\s*E-9\s*고용 전 사업주 확인 항목|사업주 확인 항목|후보자 기본 확인 항목|후보 제출 준비도|송출회사 확인 질문|행정사 검토 요청 항목)[^\n]*)"
)


@dataclass(frozen=True)
class DomainUnit:
    text: str
    source_unit_type: str
    domain_unit_id: str
    unit_heading: str
    unit_index: int
    unit_confidence: str
    splitter_version: str = SPLITTER_VERSION


def infer_source_unit_type(
    *,
    doc_type: str | None = None,
    source_path: str | None = None,
    text: str = "",
    title: str = "",
) -> str:
    value = " ".join([doc_type or "", source_path or "", title, text[:200]]).lower()
    if doc_type == "law" or "/laws/" in value or "\\laws\\" in value or LAW_HEADING_RE.search(text):
        return "law_article"
    if doc_type == "allowed_industry" or any(token in value for token in ["허용업종", "허용 범위", "allowed_industry"]):
        return "allowed_industry"
    if doc_type in {"employer_requirement", "candidate_readiness"} or any(
        token in value for token in ["사업주 확인", "후보자 기본 확인", "후보 제출 준비도", "candidate_readiness"]
    ):
        return "employer_requirement"
    if doc_type == "procedure" or any(token in value for token in ["eps", "procedure", "절차", "고용허가"]):
        return "procedure_step"
    if doc_type == "form" or any(token in value for token in ["form", "서식", "신청서", "신고서"]):
        return "form_section"
    if doc_type == "safety" or any(token in value for token in ["safety", "안전", "상담센터", "생활안내"]):
        return "safety_section"
    if doc_type == "template" or any(token in value for token in ["template", "message", "템플릿", "메시지"]):
        return "template_purpose"
    if doc_type == "case" or any(token in value for token in ["synthetic", "case", "케이스"]):
        return "case_record"
    return "general"


def split_domain_units(
    text: str,
    *,
    doc_type: str | None = None,
    source_id: str,
    source_path: str | None = None,
    title: str = "",
) -> list[DomainUnit]:
    normalized = _normalize_text(text)
    if not normalized:
        return []

    source_unit_type = infer_source_unit_type(
        doc_type=doc_type,
        source_path=source_path,
        text=normalized,
        title=title,
    )
    pattern = _pattern_for(source_unit_type)
    if pattern is None:
        return [_unit(normalized, source_unit_type, source_id, 1, title or "general", "low")]

    spans = list(pattern.finditer(normalized))
    if not spans:
        confidence = "low" if source_unit_type == "general" else "medium"
        return [_unit(normalized, source_unit_type, source_id, 1, title or source_unit_type, confidence)]

    units: list[DomainUnit] = []
    for index, match in enumerate(spans, start=1):
        start = match.start()
        end = spans[index].start() if index < len(spans) else len(normalized)
        unit_text = normalized[start:end].strip()
        heading = _clean_heading(match.group("head"))
        if unit_text:
            units.append(_unit(unit_text, source_unit_type, source_id, index, heading, "high"))

    return units or [_unit(normalized, source_unit_type, source_id, 1, title or source_unit_type, "low")]


def _pattern_for(source_unit_type: str) -> re.Pattern[str] | None:
    if source_unit_type == "law_article":
        return LAW_HEADING_RE
    if source_unit_type == "procedure_step":
        return PROCEDURE_HEADING_RE
    if source_unit_type == "form_section":
        return FORM_HEADING_RE
    if source_unit_type == "safety_section":
        return SAFETY_HEADING_RE
    if source_unit_type == "template_purpose":
        return TEMPLATE_HEADING_RE
    if source_unit_type == "allowed_industry":
        return ALLOWED_INDUSTRY_HEADING_RE
    if source_unit_type == "employer_requirement":
        return EMPLOYER_REQUIREMENT_HEADING_RE
    if source_unit_type == "case_record":
        return None
    return None


def _unit(
    text: str,
    source_unit_type: str,
    source_id: str,
    index: int,
    heading: str,
    confidence: str,
) -> DomainUnit:
    return DomainUnit(
        text=text,
        source_unit_type=source_unit_type,
        domain_unit_id=f"{source_id}::{source_unit_type}::{index:04d}",
        unit_heading=heading,
        unit_index=index,
        unit_confidence=confidence,
    )


def _clean_heading(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
