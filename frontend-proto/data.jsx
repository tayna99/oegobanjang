// 외고반장 프로토타입 데이터
// WORKERS / COMPANIES / CASES 는 백엔드 proto API에서 로딩
// 나머지 목업(CITATIONS, ACTIONS 등)은 로컬 정의

const API_BASE = 'http://127.0.0.1:8000/api/v1';

const TODAY = new Date();
TODAY.setHours(0, 0, 0, 0);

const fmtDate = (s) => {
  if (!s) return '-';
  const d = new Date(s);
  if (isNaN(d)) return '-';
  return `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')}`;
};
const dDay = (iso) => {
  if (!iso) return '-';
  const d = new Date(iso + 'T00:00:00+09:00');
  if (isNaN(d)) return '-';
  const diff = Math.round((d - TODAY) / 86400000);
  if (diff === 0) return 'D-day';
  if (diff < 0) return `D+${Math.abs(diff)}`;
  return `D-${diff}`;
};
const dDayNum = (iso) => {
  if (!iso) return 9999;
  const d = new Date(iso + 'T00:00:00+09:00');
  if (isNaN(d)) return 9999;
  return Math.round((d - TODAY) / 86400000);
};

// ---- 로딩 전 초기값 ----
let COMPANIES = [];
let WORKERS   = [];
let CASES     = [];

// ---- API 로딩 ----
Promise.all([
  fetch(`${API_BASE}/proto/companies`).then(r => r.json()),
  fetch(`${API_BASE}/proto/workers`).then(r => r.json()),
  fetch(`${API_BASE}/proto/cases`).then(r => r.json()),
]).then(([companies, workers, cases]) => {
  COMPANIES = companies;
  WORKERS   = workers;
  CASES     = cases;
  Object.assign(window, { COMPANIES, WORKERS, CASES });
  window.dispatchEvent(new Event('proto-data-ready'));
}).catch(err => {
  console.warn('[proto] API 로딩 실패:', err);
  window.dispatchEvent(new Event('proto-data-ready'));
});

// ---- 추천 액션 (목업) ----
const ACTIONS = {
  act_001: { id: 'act_001', type: 'create_handoff',    label: '행정사 검토용 자료 만들기',          status: 'pending_approval', for: '-' },
  act_002: { id: 'act_002', type: 'request_document',  label: '본인 확인 메시지 초안 보기',          status: 'pending_approval', for: '-' },
  act_003: { id: 'act_003', type: 'request_document',  label: '서류 요청 초안 보기 (다국어 포함)',   status: 'pending_approval', for: '-' },
  act_004: { id: 'act_004', type: 'create_handoff',    label: '체류기간 연장 검토 자료 만들기',      status: 'draft',            for: '-' },
  act_005: { id: 'act_005', type: 'request_document',  label: '누락 서류 요청 초안 보기',            status: 'pending_approval', for: '-' },
  act_006: { id: 'act_006', type: 'review',            label: '담당자 확인 요청',                    status: 'pending_review',   for: '-' },
  act_007: { id: 'act_007', type: 'request_document',  label: '재계약 근로계약서 수령 안내 초안',    status: 'draft',            for: '-' },
  act_008: { id: 'act_008', type: 'create_handoff',    label: '신고서 검토 자료 만들기',             status: 'pending_approval', for: '-' },
};

// ---- 근거 자료 (목업) ----
const CITATIONS = {
  cit_001: { id: 'cit_001', grade: 'A', source: '국가법령정보센터', title: '출입국관리법 제25조 (체류기간 연장허가)', url: '#', snippet: '외국인이 체류기간을 초과하여 계속 체류하고자 할 때에는 체류기간이 끝나기 전에 법무부장관의 허가를 받아야 한다.', updated: '2025.11.02' },
  cit_002: { id: 'cit_002', grade: 'A', source: '출입국관리법',    title: '제94조 벌칙 (체류기간 초과)',           url: '#', snippet: '체류기간을 초과하여 체류한 사람은 처벌 대상이며, 사업주에게도 과태료가 부과될 수 있다.',          updated: '2025.11.02' },
  cit_003: { id: 'cit_003', grade: 'B', source: 'HiKorea',        title: '체류기간 연장허가 신청 안내',           url: '#', snippet: '체류만료일 4개월 전부터 만료일까지 신청 가능. 필수서류는 여권, 외국인등록증, 사진 1매, 사업장 입증서류 등.', updated: '2026.02.10' },
  cit_004: { id: 'cit_004', grade: 'B', source: 'EPS 고용허가제', title: '외국인근로자 고용 시 보유 서류',        url: '#', snippet: '사업주는 근로계약서, 외국인등록증 사본, 여권 사본을 사업장 단위로 보관해야 한다.',                  updated: '2025.09.20' },
  cit_005: { id: 'cit_005', grade: 'A', source: '외국인근로자고용법', title: '제17조 고용변동 등의 신고',         url: '#', snippet: '근로계약 해지·변경 등이 발생한 경우 15일 이내에 신고하여야 한다.',                                   updated: '2025.11.02' },
  cit_006: { id: 'cit_006', grade: 'A', source: '외국인근로자고용법 시행규칙', title: '고용변동 신고서 서식',     url: '#', snippet: '별지 제13호 서식에 따라 사업장 관할 고용센터에 신고하여야 한다.',                                   updated: '2025.11.02' },
};

// ---- Evidence Log (목업) ----
const EVIDENCE_EVENTS = [
  { id: 'evt_001', ts: '2026-05-13T08:00:14+09:00', type: 'risk_flagged',      actor: 'system', case: 'case_001', summary: '비자 만료 CRITICAL 케이스 생성' },
  { id: 'evt_002', ts: '2026-05-13T08:00:14+09:00', type: 'risk_flagged',      actor: 'system', case: 'case_002', summary: '비자 만료 HIGH 케이스 생성' },
  { id: 'evt_003', ts: '2026-05-13T08:00:15+09:00', type: 'citation_resolved', actor: 'system', case: 'case_002', summary: 'cit_001, cit_003 연결' },
  { id: 'evt_004', ts: '2026-05-13T08:01:02+09:00', type: 'briefing_emitted',  actor: 'system', case: null,       summary: '리스크 케이스 생성 완료' },
];

// ---- 다국어 서류 요청 초안 (목업) ----
const DOC_REQUEST_DRAFT = {
  workerId: null,
  workerName: '-',
  reason: '체류기간 연장 신청을 위해 여권 사본과 외국인등록증 사본이 필요합니다.',
  dueDate: '2026-05-31',
  korean: `안녕하세요.\n외고반장입니다.\n체류기간 연장 신청을 준비하고 있습니다.\n아래 서류 사본을 기한 내 보내주세요.\n\n1. 여권 사본 (사진 면)\n2. 외국인등록증 앞·뒷면 사본\n\n수집 목적: 체류기간 연장 서류 작성\n보관 기간: 신청 종료 후 30일\n\n승인 후 사업장 담당자에게 전달됩니다.`,
  vietnamese: `Xin chào,\nĐây là Oegobanjang.\nChúng tôi đang chuẩn bị gia hạn thời gian cư trú.\nVui lòng gửi các giấy tờ sau trước hạn.\n\n1. Bản sao hộ chiếu (trang ảnh)\n2. Bản sao thẻ đăng ký người nước ngoài (mặt trước & mặt sau)\n\nMục đích thu thập: Chuẩn bị hồ sơ gia hạn cư trú.\nThời gian lưu giữ: 30 ngày sau khi nộp hồ sơ.`,
};

// ---- 핸드오프 초안 (목업) ----
const HANDOFF_DRAFT = {
  caseId: 'case_001',
  workerName: '-',
  generatedAt: '2026-05-13 08:15',
  recipient: '고려행정사사무소 (검토 대기)',
  sections: [
    { title: '근로자 기본 정보',    rows: [['성명', '마스킹 처리됨'], ['국적', '-'], ['체류자격', '-'], ['외국인등록번호', '***-*******'], ['사업장', '-']] },
    { title: '체류 / 계약 상태',   rows: [['체류만료일', '-'], ['계약종료일', '-']] },
    { title: '제출 서류',          rows: [['여권사본', '-'], ['외국인등록증', '-'], ['근로계약서', '-']] },
    { title: '근거 자료',          rows: [['출입국관리법 제25조', '체류기간 연장 허가'], ['외국인근로자고용법 제17조', '고용변동 신고 의무']] },
  ],
};

// ---- 채용 요청 (목업) ----
const RECRUITMENT_REQUESTS = [
  {
    id: 'recruit_001', type: 'E-9',
    title: '신규 E-9 채용 요청',
    worksite: '1공장', line: '조립라인', headcount: 3, readiness: 72,
    remainingTasks: ['구인노력 기간 확인', '고용허가 신청서 준비', '송출회사 요청서 확인'],
    doneTaskCount: 5, totalTaskCount: 8, candidatePackage: 'Candidate A',
    status: 'in_progress', deadline: '2026-05-31', note: '행정사 검토 전 확인 필요',
  },
  {
    id: 'recruit_002', type: 'E-9',
    title: 'Candidate A 입국 전 서류 패키지',
    worksite: '1공장', line: '도장라인', headcount: 1, readiness: 45,
    remainingTasks: ['건강진단서 원본 확인', '입국 전 교육 수료증 확인', '숙소 배정 확인'],
    doneTaskCount: 2, totalTaskCount: 5, candidatePackage: 'Candidate A',
    status: 'review_required', deadline: '2026-05-31', note: '행정사 검토 전 확인 필요',
  },
];

// ---- 다국어 컨택 스레드 (목업) ----
const CONTACT_THREADS = [
  {
    id: 'thread_001', workerId: null, workerName: '-', workerNameKo: '-',
    flag: '🇻🇳', nationality: '베트남', channel: 'Zalo', language: 'vi',
    status: 'draft', lastMessage: '서류 사본을 보내주세요.', updatedAt: '2026-05-13',
    draftMessage: {
      ko: '안녕하세요.\n체류기간 연장 신청을 준비하고 있습니다.\n여권 사본과 외국인등록증 사본을 기한 내 보내주세요.',
      vi: 'Xin chào,\nChúng tôi đang chuẩn bị gia hạn thời gian cư trú.\nVui lòng gửi bản sao hộ chiếu và thẻ đăng ký người nước ngoài.',
    },
    scenarios: [
      { type: 'positive', label: '긍정 응답',      desc: '서류 수신 후 행정사 검토 자료에 자동 반영' },
      { type: 'question', label: '추가 정보 요청', desc: '필요 서류와 형식 기준을 다시 안내' },
      { type: 'no_reply', label: '응답 지연',      desc: '2일 뒤 리마인드 메시지 제안' },
    ],
  },
];

// ---- 모바일 승인 태스크 (목업) ----
const MOBILE_APPROVAL_TASKS = [
  {
    id: 'task_4789', type: 'visa_document_request',
    title: '체류기간 연장 서류 요청',
    workerName: '-', flag: '🇻🇳', dDay: 30,
    status: 'approval_required', highlight: '누락 서류 보완',
    body: 'AI가 다국어 요청 메시지를 준비했습니다. 승인 후 근로자에게 발송됩니다.',
    threadId: 'thread_001',
  },
];

// ---- Live Agent 단계 (목업) ----
const LIVE_AGENT_STEPS = [
  { step: 1, label: '근로자 프로필 확인',   detail: '국적 · 비자 · 앱', status: 'done' },
  { step: 2, label: '이전 대화 기록 확인', detail: '서류 요청 이력 확인',          status: 'in_progress' },
  { step: 3, label: '메시지 초안 생성',    detail: '원문 + 번역',                  status: 'waiting' },
  { step: 4, label: '발송 전 승인 대기',   detail: '담당자 승인 후 발송',           status: 'waiting' },
];

// ---- Evidence Grade 팔레트 ----
const EVIDENCE_GRADE_PALETTE = {
  A: { bg: '#D1FAE5', fg: '#065F46', label: '공식 법령', border: '#6EE7B7' },
  B: { bg: '#DBEAFE', fg: '#1E40AF', label: '공공기관', border: '#93C5FD' },
  C: { bg: '#FEF9C3', fg: '#713F12', label: '참고 자료', border: '#FDE047' },
  D: { bg: '#FFEDD5', fg: '#7C2D12', label: '참고용',   border: '#FED7AA' },
  E: { bg: '#F3E8FF', fg: '#6B21A8', label: '보조 자료', border: '#D8B4FE' },
  F: { bg: '#FEE2E2', fg: '#7F1D1D', label: '데모용',   border: '#FCA5A5' },
};

// ---- 승인 큐 (목업) ----
const APPROVAL_QUEUE = [
  {
    id: 'appr_001', actionId: 'act_003', type: 'document_request',
    title: '서류 요청 메시지 발송 승인', worker: '-', flag: '🇻🇳', severity: 'HIGH',
    summary: '체류기간 연장을 위해 필요 서류를 요청하는 다국어 메시지 초안입니다.',
    channel: 'Zalo', citationIds: ['cit_001', 'cit_003'],
    status: 'pending', requestedAt: '2026-05-13T08:14:33+09:00', requestedBy: 'AI 반장',
    note: '승인 시 내부 패키지만 생성됩니다. 외부 발송은 별도 확인 필요.',
  },
  {
    id: 'appr_002', actionId: 'act_001', type: 'handoff_package',
    title: '행정사 검토 자료 생성 승인', worker: '-', flag: '🌏', severity: 'CRITICAL',
    summary: '체류만료 초과 건에 대해 행정사에 전달할 검토 패키지 생성 요청입니다.',
    channel: '내부', citationIds: ['cit_001', 'cit_002', 'cit_005'],
    status: 'pending', requestedAt: '2026-05-13T08:15:48+09:00', requestedBy: 'AI 반장',
    note: '승인 시 내부 패키지만 생성됩니다. 외부 발송은 별도 확인 필요.',
  },
];

// ---- Runtime Metrics (목업) ----
const RUNTIME_METRICS = {
  model: { avgLatencyMs: 1840, p95LatencyMs: 3210, totalTokensToday: 148200, estimatedCostKrw: 4200, callsToday: 37 },
  tools: [
    { name: 'rag_retrieve',       calls: 62, avgLatencyMs: 310 },
    { name: 'policy_lookup',      calls: 28, avgLatencyMs: 140 },
    { name: 'doc_draft_generate', calls: 14, avgLatencyMs: 920 },
    { name: 'approval_request',   calls: 11, avgLatencyMs: 55  },
  ],
  retrieval: {
    hitRate: 0.91,
    collections: [
      { name: 'immigration_law', hits: 34 },
      { name: 'eps_guidelines',  hits: 18 },
      { name: 'hikorea_docs',    hits: 9  },
      { name: 'case_history',    hits: 1  },
    ],
  },
  approval: { pending: 3, approved: 4, rejected: 0, revised: 1 },
  safety: { forbiddenBlocks: 2, revisionRate: 0.08 },
  pilot: { exportCount: 3, revisionRate: 0.08, avgApprovalTimeSec: 142 },
};

// ---- Sub-Agent Trace (목업) ----
const AGENT_TRACE = {
  requestId: 'req_20260513_0814',
  input: '체류기간 연장 서류 요청 초안 작성',
  startedAt: '2026-05-13T08:14:33+09:00',
  completedAt: '2026-05-13T08:14:37+09:00',
  totalMs: 3840,
  steps: [
    { id: 'step_01', type: 'intent_router',  label: 'Intent Router',          status: 'done', latencyMs: 310, rationale: 'intent=document_request, urgency=HIGH', evidenceGrade: null },
    { id: 'step_02', type: 'mission_agent',  label: 'Visa Mission Agent',     status: 'done', latencyMs: 820, rationale: '체류만료 확인, 연장 신청 절차 분류', evidenceGrade: 'A', citationId: 'cit_001' },
    { id: 'step_03', type: 'sub_agent',      label: 'RAG Retrieval Sub-Agent', status: 'done', latencyMs: 290, rationale: 'immigration_law 컬렉션 2건 검색', evidenceGrade: 'A', citationId: 'cit_003' },
    { id: 'step_04', type: 'sub_agent',      label: 'Doc Draft Sub-Agent',    status: 'done', latencyMs: 950, rationale: '한국어 + 다국어 번역 생성', evidenceGrade: 'B', citationId: null },
    { id: 'step_05', type: 'approval_gate',  label: 'Approval Gate',          status: 'done', latencyMs: 55,  rationale: 'approval_request 생성 → pending', evidenceGrade: null },
    { id: 'step_06', type: 'final_response', label: 'Final Response',         status: 'done', latencyMs: 210, rationale: '응답 카드 생성', evidenceGrade: null },
  ],
  evidenceEvents: [
    { type: 'rag_retrieved',      stepId: 'step_03', summary: 'cit_001 · grade A (출입국관리법 제25조)' },
    { type: 'rag_retrieved',      stepId: 'step_03', summary: 'cit_003 · grade B (HiKorea 연장 안내)' },
    { type: 'tool_executed',      stepId: 'step_04', summary: 'doc_draft_generate · 다국어 완료' },
    { type: 'approval_requested', stepId: 'step_05', summary: 'appr_001 생성 · pending' },
  ],
};

Object.assign(window, {
  TODAY, fmtDate, dDay, dDayNum,
  COMPANIES, WORKERS, CASES,
  ACTIONS, CITATIONS, EVIDENCE_EVENTS,
  DOC_REQUEST_DRAFT, HANDOFF_DRAFT,
  RECRUITMENT_REQUESTS, CONTACT_THREADS, MOBILE_APPROVAL_TASKS, LIVE_AGENT_STEPS,
  EVIDENCE_GRADE_PALETTE, APPROVAL_QUEUE, RUNTIME_METRICS, AGENT_TRACE,
});
