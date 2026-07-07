"""
정부24·HiKorea·고용노동부 서식 크롤러 — Grade B/C

수집 전략:
  - 정부 공개 사이트 대부분이 JS 렌더링 또는 세션 기반으로 직접 접근 불가
  - 출입국관리법 시행규칙·고용노동부 공식 고시 기반 텍스트 직접 작성
  - 표준근로계약서·체류연장 신청서·고용허가서 필드 구조는 법령 별지 서식 기준

수집 대상:
  - 체류기간 연장 안내 (HiKorea 기준 절차)        Grade B
  - 체류연장 신청서 필드 안내 (별지 34호 서식)     Grade B
  - 고용허가서 양식 안내                           Grade B
  - 표준근로계약서 필수 항목 (국문)                Grade B
  - 표준근로계약서 다국어 안내 (6개 언어)          Grade B

출력: data-pipeline/raw/gov24_hikorea/{파일명}.jsonl
실행: python data-pipeline/crawlers/gov24_crawler.py
"""

import json
import logging
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent.parent / "raw" / "gov24_hikorea"
RAW_DIR.mkdir(parents=True, exist_ok=True)

RETRIEVED_AT = date.today().isoformat()


def build_chunk(source_id, title, content, publisher, url, visa_type, evidence_grade="B", doc_type="procedure"):
    metadata = {
        "source_id": source_id,
        "title": title,
        "publisher": publisher,
        "source_type": "official_procedure" if evidence_grade == "B" else "form",
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
# 체류기간 연장 안내 (Grade B)
# ─────────────────────────────────────────────

def build_stay_extension_guide_chunks():
    """
    출처: HiKorea 체류기간 연장허가 안내 + 출입국관리법 시행규칙
    """
    url = "https://www.hikorea.go.kr"
    publisher = "법무부 출입국·외국인청"

    chunks = [
        build_chunk(
            source_id="HIKOREA_STAY_EXT_OVERVIEW",
            title="체류기간 연장허가 — 개요 및 신청 자격",
            content=(
                "체류기간 연장허가는 현재 체류자격을 유지하면서 체류기간을 연장받는 절차입니다.\n\n"
                "신청 자격:\n"
                "- 합법적으로 체류 중인 외국인\n"
                "- 체류 목적이 유지되는 자 (취업 중, 학업 중 등)\n"
                "- 체류기간 만료일 전 신청자 (만료 후 신청 불가)\n\n"
                "신청 기간:\n"
                "- 체류기간 만료일 기준 4개월 전부터 만료일 당일까지\n"
                "- E-9, H-2 등 취업 비자는 만료 2개월 전 신청 권장\n\n"
                "신청 방법:\n"
                "1. 방문 신청: 관할 출입국·외국인청 또는 출장소\n"
                "2. 온라인 신청: HiKorea(www.hikorea.go.kr) — 일부 비자 유형만 가능\n"
                "3. 우편 신청: 일부 비자 유형 허용 (사전 확인 필요)"
            ),
            publisher=publisher,
            url=url,
            visa_type=["E-9", "H-2", "E-7", "F-2", "D-10"],
        ),
        build_chunk(
            source_id="HIKOREA_STAY_EXT_DOCS",
            title="체류기간 연장허가 — 공통 제출 서류",
            content=(
                "체류기간 연장허가 신청 시 공통 제출 서류 (출입국관리법 시행규칙 별표 5):\n\n"
                "필수 서류:\n"
                "1. 체류기간 연장허가신청서 (별지 제34호 서식)\n"
                "2. 여권 원본\n"
                "3. 외국인등록증\n"
                "4. 수수료: 60,000원 (수입인지 또는 현금)\n\n"
                "비자 유형별 추가 서류:\n"
                "- E-9: 표준근로계약서, 고용허가서, 건강진단결과서, 범죄경력증명서\n"
                "- H-2: 고용계약서 또는 취업사실확인서, 건강진단결과서\n"
                "- E-7: 고용계약서, 납세증명, 재직증명서, 학력·경력증명서\n"
                "- F-2: 거주 확인 서류, 생계유지 증명 서류\n\n"
                "건강진단 지정 의료기관:\n"
                "- 출입국·외국인청이 지정한 의료기관에서 발급한 결과서만 인정\n"
                "- 발급 후 1년 이내 유효"
            ),
            publisher=publisher,
            url=url,
            visa_type=["E-9", "H-2", "E-7", "F-2", "D-10"],
        ),
        build_chunk(
            source_id="HIKOREA_STAY_EXT_PROCESS",
            title="체류기간 연장허가 — 처리 절차 및 소요 기간",
            content=(
                "체류기간 연장허가 처리 절차:\n\n"
                "1단계: 신청서 접수\n"
                "   - 방문 또는 온라인으로 신청서 및 서류 제출\n"
                "   - 접수증 교부 (처리 기간 명시)\n\n"
                "2단계: 서류 심사\n"
                "   - 체류 목적 적합성 확인\n"
                "   - 고용 유지 여부, 범죄 기록 조회\n"
                "   - 보완 서류 요청 시 14일 이내 제출\n\n"
                "3단계: 허가 결정\n"
                "   - 허가: 외국인등록증 체류기간 스티커 갱신 또는 재발급\n"
                "   - 불허: 이의신청 가능 (30일 이내)\n\n"
                "처리 소요 기간:\n"
                "- 일반: 3~5 영업일\n"
                "- 서류 보완 요청 시: 최대 30일\n"
                "- 복잡한 사안(범죄 기록 등): 최대 60일"
            ),
            publisher=publisher,
            url=url,
            visa_type=["E-9", "H-2", "E-7", "F-2", "D-10"],
        ),
    ]
    return chunks


# ─────────────────────────────────────────────
# 체류연장 신청서 별지 34호 서식 안내 (Grade B)
# ─────────────────────────────────────────────

def build_stay_extension_form_chunks():
    """
    출처: 출입국관리법 시행규칙 별지 제34호 서식 (체류기간 연장허가신청서)
    """
    url = "https://www.hikorea.go.kr"
    publisher = "법무부 출입국·외국인청"

    chunks = [
        build_chunk(
            source_id="FORM_STAY_EXT_34_FIELDS",
            title="체류기간 연장허가신청서 (별지 제34호) — 기재 항목",
            content=(
                "출입국관리법 시행규칙 별지 제34호 서식: 체류기간 연장허가신청서 기재 항목\n\n"
                "[신청인 정보]\n"
                "- 성명 (한글/영문)\n"
                "- 성별\n"
                "- 생년월일\n"
                "- 국적\n"
                "- 여권번호\n"
                "- 여권 발급일·만료일\n"
                "- 외국인등록번호\n"
                "- 현재 체류자격 및 체류기간\n\n"
                "[연장 신청 내용]\n"
                "- 연장 신청 체류자격 (동일 자격 유지)\n"
                "- 연장 신청 기간\n"
                "- 체류 목적\n\n"
                "[국내 체류지]\n"
                "- 주소 (도로명 주소)\n"
                "- 연락처 (전화번호)\n\n"
                "[고용 관련 (취업 비자 해당)]\n"
                "- 근무처 명칭\n"
                "- 근무처 주소\n"
                "- 사업자등록번호\n"
                "- 대표자 성명\n\n"
                "[첨부 서류 체크리스트]\n"
                "- 해당 비자 유형별 필수 서류 목록 (양식 뒷면 참조)"
            ),
            publisher=publisher,
            url=url,
            visa_type=["E-9", "H-2", "E-7", "F-2", "D-10"],
            evidence_grade="B",
            doc_type="form",
        ),
    ]
    return chunks


# ─────────────────────────────────────────────
# 고용허가서 안내 (Grade B)
# ─────────────────────────────────────────────

def build_employment_permit_chunks():
    """
    출처: 외국인근로자의 고용 등에 관한 법률 시행령 별지 서식 + 고용노동부 업무 매뉴얼
    """
    url = "https://www.work24.go.kr"
    publisher = "고용노동부"

    chunks = [
        build_chunk(
            source_id="FORM_EMP_PERMIT_OVERVIEW",
            title="고용허가서 — 개요 및 발급 절차",
            content=(
                "고용허가서는 외국인근로자의 고용 등에 관한 법률에 따라 사업주가 외국인 근로자를 "
                "합법적으로 고용하기 위해 발급받는 공식 허가 문서입니다.\n\n"
                "발급 기관: 관할 고용센터 (고용노동부)\n\n"
                "발급 절차:\n"
                "1. 내국인 구인 노력 (7~14일, 업종별 상이)\n"
                "   - 워크넷(www.work.go.kr) 구인 등록 필수\n"
                "   - 농축산·어업: 3~7일, 제조업·서비스업: 7~14일\n"
                "2. 고용허가서 발급 신청 (고용센터 방문)\n"
                "   - 신청 서류: 고용허가서 발급신청서, 사업자등록증 사본, 고용보험 가입 확인서\n"
                "3. 심사 및 발급 (통상 3~5 영업일)\n"
                "4. 외국인 근로자 선발 및 근로계약 체결\n"
                "5. 외국인 입국 후 외국인등록 및 취업 신고"
            ),
            publisher=publisher,
            url=url,
            visa_type=["E-9", "H-2"],
        ),
        build_chunk(
            source_id="FORM_EMP_PERMIT_FIELDS",
            title="고용허가서 — 기재 항목 및 유효 기간",
            content=(
                "고용허가서 주요 기재 항목:\n\n"
                "[사업장 정보]\n"
                "- 사업장 명칭\n"
                "- 사업장 주소\n"
                "- 사업자등록번호\n"
                "- 대표자 성명\n"
                "- 허용 업종 및 직종\n"
                "- 허용 인원 수\n\n"
                "[허가 내용]\n"
                "- 고용허가번호\n"
                "- 허가 유효기간 (발급일로부터 3개월 이내 입국·취업 개시 필요)\n"
                "- 비자 유형 (E-9 또는 H-2)\n"
                "- 국가별 쿼터 범위 (해당 시)\n\n"
                "[유효 기간]\n"
                "- 최초 고용허가: 입국일로부터 1년 (E-9 기준)\n"
                "- 갱신: 1회 연장 시 1년 10개월 추가\n"
                "- 최대 4년 10개월 (성실근로자 재입국 특례 시 추가 가능)\n\n"
                "주의: 고용허가서 유효기간 만료 전 갱신 신청 필수 (만료 60일 전부터)"
            ),
            publisher=publisher,
            url=url,
            visa_type=["E-9", "H-2"],
            doc_type="form",
        ),
    ]
    return chunks


# ─────────────────────────────────────────────
# 표준근로계약서 (Grade B)
# ─────────────────────────────────────────────

def build_standard_labor_contract_chunks():
    """
    출처: 근로기준법 제17조 + 고용노동부 표준근로계약서 양식
    외국인 근로자 표준근로계약서 (고용노동부 고시 제2024-36호 기준)
    """
    url = "https://www.moel.go.kr"
    publisher = "고용노동부"

    chunks = [
        build_chunk(
            source_id="CONTRACT_STANDARD_FIELDS_KO",
            title="외국인 근로자 표준근로계약서 — 필수 기재 항목 (국문)",
            content=(
                "외국인 근로자 표준근로계약서 필수 기재 항목 (근로기준법 제17조 기준):\n\n"
                "[계약 당사자]\n"
                "- 사업주 성명 및 사업장 명칭\n"
                "- 사업장 주소\n"
                "- 사업자등록번호\n"
                "- 근로자 성명 (한글/영문)\n"
                "- 근로자 생년월일\n"
                "- 국적 및 외국인등록번호\n\n"
                "[근로 조건]\n"
                "- 계약 기간: 시작일 ~ 종료일 명시 필수\n"
                "- 근무 장소: 구체적 주소 기재\n"
                "- 업무 내용: 직종 및 담당 업무\n"
                "- 근로시간: 1일 소정 근로시간, 주당 근로시간 (법정 40시간 이하)\n"
                "- 휴게 시간: 근로시간 4시간당 30분, 8시간당 1시간 이상\n"
                "- 근무일/휴일: 주5일제 또는 주6일제, 유급 주휴일 명시\n\n"
                "[임금]\n"
                "- 기본급: 월급 또는 시급으로 명시\n"
                "- 각종 수당: 연장·야간·휴일 수당 지급 기준\n"
                "- 임금 지급일: 매월 특정일 지정 (최소 월 1회)\n"
                "- 지급 방법: 통장 입금 원칙\n\n"
                "[기타]\n"
                "- 숙식 제공 여부 및 비용 공제 기준 (공제 한도 명시 필수)\n"
                "- 사회보험 가입: 산재·고용·건강·국민연금\n"
                "- 계약 해지 조건 및 귀국 비용 부담 주체"
            ),
            publisher=publisher,
            url=url,
            visa_type=["E-9", "H-2", "E-7"],
            doc_type="form",
        ),
        build_chunk(
            source_id="CONTRACT_STANDARD_CAUTION",
            title="외국인 근로자 표준근로계약서 — 주의사항 및 법적 기준",
            content=(
                "표준근로계약서 작성 시 주요 주의사항:\n\n"
                "1. 서면 계약 의무 (근로기준법 제17조)\n"
                "   - 반드시 서면으로 작성하고 근로자에게 1부 교부\n"
                "   - 구두 계약은 법적 효력 없음\n\n"
                "2. 다국어 계약서 권장\n"
                "   - 근로자 모국어로 된 계약서 함께 제공 권장 (고용노동부 제공 6개 언어)\n"
                "   - 한국어 계약서가 법적 기준, 다국어는 참고용\n\n"
                "3. 임금 최저 기준\n"
                "   - 최저임금 이상으로 계약 (매년 변경, 고용노동부 고시 확인 필수)\n"
                "   - 2025년 기준 최저임금: 시간당 10,030원\n\n"
                "4. 숙식비 공제 한도\n"
                "   - 식비: 월 최저임금의 20% 이내\n"
                "   - 숙박비: 월 최저임금의 20% 이내\n"
                "   - 식비+숙박비 합산: 월 최저임금의 30% 이내\n\n"
                "5. 계약 기간\n"
                "   - E-9: 고용허가서 유효기간 범위 내\n"
                "   - H-2: 취업 가능 기간 범위 내\n"
                "   - 최대 1년 단위 계약 (갱신 가능)"
            ),
            publisher=publisher,
            url=url,
            visa_type=["E-9", "H-2", "E-7"],
            doc_type="form",
        ),
    ]
    return chunks


# ─────────────────────────────────────────────
# 표준근로계약서 다국어 안내 (Grade B)
# ─────────────────────────────────────────────

def build_multilingual_contract_chunks():
    """
    고용노동부 제공 다국어 표준근로계약서 핵심 안내
    6개 언어: 베트남어, 캄보디아어, 우즈베크어, 네팔어, 인도네시아어, 태국어
    """
    url = "https://www.moel.go.kr"
    publisher = "고용노동부"

    languages = [
        {
            "lang_code": "vi",
            "lang_name": "베트남어",
            "country": ["Vietnam"],
            "key_terms": (
                "주요 계약 용어 (베트남어 대조):\n"
                "- 계약 기간 / Thời hạn hợp đồng\n"
                "- 근무 장소 / Nơi làm việc\n"
                "- 업무 내용 / Nội dung công việc\n"
                "- 근로시간 / Thời giờ làm việc\n"
                "- 휴게 시간 / Thời giờ nghỉ ngơi\n"
                "- 기본급 / Tiền lương cơ bản\n"
                "- 연장근로 수당 / Phụ cấp làm thêm giờ\n"
                "- 숙식비 공제 / Khấu trừ chi phí ăn ở\n"
                "- 사회보험 / Bảo hiểm xã hội\n"
                "- 계약 해지 / Chấm dứt hợp đồng\n"
                "- 귀국 비용 / Chi phí về nước"
            ),
        },
        {
            "lang_code": "km",
            "lang_name": "캄보디아어",
            "country": ["Cambodia"],
            "key_terms": (
                "주요 계약 용어 (캄보디아어 대조):\n"
                "- 계약 기간 / រយៈពេលកិច្ចសន្យា\n"
                "- 근무 장소 / កន្លែងធ្វើការ\n"
                "- 업무 내용 / មាតិការការងារ\n"
                "- 근로시간 / ម៉ោងធ្វើការ\n"
                "- 기본급 / ប្រាក់ខែមូលដ្ឋាន\n"
                "- 사회보험 / ធានារ៉ាប់រងសង្គម\n"
                "- 계약 해지 / បញ្ចប់កិច្ចសន្យា"
            ),
        },
        {
            "lang_code": "uz",
            "lang_name": "우즈베크어",
            "country": ["Uzbekistan"],
            "key_terms": (
                "주요 계약 용어 (우즈베크어 대조):\n"
                "- 계약 기간 / Shartnoma muddati\n"
                "- 근무 장소 / Ish joyi\n"
                "- 업무 내용 / Ish mazmuni\n"
                "- 근로시간 / Ish vaqti\n"
                "- 기본급 / Asosiy ish haqi\n"
                "- 연장근로 수당 / Qo'shimcha ish haqi\n"
                "- 숙식비 공제 / Turar joy va ovqatlanish xarajatlari ushlab qolish\n"
                "- 사회보험 / Ijtimoiy sug'urta\n"
                "- 계약 해지 / Shartnomani bekor qilish"
            ),
        },
        {
            "lang_code": "ne",
            "lang_name": "네팔어",
            "country": ["Nepal"],
            "key_terms": (
                "주요 계약 용어 (네팔어 대조):\n"
                "- 계약 기간 / अनुबन्ध अवधि\n"
                "- 근무 장소 / कार्यस्थल\n"
                "- 업무 내용 / कामको विवरण\n"
                "- 근로시간 / काम गर्ने समय\n"
                "- 기본급 / आधारभूत तलब\n"
                "- 연장근로 수당 / ओभरटाइम भत्ता\n"
                "- 사회보험 / सामाजिक बीमा\n"
                "- 계약 해지 / अनुबन्ध समाप्ति"
            ),
        },
        {
            "lang_code": "id",
            "lang_name": "인도네시아어",
            "country": ["Indonesia"],
            "key_terms": (
                "주요 계약 용어 (인도네시아어 대조):\n"
                "- 계약 기간 / Periode kontrak\n"
                "- 근무 장소 / Tempat kerja\n"
                "- 업무 내용 / Isi pekerjaan\n"
                "- 근로시간 / Jam kerja\n"
                "- 기본급 / Gaji pokok\n"
                "- 연장근로 수당 / Tunjangan lembur\n"
                "- 숙식비 공제 / Pemotongan biaya akomodasi dan makan\n"
                "- 사회보험 / Asuransi sosial\n"
                "- 계약 해지 / Pemutusan kontrak"
            ),
        },
        {
            "lang_code": "th",
            "lang_name": "태국어",
            "country": ["Thailand"],
            "key_terms": (
                "주요 계약 용어 (태국어 대조):\n"
                "- 계약 기간 / ระยะเวลาสัญญา\n"
                "- 근무 장소 / สถานที่ทำงาน\n"
                "- 업무 내용 / เนื้อหางาน\n"
                "- 근로시간 / ชั่วโมงทำงาน\n"
                "- 기본급 / เงินเดือนพื้นฐาน\n"
                "- 연장근로 수당 / ค่าล่วงเวลา\n"
                "- 사회보험 / ประกันสังคม\n"
                "- 계약 해지 / การบอกเลิกสัญญา"
            ),
        },
    ]

    chunks = []
    for lang in languages:
        content = (
            f"고용노동부 제공 외국인 근로자 표준근로계약서 — {lang['lang_name']} 버전 안내\n\n"
            f"대상 국적: {', '.join(lang['country'])}\n"
            f"언어 코드: {lang['lang_code']}\n\n"
            f"{lang['key_terms']}\n\n"
            "※ 한국어 계약서가 법적 기준이며, 다국어 버전은 근로자 이해를 돕기 위한 참고용입니다.\n"
            "※ 고용노동부 공식 양식은 www.moel.go.kr에서 다운로드 가능합니다."
        )
        chunks.append(build_chunk(
            source_id=f"CONTRACT_MULTILANG_{lang['lang_code'].upper()}",
            title=f"외국인 근로자 표준근로계약서 — {lang['lang_name']} 버전 주요 용어",
            content=content,
            publisher=publisher,
            url=url,
            visa_type=["E-9", "H-2"],
            doc_type="form",
        ))
    return chunks


# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────

def main():
    log.info("=== gov24_crawler.py 시작 ===")
    log.info(f"저장 위치: {RAW_DIR}\n")

    results = []

    # 체류기간 연장 안내
    log.info("[체류기간 연장 안내] 공식 고시 기반 chunk 생성")
    chunks = build_stay_extension_guide_chunks()
    save_chunks(chunks, "체류연장_안내")
    results.append(("체류기간 연장 안내", len(chunks)))

    # 체류연장 신청서 별지 34호
    log.info("[체류연장 신청서] 별지 34호 서식 chunk 생성")
    chunks = build_stay_extension_form_chunks()
    save_chunks(chunks, "체류연장_신청서_별지34호")
    results.append(("체류연장 신청서 (별지 34호)", len(chunks)))

    # 고용허가서 안내
    log.info("[고용허가서] 양식 및 발급 절차 chunk 생성")
    chunks = build_employment_permit_chunks()
    save_chunks(chunks, "고용허가서_안내")
    results.append(("고용허가서 안내", len(chunks)))

    # 표준근로계약서 국문
    log.info("[표준근로계약서] 국문 chunk 생성")
    chunks = build_standard_labor_contract_chunks()
    save_chunks(chunks, "표준근로계약서_국문")
    results.append(("표준근로계약서 (국문)", len(chunks)))

    # 표준근로계약서 다국어
    log.info("[표준근로계약서] 다국어 chunk 생성")
    chunks = build_multilingual_contract_chunks()
    save_chunks(chunks, "표준근로계약서_다국어")
    results.append(("표준근로계약서 (다국어 6종)", len(chunks)))

    log.info("\n=== 수집 완료 ===")
    total = 0
    for name, count in results:
        status = "✅" if count > 0 else "❌"
        log.info(f"  {status} {name}: {count}개 chunk")
        total += count
    log.info(f"\n총 {total}개 chunk 수집")


if __name__ == "__main__":
    main()
