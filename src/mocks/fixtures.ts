// CASE 레지스트리 이식 — reference/prototype_v3.html의 CASE(§541)·caseRows(§972)를
// src/types.ts §0.4 CaseCard로 정규화 (M0.5, docs/SPEC_INDEX.md 이식표).
// PKG(candidate/hiring 행정사 패키지 본문)는 범위 밖 — M2.4에서 이식.
import type { CaseCard, Citation } from '@/types';

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
  statusLabel: string; // v3 원문 라벨 그대로 — 배지에 라벨 텍스트 병기 규칙(GOTCHAS §3)
}

export interface CaseCheckedItem {
  label: string;
  value: string;
}

export interface CaseActivityEntry {
  runRef?: string; // "#4788" — 있는 경우만
  label: string;
  detail: string;
  at: string; // v3 원문 상대 시각 표기("오늘 07:58") — 데모 고정값
  outcome: 'approved' | 'pending' | 'question' | 'replanned';
}

// M2 케이스 시트(1단계 스펙 §M2) 구성 데이터. 케이스 시트 컴포넌트는 하나이고
// 이 데이터로 구동한다(GOTCHAS §4) — 케이스 종류별 시트 컴포넌트 복제 금지.
export interface CaseSheet {
  caseId: string;
  summary: string; // CaseSummaryBlock 1문장
  guardNote?: string; // high risk 케이스 경고문 (bayar만)
  checkedItems: CaseCheckedItem[]; // AICheckedBlock
  docs?: CaseDoc[]; // MissingDocChecklist
  readinessPercent?: number; // hiring 준비도
  citations: Citation[]; // CitationBlock — 0건이면 화면에서 근거 없음 경고 + 승인 locked(GOTCHAS §2)
  activity: CaseActivityEntry[]; // AgentActivityBlock.runs
  nextWake?: string; // AgentActivityBlock.nextWake.condition
}

function citation(grade: Citation['grade'], title: string, raw: string): Citation {
  const [source, updatedAt = ''] = raw.split('·').map((s) => s.trim());
  return { grade, title, source, updatedAt };
}

export const CASE_CARDS: CaseCard[] = [
  {
    caseId: 'nguyen',
    title: 'Nguyen V. 체류기간 연장 서류 요청',
    workerRef: { displayName: 'Nguyen V.', nationality: '베트남', maskLevel: 'masked' },
    severity: 'HIGH',
    dDay: 30,
    missingDocCount: 2,
    state: 'approval_pending',
    approvalRequired: true,
    primaryAction: {
      actionId: 'nguyen-approve',
      label: '승인하기',
      state: 'ready',
      requiresApproval: true,
    },
    secondaryAction: {
      actionId: 'nguyen-draft',
      label: '초안 보기',
      state: 'ready',
      requiresApproval: false,
    },
    preparedBy: 'agent',
    preparedRunRef: '#4788',
  },
  {
    caseId: 'bayar',
    title: 'Bayar M. 체류기간 경과',
    workerRef: { displayName: 'Bayar M.', nationality: '몽골', maskLevel: 'masked' },
    severity: 'CRITICAL',
    dDay: -3,
    state: 'blocked',
    approvalRequired: true,
    primaryAction: {
      actionId: 'bayar-handoff',
      label: '행정사 검토 자료 만들기',
      state: 'ready',
      requiresApproval: true,
    },
    secondaryAction: {
      actionId: 'bayar-detail',
      label: '상세 보기',
      state: 'ready',
      requiresApproval: false,
    },
    preparedBy: 'rule',
  },
  {
    caseId: 'mohammad',
    title: 'Mohammad I. 서류 보완',
    workerRef: { displayName: 'Mohammad I.', nationality: '방글라데시', maskLevel: 'masked' },
    severity: 'MEDIUM',
    dDay: 96,
    state: 'approval_pending',
    approvalRequired: true,
    primaryAction: {
      actionId: 'mohammad-approve',
      label: '승인하기',
      state: 'ready',
      requiresApproval: true,
    },
    secondaryAction: {
      actionId: 'mohammad-draft',
      label: '요청 초안 보기',
      state: 'ready',
      requiresApproval: false,
    },
    preparedBy: 'rule',
  },
  {
    caseId: 'tranCase',
    title: 'Tran T.H. 계약-체류 기간 확인',
    workerRef: { displayName: 'Tran T.H.', nationality: '베트남', maskLevel: 'masked' },
    severity: 'MEDIUM',
    dDay: 45,
    state: 'risk_review',
    approvalRequired: false,
    primaryAction: {
      actionId: 'tranCase-confirm',
      label: '케이스 확인 완료',
      state: 'ready',
      requiresApproval: false,
    },
    secondaryAction: {
      actionId: 'tranCase-thread',
      label: '응답 보기',
      state: 'ready',
      requiresApproval: false,
    },
    preparedBy: 'rule',
  },
  {
    caseId: 'hiring',
    title: '신규 베트남 E-9 3명 채용 준비',
    severity: 'LOW',
    state: 'draft',
    approvalRequired: true,
    primaryAction: {
      actionId: 'hiring-review',
      label: '행정사 검토 요청',
      state: 'ready',
      requiresApproval: true,
    },
    secondaryAction: {
      actionId: 'hiring-pkg',
      label: '요청서 보기',
      state: 'ready',
      requiresApproval: false,
    },
    preparedBy: 'rule',
  },
];

export const CASE_SHEETS: Record<string, CaseSheet> = {
  nguyen: {
    caseId: 'nguyen',
    summary: '체류만료가 30일 남았고 서류 2건이 누락되어 요청이 필요합니다.',
    checkedItems: [
      { label: '체류만료일', value: '2026.08.03 · D-30' },
      { label: '이전 요청', value: '3일 전 이력 있음' },
      { label: '컨택 채널', value: 'Zalo · 베트남어' },
    ],
    docs: [
      { name: '표준근로계약서 사본', status: 'missing', statusLabel: '누락' },
      { name: '여권 사본', status: 'missing', statusLabel: '누락' },
      { name: '외국인등록증', status: 'received', statusLabel: '확보' },
    ],
    citations: [
      citation('A', '출입국관리법 제25조 — 체류기간 연장허가', '국가법령정보센터 · 2025.11'),
      citation('B', '체류기간 연장 신청 구비서류 안내', 'HiKorea · 2026.01'),
    ],
    activity: [
      {
        runRef: '#4788',
        label: '서류요청 준비',
        detail: 'D-30 감지로 자동 실행 — 초안 생성 후 승인 대기',
        at: '오늘 07:58',
        outcome: 'pending',
      },
      {
        runRef: '#4741',
        label: '1차 서류 요청',
        detail: '여권 사본 요청 — 승인·발송 완료',
        at: '7.1 08:30',
        outcome: 'approved',
      },
    ],
    nextWake: '다음: 발송 후 2일간 응답 없으면 리마인드 여부를 판단합니다',
  },
  bayar: {
    caseId: 'bayar',
    summary: '체류기간이 3일 경과된 상태입니다. 행정사 검토가 필요합니다.',
    guardNote: '기한 경과 케이스는 앱에서 처리할 수 없습니다 — 행정사 검토로만 진행됩니다 (high risk 강제 전달)',
    checkedItems: [
      { label: '체류만료일', value: '2026.07.01 · D+3' },
      { label: '계약종료일', value: '2026.07.01' },
      { label: '비자', value: 'E-9-1 · 몽골' },
    ],
    docs: [
      { name: '여권 사본', status: 'received', statusLabel: '확보' },
      { name: '외국인등록증', status: 'received', statusLabel: '확보' },
      { name: '표준근로계약서', status: 'received', statusLabel: '확보' },
    ],
    citations: [
      citation('A', '출입국관리법 제25조 — 체류기간 연장허가', '국가법령정보센터 · 2025.11'),
      citation('A', '출입국관리법 제94조 — 벌칙(체류기간 초과)', '국가법령정보센터 · 2025.11'),
    ],
    activity: [
      {
        label: '위험 감지 · CRITICAL',
        detail: '체류만료 경과 자동 탐지 — 행정사 검토 필요 표시',
        at: '오늘 07:58',
        outcome: 'pending',
      },
    ],
    nextWake: '다음: 검토 자료 승인 시 행정사 전달 준비 완료로 전환됩니다',
  },
  mohammad: {
    caseId: 'mohammad',
    summary: '건강검진 확인서가 만료 예정이라 갱신 요청이 필요합니다.',
    checkedItems: [
      { label: '체류만료일', value: '2026.10.08 · D-96' },
      { label: '대상 서류', value: '건강검진 확인서' },
      { label: '컨택 채널', value: 'SMS · 방글라데시' },
    ],
    docs: [
      { name: '건강검진 확인서', status: 'expiring', statusLabel: '만료 예정' },
      { name: '여권 사본', status: 'received', statusLabel: '확보' },
      { name: '외국인등록증', status: 'received', statusLabel: '확보' },
    ],
    citations: [citation('B', '외국인근로자 건강검진 안내', '고용24 · 2026.02')],
    activity: [],
    nextWake: '다음: 요청 발송 승인 시 제출 기한 D-7 리마인드가 예약됩니다',
  },
  tranCase: {
    caseId: 'tranCase',
    summary: '계약종료일이 체류만료일보다 빠릅니다. 재계약 여부 확인이 필요합니다.',
    checkedItems: [
      { label: '계약종료일', value: '2026.08.18 · D-45' },
      { label: '체류만료일', value: '2026.09.15' },
      { label: '탐지 규칙', value: 'contract_visa_conflict' },
    ],
    docs: [
      { name: '표준근로계약서', status: 'company_check', statusLabel: '회사 확인 필요' },
      { name: '여권 사본', status: 'requested', statusLabel: '제출 예정 · 내일' },
    ],
    citations: [citation('B', '고용변동 신고 안내', '고용24 · 2026.03')],
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
  hiring: {
    caseId: 'hiring',
    summary: '요청서 준비도 5/8 — 남은 확인 항목 3개가 있습니다.',
    readinessPercent: 62,
    checkedItems: [
      { label: '공장 · 라인', value: '화성 1공장 · 조립라인' },
      { label: '인원 · 언어', value: 'E-9 3명 · 베트남어' },
      { label: '마감', value: '2026.07.20' },
    ],
    docs: [
      { name: '내국인 구인노력 기간 확인', status: 'received', statusLabel: '완료' },
      { name: '고용허가 신청서 준비', status: 'received', statusLabel: '완료' },
      { name: '송출회사 요청서 확인', status: 'pending', statusLabel: '대기' },
      { name: '숙소 정보 정리', status: 'pending', statusLabel: '대기' },
      { name: '안전교육 자료 확인', status: 'pending', statusLabel: '대기' },
    ],
    citations: [
      citation('B', '고용허가제 사업주 고용절차', 'EPS · 2026.01'),
      citation('E', '내부 채용 준비 체크리스트', '내부 승인 템플릿'),
    ],
    activity: [],
    nextWake: '다음: 8개 항목 완료 시 행정사 검토 요청을 제안합니다',
  },
};
