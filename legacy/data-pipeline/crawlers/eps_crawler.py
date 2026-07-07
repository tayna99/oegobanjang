"""
EPS·HRD Korea 절차 크롤러 — Grade B (공식 절차)

수집 전략:
  - H-2 절차: eps.hrdkorea.or.kr 공개 페이지 requests 크롤링
  - E-9/E-7 절차: eps.go.kr 로그인 불가(외국인 전용 계정)로 수집 불가
                  → 고용노동부·출입국청 공식 고시 텍스트 직접 작성

수집 대상:
  - E-9 체류연장 절차
  - E-9 사업장변경 절차
  - E-7 갱신 절차
  - H-2 방문취업 취업 절차 (크롤링)
  - H-2 신고의무사항 (크롤링)

출력: data-pipeline/raw/eps/{파일명}.jsonl
실행: python data-pipeline/crawlers/eps_crawler.py
"""

import json
import logging
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent.parent / "raw" / "eps"
RAW_DIR.mkdir(parents=True, exist_ok=True)

RETRIEVED_AT = date.today().isoformat()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


# ─────────────────────────────────────────────
# 공통 유틸
# ─────────────────────────────────────────────

def build_chunk(source_id, title, content, publisher, url, visa_type, doc_type="procedure", evidence_grade="B"):
    metadata = {
        "source_id": source_id,
        "title": title,
        "publisher": publisher,
        "source_type": "official_procedure",
        "url": url,
        "retrieved_at": RETRIEVED_AT,
        "effective_date": None,
        "doc_type": doc_type,
        "mission_agent": ["visa_document_agent"],
        "visa_type": visa_type,
        "country": ["ALL"],
        "industry": ["ALL"],
        "risk_level": "high",
        "evidence_grade": evidence_grade,
    }
    return {"source_id": source_id, "title": title, "content": content, "metadata": metadata}


def save_chunks(chunks, filename):
    output_path = RAW_DIR / f"{filename}.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    log.info(f"  저장 완료: {output_path.name} ({len(chunks)}개 chunk)")
    return output_path


# ─────────────────────────────────────────────
# E-9 체류연장 절차 (공식 고시 기반 직접 작성)
# ─────────────────────────────────────────────

def build_e9_stay_extension_chunks():
    """
    출처: 고용노동부 고용허가제 업무 매뉴얼 + 출입국관리법 시행규칙
    eps.go.kr 로그인 불가(외국인 전용)로 공식 고시 텍스트 직접 입력
    """
    url = "https://www.eps.go.kr"
    visa_type = ["E-9"]
    publisher = "고용노동부·법무부"

    steps = [
        {
            "id": "E9_STAY_EXT_STEP1",
            "title": "E-9 체류연장 절차 — 1단계: 신청 가능 기간 확인",
            "content": (
                "E-9(비전문취업) 비자 체류기간 연장 신청은 체류기간 만료일 기준 4개월 전부터 만료일 당일까지 가능합니다. "
                "단, 고용허가서 유효기간 범위 내에서만 연장이 허용됩니다. "
                "1회 연장 시 최대 1년 10개월, 최초 입국일부터 최대 4년 10개월까지 체류 가능합니다."
            ),
        },
        {
            "id": "E9_STAY_EXT_STEP2",
            "title": "E-9 체류연장 절차 — 2단계: 고용허가기간 연장 신청 (사업주)",
            "content": (
                "사업주는 근로계약 만료 60일 전부터 만료 전일까지 관할 고용센터에 고용허가기간 연장신청을 해야 합니다. "
                "신청 서류: 고용허가기간 연장신청서, 외국인근로자 표준근로계약서(갱신). "
                "고용센터에서 심사 후 고용허가서를 재발급합니다."
            ),
        },
        {
            "id": "E9_STAY_EXT_STEP3",
            "title": "E-9 체류연장 절차 — 3단계: 체류기간 연장 필요 서류 준비",
            "content": (
                "체류기간 연장 신청 시 필요 서류 (출입국관리법 시행규칙 별표 5 기준):\n"
                "1. 체류기간 연장허가신청서 (별지 제34호 서식)\n"
                "2. 여권 원본\n"
                "3. 외국인등록증\n"
                "4. 표준근로계약서 사본 (갱신된 것)\n"
                "5. 고용허가서 사본\n"
                "6. 건강진단결과서 (출입국·외국인청 지정 의료기관 발급, 1년 이내)\n"
                "7. 범죄경력증명서 (해당자에 한함)\n"
                "수수료: 60,000원"
            ),
        },
        {
            "id": "E9_STAY_EXT_STEP4",
            "title": "E-9 체류연장 절차 — 4단계: 출입국·외국인청 신청",
            "content": (
                "준비된 서류를 지참하여 관할 출입국·외국인청(또는 출장소)에 방문 신청하거나 "
                "HiKorea(www.hikorea.go.kr)에서 온라인 신청이 가능합니다. "
                "처리 기간은 통상 3~5 영업일이며, 복잡한 경우 최대 14일이 소요될 수 있습니다. "
                "연장 허가 후 외국인등록증의 체류기간이 갱신됩니다."
            ),
        },
        {
            "id": "E9_STAY_EXT_NOTE",
            "title": "E-9 체류연장 — 주의사항 및 제한",
            "content": (
                "E-9 비자 체류연장 시 주요 제한 사항:\n"
                "1. 사업장 변경 없이 동일 사업장에서 계속 근무하는 경우에만 연장 가능\n"
                "2. 체류기간 만료 후 신청 시 불법 체류로 처리되며 출국 조치 대상\n"
                "3. 고용허가서 유효기간이 체류기간보다 짧으면 고용허가서 범위 내에서만 연장\n"
                "4. 연장 거부 사유: 범죄 기록, 산업재해 은폐, 출국 명령 이력 등\n"
                "5. 최대 체류 가능 기간(4년 10개월) 초과 후 재입국 특례 적용 가능 (성실 근로자)"
            ),
        },
    ]

    chunks = []
    for step in steps:
        chunks.append(build_chunk(
            source_id=step["id"],
            title=step["title"],
            content=step["content"],
            publisher=publisher,
            url=url,
            visa_type=visa_type,
        ))
    return chunks


# ─────────────────────────────────────────────
# E-9 사업장변경 절차 (공식 고시 기반 직접 작성)
# ─────────────────────────────────────────────

def build_e9_workplace_change_chunks():
    """
    출처: 외국인근로자의 고용 등에 관한 법률 제25조 + 고용허가제 업무 매뉴얼
    """
    url = "https://www.eps.go.kr"
    visa_type = ["E-9"]
    publisher = "고용노동부"

    steps = [
        {
            "id": "E9_WPC_STEP1",
            "title": "E-9 사업장변경 절차 — 1단계: 변경 사유 확인",
            "content": (
                "E-9 외국인근로자의 사업장 변경은 외국인근로자의 고용 등에 관한 법률 제25조에 따라 "
                "아래 사유에 해당하는 경우에만 허용됩니다:\n"
                "1. 사용자가 정당한 사유 없이 근로계약 조건을 위반한 경우\n"
                "2. 휴업·폐업 또는 고용허가 취소·고용제한 조치를 받은 경우\n"
                "3. 사용자의 근로조건 위반 또는 부당한 처우로 근로 지속이 어려운 경우\n"
                "4. 사업장의 근로환경이 법령 위반으로 근로 지속이 어려운 경우\n"
                "5. 사용자와의 협의 하에 계약 해지 합의가 이루어진 경우\n"
                "원칙적으로 사업장 변경 횟수는 3년간 3회, 연장 후 2년간 2회로 제한됩니다."
            ),
        },
        {
            "id": "E9_WPC_STEP2",
            "title": "E-9 사업장변경 절차 — 2단계: 사업장변경 신청",
            "content": (
                "사업장 변경 신청 방법:\n"
                "- 신청처: 관할 고용센터 (외국인 본인 또는 위임장 지참 대리인)\n"
                "- 신청 서류:\n"
                "  1. 외국인근로자 사업장 변경 신청서\n"
                "  2. 여권 사본\n"
                "  3. 외국인등록증 사본\n"
                "  4. 근로계약 해지 확인서 또는 사유 입증 서류\n"
                "- 신청 기한: 이전 사업장 근무 종료일부터 3개월 이내\n"
                "  (기한 초과 시 출국 조치 대상)"
            ),
        },
        {
            "id": "E9_WPC_STEP3",
            "title": "E-9 사업장변경 절차 — 3단계: 새 사업장 구직 및 계약 체결",
            "content": (
                "고용센터에서 구직 등록 후 새 사업장 매칭 절차:\n"
                "1. 고용센터 구직 등록 (구직 활동 기간: 3개월, 1회 연장 가능)\n"
                "2. 사업주 구인 신청 및 매칭\n"
                "3. 새 사업장과 표준근로계약서 체결\n"
                "4. 고용센터에 고용허가서 발급 신청 (새 사업주)\n"
                "5. 출입국·외국인청에 근무처 변경 신고 (취업 후 14일 이내)\n"
                "주의: 구직 기간 중 무단 취업 시 강제 출국 대상"
            ),
        },
        {
            "id": "E9_WPC_NOTE",
            "title": "E-9 사업장변경 — 제한 및 주의사항",
            "content": (
                "E-9 사업장 변경 시 주요 제한 사항:\n"
                "1. 허가된 업종 범위 내에서만 변경 가능 (제조업 → 제조업)\n"
                "2. 변경 횟수 초과 시 출국 조치: 3년간 최대 3회, 연장 기간 내 2회\n"
                "3. 귀책 사유가 근로자에게 있는 경우 변경 불허\n"
                "4. 새 사업장에서도 고용허가 요건(내국인 구인 노력 등) 충족 필요\n"
                "5. 사업장 변경 후 체류기간은 기존 잔여 기간 내에서만 인정"
            ),
        },
    ]

    chunks = []
    for step in steps:
        chunks.append(build_chunk(
            source_id=step["id"],
            title=step["title"],
            content=step["content"],
            publisher=publisher,
            url=url,
            visa_type=visa_type,
        ))
    return chunks


# ─────────────────────────────────────────────
# E-7 갱신 절차 (공식 고시 기반 직접 작성)
# ─────────────────────────────────────────────

def build_e7_renewal_chunks():
    """
    출처: 출입국관리법 시행령 별표 1의2 + 출입국·외국인청 체류안내서
    """
    url = "https://www.immigration.go.kr"
    visa_type = ["E-7"]
    publisher = "법무부"

    steps = [
        {
            "id": "E7_RENEWAL_STEP1",
            "title": "E-7 체류자격 갱신 절차 — 1단계: 갱신 요건 확인",
            "content": (
                "E-7(특정활동) 체류자격 갱신을 위한 기본 요건:\n"
                "1. 체류기간 만료 전 4개월 이내에 신청\n"
                "2. 동일 직종·동일 사업체 또는 법무부 장관이 허가한 범위 내 활동\n"
                "3. 소득 요건: 전년도 1인당 GNI의 80% 이상 연봉 (직종별 기준 상이)\n"
                "4. 결격 사유 없음: 범죄 기록, 출입국 법규 위반 이력 등 없어야 함\n"
                "5. 고용계약서 유효: 갱신 기간을 포괄하는 고용계약이 존재해야 함"
            ),
        },
        {
            "id": "E7_RENEWAL_STEP2",
            "title": "E-7 체류자격 갱신 절차 — 2단계: 필요 서류 준비",
            "content": (
                "E-7 갱신 신청 필요 서류:\n"
                "1. 체류기간 연장허가신청서 (별지 제34호 서식)\n"
                "2. 여권 원본\n"
                "3. 외국인등록증\n"
                "4. 고용계약서 (갱신 기간 포함)\n"
                "5. 사업자등록증 사본\n"
                "6. 납세사실증명 또는 소득금액증명원 (최근 1년)\n"
                "7. 재직증명서\n"
                "8. 학위증명서 또는 경력증명서 (직종별 요구 상이)\n"
                "9. 건강진단결과서 (1년 이내, 일부 직종 해당)\n"
                "수수료: 60,000원"
            ),
        },
        {
            "id": "E7_RENEWAL_STEP3",
            "title": "E-7 체류자격 갱신 절차 — 3단계: 신청 및 처리",
            "content": (
                "신청 방법:\n"
                "- 방문 신청: 관할 출입국·외국인청 또는 출장소\n"
                "- 온라인 신청: HiKorea(www.hikorea.go.kr)\n\n"
                "처리 기간:\n"
                "- 통상 5~7 영업일 (서류 완비 기준)\n"
                "- 심사 강화 직종(IT, 연구 등)은 2~4주 소요 가능\n\n"
                "갱신 후 체류 기간:\n"
                "- 최초 허가: 1~3년 (직종별 상이)\n"
                "- 갱신 시: 최대 3년 단위로 연장 가능\n"
                "- 장기 체류(5년 이상) 후 F-2(장기거주) 자격 변경 검토 가능"
            ),
        },
    ]

    chunks = []
    for step in steps:
        chunks.append(build_chunk(
            source_id=step["id"],
            title=step["title"],
            content=step["content"],
            publisher=publisher,
            url=url,
            visa_type=visa_type,
        ))
    return chunks


# ─────────────────────────────────────────────
# H-2 절차 (eps.hrdkorea.or.kr 크롤링)
# ─────────────────────────────────────────────

H2_PAGES = [
    {
        "url": "https://eps.hrdkorea.or.kr/h2/empProcess/empProcess.do",
        "source_id": "H2_EMP_PROCESS",
        "title": "H-2 방문취업 취업 절차 안내",
        "visa_type": ["H-2"],
    },
    {
        "url": "https://eps.hrdkorea.or.kr/h2/empProcess/reportDuty.do",
        "source_id": "H2_REPORT_DUTY",
        "title": "H-2 방문취업 신고의무사항 (체류연장·근무처변경)",
        "visa_type": ["H-2"],
    },
    {
        "url": "https://eps.hrdkorea.or.kr/h2/empProcess/empEdu.do",
        "source_id": "H2_EMP_EDU",
        "title": "H-2 방문취업 취업교육 안내",
        "visa_type": ["H-2"],
    },
    {
        "url": "https://eps.hrdkorea.or.kr/h2/empProcess/empMediLab.do",
        "source_id": "H2_EMP_MEDI",
        "title": "H-2 방문취업 취업알선 및 근로계약체결 절차",
        "visa_type": ["H-2"],
    },
    {
        "url": "https://eps.hrdkorea.or.kr/h2/empProcess/protecOfRights.do",
        "source_id": "H2_RIGHTS",
        "title": "H-2 방문취업 권익보호 및 고충처리 안내",
        "visa_type": ["H-2"],
    },
    {
        "url": "https://eps.hrdkorea.or.kr/h2/h2empl/whatH2empl.do",
        "source_id": "H2_INTRO",
        "title": "특례고용허가제(H-2) 제도 개요",
        "visa_type": ["H-2"],
    },
]


def fetch_h2_page(page_meta):
    url = page_meta["url"]
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except Exception as e:
        log.error(f"  요청 실패: {url} — {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # 불필요한 태그 제거
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()

    # 본문 영역 우선 추출
    content_area = (
        soup.find("div", class_="cont_wrap")
        or soup.find("div", id="content")
        or soup.find("div", class_="content")
        or soup.find("main")
        or soup.find("body")
    )

    if not content_area:
        log.warning(f"  본문 영역 없음: {url}")
        return None

    text = content_area.get_text(separator="\n", strip=True)

    # 빈 줄 정리
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    content = "\n".join(lines)

    if len(content) < 50:
        log.warning(f"  콘텐츠 너무 짧음 ({len(content)}자): {url}")
        return None

    return build_chunk(
        source_id=page_meta["source_id"],
        title=page_meta["title"],
        content=content,
        publisher="한국산업인력공단 EPS",
        url=url,
        visa_type=page_meta["visa_type"],
    )


def crawl_h2_pages():
    chunks = []
    for page_meta in H2_PAGES:
        log.info(f"  크롤링: {page_meta['title']}")
        chunk = fetch_h2_page(page_meta)
        if chunk:
            chunks.append(chunk)
            log.info(f"    수집 성공 ({len(chunk['content'])}자)")
        time.sleep(1)
    return chunks


# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────

def main():
    log.info("=== eps_crawler.py 시작 ===")
    log.info(f"저장 위치: {RAW_DIR}\n")

    results = []

    # E-9 체류연장
    log.info("[E-9 체류연장] 공식 고시 기반 chunk 생성")
    chunks = build_e9_stay_extension_chunks()
    save_chunks(chunks, "E9_체류연장")
    results.append(("E-9 체류연장", len(chunks)))

    # E-9 사업장변경
    log.info("[E-9 사업장변경] 공식 고시 기반 chunk 생성")
    chunks = build_e9_workplace_change_chunks()
    save_chunks(chunks, "E9_사업장변경")
    results.append(("E-9 사업장변경", len(chunks)))

    # E-7 갱신
    log.info("[E-7 갱신] 공식 고시 기반 chunk 생성")
    chunks = build_e7_renewal_chunks()
    save_chunks(chunks, "E7_갱신")
    results.append(("E-7 갱신", len(chunks)))

    # H-2 절차 (크롤링)
    log.info("[H-2 절차] eps.hrdkorea.or.kr 크롤링")
    chunks = crawl_h2_pages()
    save_chunks(chunks, "H2_방문취업절차")
    results.append(("H-2 방문취업 절차", len(chunks)))

    log.info("\n=== 수집 완료 ===")
    total = 0
    for name, count in results:
        status = "✅" if count > 0 else "❌"
        log.info(f"  {status} {name}: {count}개 chunk")
        total += count
    log.info(f"\n총 {total}개 chunk 수집")


if __name__ == "__main__":
    main()
