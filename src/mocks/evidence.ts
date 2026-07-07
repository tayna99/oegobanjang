// EV 이벤트 이식 — reference/prototype_v3.html의 초기 EV 시드(§499)를
// EvidenceEvent(src/types.ts)로 정규화 (M0.5, docs/SPEC_INDEX.md 이식표).
// v3의 EV는 이후 addEv() 호출로 승인·응답 등에 append되지만, 그 뒤 항목들은
// evidenceStore.append()가 실제 상호작용 시점에 만들어야 할 런타임 이벤트다 —
// 여기서는 "오늘 아침, 앱을 열기 전 이미 기록된" 초기 시드 5건만 이식한다.
import type { EvidenceEvent } from '@/types';

export const EVIDENCE_SEED: EvidenceEvent[] = [
  {
    id: 'nguyen-run-started',
    type: 'plan_created',
    at: '2026-07-04T07:58:00.000Z',
    caseId: 'nguyen',
    evidenceRef: '#4788',
    summary: '프로액티브 런 #4788 실행',
    actor: '시스템 · Visa Document Agent',
  },
  {
    id: 'nguyen-risk-flagged',
    type: 'risk_flagged',
    at: '2026-07-04T07:58:00.000Z',
    caseId: 'nguyen',
    evidenceRef: '#4788',
    summary: '위험 감지 — Nguyen 체류만료 D-30 (HIGH)',
    actor: '시스템 · risk_flagged',
  },
  {
    id: 'nguyen-draft-created',
    type: 'tool_executed',
    at: '2026-07-04T07:59:00.000Z',
    caseId: 'nguyen',
    evidenceRef: '#4788',
    summary: 'VN/KR 서류요청 초안 생성',
    actor: '시스템 · message_drafted · 근거 A',
  },
  {
    id: 'nguyen-approval-requested',
    type: 'approval_requested',
    at: '2026-07-04T07:59:00.000Z',
    caseId: 'nguyen',
    evidenceRef: '#4788',
    summary: '승인 요청 생성 — 발송 차단 상태',
    actor: '시스템 · approval_requested',
  },
  {
    id: 'briefing-emitted',
    type: 'final_response_generated',
    at: '2026-07-04T08:30:00.000Z',
    summary: '오늘 브리핑 발행 (3건)',
    actor: '시스템 · briefing_emitted',
  },
];
