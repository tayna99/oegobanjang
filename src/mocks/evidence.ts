// EV 시드 — 2.5.4b에서 디자인 §3c 감사 로그(외고반장 PC.dc.html 594~599행) 대역으로 치환.
// #4783~#4791 + 브리핑 발행(9단계 briefing_emitted 계약 유지, §3a 활동 스트림 08:00).
// hash는 표시용 접두("sha256:9f2c…e1a7") — 원문 PII는 어디에도 없다(INSERT-only, 해시만).
// 이후 항목들은 evidenceStore.append()가 실제 상호작용 시점에 만드는 런타임 이벤트다.
import type { EvidenceEvent } from '@/types';

export const EVIDENCE_SEED: EvidenceEvent[] = [
  {
    id: 'batbayar-export-0031',
    type: 'exported',
    at: '2026-07-02T14:10:00.000Z',
    caseId: 'batbayar',
    evidenceRef: '#4783',
    summary: 'Batbayar E. · 행정사 패키지 PDF (export_0031)',
    actor: '김담당',
    hash: 'sha256:aa72…3c19',
  },
  {
    id: 'batbayar-risk-critical',
    type: 'risk_flagged',
    at: '2026-07-08T08:00:00.000Z',
    caseId: 'batbayar',
    evidenceRef: '#4787',
    summary: 'Batbayar E. · 체류기간 경과 CRITICAL 탐지',
    actor: 'system',
    hash: 'sha256:1d95…b8f2',
  },
  {
    id: 'nguyen-risk-high',
    type: 'risk_flagged',
    at: '2026-07-09T08:00:00.000Z',
    caseId: 'nguyen',
    evidenceRef: '#4788',
    summary: 'Nguyen Van A · 체류만료 D-30 HIGH 상향',
    actor: 'system',
    hash: 'sha256:77e0…41cc',
  },
  {
    id: 'nguyen-approval-requested',
    type: 'approval_requested',
    at: '2026-07-09T08:00:00.000Z',
    caseId: 'nguyen',
    evidenceRef: '#4789',
    summary: 'Nguyen Van A · 서류요청 발송 승인 요청 생성',
    actor: 'system',
    hash: 'sha256:c2af…9b30',
  },
  {
    id: 'siti-approval-requested',
    type: 'approval_requested',
    at: '2026-07-09T08:00:00.000Z',
    caseId: 'siti',
    evidenceRef: '#4790',
    summary: 'Siti R. · 신고서 초안 확인 요청 생성',
    actor: 'system',
    hash: 'sha256:52d8…a94e',
  },
  {
    // 자동 에스컬레이션(7단계 §3.2) — 케이스 상태는 그대로 approval_pending, evidence만 추가된다
    // (활성 6케이스 로스터·기존 큐 카운트 테스트를 건드리지 않는 저위험 프리시드).
    id: 'siti-approval-escalated',
    type: 'approval_escalated',
    at: '2026-07-09T20:00:00.000Z',
    caseId: 'siti',
    evidenceRef: '#4790',
    summary: 'Siti R. · 신고서 초안 확인 요청 — 48h 미응답으로 재알림 발송(timeout_48h)',
    actor: 'system',
    hash: 'sha256:8b41…c0d5',
  },
  {
    id: 'pham-approval-decided',
    type: 'approval_decided',
    at: '2026-07-09T16:02:00.000Z',
    evidenceRef: '#4791',
    summary: 'Pham Duc M. · 서류 리마인드 발송 승인',
    actor: '김담당 (본인)',
    hash: 'sha256:9f2c…e1a7',
  },
  {
    id: 'briefing-emitted',
    type: 'final_response_generated',
    at: '2026-07-10T08:00:00.000Z',
    summary: '브리핑 생성 완료 · 케이스 6건',
    actor: 'system',
  },
];
