// Sample data for 외고반장 Daily Briefing MVP prototype
// Reference date: 2026-05-08 (Asia/Seoul)
// All risk severities computed off this date per PRD §9.

const TODAY = new Date('2026-05-08T08:00:00+09:00');
const fmtDate = (s) => {
  const d = new Date(s);
  return `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')}`;
};
const dDay = (iso) => {
  const d = new Date(iso + 'T00:00:00+09:00');
  const diff = Math.round((d - TODAY) / 86400000);
  if (diff === 0) return 'D-day';
  if (diff < 0) return `D+${Math.abs(diff)}`;
  return `D-${diff}`;
};
const dDayNum = (iso) => {
  const d = new Date(iso + 'T00:00:00+09:00');
  return Math.round((d - TODAY) / 86400000);
};

// ---- Companies / sites ----
const COMPANIES = [
  { id: 'co_001', name: '한별제조', sub: '경기 화성 · 자동차부품', workers: 24, manager: '김인사 차장' },
  { id: 'co_002', name: '대성정밀', sub: '인천 남동 · 금속가공',   workers: 11, manager: '박민지 대리' },
  { id: 'co_003', name: '신영식품', sub: '충남 천안 · 식품가공',   workers: 18, manager: '이성호 과장' },
];

// ---- Workers (E-9) ----
// Realistic mix across CRITICAL / HIGH / MEDIUM / LOW per PRD §9
const WORKERS = [
  {
    id: 'w_001', companyId: 'co_001',
    name: 'Nguyen V.', nameKo: '응우옌 V.', nationality: '베트남', flag: '🇻🇳',
    line: 'A동 조립라인', arn: '950***-5******',
    visaType: 'E-9-1', visaExpiry: '2026-06-07',  // D-30 → HIGH
    contractEnd: '2026-09-30',
    docs: { 여권사본: 'missing', 외국인등록증: 'missing', 근로계약서: 'ok', 건강진단서: 'ok' },
    notes: '체류기간 연장 신청 준비 필요',
    tenure: '2년 7개월',
    avatar: 'V',
  },
  {
    id: 'w_002', companyId: 'co_001',
    name: 'Bayar M.', nameKo: '바야르 M.', nationality: '몽골', flag: '🇲🇳',
    line: 'B동 도장공정', arn: '880***-5******',
    visaType: 'E-9-1', visaExpiry: '2026-05-05',  // D+3 → CRITICAL (expired)
    contractEnd: '2026-05-05',
    docs: { 여권사본: 'ok', 외국인등록증: 'ok', 근로계약서: 'ok', 건강진단서: 'expired' },
    notes: '체류만료 초과. 즉시 확인 필요',
    tenure: '4년 1개월',
    avatar: 'B',
  },
  {
    id: 'w_003', companyId: 'co_001',
    name: 'Tran T. H.', nameKo: '쩐 T. H.', nationality: '베트남', flag: '🇻🇳',
    line: 'A동 조립라인', arn: '930***-5******',
    visaType: 'E-9-1', visaExpiry: '2026-09-15',
    contractEnd: '2026-06-22',  // D-45 → MEDIUM contract / 충돌
    docs: { 여권사본: 'ok', 외국인등록증: 'ok', 근로계약서: 'ok', 건강진단서: 'ok' },
    notes: '체류만료일과 계약종료일 불일치',
    tenure: '1년 8개월',
    avatar: 'T',
  },
  {
    id: 'w_004', companyId: 'co_001',
    name: 'Mohammad I.', nameKo: '모하맛 I.', nationality: '방글라데시', flag: '🇧🇩',
    line: 'C동 검수라인', arn: '910***-5******',
    visaType: 'E-9-1', visaExpiry: '2026-08-12',
    contractEnd: '2026-08-12',
    docs: { 여권사본: 'ok', 외국인등록증: 'ok', 근로계약서: 'missing', 건강진단서: 'ok' },
    notes: '재계약 근로계약서 미수령',
    tenure: '2년 2개월',
    avatar: 'M',
  },
  {
    id: 'w_005', companyId: 'co_001',
    name: 'Sopheak S.', nameKo: '소페악 S.', nationality: '캄보디아', flag: '🇰🇭',
    line: 'B동 도장공정', arn: '960***-5******',
    visaType: 'E-9-1', visaExpiry: '2026-07-04',  // D-57 → MEDIUM
    contractEnd: '2026-07-04',
    docs: { 여권사본: 'ok', 외국인등록증: 'ok', 근로계약서: 'ok', 건강진단서: 'ok' },
    notes: '정상 진행 중. D-60 임박',
    tenure: '11개월',
    avatar: 'S',
  },
  {
    id: 'w_006', companyId: 'co_001',
    name: 'Abebe K.', nameKo: '아베베 K.', nationality: '에티오피아', flag: '🇪🇹',
    line: 'C동 검수라인', arn: '920***-5******',
    visaType: 'E-9-1', visaExpiry: '2026-08-30',
    contractEnd: '2026-08-30',
    docs: { 여권사본: 'ok', 외국인등록증: 'ok', 근로계약서: 'ok', 건강진단서: 'ok' },
    notes: '정상',
    tenure: '1년 3개월',
    avatar: 'A',
  },
];

// ---- Risk cases — derived from workers + standalone (e.g. reporting deadline) ----
const CASES = [
  {
    id: 'case_001', workerId: 'w_002', riskType: 'visa_expiry',
    severity: 'CRITICAL', label: '체류만료 초과',
    summary: '체류만료일(2026.05.05)이 3일 지났습니다.',
    citationIds: ['cit_001', 'cit_002'],
    actions: ['act_001', 'act_002'],
  },
  {
    id: 'case_002', workerId: 'w_001', riskType: 'visa_expiry',
    severity: 'HIGH', label: '체류만료 임박',
    summary: '체류만료까지 30일 남았습니다. 연장 신청 또는 자진 출국 검토가 필요합니다.',
    citationIds: ['cit_001', 'cit_003'],
    actions: ['act_003', 'act_004'],
  },
  {
    id: 'case_003', workerId: 'w_001', riskType: 'missing_document',
    severity: 'HIGH', label: '필수서류 누락',
    summary: '여권 사본, 외국인등록증 사본 보완이 필요합니다.',
    citationIds: ['cit_004'],
    actions: ['act_005'],
  },
  {
    id: 'case_004', workerId: 'w_003', riskType: 'contract_visa_conflict',
    severity: 'MEDIUM', label: '계약·체류 불일치',
    summary: '계약종료일이 체류만료일보다 85일 빠릅니다. 재계약 또는 변동 신고 검토 필요.',
    citationIds: ['cit_005'],
    actions: ['act_006'],
  },
  {
    id: 'case_005', workerId: 'w_004', riskType: 'missing_document',
    severity: 'MEDIUM', label: '재계약 서류 미수령',
    summary: '재계약 근로계약서 원본이 아직 수령되지 않았습니다.',
    citationIds: ['cit_004'],
    actions: ['act_007'],
  },
  {
    id: 'case_006', workerId: null, riskType: 'reporting_deadline',
    severity: 'HIGH', label: '고용변동 신고기한',
    summary: 'Bayar M. 건의 고용변동 신고기한이 3일 남았습니다.',
    citationIds: ['cit_006'],
    actions: ['act_008'],
  },
  {
    id: 'case_007', workerId: 'w_005', riskType: 'visa_expiry',
    severity: 'MEDIUM', label: '체류만료 D-57',
    summary: '체류만료일(2026.07.04)까지 57일. 사전 준비 권장.',
    citationIds: ['cit_001'],
    actions: [],
  },
];

// ---- Next actions ----
const ACTIONS = {
  act_001: { id: 'act_001', type: 'create_handoff', label: '행정사 검토용 자료 만들기',          status: 'pending_approval', for: 'Bayar M.' },
  act_002: { id: 'act_002', type: 'request_document',label: '본인 확인 메시지 초안 보기',           status: 'pending_approval', for: 'Bayar M.' },
  act_003: { id: 'act_003', type: 'request_document',label: '서류 요청 초안 보기 (베트남어 포함)',  status: 'pending_approval', for: 'Nguyen V.' },
  act_004: { id: 'act_004', type: 'create_handoff', label: '체류기간 연장 검토 자료 만들기',         status: 'draft',            for: 'Nguyen V.' },
  act_005: { id: 'act_005', type: 'request_document',label: '여권/외국인등록증 사본 요청 초안 보기', status: 'pending_approval', for: 'Nguyen V.' },
  act_006: { id: 'act_006', type: 'review',         label: '담당자 확인 요청',                       status: 'pending_review',   for: 'Tran T. H.' },
  act_007: { id: 'act_007', type: 'request_document',label: '재계약 근로계약서 수령 안내 초안',      status: 'draft',            for: 'Mohammad I.' },
  act_008: { id: 'act_008', type: 'create_handoff', label: '신고서 검토 자료 만들기',                status: 'pending_approval', for: 'Bayar M.' },
};

// ---- Citations (RAG sources) ----
const CITATIONS = {
  cit_001: { id: 'cit_001', grade: 'A', source: '국가법령정보센터', title: '출입국관리법 제25조 (체류기간 연장허가)', url: 'law.go.kr/...', snippet: '외국인이 체류기간을 초과하여 계속 체류하고자 할 때에는 체류기간이 끝나기 전에 법무부장관의 허가를 받아야 한다.', updated: '2025.11.02' },
  cit_002: { id: 'cit_002', grade: 'A', source: '출입국관리법',     title: '제94조 벌칙 (체류기간 초과)',                url: 'law.go.kr/...', snippet: '체류기간을 초과하여 체류한 사람은 처벌 대상이며, 사업주에게도 과태료가 부과될 수 있다.',          updated: '2025.11.02' },
  cit_003: { id: 'cit_003', grade: 'B', source: 'HiKorea',         title: '체류기간 연장허가 신청 안내',                  url: 'hikorea.go.kr/...', snippet: '체류만료일 4개월 전부터 만료일까지 신청 가능. 필수서류는 여권, 외국인등록증, 사진 1매, 사업장 입증서류 등.', updated: '2026.02.10' },
  cit_004: { id: 'cit_004', grade: 'B', source: 'EPS 고용허가제',  title: '외국인근로자 고용 시 보유 서류',                url: 'eps.go.kr/...',  snippet: '사업주는 근로계약서, 외국인등록증 사본, 여권 사본을 사업장 단위로 보관해야 한다.',                  updated: '2025.09.20' },
  cit_005: { id: 'cit_005', grade: 'A', source: '외국인근로자고용법', title: '제17조 고용변동 등의 신고',                    url: 'law.go.kr/...',  snippet: '근로계약 해지·변경 등이 발생한 경우 15일 이내에 신고하여야 한다.',                                   updated: '2025.11.02' },
  cit_006: { id: 'cit_006', grade: 'A', source: '외국인근로자고용법 시행규칙', title: '고용변동 신고서 서식',                  url: 'law.go.kr/...',  snippet: '별지 제13호 서식에 따라 사업장 관할 고용센터에 신고하여야 한다.',                                   updated: '2025.11.02' },
};

// ---- Evidence Log events ----
const EVIDENCE_EVENTS = [
  { id: 'evt_001', ts: '2026-05-08T08:00:14+09:00', type: 'risk_flagged',     actor: 'system',  case: 'case_001', summary: 'worker_002 visa expiry CRITICAL (expired D+3)' },
  { id: 'evt_002', ts: '2026-05-08T08:00:14+09:00', type: 'risk_flagged',     actor: 'system',  case: 'case_002', summary: 'worker_001 visa expiry HIGH (D-30)' },
  { id: 'evt_003', ts: '2026-05-08T08:00:14+09:00', type: 'risk_flagged',     actor: 'system',  case: 'case_003', summary: 'worker_001 missing 여권사본, 외국인등록증' },
  { id: 'evt_004', ts: '2026-05-08T08:00:15+09:00', type: 'citation_resolved', actor: 'system', case: 'case_002', summary: 'cit_001, cit_003 attached' },
  { id: 'evt_005', ts: '2026-05-08T08:00:15+09:00', type: 'action_drafted',    actor: 'system', case: 'case_003', summary: 'request_document draft generated (KO + VN)' },
  { id: 'evt_006', ts: '2026-05-08T08:01:02+09:00', type: 'briefing_emitted',  actor: 'system', case: null,       summary: '7 risk items, 5 actions pending approval' },
  { id: 'evt_007', ts: '2026-05-08T08:14:33+09:00', type: 'approval_requested',actor: '김인사 차장', case: 'case_002', summary: 'act_003 routed for approval' },
  { id: 'evt_008', ts: '2026-05-08T08:15:48+09:00', type: 'handoff_drafted',   actor: 'system', case: 'case_001', summary: 'handoff package draft created' },
];

// ---- Multilingual document request draft ----
const DOC_REQUEST_DRAFT = {
  workerId: 'w_001',
  workerName: 'Nguyen V.',
  reason: '체류기간 연장 신청을 위해 여권 사본과 외국인등록증 사본이 필요합니다.',
  dueDate: '2026-05-15',
  korean: `Nguyen V.님 안녕하세요.\n외고반장입니다.\n체류기간 연장 신청을 준비하고 있습니다.\n아래 서류 사본을 5월 15일까지 보내주세요.\n\n1. 여권 사본 (사진 면)\n2. 외국인등록증 앞·뒷면 사본\n\n수집 목적: 체류기간 연장 서류 작성\n보관 기간: 신청 종료 후 30일\n\n승인 후 사업장 담당자에게 전달됩니다.`,
  vietnamese: `Xin chào anh Nguyen V.,\nĐây là Oegobanjang.\nChúng tôi đang chuẩn bị gia hạn thời gian cư trú.\nVui lòng gửi các giấy tờ sau trước ngày 15 tháng 5.\n\n1. Bản sao hộ chiếu (trang ảnh)\n2. Bản sao thẻ đăng ký người nước ngoài (mặt trước & mặt sau)\n\nMục đích thu thập: Chuẩn bị hồ sơ gia hạn cư trú.\nThời gian lưu giữ: 30 ngày sau khi nộp hồ sơ.\n\nSau khi được phê duyệt, dữ liệu sẽ được gửi đến người phụ trách của doanh nghiệp.`,
};

const HANDOFF_DRAFT = {
  caseId: 'case_001',
  workerName: 'Bayar M.',
  generatedAt: '2026-05-08 08:15',
  recipient: '고려행정사사무소 (검토 대기)',
  sections: [
    { title: '근로자 기본 정보',
      rows: [['성명', 'Bayar M. (마스킹: Bayar **)'], ['국적', '몽골'], ['체류자격', 'E-9-1'], ['외국인등록번호', '880***-5******'], ['사업장', '한별제조 / B동 도장공정']] },
    { title: '체류 / 계약 상태',
      rows: [['체류만료일', '2026.05.05 (D+3, 만료 초과)'], ['계약종료일', '2026.05.05'], ['고용변동 신고기한', '2026.05.20 (D-12)']] },
    { title: '제출 서류',
      rows: [['여권 사본', '확보됨'], ['외국인등록증 사본', '확보됨'], ['근로계약서', '확보됨'], ['건강진단서', '⚠ 만료']] },
    { title: '근거 자료',
      rows: [['출입국관리법 제25조', '체류기간 연장 허가'], ['외국인근로자고용법 제17조', '고용변동 신고 의무'], ['EPS 보유서류 안내', '서류 보관 기준']] },
  ],
};

// ---- 채용 준비 요청 ----
const RECRUITMENT_REQUESTS = [
  {
    id: 'recruit_001',
    type: 'E-9',
    title: '신규 베트남 E-9 3명 채용 요청',
    worksite: '화성 1공장',
    line: '조립라인',
    headcount: 3,
    readiness: 72,
    remainingTasks: [
      '구인노력 기간 확인',
      '고용허가 신청서 준비',
      '송출회사 요청서 확인',
    ],
    doneTaskCount: 5,
    totalTaskCount: 8,
    candidatePackage: 'Candidate A',
    status: 'in_progress',
    deadline: '2026-05-20',
    note: '행정사 검토 전 확인 필요',
  },
  {
    id: 'recruit_002',
    type: 'E-9',
    title: 'Candidate A 입국 전 서류 패키지',
    worksite: '화성 1공장',
    line: '도장라인',
    headcount: 1,
    readiness: 45,
    remainingTasks: [
      '건강진단서 원본 확인',
      '입국 전 교육 수료증 확인',
      '숙소 배정 확인',
    ],
    doneTaskCount: 2,
    totalTaskCount: 5,
    candidatePackage: 'Candidate A',
    status: 'review_required',
    deadline: '2026-05-20',
    note: '행정사 검토 전 확인 필요',
  },
];

// ---- 다국어 컨택 스레드 ----
const CONTACT_THREADS = [
  {
    id: 'thread_001',
    workerId: 'w_001',
    workerName: 'Nguyen V.',
    workerNameKo: '응우옌 V.',
    flag: '🇻🇳',
    nationality: '베트남',
    channel: 'Zalo',
    language: 'vi',
    status: 'draft',
    lastMessage: '표준근로계약서 사본과 여권 사본을 보내주세요.',
    updatedAt: '2026-05-11',
    draftMessage: {
      ko: 'Nguyen V.님 안녕하세요.\n외고반장입니다.\n체류기간 연장 신청을 준비하고 있습니다.\n아래 서류 사본을 5월 20일까지 보내주세요.\n\n1. 여권 사본 (사진 면)\n2. 외국인등록증 앞·뒷면 사본\n\n수집 목적: 체류기간 연장 서류 작성\n보관 기간: 신청 종료 후 30일',
      vi: 'Xin chào anh Nguyen V.,\nĐây là Oegobanjang.\nChúng tôi đang chuẩn bị gia hạn thời gian cư trú.\nVui lòng gửi các giấy tờ sau trước ngày 20 tháng 5.\n\n1. Bản sao hộ chiếu (trang ảnh)\n2. Bản sao thẻ đăng ký người nước ngoài (mặt trước & mặt sau)\n\nMục đích thu thập: Chuẩn bị hồ sơ gia hạn cư trú.\nThời gian lưu giữ: 30 ngày sau khi nộp hồ sơ.',
    },
    scenarios: [
      { type: 'positive',  label: '긍정 응답',      desc: '서류 수신 후 행정사 검토 자료에 자동 반영' },
      { type: 'question',  label: '추가 정보 요청', desc: '필요 서류와 형식 기준을 다시 안내' },
      { type: 'no_reply',  label: '응답 지연',      desc: '2일 뒤 리마인드 메시지 제안' },
    ],
  },
  {
    id: 'thread_002',
    workerId: 'w_003',
    workerName: 'Tran T. H.',
    workerNameKo: '쩐 T. H.',
    flag: '🇻🇳',
    nationality: '베트남',
    channel: 'Zalo',
    language: 'vi',
    status: 'replied',
    lastMessage: '계약 종료 관련 확인 요청에 응답이 도착했습니다.',
    updatedAt: '2026-05-11',
    draftMessage: {
      ko: 'Tran T. H.님 안녕하세요.\n계약 종료일(2026.06.22)이 다가오고 있습니다.\n재계약 여부를 확인 부탁드립니다.',
      vi: 'Xin chào Tran T. H.,\nNgày kết thúc hợp đồng (22/06/2026) đang đến gần.\nVui lòng xác nhận về việc gia hạn hợp đồng.',
    },
    scenarios: [
      { type: 'positive',  label: '재계약 의사',    desc: '재계약 서류 준비 절차 안내' },
      { type: 'question',  label: '조건 문의',      desc: '조건 확인 후 담당자에게 전달' },
      { type: 'no_reply',  label: '퇴직 의사',      desc: '계약 종료 처리 절차 시작' },
    ],
  },
  {
    id: 'thread_003',
    workerId: 'w_004',
    workerName: 'Mohammad I.',
    workerNameKo: '모하맛 I.',
    flag: '🇧🇩',
    nationality: '방글라데시',
    channel: 'SMS',
    language: 'bn',
    status: 'pending_approval',
    lastMessage: '재계약 근로계약서 수령 안내 초안이 준비되었습니다.',
    updatedAt: '2026-05-10',
    draftMessage: {
      ko: 'Mohammad I.님 안녕하세요.\n재계약 근로계약서 원본 수령이 확인되지 않았습니다.\n아래 주소로 원본 서류를 제출해 주세요.\n\n제출처: 화성 3공장 인사팀',
      vi: 'Mohammad I. সাহেব, আসসালামুয়ালাইকুম।\nপুনর্চুক্তি শ্রম চুক্তির মূল কপি গ্রহণ নিশ্চিত হয়নি।\nঅনুগ্রহ করে নিচের ঠিকানায় মূল নথি জমা দিন।',
    },
    scenarios: [
      { type: 'positive',  label: '서류 제출',      desc: '제출 확인 후 서류 상태 업데이트' },
      { type: 'question',  label: '제출 방법 문의', desc: '제출 방법 및 양식 안내' },
      { type: 'no_reply',  label: '응답 지연',      desc: '3일 뒤 리마인드 제안' },
    ],
  },
];

// ---- 모바일 승인 태스크 ----
const MOBILE_APPROVAL_TASKS = [
  {
    id: 'task_4789',
    type: 'visa_document_request',
    title: 'Nguyen V. 체류기간 연장 서류 요청',
    workerName: 'Nguyen V.',
    flag: '🇻🇳',
    dDay: 30,
    status: 'approval_required',
    highlight: '누락 서류 2건',
    body: 'AI가 베트남어 요청 메시지를 준비했습니다. 승인 후 근로자에게 발송됩니다.',
    threadId: 'thread_001',
  },
  {
    id: 'task_4790',
    type: 'pre_entry_package',
    title: 'Candidate A 입국 전 서류 패키지',
    workerName: 'Candidate A',
    flag: '🇻🇳',
    dDay: null,
    status: 'review_required',
    highlight: '행정사 검토 전 확인 필요',
    body: '행정사 검토 전 서류 패키지 확인이 필요합니다. 승인 마감 5/20.',
    recruitId: 'recruit_002',
  },
  {
    id: 'task_4791',
    type: 'contract_termination',
    title: 'Tran T. H. 계약 종료 확인',
    workerName: 'Tran T. H.',
    flag: '🇻🇳',
    dDay: 42,
    status: 'replied',
    highlight: '근로자 응답 도착',
    body: '응답이 도착했습니다. 요약 확인 후 다음 절차를 진행하세요.',
    threadId: 'thread_002',
  },
];

// ---- Live Agent 처리 단계 ----
const LIVE_AGENT_STEPS = [
  { step: 1, label: '근로자 프로필 확인',   detail: 'Nguyen Van A · 베트남 · E-9 · Zalo', status: 'done' },
  { step: 2, label: '이전 대화 기록 확인', detail: '3일 전 서류 요청 이력 있음',           status: 'in_progress' },
  { step: 3, label: '메시지 초안 생성',    detail: '베트남어 원문 + 한국어 번역',          status: 'waiting' },
  { step: 4, label: '발송 전 승인 대기',   detail: '대표님 승인 후 발송됩니다',           status: 'waiting' },
];

Object.assign(window, {
  TODAY, fmtDate, dDay, dDayNum,
  COMPANIES, WORKERS, CASES, ACTIONS, CITATIONS, EVIDENCE_EVENTS,
  DOC_REQUEST_DRAFT, HANDOFF_DRAFT,
  RECRUITMENT_REQUESTS, CONTACT_THREADS, MOBILE_APPROVAL_TASKS, LIVE_AGENT_STEPS,
});
