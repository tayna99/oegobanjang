-- ============================================================================
-- 외고반장 참조 시드 (seed_reference) — 모든 환경(프로덕션·데모·CI) 필수
--
-- 이 파일은 "빈 DB(신규 테넌트)에서도 제품이 구조적으로 동작하려면 반드시 있어야 하는
-- 전역 참조 데이터"만 담는다. 회사(company_id)에 매이지 않는 두 테이블뿐이다:
--   1. citations (전역 A/B등급) — 승인 근거 게이트·v_global_usable_citations·
--      document_requirements.citation_id FK의 공급원. 이게 비면 근거 라이브러리가 비고
--      승인 citation-lock이 항상 잠긴다.
--   2. document_requirements (전역 룩업) — context_service._load_document_requirements가
--      전량 읽어 ContextSnapshot에 싣는다. 이게 비면 룰 엔진·미션이 서류 요건 0으로 공전.
--
-- 로드 순서: schema.sql → **seed_reference.sql** → (데모·로컬만) seed_demo.sql
--   citations를 먼저 넣어야 document_requirements.citation_id FK가 풀린다(파일 내 순서도 동일).
--   seed_demo.sql은 여기 없는 것(6인 로스터·E등급 내부 근거·케이스·승인 등)만 넣는다.
--
-- === document_requirements 원천·정본 규칙 (중요) ===
--   * 지식 원천: rag/data-pipeline/seed/document_requirements.csv (22행).
--     그 CSV를 직접 로드하지 않는다 — case_type이 영문(stay_extension 등)이고 doc명이 영문
--     슬러그(employment_contract)라 서비스 DB 계약과 불일치한다. CSV는 rag 코퍼스(E등급 청크)
--     정본으로 계속 존치하고, 여기서는 아래 매핑으로 사람이 검수해 재작성한다.
--   * case_type 매핑: stay_extension→visa_expiry / employment_change→reporting_deadline /
--     new_hiring→hiring (DB cases.case_type enum 부분집합). H-2 비자 요건도 함께 싣는다.
--   * required_doc 정본 = 한국어 라벨(worker_documents.doc_type·프론트·seed_demo가 전부 한국어).
--   * 개정 시: 이 파일과 rag CSV **양쪽**을 함께 갱신한다(둘은 소비자가 다른 별개 정본).
--
-- === citations 제약(db/schema.sql) ===
--   * 전역 근거는 company_id=NULL, grade∈{A,B}, status='official'|'review_needed'|'stale'.
--   * E등급(내부 템플릿)은 전역 금지 — CHECK(company_id IS NOT NULL OR status<>'internal').
--     내부 근거는 회사 자산이라 seed_demo.sql(테넌트 시드)에만 있다.
--   * D/F등급은 넣지 않는다(F는 승인 게이트에서 구조적으로 배제 — GOTCHAS).
-- ============================================================================

-- 4.4 전역 근거 라이브러리 (A/B등급, company_id=NULL) --------------------------
-- cit_001~011은 seed_demo.sql에서 승격(id·제목·등급 보존 — 데모 case_citations FK가 물림).
-- source_url·effective_date는 이번에 채웠다(코퍼스 메타: rag/data-pipeline/raw/laws/*.jsonl).

INSERT INTO citations (id, company_id, grade, status, title, source, source_url, effective_date, ingest_at) VALUES
  -- 출입국관리법 계열 (체류·연장)
  ('cit_001', NULL, 'A', 'official', '출입국관리법 시행규칙 · 연장 제출서류 별표', '국가법령정보센터', 'https://www.law.go.kr/법령/출입국관리법시행규칙', '2024-01-01', '2026-07-01T00:00:00Z'),
  ('cit_003', NULL, 'A', 'official', '출입국관리법 제25조 · 체류기간 연장허가', '국가법령정보센터', 'https://www.law.go.kr/법령/출입국관리법', '2024-01-01', '2026-07-01T00:00:00Z'),
  ('cit_007', NULL, 'A', 'official', '출입국관리법 시행규칙 · 경과 시 조치', '국가법령정보센터', 'https://www.law.go.kr/법령/출입국관리법시행규칙', '2024-01-01', '2026-07-01T00:00:00Z'),
  ('cit_030', NULL, 'A', 'official', '출입국관리법 제21조 · 근무처 변경·추가 허가', '국가법령정보센터', 'https://www.law.go.kr/법령/출입국관리법', '2024-01-01', '2026-07-01T00:00:00Z'),
  ('cit_033', NULL, 'A', 'official', '출입국관리법 시행령 · 체류기간 연장 신청 절차', '국가법령정보센터', 'https://www.law.go.kr/법령/출입국관리법시행령', '2024-01-01', '2026-07-01T00:00:00Z'),
  ('cit_036', NULL, 'A', 'official', '출입국관리법 시행규칙 · 사증발급 제출서류 별표', '국가법령정보센터', 'https://www.law.go.kr/법령/출입국관리법시행규칙', '2024-01-01', '2026-07-01T00:00:00Z'),
  ('cit_039', NULL, 'A', 'official', '출입국관리법 · 방문취업(H-2) 체류자격', '국가법령정보센터', 'https://www.law.go.kr/법령/출입국관리법', '2024-01-01', '2026-07-01T00:00:00Z'),
  -- 외국인근로자고용법 계열 (고용·변동 신고)
  ('cit_002', NULL, 'A', 'official', '외국인근로자고용법 시행령 · 고용변동 신고', '국가법령정보센터', 'https://www.law.go.kr/법령/외국인근로자의고용등에관한법률시행령', '2024-01-01', '2026-06-28T00:00:00Z'),
  ('cit_031', NULL, 'A', 'official', '외국인근로자고용법 제25조 · 사업장 변경', '국가법령정보센터', 'https://www.law.go.kr/법령/외국인근로자의고용등에관한법률', '2024-01-01', '2026-06-28T00:00:00Z'),
  ('cit_032', NULL, 'A', 'official', '외국인근로자고용법 시행규칙 · 고용변동 신고 서식', '국가법령정보센터', 'https://www.law.go.kr/법령/외국인근로자의고용등에관한법률시행규칙', '2024-01-01', '2026-06-28T00:00:00Z'),
  ('cit_037', NULL, 'A', 'official', '외국인근로자고용법 시행령 · 건강진단 및 안전', '국가법령정보센터', 'https://www.law.go.kr/법령/외국인근로자의고용등에관한법률시행령', '2024-01-01', '2026-06-28T00:00:00Z'),
  ('cit_041', NULL, 'A', 'official', '외국인근로자고용법 · 표준근로계약', '국가법령정보센터', 'https://www.law.go.kr/법령/외국인근로자의고용등에관한법률', '2024-01-01', '2026-06-28T00:00:00Z'),
  -- 행정 안내 채널 (B등급 — 절차 안내)
  ('cit_004', NULL, 'B', 'official',      '고용24 · 외국인근로자 고용변동 신고 절차', '고용24', 'https://www.work24.go.kr', '2026-01-01', '2026-06-20T00:00:00Z'),
  ('cit_035', NULL, 'B', 'official',      '고용24 · 외국인 신규 고용 절차 안내', '고용24', 'https://www.work24.go.kr', '2026-01-01', '2026-06-20T00:00:00Z'),
  ('cit_040', NULL, 'B', 'official',      '고용24 · 방문취업(H-2) 취업 절차 안내', '고용24', 'https://www.work24.go.kr', '2026-01-01', '2026-06-20T00:00:00Z'),
  ('cit_042', NULL, 'B', 'official',      '고용노동부 · 표준근로계약서 서식 안내', '고용노동부', 'https://www.moel.go.kr', '2026-01-01', '2026-06-20T00:00:00Z'),
  ('cit_009', NULL, 'B', 'review_needed', '하이코리아 · 체류기간 연장 민원 안내', 'HiKorea', 'https://www.hikorea.go.kr', '2025-09-01', '2026-04-02T00:00:00Z'),
  ('cit_034', NULL, 'B', 'review_needed', '하이코리아 · 외국인 체류 종합 안내', 'HiKorea', 'https://www.hikorea.go.kr', '2025-09-01', '2026-04-02T00:00:00Z'),
  ('cit_038', NULL, 'B', 'official',      '국민건강보험공단 · 외국인 건강보험 가입 안내', '국민건강보험공단', 'https://www.nhis.or.kr', '2026-01-01', '2026-05-10T00:00:00Z'),
  ('cit_011', NULL, 'B', 'stale',         'KOSHA · 외국인 근로자 다국어 안전 안내', '안전보건공단', 'https://www.kosha.or.kr', '2024-06-01', '2025-11-14T00:00:00Z');

-- 필수 서류 정의 (전역 룩업 — company_id 없음) --------------------------------
-- req_001~004는 seed_demo.sql에서 승격(id·라벨·case_type 보존).
-- required=false는 "제출 시 인정되나 필수는 아님"(rag CSV의 required 컬럼 승계).

INSERT INTO document_requirements (id, case_type, visa_type, required_doc, required, citation_id) VALUES
  -- 체류기간 연장 (visa_expiry) · E-9
  ('req_001', 'visa_expiry',        'E-9', '여권 사본',                 true,  'cit_001'),
  ('req_002', 'visa_expiry',        'E-9', '표준근로계약서 사본',        true,  'cit_001'),
  ('req_010', 'visa_expiry',        'E-9', '외국인등록증 사본',          true,  'cit_001'),
  ('req_011', 'visa_expiry',        'E-9', '고용허가서 사본',            true,  'cit_033'),
  ('req_012', 'visa_expiry',        'E-9', '건강검진 결과서',            false, NULL),
  ('req_013', 'visa_expiry',        'E-9', '범죄경력 조회서',            false, NULL),
  -- 고용변동 신고 (reporting_deadline) · E-9
  ('req_003', 'reporting_deadline', 'E-9', '고용변동 신고서',            true,  'cit_002'),
  ('req_020', 'reporting_deadline', 'E-9', '신규 근로계약서',            true,  'cit_032'),
  ('req_021', 'reporting_deadline', 'E-9', '기존 사업장 동의서',         true,  'cit_031'),
  -- 필수 서류 누락 (missing_document) · E-9
  ('req_004', 'missing_document',   'E-9', '건강보험 자격득실 확인서',   true,  NULL),
  -- 신규 고용 (hiring) · E-9
  ('req_030', 'hiring',             'E-9', '여권 원본',                 true,  'cit_036'),
  ('req_031', 'hiring',             'E-9', '건강검진 결과서',            true,  'cit_037'),
  ('req_032', 'hiring',             'E-9', '범죄경력 조회서',            true,  NULL),
  ('req_033', 'hiring',             'E-9', '학력 증명서',                false, NULL),
  -- 체류기간 연장 (visa_expiry) · H-2 (방문취업)
  ('req_040', 'visa_expiry',        'H-2', '표준근로계약서 사본',        true,  'cit_041'),
  ('req_041', 'visa_expiry',        'H-2', '여권 사본',                 true,  'cit_039'),
  ('req_042', 'visa_expiry',        'H-2', '외국인등록증 사본',          true,  'cit_039'),
  ('req_043', 'visa_expiry',        'H-2', '고용허가서 사본',            true,  'cit_033'),
  ('req_044', 'visa_expiry',        'H-2', '건강검진 결과서',            false, NULL),
  -- 신규 고용 (hiring) · H-2
  ('req_050', 'hiring',             'H-2', '여권 원본',                 true,  'cit_039'),
  ('req_051', 'hiring',             'H-2', '건강검진 결과서',            true,  NULL),
  ('req_052', 'hiring',             'H-2', '기술 자격증',                true,  NULL);
