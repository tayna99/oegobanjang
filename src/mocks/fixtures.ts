// CASE 레지스트리 — 2.5.4b에서 디자인 세계관(6인 로스터)으로 전면 치환.
// 출처: reference/design-system/외고반장 PC.dc.html §3a 큐(132~191행)·§3b 워크벤치,
// 외고반장 Mobile.dc.html §2a(52~81행). 값 충돌 시 디자인이 정본(블루프린트 §3).
// title은 업무 단위(근로자명 미포함) — 이름·팀은 workerRef가 담당한다.
// 행정사 패키지(2.4)의 대상 케이스는 hiring → batbayar (관제형 §2d).
import type { CaseCard, Citation } from '@/types';
import { libCitation } from './citations';

export type CaseDocStatus =
  | 'missing'
  | 'requested'
  | 'received'
  | 'expiring'
  | 'company_check'
  | 'pending';

export interface CaseDoc {
  name: string;
  status: CaseDocStatus;
  statusLabel: string; // 디자인 원문 라벨 그대로 — 배지에 라벨 텍스트 병기 규칙(GOTCHAS §3)
}

export interface CaseCheckedItem {
  label: string;
  value: string;
}

export interface CaseActivityEntry {
  runRef?: string; // "#4788" — 있는 경우만
  label: string;
  detail: string;
  at: string; // 데모 고정값 상대 시각 표기("오늘 07:58")
  outcome: 'approved' | 'pending' | 'question' | 'replanned';
}

// M2 케이스 시트(1단계 스펙 §M2) 구성 데이터. 케이스 시트 컴포넌트는 하나이고
// 이 데이터로 구동한다(GOTCHAS §4) — 케이스 종류별 시트 컴포넌트 복제 금지.
export interface CaseSheet {
  caseId: string;
  summary: string; // CaseSummaryBlock 1문장
  guardNote?: string; // high risk 케이스 경고문 (batbayar만)
  checkedItems: CaseCheckedItem[]; // AICheckedBlock
  docs?: CaseDoc[]; // MissingDocChecklist
  readinessPercent?: number;
  citations: Citation[]; // 근거 라이브러리 레코드 참조(libCitation) — 0건이면 승인 locked(GOTCHAS §2)
  activity: CaseActivityEntry[]; // AgentActivityBlock.runs
  nextWake?: string; // AgentActivityBlock.nextWake.condition
}

// "실행(주) 12 · mock 발송" — 주간 실행(mock) 집계는 백엔드 접속점 전까지 데모 고정값
// (디자인 §2a 스탯 로우·§3a 타일 5번. 활성 케이스에서 파생 불가한 지난주 이력 값).
export const EXECUTED_WEEKLY_MOCK = 12;

export const CASE_CARDS: CaseCard[] = [
  {
    caseId: 'batbayar',
    caseCode: 'case_001',
    title: '체류기간 만료 경과 · 행정사 검토',
    workerRef: { displayName: 'Batbayar E.', nationality: '몽골', team: '제조2팀', maskLevel: 'masked' },
    severity: 'CRITICAL',
    dDay: -2,
    stayExpiryDate: '2026.07.08',
    assignee: '김담당',
    evidenceCompleteness: 100,
    agentStage: 'awaiting_approval',
    state: 'blocked',
    approvalRequired: true,
    primaryAction: {
      actionId: 'batbayar-handoff',
      label: '행정사 검토 자료 만들기',
      state: 'ready',
      requiresApproval: true,
      kind: 'approve',
    },
    secondaryAction: {
      actionId: 'batbayar-detail',
      label: '상세 보기',
      state: 'ready',
      requiresApproval: false,
      kind: 'detail',
    },
    preparedBy: 'rule',
  },
  {
    caseId: 'nguyen',
    caseCode: 'case_002',
    title: '체류기간 연장 서류 요청',
    workerRef: { displayName: 'Nguyen Van A', nationality: '베트남', team: '제조1팀', maskLevel: 'masked' },
    severity: 'HIGH',
    dDay: 30,
    stayExpiryDate: '2026.08.09',
    missingDocCount: 2,
    assignee: '김담당',
    evidenceCompleteness: 100,
    agentStage: 'awaiting_approval',
    state: 'approval_pending',
    approvalRequired: true,
    primaryAction: {
      actionId: 'nguyen-approve',
      label: '승인하기',
      state: 'ready',
      requiresApproval: true,
      kind: 'approve',
    },
    secondaryAction: {
      actionId: 'nguyen-draft',
      label: '초안 보기',
      state: 'ready',
      requiresApproval: false,
      kind: 'draft',
    },
    preparedBy: 'agent',
    preparedRunRef: '#4788',
  },
  {
    caseId: 'siti',
    caseCode: 'case_003',
    title: '고용변동 신고 기한 임박',
    workerRef: { displayName: 'Siti R.', nationality: '인도네시아', team: '포장팀', maskLevel: 'masked' },
    severity: 'HIGH',
    dDay: 3,
    missingDocCount: 1,
    assignee: '김담당',
    evidenceCompleteness: 100,
    agentStage: 'awaiting_approval',
    state: 'approval_pending',
    approvalRequired: true,
    primaryAction: {
      actionId: 'siti-approve',
      label: '승인하기',
      state: 'ready',
      requiresApproval: true,
      kind: 'approve',
    },
    secondaryAction: {
      actionId: 'siti-detail',
      label: '상세 보기',
      state: 'ready',
      requiresApproval: false,
      kind: 'detail',
    },
    preparedBy: 'rule',
  },
  {
    caseId: 'tranCase',
    caseCode: 'case_004',
    title: '계약-체류 만료일 불일치 검토',
    workerRef: { displayName: 'Tran Thi H.', nationality: '베트남', team: '품질팀', maskLevel: 'masked' },
    severity: 'MEDIUM',
    dDay: 45,
    stayExpiryDate: '2026.09.15',
    assignee: '박주임',
    evidenceCompleteness: 80,
    agentStage: 'drafted',
    state: 'risk_review',
    approvalRequired: false,
    primaryAction: {
      actionId: 'tranCase-confirm',
      label: '케이스 확인 완료',
      state: 'ready',
      requiresApproval: false,
      kind: 'confirm',
    },
    secondaryAction: {
      actionId: 'tranCase-thread',
      label: '응답 보기',
      state: 'ready',
      requiresApproval: false,
      kind: 'thread',
    },
    preparedBy: 'rule',
  },
  {
    caseId: 'rahmat',
    caseCode: 'case_005',
    title: '필수 서류 누락 · 건강보험 자격득실 확인서',
    workerRef: { displayName: 'Rahmat P.', nationality: '인도네시아', team: '제조1팀', maskLevel: 'masked' },
    severity: 'MEDIUM',
    missingDocCount: 1,
    assignee: '박주임',
    evidenceCompleteness: 60,
    agentStage: 'collecting',
    state: 'draft',
    approvalRequired: false,
    primaryAction: {
      actionId: 'rahmat-detail',
      label: '상세 보기',
      state: 'ready',
      requiresApproval: false,
      kind: 'detail',
    },
    secondaryAction: {
      actionId: 'rahmat-confirm',
      label: '케이스 확인 완료',
      state: 'ready',
      requiresApproval: false,
      kind: 'confirm',
    },
    preparedBy: 'agent',
  },
  {
    caseId: 'oyunaa',
    caseCode: 'case_006',
    title: '계약 만료 사전 모니터링',
    workerRef: { displayName: 'Oyunaa T.', nationality: '몽골', team: '포장팀', maskLevel: 'masked' },
    severity: 'LOW',
    dDay: 75,
    evidenceCompleteness: 20,
    agentStage: 'detected',
    state: 'draft',
    approvalRequired: false,
    primaryAction: {
      actionId: 'oyunaa-detail',
      label: '상세 보기',
      state: 'ready',
      requiresApproval: false,
      kind: 'detail',
    },
    secondaryAction: {
      actionId: 'oyunaa-confirm',
      label: '케이스 확인 완료',
      state: 'ready',
      requiresApproval: false,
      kind: 'confirm',
    },
    preparedBy: 'agent',
  },
];

export const CASE_SHEETS: Record<string, CaseSheet> = {
  batbayar: {
    caseId: 'batbayar',
    summary: '체류기간이 2일 경과된 상태입니다. 행정사 검토가 필요합니다.',
    guardNote: '기한 경과 케이스는 앱에서 처리할 수 없습니다 — 행정사 검토로만 진행됩니다 (high risk 강제 전달)',
    checkedItems: [
      { label: '체류만료일', value: '2026.07.08 · D+2' },
      { label: '계약종료일', value: '2026.07.08' },
      { label: '비자', value: 'E-9-1 · 몽골' },
    ],
    docs: [
      { name: '여권 사본', status: 'received', statusLabel: '확보' },
      { name: '외국인등록증', status: 'received', statusLabel: '확보' },
      { name: '표준근로계약서', status: 'received', statusLabel: '확보' },
    ],
    citations: [libCitation('cit_003'), libCitation('cit_007')],
    activity: [
      {
        label: '위험 감지 · CRITICAL',
        detail: '체류만료 경과 자동 탐지 — 행정사 검토 필요 표시',
        at: '7.8 08:00',
        outcome: 'pending',
      },
    ],
    nextWake: '다음: 검토 자료 승인 시 행정사 전달 준비 완료로 전환됩니다',
  },
  nguyen: {
    caseId: 'nguyen',
    summary: '체류만료가 30일 남았고 서류 2건이 누락되어 요청이 필요합니다.',
    checkedItems: [
      { label: '체류만료일', value: '2026.08.09 · D-30' },
      { label: '이전 요청', value: '3일 전 이력 있음' },
      { label: '컨택 채널', value: 'Zalo · 베트남어' },
    ],
    docs: [
      { name: '고용계약서', status: 'received', statusLabel: '05/12 확인' },
      { name: '재직증명서', status: 'received', statusLabel: '05/12 확인' },
      { name: '급여명세서 (최근 3개월)', status: 'received', statusLabel: '06/30 확인' },
      { name: '여권 사본', status: 'missing', statusLabel: '누락' },
      { name: '표준근로계약서 사본', status: 'missing', statusLabel: '누락' },
    ],
    citations: [libCitation('cit_001'), libCitation('cit_009'), libCitation('cit_014')],
    activity: [
      {
        runRef: '#4788',
        label: '서류요청 준비',
        detail: 'D-30 감지로 자동 실행 — 초안 생성 후 승인 대기',
        at: '오늘 07:58',
        outcome: 'pending',
      },
      {
        runRef: '#4712',
        label: '1차 서류 요청',
        detail: '여권 사본 요청 — 승인·발송 완료',
        at: '6.12 10:31',
        outcome: 'approved',
      },
    ],
    nextWake: '다음: 발송 후 2일간 응답 없으면 리마인드 여부를 판단합니다',
  },
  siti: {
    caseId: 'siti',
    summary: '고용변동 신고 기한이 3일 남았습니다. 신고서 초안 확인이 필요합니다.',
    checkedItems: [
      { label: '신고 기한', value: '2026.07.13 · D-3' },
      { label: '변동 사유', value: '근무처 내 공정 변경' },
      { label: '누락 서류', value: '고용변동 신고서 초안 확인' },
    ],
    docs: [
      { name: '고용변동 신고서 초안', status: 'pending', statusLabel: '확인 필요' },
      { name: '표준근로계약서', status: 'received', statusLabel: '확보' },
    ],
    citations: [libCitation('cit_002'), libCitation('cit_004')],
    activity: [
      {
        runRef: '#4790',
        label: '신고서 초안 준비',
        detail: '기한 D-3 감지로 자동 실행 — 확인 요청 생성',
        at: '오늘 08:00',
        outcome: 'pending',
      },
    ],
    nextWake: '다음: 승인 시 신고 접수 준비 상태로 전환됩니다',
  },
  tranCase: {
    caseId: 'tranCase',
    summary: '계약종료일이 체류만료일보다 빠릅니다. 재계약 여부 확인이 필요합니다.',
    checkedItems: [
      { label: '계약종료일', value: '2026.08.18 · D-45' },
      { label: '체류만료일', value: '2026.09.15' },
      { label: '탐지 규칙', value: 'contract_visa_conflict' },
    ],
    // 확인 전 상태 — 해석 카드(src/mocks/threads.ts TRAN_INTERPRETATION.updates)의
    // "누락 → 회사 확인 필요" / "누락 → 제출 예정 · 내일" 전이가 성립하려면 확인 전 값은
    // 반드시 '누락'이어야 한다. 담당자가 응답 해석을 확인(threadStore.confirmInterpretation)한
    // 뒤 caseStore.docUpdates에 쌓인 값이 CaseSheetPage에서 statusLabel에 오버레이된다
    // (status 열거값 자체는 이 화면에서 쓰이지 않으므로 바꾸지 않는다).
    docs: [
      { name: '표준근로계약서', status: 'missing', statusLabel: '누락' },
      { name: '여권 사본', status: 'missing', statusLabel: '누락' },
    ],
    citations: [libCitation('cit_004')],
    activity: [
      {
        label: '응답 도착 · 해석 완료',
        detail: '계약서 회사 보관 · 여권 내일 제출 — 담당자 확인 대기',
        at: '오늘 10:12',
        outcome: 'question',
      },
    ],
    nextWake: '다음: 서류 확보 시 재계약 검토 자료 준비를 제안합니다',
  },
  rahmat: {
    caseId: 'rahmat',
    summary: '건강보험 자격득실 확인서가 누락되어 서류 요건 근거를 수집하고 있습니다.',
    checkedItems: [
      { label: '누락 서류', value: '건강보험 자격득실 확인서' },
      { label: '진행 단계', value: '근거 수집 중' },
    ],
    docs: [
      { name: '건강보험 자격득실 확인서', status: 'missing', statusLabel: '누락' },
      { name: '여권 사본', status: 'received', statusLabel: '확보' },
    ],
    citations: [],
    activity: [
      {
        label: '서류 요건 근거 수집 시작',
        detail: '필수 서류 요건 확인 중 — 근거 연결 전',
        at: '오늘 07:55',
        outcome: 'pending',
      },
    ],
    nextWake: '다음: 근거 연결이 끝나면 요청 초안 준비를 제안합니다',
  },
  oyunaa: {
    caseId: 'oyunaa',
    summary: '계약 만료가 75일 남아 사전 모니터링 중입니다.',
    checkedItems: [
      { label: '계약종료일', value: '2026.09.24 · D-75' },
      { label: '탐지 규칙', value: 'contract_expiry_monitor' },
    ],
    citations: [],
    activity: [
      {
        label: '계약 만료 D-75 감지',
        detail: '사전 모니터링 등록 — 조치 필요 시점 전',
        at: '오늘 07:52',
        outcome: 'pending',
      },
    ],
    nextWake: '다음: D-60 진입 시 재계약 확인 요청을 제안합니다',
  },
};
