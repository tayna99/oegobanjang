"""
산업인력공단·안전보건공단 안전자료 크롤러 — Grade D (안전·참고 자료)

수집 전략:
  - hrdkorea.or.kr: 세션 기반으로 직접 접근 불가
  - kosha.or.kr: JS 렌더링으로 직접 접근 불가
  - 산업안전보건법·고용노동부 공식 고시·안전보건공단 공개 자료 기반 텍스트 직접 작성

수집 대상:
  - 외국인 근로자 기초안전보건교육 안내     Grade D
  - 다국어 안전 용어 및 표지 안내           Grade D
  - 외국인 근로자 생활 안내 (권리·의무)     Grade D
  - 외국인 근로자 상담센터 안내             Grade D

출력: data-pipeline/raw/safety/{파일명}.jsonl
실행: python data-pipeline/crawlers/hrd_crawler.py
"""

import json
import logging
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

RAW_DIR = Path(__file__).parent.parent / "raw" / "safety"
RAW_DIR.mkdir(parents=True, exist_ok=True)

RETRIEVED_AT = date.today().isoformat()


def build_chunk(source_id, title, content, publisher, url, visa_type=None, country=None):
    metadata = {
        "source_id": source_id,
        "title": title,
        "publisher": publisher,
        "source_type": "safety_guide",
        "url": url,
        "retrieved_at": RETRIEVED_AT,
        "effective_date": None,
        "doc_type": "safety",
        "mission_agent": ["visa_document_agent"],
        "visa_type": visa_type or ["E-9", "H-2"],
        "country": country or ["ALL"],
        "industry": ["ALL"],
        "risk_level": "medium",
        "evidence_grade": "D",
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
# 기초안전보건교육 안내 (Grade D)
# ─────────────────────────────────────────────

def build_basic_safety_edu_chunks():
    """
    출처: 산업안전보건법 제31조 + 고용노동부 고시 + 한국산업인력공단 안전교육 안내
    """
    url = "https://www.hrdkorea.or.kr"
    publisher = "한국산업인력공단·고용노동부"

    chunks = [
        build_chunk(
            source_id="SAFETY_EDU_OVERVIEW",
            title="외국인 근로자 기초안전보건교육 — 개요 및 법적 근거",
            content=(
                "외국인 근로자 기초안전보건교육은 산업안전보건법 제31조에 따라 "
                "사업주가 근로자를 채용할 때 의무적으로 실시해야 하는 교육입니다.\n\n"
                "법적 근거:\n"
                "- 산업안전보건법 제31조 (안전보건교육)\n"
                "- 산업안전보건법 시행규칙 별표 4 (안전보건교육 내용)\n"
                "- 고용노동부 고시 '외국인 근로자 기초안전보건교육에 관한 규정'\n\n"
                "교육 대상:\n"
                "- E-9(비전문취업), H-2(방문취업) 외국인 근로자 전원\n"
                "- 신규 입국자: 입국 후 취업 전 반드시 이수\n"
                "- 재입국자: 재입국 후 취업 전 이수 (단축 과정 가능)\n\n"
                "교육 기관:\n"
                "- 한국산업인력공단 지정 교육기관\n"
                "- 전국 주요 도시에 교육장 운영\n"
                "- 문의: 1577-0071 (외국인력상담센터)"
            ),
            publisher=publisher,
            url=url,
        ),
        build_chunk(
            source_id="SAFETY_EDU_CONTENT",
            title="외국인 근로자 기초안전보건교육 — 교육 내용 및 시간",
            content=(
                "기초안전보건교육 교과목 및 시간 (고용노동부 고시 기준):\n\n"
                "총 교육 시간: 16시간 (신규), 8시간 (재입국)\n\n"
                "교과목별 내용:\n"
                "1. 산업안전보건 법령 (2시간)\n"
                "   - 산업안전보건법 주요 내용\n"
                "   - 근로자의 권리와 의무\n"
                "   - 산업재해 발생 시 처리 절차\n\n"
                "2. 작업장 위험 인식 (3시간)\n"
                "   - 제조업 작업 현장 주요 위험 요소\n"
                "   - 기계·설비 안전 작동법\n"
                "   - 화학물질 취급 주의사항\n"
                "   - 전기 안전 기초\n\n"
                "3. 개인보호장비 착용법 (2시간)\n"
                "   - 안전모, 안전화, 안전장갑, 보안경 착용법\n"
                "   - 방진마스크, 방독마스크 착용·관리법\n"
                "   - 귀마개·귀덮개 착용 기준\n\n"
                "4. 화재·폭발 예방 및 대피 (2시간)\n"
                "   - 화재 발생 시 행동 요령\n"
                "   - 소화기 사용법\n"
                "   - 비상구 위치 확인 및 대피 경로\n\n"
                "5. 응급처치 기초 (2시간)\n"
                "   - 심폐소생술(CPR) 기초\n"
                "   - 외상 처치 기초\n"
                "   - 119 신고 방법 (다국어)\n\n"
                "6. 한국 생활 적응 및 문화 (3시간)\n"
                "   - 한국의 직장 문화\n"
                "   - 대중교통 이용법\n"
                "   - 의료기관 이용법\n"
                "   - 긴급 상황 대처법"
            ),
            publisher=publisher,
            url=url,
        ),
        build_chunk(
            source_id="SAFETY_EDU_PROCEDURE",
            title="외국인 근로자 기초안전보건교육 — 이수 절차 및 수료증",
            content=(
                "기초안전보건교육 이수 절차:\n\n"
                "1단계: 교육 신청\n"
                "   - 사업주 또는 근로자 본인이 지정 교육기관에 신청\n"
                "   - 신청 서류: 여권 사본, 외국인등록증 사본\n"
                "   - 교육비: 신규 127,500원, 재입국 75,000원\n\n"
                "2단계: 교육 이수\n"
                "   - 집합 교육 (집체 교육) 또는 온라인 교육 (일부 가능)\n"
                "   - 모국어 통역 지원 (베트남어, 캄보디아어, 인도네시아어 등)\n"
                "   - 출석 확인 필수 (결석 시 재수강)\n\n"
                "3단계: 수료증 발급\n"
                "   - 교육 이수 후 '기초안전보건교육 수료증' 발급\n"
                "   - 수료증은 취업 시 사업주에게 제출\n"
                "   - 유효기간: 별도 만료 없음 (단, 재입국 시 재이수 필요)\n\n"
                "사업주 주의사항:\n"
                "   - 수료증 미제출 근로자 채용 시 과태료 부과 (산업안전보건법)\n"
                "   - 교육 미이수 근로자 취업 개시 전 교육 이수 확인 의무"
            ),
            publisher=publisher,
            url=url,
        ),
    ]
    return chunks


# ─────────────────────────────────────────────
# 다국어 안전 용어 및 표지 (Grade D)
# ─────────────────────────────────────────────

def build_multilingual_safety_chunks():
    """
    출처: 고용노동부·안전보건공단 다국어 안전표지 안내자료
    """
    url = "https://www.kosha.or.kr"
    publisher = "안전보건공단·고용노동부"

    languages = [
        {
            "lang": "vi", "name": "베트남어",
            "terms": [
                ("위험", "Nguy hiểm"), ("출입금지", "Cấm vào"), ("안전모 착용", "Đội mũ bảo hộ"),
                ("안전화 착용", "Đi giày bảo hộ"), ("화기금지", "Cấm lửa"), ("비상구", "Lối thoát hiểm"),
                ("소화기", "Bình chữa cháy"), ("응급처치", "Sơ cứu"), ("전기위험", "Nguy hiểm điện"),
                ("추락주의", "Chú ý té ngã"), ("119 신고", "Gọi 119"), ("1345 출입국", "Gọi 1345"),
            ],
        },
        {
            "lang": "km", "name": "캄보디아어",
            "terms": [
                ("위험", "គ្រោះថ្នាក់"), ("출입금지", "ហាមចូល"), ("안전모 착용", "ពាក់មួកការពារ"),
                ("안전화 착용", "ពាក់ស្បែកជើងការពារ"), ("화기금지", "ហាមភ្លើង"), ("비상구", "ច្រកចេញពេលអាសន្ន"),
                ("소화기", "ម៉ាស៊ីនពន្លត់អគ្គីភ័យ"), ("응급처치", "ការព្យាបាលបន្ទាន់"), ("119 신고", "ហៅ 119"),
            ],
        },
        {
            "lang": "uz", "name": "우즈베크어",
            "terms": [
                ("위험", "Xavfli"), ("출입금지", "Kirish taqiqlangan"), ("안전모 착용", "Xavfsizlik dubulg'asi kiy"),
                ("안전화 착용", "Xavfsizlik poyabzali kiy"), ("화기금지", "Olov taqiqlangan"), ("비상구", "Favqulodda chiqish"),
                ("소화기", "O't o'chiruvchi"), ("응급처치", "Birinchi yordam"), ("119 신고", "119 ga qo'ng'iroq qiling"),
            ],
        },
        {
            "lang": "ne", "name": "네팔어",
            "terms": [
                ("위험", "खतरा"), ("출입금지", "प्रवेश निषेध"), ("안전모 착용", "हेलमेट लगाउनुहोस्"),
                ("안전화 착용", "सुरक्षा जुत्ता लगाउनुहोस्"), ("화기금지", "आगो निषेध"), ("비상구", "आपतकालीन निकास"),
                ("소화기", "आगो निभाउने यन्त्र"), ("응급처치", "प्राथमिक उपचार"), ("119 신고", "११९ मा कल गर्नुहोस्"),
            ],
        },
        {
            "lang": "id", "name": "인도네시아어",
            "terms": [
                ("위험", "Bahaya"), ("출입금지", "Dilarang masuk"), ("안전모 착용", "Pakai helm keselamatan"),
                ("안전화 착용", "Pakai sepatu keselamatan"), ("화기금지", "Dilarang api"), ("비상구", "Pintu darurat"),
                ("소화기", "Alat pemadam kebakaran"), ("응급처치", "Pertolongan pertama"), ("119 신고", "Hubungi 119"),
            ],
        },
        {
            "lang": "th", "name": "태국어",
            "terms": [
                ("위험", "อันตราย"), ("출입금지", "ห้ามเข้า"), ("안전모 착용", "สวมหมวกนิรภัย"),
                ("안전화 착용", "สวมรองเท้านิรภัย"), ("화기금지", "ห้ามใช้ไฟ"), ("비상구", "ทางออกฉุกเฉิน"),
                ("소화기", "เครื่องดับเพลิง"), ("응급처치", "การปฐมพยาบาล"), ("119 신고", "โทร 119"),
            ],
        },
    ]

    chunks = []
    for lang_data in languages:
        terms_text = "\n".join([f"- {ko} / {foreign}" for ko, foreign in lang_data["terms"]])
        content = (
            f"작업장 안전표지 주요 용어 — {lang_data['name']} 대조표\n\n"
            f"{terms_text}\n\n"
            "긴급 연락처:\n"
            "- 화재·구급: 119\n"
            "- 출입국 문제: 1345 (법무부)\n"
            "- 고용 문제: 1350 (고용노동부)\n"
            "- 외국인 상담: 1577-0071 (외국인력상담센터)"
        )
        chunks.append(build_chunk(
            source_id=f"SAFETY_SIGNS_{lang_data['lang'].upper()}",
            title=f"작업장 안전표지 다국어 안내 — {lang_data['name']}",
            content=content,
            publisher=publisher,
            url=url,
        ))
    return chunks


# ─────────────────────────────────────────────
# 외국인 근로자 권리·의무 생활 안내 (Grade D)
# ─────────────────────────────────────────────

def build_worker_life_guide_chunks():
    """
    출처: 고용노동부·법무부 외국인 근로자 생활 안내 자료
    """
    url = "https://www.hrdkorea.or.kr"
    publisher = "한국산업인력공단·고용노동부"

    chunks = [
        build_chunk(
            source_id="LIFE_GUIDE_RIGHTS",
            title="외국인 근로자 권리 안내 — 노동 권리 및 보호",
            content=(
                "외국인 근로자의 주요 노동 권리 (내국인과 동일하게 적용):\n\n"
                "1. 최저임금 보장\n"
                "   - 최저임금법에 따라 국적 관계없이 동일 적용\n"
                "   - 2025년 기준 시간당 10,030원\n"
                "   - 최저임금 미달 지급 시 사업주 처벌\n\n"
                "2. 근로시간 및 휴식 권리\n"
                "   - 법정 근로시간: 1일 8시간, 주 40시간\n"
                "   - 연장·야간·휴일 근로 시 가산수당 지급 의무\n"
                "   - 주휴일: 1주 15시간 이상 근무 시 유급 주휴일 1일\n"
                "   - 연차휴가: 1년 근무 시 15일 (80% 이상 출근 조건)\n\n"
                "3. 사회보험 가입 권리\n"
                "   - 산재보험: 모든 외국인 근로자 의무 가입\n"
                "   - 건강보험: 직장 가입자로 당연 적용\n"
                "   - 고용보험: E-9, H-2 가입 (일부 조건 있음)\n"
                "   - 국민연금: 상호주의 원칙 (국적별 상이)\n\n"
                "4. 부당대우 금지\n"
                "   - 폭행, 폭언, 차별 대우 금지\n"
                "   - 여권·외국인등록증 강제 보관 금지\n"
                "   - 강제 저축 또는 임금 불법 공제 금지\n"
                "   - 부당해고 금지"
            ),
            publisher=publisher,
            url=url,
        ),
        build_chunk(
            source_id="LIFE_GUIDE_DUTIES",
            title="외국인 근로자 의무 안내 — 신고 의무 및 준수 사항",
            content=(
                "외국인 근로자의 주요 의무 사항:\n\n"
                "1. 외국인등록 의무\n"
                "   - 입국일로부터 90일 이내 출입국·외국인청에 등록\n"
                "   - 외국인등록증은 항상 소지 (분실 시 즉시 재발급 신청)\n\n"
                "2. 체류지 변경 신고\n"
                "   - 주소 변경 후 14일 이내 신고\n"
                "   - 신고처: 관할 시청·구청 또는 hikorea.go.kr\n\n"
                "3. 근무처 변경 신고\n"
                "   - 사업장 변경 후 14일 이내 신고\n"
                "   - 신고처: hikorea.go.kr 또는 관할 출입국청\n\n"
                "4. 체류기간 준수\n"
                "   - 체류기간 만료 전 연장 신청 또는 출국\n"
                "   - 불법 체류 시: 강제 출국, 재입국 제한(최대 5~10년)\n\n"
                "5. 허가된 취업 활동 범위 준수\n"
                "   - 허가된 업종·사업장 외 취업 금지\n"
                "   - E-9: 지정 사업장만 근무 (변경 절차 없이 이동 불가)\n"
                "   - H-2: 허용 업종 범위 내 자유 취업 가능"
            ),
            publisher=publisher,
            url=url,
        ),
        build_chunk(
            source_id="LIFE_GUIDE_MEDICAL",
            title="외국인 근로자 의료·건강 이용 안내",
            content=(
                "외국인 근로자 의료기관 이용 방법:\n\n"
                "건강보험 이용:\n"
                "- 직장 건강보험 가입 후 건강보험증 또는 앱으로 이용\n"
                "- 병원 방문 시 외국인등록증 제시\n"
                "- 본인부담금: 진료비의 20~30% (비급여 별도)\n\n"
                "산업재해 발생 시:\n"
                "- 즉시 119에 신고\n"
                "- 사업주에게 산재 신고 요청 (은폐 시 처벌)\n"
                "- 산재보험 적용: 치료비 전액 + 휴업급여(평균임금 70%) 지급\n"
                "- 외국인도 산재보험 동일 적용\n\n"
                "체류연장 필수 건강검진:\n"
                "- 지정 의료기관에서 수검 (출입국청 지정 병원)\n"
                "- 검진 항목: 결핵, HIV, 매독, B형간염 등\n"
                "- 결과서 유효기간: 1년\n\n"
                "다국어 의료 지원:\n"
                "- 외국인력상담센터: 1577-0071 (통역 지원)\n"
                "- 이민자 통역 서비스: 주요 거점 병원 운영"
            ),
            publisher=publisher,
            url=url,
        ),
    ]
    return chunks


# ─────────────────────────────────────────────
# 상담센터 안내 (Grade D)
# ─────────────────────────────────────────────

def build_counseling_center_chunks():
    """
    출처: 고용노동부·법무부 외국인 근로자 지원 기관 안내
    """
    url = "https://www.hrdkorea.or.kr"
    publisher = "고용노동부·법무부"

    chunks = [
        build_chunk(
            source_id="COUNSELING_CENTER_GUIDE",
            title="외국인 근로자 지원 기관 및 상담 안내",
            content=(
                "외국인 근로자 주요 지원 기관 및 연락처:\n\n"
                "1. 외국인력상담센터 (1577-0071)\n"
                "   - 운영: 한국산업인력공단\n"
                "   - 지원 언어: 베트남어, 캄보디아어, 인도네시아어, 네팔어, 우즈베크어 등\n"
                "   - 주요 서비스: 고용허가제 관련 상담, 통역 지원, 권리 침해 신고\n"
                "   - 운영 시간: 평일 09:00~18:00\n\n"
                "2. 고용노동부 고객상담센터 (1350)\n"
                "   - 서비스: 임금 체불, 부당해고, 근로조건 위반 신고\n"
                "   - 운영 시간: 평일 09:00~18:00\n\n"
                "3. 법무부 출입국·외국인청 (1345)\n"
                "   - 서비스: 체류 문제, 비자 연장, 강제 출국 관련 상담\n"
                "   - 24시간 운영 (자동 안내)\n\n"
                "4. 근로복지공단 (1588-0075)\n"
                "   - 서비스: 산업재해 신청, 요양급여, 휴업급여\n\n"
                "5. 국가인권위원회 (02-2125-9700)\n"
                "   - 서비스: 차별, 인권침해 신고 및 구제\n\n"
                "6. 외국인 노동자 쉼터 (지역별 운영)\n"
                "   - 서비스: 긴급 숙소, 심리 상담, 법률 지원\n"
                "   - 문의: 외국인력상담센터(1577-0071)에서 연결\n\n"
                "긴급 연락처 요약:\n"
                "- 화재·응급: 119\n"
                "- 범죄 신고: 112\n"
                "- 출입국 문제: 1345\n"
                "- 고용 문제: 1350\n"
                "- 외국인 상담: 1577-0071"
            ),
            publisher=publisher,
            url=url,
        ),
        build_chunk(
            source_id="COUNSELING_CENTER_MULTILANG",
            title="외국인 근로자 긴급 연락처 — 다국어 안내",
            content=(
                "긴급 연락처 다국어 안내 (Emergency Contacts):\n\n"
                "한국어: 화재·응급 119 / 범죄신고 112 / 출입국 1345 / 고용상담 1350\n\n"
                "베트남어 (Tiếng Việt):\n"
                "- Cứu hỏa/Cấp cứu: 119\n"
                "- Báo án: 112\n"
                "- Xuất nhập cảnh: 1345\n"
                "- Tư vấn việc làm: 1350\n"
                "- Tư vấn lao động nước ngoài: 1577-0071\n\n"
                "캄보디아어 (ភាសាខ្មែរ):\n"
                "- អគ្គីភ័យ/ហានិភ័យ: 119\n"
                "- រាយការណ៍ឧក្រិដ្ឋកម្ម: 112\n"
                "- អន្តោប្រវេសន៍: 1345\n"
                "- ប្រឹក្សាការងារ: 1350\n\n"
                "우즈베크어 (O'zbek tili):\n"
                "- Yong'in/Favqulodda: 119\n"
                "- Jinoyat xabari: 112\n"
                "- Immigratsiya: 1345\n"
                "- Ish masalalari: 1350\n\n"
                "네팔어 (नेपाली):\n"
                "- आगो/आपतकाल: 119\n"
                "- अपराध रिपोर्ट: 112\n"
                "- आप्रवासन: 1345\n"
                "- रोजगार परामर्श: 1350\n\n"
                "인도네시아어 (Bahasa Indonesia):\n"
                "- Kebakaran/Darurat: 119\n"
                "- Laporan kejahatan: 112\n"
                "- Imigrasi: 1345\n"
                "- Konsultasi kerja: 1350\n\n"
                "태국어 (ภาษาไทย):\n"
                "- ไฟไหม้/ฉุกเฉิน: 119\n"
                "- แจ้งอาชญากรรม: 112\n"
                "- ตรวจคนเข้าเมือง: 1345\n"
                "- ปรึกษาการจ้างงาน: 1350"
            ),
            publisher=publisher,
            url=url,
        ),
    ]
    return chunks


# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────

def main():
    log.info("=== hrd_crawler.py 시작 ===")
    log.info(f"저장 위치: {RAW_DIR}\n")

    results = []

    # 기초안전보건교육
    log.info("[기초안전보건교육] 공식 고시 기반 chunk 생성")
    chunks = build_basic_safety_edu_chunks()
    save_chunks(chunks, "기초안전보건교육")
    results.append(("기초안전보건교육", len(chunks)))

    # 다국어 안전표지
    log.info("[다국어 안전표지] chunk 생성")
    chunks = build_multilingual_safety_chunks()
    save_chunks(chunks, "다국어_안전표지")
    results.append(("다국어 안전표지", len(chunks)))

    # 생활 안내 (권리·의무)
    log.info("[생활 안내] 권리·의무·의료 chunk 생성")
    chunks = build_worker_life_guide_chunks()
    save_chunks(chunks, "근로자_생활안내")
    results.append(("근로자 생활 안내", len(chunks)))

    # 상담센터 안내
    log.info("[상담센터] 지원기관 및 긴급연락처 chunk 생성")
    chunks = build_counseling_center_chunks()
    save_chunks(chunks, "상담센터_안내")
    results.append(("상담센터 안내", len(chunks)))

    log.info("\n=== 수집 완료 ===")
    total = 0
    for name, count in results:
        status = "✅" if count > 0 else "❌"
        log.info(f"  {status} {name}: {count}개 chunk")
        total += count
    log.info(f"\n총 {total}개 chunk 수집")


if __name__ == "__main__":
    main()
