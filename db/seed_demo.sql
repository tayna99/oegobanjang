-- ============================================================================
-- 외고반장 데모 시드 — 디자인 세계관(6인 로스터, 기준일 2026-07-10)
-- 원천: src/mocks/{fixtures,citations,evidence,runs,drafts}.ts (2.5.4b 로스터)
--       + docs/DB_SCHEMA.md §9 번호 체계(#4783~#4797 대역)
--
-- 주의
--  * 실서비스 PK는 UUIDv7 — 여기서는 DBeaver 탐색 가독성을 위해 슬러그 id 사용
--  * mock에 없는 값(일부 근로자 체류만료일, 체크리스트 라벨 등)은 [데모 보강] 주석 표기
--  * PII 원문 없음: 전화번호는 가짜 대역, 등록번호는 마스킹 값만
-- ============================================================================

PRAGMA foreign_keys = ON;

-- 4.1 테넌트·계정 ------------------------------------------------------------

INSERT INTO companies (id, name, industry, region, worker_count_band, approval_policy,
                       onboarding_step, onboarding_path, case_seq, evidence_seq)
VALUES ('cmp_greenfood', '그린푸드 제조', '식품 제조업', '경기 화성', '5_20', 'owner_only',
        'done', 'manual', 6, 4797); -- 카운터: case_006 · #4797까지 발급됨(§9)

INSERT INTO users (id, phone, name, terms_agreed_at) VALUES
  ('usr_kim',   '010-0000-0001', '김담당', '2026-06-01T09:00:00Z'),
  ('usr_park',  '010-0000-0002', '박주임', '2026-06-01T09:10:00Z'),
  ('usr_owner', '010-0000-0003', '김대표', '2026-06-01T09:20:00Z');

INSERT INTO memberships (id, company_id, user_id, role, status) VALUES
  ('mem_kim',   'cmp_greenfood', 'usr_kim',   'manager', 'active'),
  ('mem_park',  'cmp_greenfood', 'usr_park',  'manager', 'active'),
  ('mem_owner', 'cmp_greenfood', 'usr_owner', 'owner',   'active');

-- 4.2 근로자 ------------------------------------------------------------------
-- stay_expires_at: batbayar/nguyen/tran은 디자인 값. siti/rahmat/oyunaa는 [데모 보강]
--                  (케이스 기준일이 신고·서류·계약이라 디자인에 체류만료일이 없음)

INSERT INTO workers (id, company_id, display_name, nationality, team, visa_type,
                     stay_expires_at, contract_ends_at, contact_channel, preferred_language,
                     registration_no_masked, source) VALUES
  ('wrk_batbayar', 'cmp_greenfood', 'Batbayar E.',  '몽골',       '제조2팀', 'E-9-1',
   '2026-07-08', '2026-07-08', NULL,   NULL, '******-*******', 'manual'),
  ('wrk_nguyen',   'cmp_greenfood', 'Nguyen Van A', '베트남',     '제조1팀', 'E-9',
   '2026-08-09', NULL,          'zalo', 'vi', '******-*******', 'manual'),
  ('wrk_siti',     'cmp_greenfood', 'Siti R.',      '인도네시아', '포장팀',  'E-9',
   '2027-01-20', NULL,          NULL,   'id', '******-*******', 'manual'),
  ('wrk_tran',     'cmp_greenfood', 'Tran Thi H.',  '베트남',     '품질팀',  'E-9',
   '2026-09-15', '2026-08-18',  'zalo', 'vi', '******-*******', 'manual'),
  ('wrk_rahmat',   'cmp_greenfood', 'Rahmat P.',    '인도네시아', '제조1팀', 'E-9',
   '2027-03-15', NULL,          NULL,   'id', '******-*******', 'manual'),
  ('wrk_oyunaa',   'cmp_greenfood', 'Oyunaa T.',    '몽골',       '포장팀',  'E-9',
   '2027-05-10', '2026-09-24',  NULL,   NULL, '******-*******', 'manual');

-- 4.4 근거 라이브러리 (src/mocks/citations.ts 전량) ---------------------------
-- cit_014/cit_021은 내부 기준(김담당) → company 스코프

INSERT INTO citations (id, company_id, grade, status, title, source, ingest_at, updated_at) VALUES
  ('cit_001', NULL, 'A', 'official',      '출입국관리법 시행규칙 · 연장 제출서류 별표', '국가법령정보센터', '2026-07-01T00:00:00Z', '2026-07-01T00:00:00Z'),
  ('cit_002', NULL, 'A', 'official',      '외국인근로자고용법 시행령 · 고용변동 신고', '국가법령정보센터', '2026-06-28T00:00:00Z', '2026-06-28T00:00:00Z'),
  ('cit_003', NULL, 'A', 'official',      '출입국관리법 제25조 · 체류기간 연장허가', '국가법령정보센터', '2026-07-01T00:00:00Z', '2026-07-01T00:00:00Z'),
  ('cit_004', NULL, 'B', 'official',      '고용24 · 외국인근로자 고용변동 신고 절차', '고용24', '2026-06-20T00:00:00Z', '2026-06-20T00:00:00Z'),
  ('cit_007', NULL, 'A', 'official',      '출입국관리법 시행규칙 · 경과 시 조치', '국가법령정보센터', '2026-07-01T00:00:00Z', '2026-07-01T00:00:00Z'),
  ('cit_009', NULL, 'B', 'review_needed', '하이코리아 · 체류기간 연장 민원 안내', 'HiKorea', '2026-04-02T00:00:00Z', '2026-04-02T00:00:00Z'),
  ('cit_011', NULL, 'B', 'stale',         'KOSHA · 외국인 근로자 다국어 안전 안내', '안전보건공단', '2025-11-14T00:00:00Z', '2025-11-14T00:00:00Z'),
  ('cit_014', 'cmp_greenfood', 'E', 'internal',      '내부 승인 템플릿 · 서류요청 (VN/KR/ID/MN)', '내부 · 김담당', '2026-07-05T00:00:00Z', '2026-07-05T00:00:00Z'),
  ('cit_021', 'cmp_greenfood', 'E', 'review_needed', '내부 체크리스트 · 행정사 전달 패키지 구성', '내부 · 김담당', '2026-07-02T00:00:00Z', '2026-07-02T00:00:00Z');

-- 필수 서류 정의 [데모 보강 — document_requirements 예시]
INSERT INTO document_requirements (id, case_type, visa_type, required_doc, required, citation_id) VALUES
  ('req_001', 'visa_expiry',        'E-9', '여권 사본',                 1, 'cit_001'),
  ('req_002', 'visa_expiry',        'E-9', '표준근로계약서 사본',        1, 'cit_001'),
  ('req_003', 'reporting_deadline', 'E-9', '고용변동 신고서',            1, 'cit_002'),
  ('req_004', 'missing_document',   'E-9', '건강보험 자격득실 확인서',   1, NULL);

-- 서류 상태 (CASE_SHEETS.docs 그대로) -----------------------------------------

INSERT INTO worker_documents (id, company_id, worker_id, doc_type, status) VALUES
  ('doc_bat_passport', 'cmp_greenfood', 'wrk_batbayar', '여권 사본',               'received'),
  ('doc_bat_arc',      'cmp_greenfood', 'wrk_batbayar', '외국인등록증',            'received'),
  ('doc_bat_contract', 'cmp_greenfood', 'wrk_batbayar', '표준근로계약서',          'received'),
  ('doc_ngu_emp',      'cmp_greenfood', 'wrk_nguyen',   '고용계약서',              'received'),
  ('doc_ngu_cert',     'cmp_greenfood', 'wrk_nguyen',   '재직증명서',              'received'),
  ('doc_ngu_pay',      'cmp_greenfood', 'wrk_nguyen',   '급여명세서 (최근 3개월)', 'received'),
  ('doc_ngu_passport', 'cmp_greenfood', 'wrk_nguyen',   '여권 사본',               'missing'),
  ('doc_ngu_contract', 'cmp_greenfood', 'wrk_nguyen',   '표준근로계약서 사본',      'missing'),
  ('doc_sit_report',   'cmp_greenfood', 'wrk_siti',     '고용변동 신고서 초안',     'pending'),
  ('doc_sit_contract', 'cmp_greenfood', 'wrk_siti',     '표준근로계약서',          'received'),
  ('doc_tra_contract', 'cmp_greenfood', 'wrk_tran',     '표준근로계약서',          'company_check'),
  ('doc_tra_passport', 'cmp_greenfood', 'wrk_tran',     '여권 사본',               'requested'),
  ('doc_rah_health',   'cmp_greenfood', 'wrk_rahmat',   '건강보험 자격득실 확인서', 'missing'),
  ('doc_rah_passport', 'cmp_greenfood', 'wrk_rahmat',   '여권 사본',               'received');

-- 4.3 케이스 (CASE_CARDS 6건 — prepared_run_id는 runs 삽입 후 UPDATE) ----------

INSERT INTO cases (id, company_id, case_code, worker_id, case_type, title, summary,
                   severity, state, agent_stage, due_date, assignee_user_id,
                   approval_required, prepared_by, guard_note, checked_items,
                   next_wake_condition) VALUES
  ('cs_batbayar', 'cmp_greenfood', 'case_001', 'wrk_batbayar', 'visa_expiry',
   '체류기간 만료 경과 · 행정사 검토',
   '체류기간이 2일 경과된 상태입니다. 행정사 검토가 필요합니다.',
   'CRITICAL', 'blocked', 'awaiting_approval', '2026-07-08', 'usr_kim', 1, 'rule',
   '기한 경과 케이스는 앱에서 처리할 수 없습니다 — 행정사 검토로만 진행됩니다 (high risk 강제 전달)',
   '[{"label":"체류만료일","value":"2026.07.08 · D+2"},{"label":"계약종료일","value":"2026.07.08"},{"label":"비자","value":"E-9-1 · 몽골"}]',
   '다음: 검토 자료 승인 시 행정사 전달 준비 완료로 전환됩니다'),
  ('cs_nguyen', 'cmp_greenfood', 'case_002', 'wrk_nguyen', 'visa_expiry',
   '체류기간 연장 서류 요청',
   '체류만료가 30일 남았고 서류 2건이 누락되어 요청이 필요합니다.',
   'HIGH', 'approval_pending', 'awaiting_approval', '2026-08-09', 'usr_kim', 1, 'agent',
   NULL,
   '[{"label":"체류만료일","value":"2026.08.09 · D-30"},{"label":"이전 요청","value":"3일 전 이력 있음"},{"label":"컨택 채널","value":"Zalo · 베트남어"}]',
   '다음: 발송 후 2일간 응답 없으면 리마인드 여부를 판단합니다'),
  ('cs_siti', 'cmp_greenfood', 'case_003', 'wrk_siti', 'reporting_deadline',
   '고용변동 신고 기한 임박',
   '고용변동 신고 기한이 3일 남았습니다. 신고서 초안 확인이 필요합니다.',
   'HIGH', 'approval_pending', 'awaiting_approval', '2026-07-13', 'usr_kim', 1, 'rule',
   NULL,
   '[{"label":"신고 기한","value":"2026.07.13 · D-3"},{"label":"변동 사유","value":"근무처 내 공정 변경"},{"label":"누락 서류","value":"고용변동 신고서 초안 확인"}]',
   '다음: 승인 시 신고 접수 준비 상태로 전환됩니다'),
  ('cs_tran', 'cmp_greenfood', 'case_004', 'wrk_tran', 'contract_visa_conflict',
   '계약-체류 만료일 불일치 검토',
   '계약종료일이 체류만료일보다 빠릅니다. 재계약 여부 확인이 필요합니다.',
   'MEDIUM', 'risk_review', 'drafted', '2026-08-18', 'usr_park', 0, 'rule',
   NULL,
   '[{"label":"계약종료일","value":"2026.08.18 · D-45"},{"label":"체류만료일","value":"2026.09.15"},{"label":"탐지 규칙","value":"contract_visa_conflict"}]',
   '다음: 서류 확보 시 재계약 검토 자료 준비를 제안합니다'),
  ('cs_rahmat', 'cmp_greenfood', 'case_005', 'wrk_rahmat', 'missing_document',
   '필수 서류 누락 · 건강보험 자격득실 확인서',
   '건강보험 자격득실 확인서가 누락되어 서류 요건 근거를 수집하고 있습니다.',
   'MEDIUM', 'draft', 'collecting', NULL, 'usr_park', 0, 'agent',
   NULL,
   '[{"label":"누락 서류","value":"건강보험 자격득실 확인서"},{"label":"진행 단계","value":"근거 수집 중"}]',
   '다음: 근거 연결이 끝나면 요청 초안 준비를 제안합니다'),
  ('cs_oyunaa', 'cmp_greenfood', 'case_006', 'wrk_oyunaa', 'other',
   '계약 만료 사전 모니터링',
   '계약 만료가 75일 남아 사전 모니터링 중입니다.',
   'LOW', 'draft', 'detected', '2026-09-24', NULL, 0, 'agent',
   NULL,
   '[{"label":"계약종료일","value":"2026.09.24 · D-75"},{"label":"탐지 규칙","value":"contract_expiry_monitor"}]',
   '다음: D-60 진입 시 재계약 확인 요청을 제안합니다');

-- 4.6 런 (runs.ts + CASE_SHEETS.activity — anchor_event_no는 §9 규칙) ----------

INSERT INTO runs (id, company_id, case_id, started_by, trigger_event, started_by_user_id,
                  agent_name, autonomy, status, goal_text, result_summary, anchor_event_no,
                  started_at, ended_at) VALUES
  ('run_4712', 'cmp_greenfood', 'cs_nguyen', 'event', '서류 누락 감지', NULL,
   'Multilingual Contact Agent', 'medium', 'completed', NULL,
   '여권 사본 요청 — 승인·발송 완료', 4712, '2026-06-12T10:31:00Z', '2026-06-12T10:33:00Z'),
  ('run_4788', 'cmp_greenfood', 'cs_nguyen', 'event', 'D-30 진입', NULL,
   'Multilingual Contact Agent', 'medium', 'completed', NULL,
   '베트남어 원문 + 한국어 번역 초안 생성 · 승인 대기', 4788, '2026-07-09T08:00:00Z', '2026-07-09T08:01:00Z'),
  ('run_4790', 'cmp_greenfood', 'cs_siti', 'event', '신고 기한 D-3 진입', NULL,
   'Workforce Agent', 'medium', 'completed', NULL,
   '고용변동 신고서 초안 생성 · 확인 요청', 4790, '2026-07-09T08:00:00Z', '2026-07-09T08:01:00Z'),
  ('run_4797', 'cmp_greenfood', NULL, 'user', NULL, 'usr_kim',
   'Workforce Agent', 'medium', 'completed', '이번 달 급한 직원만 정리해줘',
   '대상 케이스 3건 · 케이스별 액션 초안 3건', 4797, '2026-07-10T09:12:00Z', '2026-07-10T09:13:00Z');

UPDATE cases SET prepared_run_id = 'run_4788' WHERE id = 'cs_nguyen';

INSERT INTO run_steps (id, company_id, run_id, seq, kind, label, detail, tool_status) VALUES
  ('st_4712_1', 'cmp_greenfood', 'run_4712', 1, 'tool_call', '누락 서류 확인',            '여권 사본 미확보 — 요청 대상 판별', 'done'),
  ('st_4712_2', 'cmp_greenfood', 'run_4712', 2, 'tool_call', '요청 메시지 초안 생성',     '베트남어 + 한국어 · 여권 사본 요청', 'done'),
  ('st_4788_1', 'cmp_greenfood', 'run_4788', 1, 'tool_call', '근로자 프로필 확인 완료',   'Nguyen Van A · 베트남 · E-9 · Zalo', 'done'),
  ('st_4788_2', 'cmp_greenfood', 'run_4788', 2, 'tool_call', '이전 대화 기록 확인 완료',  '3일 전 표준근로계약서 요청 이력 있음', 'done'),
  ('st_4788_3', 'cmp_greenfood', 'run_4788', 3, 'tool_call', '메시지 초안 생성 완료',     '베트남어 원문 + 한국어 번역', 'done'),
  ('st_4790_1', 'cmp_greenfood', 'run_4790', 1, 'tool_call', '신고 기한 확인',            '고용변동 신고 · 7.13 기한 (D-3)', 'done'),
  ('st_4790_2', 'cmp_greenfood', 'run_4790', 2, 'tool_call', '신고서 초안 생성 완료',     '고용변동 신고서 · 근거 A·B 연결', 'done'),
  ('st_4797_1', 'cmp_greenfood', 'run_4797', 1, 'thinking',  '이번 달 마감 케이스 판별',  'D-day 30일 이내 · 승인 대기 상태 기준', NULL),
  ('st_4797_2', 'cmp_greenfood', 'run_4797', 2, 'tool_call', '대상 케이스 3건 확인',      'Nguyen(D-30) · Siti(신고 기한 D-3) · Batbayar(행정사 검토)', 'done'),
  ('st_4797_3', 'cmp_greenfood', 'run_4797', 3, 'tool_call', '케이스별 액션 초안 생성',   '메시지·신고서·검토 자료 3건', 'done');

-- 다음 행동 (CASE_CARDS primary/secondary — slot 유니크) ----------------------

INSERT INTO next_actions (id, company_id, case_id, kind, action_type, label, state,
                          requires_approval, slot) VALUES
  ('act_batbayar_handoff', 'cmp_greenfood', 'cs_batbayar', 'approve', 'create_handoff', '행정사 검토 자료 만들기', 'ready', 1, 'primary'),
  ('act_batbayar_detail',  'cmp_greenfood', 'cs_batbayar', 'detail',  'other',          '상세 보기',             'ready', 0, 'secondary'),
  ('act_nguyen_approve',   'cmp_greenfood', 'cs_nguyen',   'approve', 'send_message',   '승인하기',              'ready', 1, 'primary'),
  ('act_nguyen_draft',     'cmp_greenfood', 'cs_nguyen',   'draft',   'other',          '초안 보기',             'ready', 0, 'secondary'),
  ('act_siti_approve',     'cmp_greenfood', 'cs_siti',     'approve', 'confirm_status', '승인하기',              'ready', 1, 'primary'),
  ('act_siti_detail',      'cmp_greenfood', 'cs_siti',     'detail',  'other',          '상세 보기',             'ready', 0, 'secondary'),
  ('act_tran_confirm',     'cmp_greenfood', 'cs_tran',     'confirm', 'confirm_status', '케이스 확인 완료',       'ready', 0, 'primary'),
  ('act_tran_thread',      'cmp_greenfood', 'cs_tran',     'thread',  'other',          '응답 보기',             'ready', 0, 'secondary'),
  ('act_rahmat_detail',    'cmp_greenfood', 'cs_rahmat',   'detail',  'other',          '상세 보기',             'ready', 0, 'primary'),
  ('act_rahmat_confirm',   'cmp_greenfood', 'cs_rahmat',   'confirm', 'confirm_status', '케이스 확인 완료',       'ready', 0, 'secondary'),
  ('act_oyunaa_detail',    'cmp_greenfood', 'cs_oyunaa',   'detail',  'other',          '상세 보기',             'ready', 0, 'primary'),
  ('act_oyunaa_confirm',   'cmp_greenfood', 'cs_oyunaa',   'confirm', 'confirm_status', '케이스 확인 완료',       'ready', 0, 'secondary');

-- 승인 (pending 2건 = 모바일 §2a "내가 처리할 승인" · package export는 아래에서
-- pending → approved 동기화 뒤에 생성)
-- checklist 4항목 라벨은 [데모 보강] — M2.6 §2c 확정 시 교체

-- pending 승인은 idempotency_key가 아직 없다(NULL) — decide() 호출 시에만 채워진다
-- (§4.3 정정, 2026-07-12). NULL은 UNIQUE 제약과 충돌하지 않으므로 pending 2건 동시 존재 가능.
INSERT INTO approvals (id, company_id, case_id, action_id, status, idempotency_key,
                       requested_by_actor, decided_by_user_id, identity_method,
                       checklist, requested_at, decided_at) VALUES
  ('apv_nguyen', 'cmp_greenfood', 'cs_nguyen', 'act_nguyen_approve', 'pending', NULL,
   'agent', NULL, NULL,
   '[{"key":"target","label":"대상자 확인","checked":false},{"key":"docs","label":"서류·기한 확인","checked":false},{"key":"evidence","label":"근거 확인","checked":false},{"key":"content","label":"발송 내용 확인","checked":false}]',
   '2026-07-09T08:00:00Z', NULL),
  ('apv_siti', 'cmp_greenfood', 'cs_siti', 'act_siti_approve', 'pending', NULL,
   'rule', NULL, NULL,
   '[{"key":"target","label":"대상자 확인","checked":false},{"key":"docs","label":"서류·기한 확인","checked":false},{"key":"evidence","label":"근거 확인","checked":false},{"key":"content","label":"발송 내용 확인","checked":false}]',
   '2026-07-09T08:00:00Z', NULL),
  ('apv_batbayar_export', 'cmp_greenfood', 'cs_batbayar', 'act_batbayar_handoff', 'pending',
   NULL, 'user', NULL, NULL, NULL,
   '2026-07-02T14:00:00Z', NULL);

-- 케이스↔근거 (CASE_SHEETS.citations — rahmat·oyunaa는 0건 → 승인 잠금 시연) ----

INSERT INTO case_citations (company_id, case_id, citation_id, added_by_actor, added_by_run_id) VALUES
  ('cmp_greenfood', 'cs_batbayar', 'cit_003', 'rule',  NULL),
  ('cmp_greenfood', 'cs_batbayar', 'cit_007', 'rule',  NULL),
  ('cmp_greenfood', 'cs_nguyen',   'cit_001', 'agent', 'run_4788'),
  ('cmp_greenfood', 'cs_nguyen',   'cit_009', 'agent', 'run_4788'),
  ('cmp_greenfood', 'cs_nguyen',   'cit_014', 'agent', 'run_4788'),
  ('cmp_greenfood', 'cs_siti',     'cit_002', 'agent', 'run_4790'),
  ('cmp_greenfood', 'cs_siti',     'cit_004', 'agent', 'run_4790'),
  ('cmp_greenfood', 'cs_tran',     'cit_004', 'rule',  NULL);

-- 4.5 판단 기록 (src/mocks/evidence.ts #4783~#4791 + 런 anchor 보강) -----------
-- #4712·#4782·#4794·#4797은 mock에 없는 런타임 이벤트를 [데모 보강]한 것

INSERT INTO evidence_events (id, company_id, event_no, type, at, case_id, action_id,
                             approval_id, run_id, actor_type, actor_user_id, actor_display,
                             summary, input_hash) VALUES
  ('ev_4712', 'cmp_greenfood', 4712, 'plan_created', '2026-06-12T10:31:00Z',
   'cs_nguyen', NULL, NULL, 'run_4712', 'agent', NULL, '시스템',
   '1차 서류 요청 런 시작 · 여권 사본 요청 준비', NULL),
  ('ev_4782', 'cmp_greenfood', 4782, 'approval_decided', '2026-07-02T14:05:00Z',
   'cs_batbayar', 'act_batbayar_handoff', 'apv_batbayar_export', NULL, 'approver', 'usr_kim', '김담당 (본인)',
   'Batbayar E. · 행정사 패키지 전달 준비 승인', NULL),
  ('ev_4783', 'cmp_greenfood', 4783, 'exported', '2026-07-02T14:10:00Z',
   'cs_batbayar', NULL, NULL, NULL, 'user', 'usr_kim', '김담당',
   'Batbayar E. · 행정사 패키지 PDF (export_0031)', 'sha256:aa72…3c19'),
  ('ev_4787', 'cmp_greenfood', 4787, 'risk_flagged', '2026-07-08T08:00:00Z',
   'cs_batbayar', NULL, NULL, NULL, 'system', NULL, '시스템',
   'Batbayar E. · 체류기간 경과 CRITICAL 탐지', 'sha256:1d95…b8f2'),
  ('ev_4788', 'cmp_greenfood', 4788, 'risk_flagged', '2026-07-09T08:00:00Z',
   'cs_nguyen', NULL, NULL, 'run_4788', 'system', NULL, '시스템',
   'Nguyen Van A · 체류만료 D-30 HIGH 상향', 'sha256:77e0…41cc'),
  ('ev_4789', 'cmp_greenfood', 4789, 'approval_requested', '2026-07-09T08:00:00Z',
   'cs_nguyen', 'act_nguyen_approve', 'apv_nguyen', 'run_4788', 'system', NULL, '시스템',
   'Nguyen Van A · 서류요청 발송 승인 요청 생성', 'sha256:c2af…9b30'),
  ('ev_4790', 'cmp_greenfood', 4790, 'approval_requested', '2026-07-09T08:00:00Z',
   'cs_siti', 'act_siti_approve', 'apv_siti', 'run_4790', 'system', NULL, '시스템',
   'Siti R. · 신고서 초안 확인 요청 생성', 'sha256:52d8…a94e'),
  ('ev_4791', 'cmp_greenfood', 4791, 'approval_decided', '2026-07-09T16:02:00Z',
   NULL, NULL, NULL, NULL, 'approver', 'usr_kim', '김담당 (본인)',
   'Pham Duc M. · 서류 리마인드 발송 승인', 'sha256:9f2c…e1a7'),
  ('ev_4794', 'cmp_greenfood', 4794, 'briefing_emitted', '2026-07-10T08:00:00Z',
   NULL, NULL, NULL, NULL, 'system', NULL, '시스템',
   '브리핑 생성 완료 · 케이스 6건', NULL),
  ('ev_4797', 'cmp_greenfood', 4797, 'plan_created', '2026-07-10T09:12:00Z',
   NULL, NULL, NULL, 'run_4797', 'user', 'usr_kim', '김담당',
   '커맨드 런 시작 · 이번 달 급한 직원 정리', NULL);

-- 4.7 초안 (src/mocks/drafts.ts) ----------------------------------------------

INSERT INTO drafts (id, company_id, case_id, created_by_run_id, channel, purpose, status,
                    approval_id, compliance_checks, expected_scenarios) VALUES
   ('drf_nguyen', 'cmp_greenfood', 'cs_nguyen', 'run_4788', 'Zalo', '서류 요청 메시지',
    'draft', NULL,
   '[{"label":"개인정보 사용 목적 포함","passed":true},{"label":"제출 기한 포함","passed":true}]',
   '[{"type":"positive","label":"긍정 응답","description":"서류 수신 후 검토 자료에 반영"},{"type":"question","label":"추가 질문","description":"서류 형식 기준 재안내"},{"type":"delayed","label":"응답 지연","description":"2일 뒤 리마인드 제안"}]'),
  ('drf_tran_reminder', 'cmp_greenfood', 'cs_tran', NULL, 'Zalo', '리마인드 초안',
   'draft', NULL, NULL,
   '[{"type":"positive","label":"긍정 응답","description":"여권 수신 후 상태 갱신"},{"type":"question","label":"일정 변경","description":"제출 예정일 갱신"},{"type":"delayed","label":"응답 지연","description":"추가 리마인드 판단"}]');

INSERT INTO draft_variants (id, company_id, draft_id, lang, text, is_revised) VALUES
  ('dv_nguyen_ko', 'cmp_greenfood', 'drf_nguyen', 'ko',
   '안녕하세요 Nguyen 씨,' || char(10) || '체류기간 연장 준비를 위해 아래 서류가 필요합니다.' || char(10) || char(10) || '· 표준근로계약서 사본' || char(10) || '· 여권 사본' || char(10) || char(10) || '가능하면 2일 이내에 보내주세요.' || char(10) || '제출하신 서류는 고용 및 체류 관련 행정 절차에만 사용됩니다.' || char(10) || char(10) || '감사합니다.', 0),
  ('dv_nguyen_vi', 'cmp_greenfood', 'drf_nguyen', 'vi',
   'Xin chào Nguyen,' || char(10) || 'để chuẩn bị gia hạn thời gian lưu trú, vui lòng gửi các giấy tờ sau.' || char(10) || char(10) || '· Bản sao hợp đồng lao động tiêu chuẩn' || char(10) || '· Bản sao hộ chiếu' || char(10) || char(10) || 'Vui lòng gửi trong vòng 2 ngày nếu có thể.' || char(10) || 'Giấy tờ chỉ được dùng cho thủ tục hành chính về việc làm và lưu trú.' || char(10) || char(10) || 'Cảm ơn bạn.', 0),
  ('dv_nguyen_ko_rev', 'cmp_greenfood', 'drf_nguyen', 'ko',
   '안녕하세요 Nguyen 씨, 잘 지내고 계신가요.' || char(10) || '체류기간 연장을 준비하고 있어 서류 두 가지를 부탁드리려고 합니다.' || char(10) || char(10) || '· 표준근로계약서 사본' || char(10) || '· 여권 사본' || char(10) || char(10) || '바쁘시겠지만 이번 주 안에 보내주시면 큰 도움이 됩니다.' || char(10) || '제출하신 서류는 고용 및 체류 관련 행정 절차에만 사용됩니다.' || char(10) || char(10) || '항상 감사합니다.', 1),
  ('dv_tran_ko', 'cmp_greenfood', 'drf_tran_reminder', 'ko',
   '안녕하세요 Tran 씨,' || char(10) || '어제 말씀하신 여권 사본을 오늘 보내주실 수 있을까요.' || char(10) || '계약 관련 준비에 필요합니다.' || char(10) || char(10) || '감사합니다.', 0),
  ('dv_tran_vi', 'cmp_greenfood', 'drf_tran_reminder', 'vi',
   'Chào anh Tran,' || char(10) || 'anh có thể gửi bản sao hộ chiếu hôm nay như đã nói không ạ.' || char(10) || 'Cần cho việc chuẩn bị hợp đồng.' || char(10) || char(10) || 'Cảm ơn anh.', 0),
  ('dv_tran_ko_rev', 'cmp_greenfood', 'drf_tran_reminder', 'ko',
   '안녕하세요 Tran 씨, 바쁘신데 죄송합니다.' || char(10) || '어제 말씀해주신 여권 사본을 편하실 때 보내주시면 감사하겠습니다.' || char(10) || '계약 관련 준비에 필요해서요.' || char(10) || char(10) || '고맙습니다.', 1);

-- 스레드·응답 해석 (P2 시연 — tranCase "응답 도착 · 해석 완료, 담당자 확인 대기")
-- 서류 상태는 시트 표기(정본)를 따르고, 제안은 그 이력을 기록한 [데모 보강]

UPDATE drafts
SET status = 'pending_approval', approval_id = 'apv_nguyen'
WHERE id = 'drf_nguyen';

INSERT INTO threads (id, company_id, worker_id, channel, last_message_at) VALUES
  ('th_tran', 'cmp_greenfood', 'wrk_tran', 'zalo', '2026-07-10T10:12:00Z');

INSERT INTO thread_messages (id, thread_id, company_id, direction, lang,
                             body_original, body_ko, received_at) VALUES
  ('tm_tran_reply', 'th_tran', 'cmp_greenfood', 'inbound', 'vi',
   'Hợp đồng thì công ty đang giữ, còn hộ chiếu mai tôi gửi ạ.',
   '계약서는 회사에서 보관 중이고, 여권은 내일 보내드릴게요.',
   '2026-07-10T10:12:00Z');

INSERT INTO interpretations (id, company_id, thread_message_id, case_id, summary_ko,
                             confidence, status) VALUES
  ('int_tran', 'cmp_greenfood', 'tm_tran_reply', 'cs_tran',
   '계약서 회사 보관 · 여권 내일 제출 — 담당자 확인 대기', 'high', 'proposed');

INSERT INTO status_update_proposals (id, company_id, interpretation_id, target_type, target_key,
                                     from_value, to_value, status) VALUES
  ('sup_tran_contract', 'cmp_greenfood', 'int_tran', 'worker_document', '표준근로계약서', 'missing', 'company_check', 'proposed'),
  ('sup_tran_passport', 'cmp_greenfood', 'int_tran', 'worker_document', '여권 사본',      'missing', 'requested',     'proposed');

-- 4.8 행정사 패키지 (7.2 export_0031 — evidence #4783과 쌍) --------------------

INSERT INTO handoff_packages (id, company_id, case_id, package_type, masked_payload,
                              included_items, status, approval_id) VALUES
  ('hp_batbayar', 'cmp_greenfood', 'cs_batbayar', 'expert_review',
   '{"case_summary":{"title":"체류기간 만료 경과 · 행정사 검토","risk_level":"CRITICAL"},"worker_summary":{"masked_worker_id":"wrk-****","visa_type":"E-9-1","stay_expires_at":"2026-07-08"},"document_summary":{"submitted_documents":["여권 사본","외국인등록증","표준근로계약서"],"missing_documents":[]},"evidence":{"citation_ids":["cit_003","cit_007"],"not_for_legal_judgment":true}}',
   '[{"item":"서류 3종","included":true},{"item":"쟁점 요약","included":true},{"item":"판단 기록 발췌","included":true}]',
    'pending_approval', 'apv_batbayar_export');

UPDATE approvals
SET status = 'approved',
    idempotency_key = 'idem-batbayar-0001',
    decided_by_user_id = 'usr_owner',
    identity_method = 'pin',
    decided_at = '2026-07-02T14:05:00Z'
WHERE id = 'apv_batbayar_export';

INSERT INTO package_exports (id, package_id, company_id, format, content_hash,
                             exported_by_user_id) VALUES
  ('px_batbayar_0031', 'hp_batbayar', 'cmp_greenfood', 'pdf', 'sha256:aa72…3c19', 'usr_kim');

-- 4.9 브리핑 (2026-07-10 · 정렬 스냅샷 = severity → D-day) ---------------------

INSERT INTO briefings (id, company_id, briefing_date, generated_at, source_snapshot_hash) VALUES
  ('brf_20260710', 'cmp_greenfood', '2026-07-10', '2026-07-10T08:00:00Z', 'sha256:demo-snapshot-0710');

INSERT INTO briefing_items (id, company_id, briefing_id, case_id, rank) VALUES
  ('bi_1', 'cmp_greenfood', 'brf_20260710', 'cs_batbayar', 1),
  ('bi_2', 'cmp_greenfood', 'brf_20260710', 'cs_siti',     2),
  ('bi_3', 'cmp_greenfood', 'brf_20260710', 'cs_nguyen',   3),
  ('bi_4', 'cmp_greenfood', 'brf_20260710', 'cs_tran',     4),
  ('bi_5', 'cmp_greenfood', 'brf_20260710', 'cs_rahmat',   5),
  ('bi_6', 'cmp_greenfood', 'brf_20260710', 'cs_oyunaa',   6);
