import { maskPassport, maskPhone, maskSensitiveText } from "@/lib/masking";

export type DashboardTask = {
  id: string;
  title: string;
  owner: string;
  dueLabel: string;
  risk: "low" | "medium" | "high";
};

export type VisaExpiry = {
  workerId: string;
  workerName: string;
  visaType: "E-9" | "F-2" | "E-7";
  dDay: number;
};

export type DocumentGap = {
  caseId: string;
  workerName: string;
  missing: string[];
};

export type HiringRequest = {
  requestId: string;
  industry: string;
  headcount: number;
  status: string;
};

export type ApprovalItem = {
  approvalId: string;
  label: string;
  blockedAction: string;
};

export type EvidenceEvent = {
  eventId: string;
  eventType: string;
  summary: string;
};

export const dashboardTasks: DashboardTask[] = [
  {
    id: "TASK-001",
    title: "E-9 신규 채용 요청서 검토",
    owner: "인사 담당자",
    dueLabel: "이번 주",
    risk: "medium",
  },
  {
    id: "TASK-002",
    title: "체류기간 만료 전 서류 누락 확인",
    owner: "운영 매니저",
    dueLabel: "D-14",
    risk: "high",
  },
  {
    id: "TASK-003",
    title: "송출회사 확인 질문 승인",
    owner: "관리자",
    dueLabel: "대기 중",
    risk: "medium",
  },
];

export const visaExpiries: VisaExpiry[] = [
  { workerId: "W-104", workerName: "Nguyen A.", visaType: "E-9", dDay: 21 },
  { workerId: "W-118", workerName: "Sita B.", visaType: "E-9", dDay: 34 },
  { workerId: "W-121", workerName: "Batsaikhan C.", visaType: "E-7", dDay: 48 },
];

export const documentGaps: DocumentGap[] = [
  {
    caseId: "DOC-901",
    workerName: "Tran D.",
    missing: ["표준근로계약서 서명본", "건강검진 확인"],
  },
  {
    caseId: "DOC-904",
    workerName: "Mina E.",
    missing: ["증명사진", `여권 ${maskPassport("M12345678")}`],
  },
];

export const hiringRequests: HiringRequest[] = [
  {
    requestId: "HIR-2026-0510-01",
    industry: "자동차부품 제조",
    headcount: 3,
    status: "행정사 검토 필요",
  },
  {
    requestId: "HIR-2026-0510-02",
    industry: "농축산 단순노무",
    headcount: 2,
    status: "송출회사 확인 질문 초안",
  },
];

export const approvalItems: ApprovalItem[] = [
  {
    approvalId: "APR-301",
    label: "후보 준비도 확인 질문 전달",
    blockedAction: "auto_send_to_sending_agency",
  },
  {
    approvalId: "APR-302",
    label: "행정사 검토 요청 패키지 준비",
    blockedAction: "auto_send_to_admin_scrivener",
  },
];

export const evidenceEvents: EvidenceEvent[] = [
  {
    eventId: "EVT-701",
    eventType: "rag_retrieved",
    summary: "EPS 사업주 고용절차 source_id=eps_employer_process 조회",
  },
  {
    eventId: "EVT-702",
    eventType: "approval_requested",
    summary: maskSensitiveText("승인 요청 생성, 담당자 연락처 010-1234-5678 원문 미표시"),
  },
  {
    eventId: "EVT-703",
    eventType: "final_response_generated",
    summary: "외부 발송 없이 내부 검토용 초안 생성",
  },
];

export const dashboardMetrics = [
  { label: "이번 달 업무", value: dashboardTasks.length },
  { label: "승인 대기", value: approvalItems.length },
  { label: "서류 누락 케이스", value: documentGaps.length },
] as const;
