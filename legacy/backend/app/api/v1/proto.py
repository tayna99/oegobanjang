"""프로토타입 UI용 더미 데이터 API — data-pipeline/seed CSV를 읽어 반환한다."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/proto", tags=["proto"])

SEED_DIR = Path(__file__).resolve().parents[4] / "data-pipeline" / "seed"

NATIONALITY_FLAG = {
    "Vietnam": "🇻🇳",
    "Cambodia": "🇰🇭",
    "Uzbekistan": "🇺🇿",
    "Nepal": "🇳🇵",
    "Indonesia": "🇮🇩",
}

DOC_TYPE_KO = {
    "employment_contract": "근로계약서",
    "passport_copy": "여권사본",
    "alien_registration": "외국인등록증",
    "work_permit": "취업허가서",
    "labor_contract": "표준근로계약서",
}


def _read_csv(name: str) -> list[dict[str, str]]:
    path = SEED_DIR / name
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _build_company_map() -> dict[str, dict]:
    rows = _read_csv("companies.csv")
    return {r["id"]: r for r in rows}


def _calc_tenure(start_iso: str) -> str:
    """contract_starts_at 기준 근속 기간 계산."""
    if not start_iso:
        return "-"
    try:
        started = date.fromisoformat(start_iso)
        today = date.today()
        months = (today.year - started.year) * 12 + (today.month - started.month)
        years, m = divmod(months, 12)
        if years and m:
            return f"{years}년 {m}개월"
        if years:
            return f"{years}년"
        return f"{m}개월"
    except ValueError:
        return "-"


def _dday(expiry_iso: str) -> int:
    if not expiry_iso:
        return 9999
    try:
        d = date.fromisoformat(expiry_iso)
        return (d - date.today()).days
    except ValueError:
        return 9999


def _severity(days: int) -> str:
    if days < 0:
        return "CRITICAL"
    if days <= 30:
        return "HIGH"
    if days <= 90:
        return "MEDIUM"
    return "LOW"


@router.get("/companies")
def get_companies() -> list[dict[str, Any]]:
    rows = _read_csv("companies.csv")
    worker_rows = _read_csv("workers.csv")

    worker_count: dict[str, int] = {}
    for w in worker_rows:
        cid = w["company_id"]
        worker_count[cid] = worker_count.get(cid, 0) + 1

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "industry": r["industry"],
            "region": r["region"],
            "workers": worker_count.get(r["id"], 0),
            "shift_type": r.get("shift_type", ""),
        }
        for r in rows
    ]


@router.get("/workers")
def get_workers() -> list[dict[str, Any]]:
    workers = _read_csv("workers.csv")
    visas = {v["worker_id"]: v for v in _read_csv("visas.csv")}
    docs_raw = _read_csv("worker_documents.csv")
    company_map = _build_company_map()

    # worker별 서류 상태 집계 — 한글 키로 변환
    docs_by_worker: dict[str, dict[str, str]] = {}
    for d in docs_raw:
        wid = d["worker_id"]
        if wid not in docs_by_worker:
            docs_by_worker[wid] = {}
        ko_key = DOC_TYPE_KO.get(d["doc_type"], d["doc_type"])
        status = d["status"].upper()
        docs_by_worker[wid][ko_key] = "ok" if status == "SUBMITTED" else "missing"

    result = []
    for w in workers:
        wid = w["id"]
        visa = visas.get(wid, {})
        company = company_map.get(w["company_id"], {})
        docs = docs_by_worker.get(wid, {})
        missing_count = sum(1 for v in docs.values() if v == "missing")
        visa_expiry = visa.get("expires_at") or w.get("visa_expires_at", "")
        days = _dday(visa_expiry)

        result.append({
            "id": wid,
            "companyId": w["company_id"],
            "companyName": company.get("name", ""),
            "name": w["name"],
            "nameKo": w["name"],
            "nationality": w["nationality"],
            "flag": NATIONALITY_FLAG.get(w["nationality"], "🌏"),
            "line": company.get("region", "") + " · " + company.get("industry", ""),
            "arn": "***-*******",
            "visaType": w["visa_type"],
            "visaExpiry": visa_expiry,
            "visaStatus": visa.get("status", ""),
            "contractEnd": w.get("contract_ends_at", ""),
            "contractStart": w.get("contract_starts_at", ""),
            "tenure": _calc_tenure(w.get("contract_starts_at", "")),
            "status": w.get("status", "ACTIVE"),
            "docs": docs,
            "missingDocs": missing_count,
            "severity": _severity(days),
            "preferredLanguage": w.get("preferred_language", ""),
            "avatar": w["name"][0] if w.get("name") else "?",
            "notes": (
                "체류만료 초과. 즉시 확인 필요" if days < 0
                else "체류기간 연장 신청 준비 필요" if days <= 30
                else "만료 90일 이내. 사전 준비 권장" if days <= 90
                else "정상"
            ),
        })

    return result


@router.get("/cases")
def get_cases() -> list[dict[str, Any]]:
    """근로자 데이터 기반으로 리스크 케이스를 동적 생성한다."""
    workers_resp = get_workers()
    cases = []
    idx = 1

    for w in workers_resp:
        days = _dday(w["visaExpiry"])
        sev = w["severity"]

        # 비자 만료 케이스
        if days < 0:
            cases.append({
                "id": f"case_{idx:03d}",
                "workerId": w["id"],
                "riskType": "visa_expiry",
                "severity": "CRITICAL",
                "label": "체류만료 초과",
                "summary": f"체류만료일({w['visaExpiry']})이 {abs(days)}일 지났습니다. 즉시 확인이 필요합니다.",
                "citationIds": ["cit_001", "cit_002"],
                "actions": ["act_001"],
            })
            idx += 1
        elif days <= 30:
            cases.append({
                "id": f"case_{idx:03d}",
                "workerId": w["id"],
                "riskType": "visa_expiry",
                "severity": "HIGH",
                "label": f"체류만료 D-{days}",
                "summary": f"체류만료까지 {days}일 남았습니다. 연장 신청 또는 자진 출국 검토가 필요합니다.",
                "citationIds": ["cit_001", "cit_003"],
                "actions": ["act_003", "act_004"],
            })
            idx += 1
        elif days <= 90:
            cases.append({
                "id": f"case_{idx:03d}",
                "workerId": w["id"],
                "riskType": "visa_expiry",
                "severity": "MEDIUM",
                "label": f"체류만료 D-{days}",
                "summary": f"체류만료일({w['visaExpiry']})까지 {days}일. 사전 준비 권장.",
                "citationIds": ["cit_001"],
                "actions": [],
            })
            idx += 1

        # 서류 누락 케이스
        if w["missingDocs"] > 0:
            missing_names = [k for k, v in w["docs"].items() if v == "missing"]
            cases.append({
                "id": f"case_{idx:03d}",
                "workerId": w["id"],
                "riskType": "missing_document",
                "severity": "HIGH" if sev in ("CRITICAL", "HIGH") else "MEDIUM",
                "label": "필수서류 누락",
                "summary": f"{', '.join(missing_names)} 보완이 필요합니다.",
                "citationIds": ["cit_004"],
                "actions": ["act_005"],
            })
            idx += 1

    return cases
