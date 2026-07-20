import { describe, expect, it } from 'vitest';
import {
  AUDIT_TYPE_LABEL,
  AUDIT_TYPE_TONE,
  caseTimelineActivity,
  filterAudit,
  mergedAuditLog,
  mergedAuditLogAscending,
} from './audit';
import { EVIDENCE_SEED } from '@/mocks/evidence';
import type { CaseActivityEntry } from '@/mocks/fixtures';
import type { EvidenceEvent, EvidenceType } from '@/types';

const ALL_TYPES: EvidenceType[] = [
  'intent_classified', 'plan_created', 'tool_executed', 'rag_retrieved', 'risk_flagged',
  'approval_requested', 'approval_decided', 'approval_rejected', 'review_started',
  'checklist_completed', 'exported', 'final_response_generated', 'interpretation_confirmed',
  // 7단계 §5 권한 이벤트(운영급 RBAC 확장).
  'role_granted', 'role_changed', 'member_invited', 'member_removed',
  'delegation_granted', 'delegation_revoked', 'approval_escalated',
  'package_link_issued', 'package_link_viewed',
  'dispatch_executed', 'delivery_confirmed', 'package_reply', 'worker_reply_received',
];

describe('audit type maps — 전 EvidenceType 커버(런타임 undefined 방지)', () => {
  it('라벨·톤 맵이 모든 타입을 갖는다', () => {
    for (const type of ALL_TYPES) {
      expect(AUDIT_TYPE_LABEL[type]).toBeTruthy();
      expect(AUDIT_TYPE_TONE[type]).toBeTruthy();
    }
  });
});

describe('mergedAuditLog — 시드+런타임 병합, 최신순', () => {
  it('빈 스토어면 시드만 최신순으로 반환', () => {
    const merged = mergedAuditLog([]);
    expect(merged).toHaveLength(EVIDENCE_SEED.length);
    for (let i = 1; i < merged.length; i += 1) {
      expect(merged[i - 1].at >= merged[i].at).toBe(true);
    }
  });

  it('런타임 이벤트가 같은 id 시드를 대체한다(중복 없음)', () => {
    const runtime: EvidenceEvent = { ...EVIDENCE_SEED[0], summary: '갱신됨' };
    const merged = mergedAuditLog([runtime]);
    expect(merged.filter((e) => e.id === EVIDENCE_SEED[0].id)).toHaveLength(1);
    expect(merged.find((e) => e.id === EVIDENCE_SEED[0].id)?.summary).toBe('갱신됨');
  });
});

describe('mergedAuditLogAscending — CaseHistoryPage용 오름차순, 동시각 tie 순서 보존', () => {
  it('빈 스토어면 시드만 오래된 순으로 반환한다(mergedAuditLog의 정반대 순서)', () => {
    const ascending = mergedAuditLogAscending([]);
    expect(ascending).toHaveLength(EVIDENCE_SEED.length);
    for (let i = 1; i < ascending.length; i += 1) {
      expect(ascending[i - 1].at <= ascending[i].at).toBe(true);
    }
  });

  // 코드리뷰 회귀: [...mergedAuditLog(events)].reverse()는 안정 정렬이 보존한 동시각
  // 이벤트의 상대 순서까지 뒤집었다 — checklist_completed가 approval_decided보다 먼저
  // append됐다면(둘 다 같은 caseId, 같은 at) 오름차순에서도 그 순서(체크리스트 완료 →
  // 최종 승인)가 그대로 유지돼야 한다.
  it('같은 caseId·같은 at인 두 이벤트는 append 순서를 그대로 유지한다', () => {
    const at = '2026-07-17T09:00:00.000Z';
    const first: EvidenceEvent = { id: 'eA', type: 'checklist_completed', at, caseId: 'nguyen' };
    const second: EvidenceEvent = { id: 'eB', type: 'approval_decided', at, caseId: 'nguyen' };
    const ascending = mergedAuditLogAscending([first, second]);
    const indexOf = (id: string) => ascending.findIndex((e) => e.id === id);
    expect(indexOf('eA')).toBeLessThan(indexOf('eB'));
  });
});

describe('caseTimelineActivity — D-3 실시간 반영 + 모순 표시 제거(코드리뷰 회귀)', () => {
  const staticActivity: CaseActivityEntry[] = [
    { label: '응답 도착 · 해석 완료', detail: '담당자 확인 대기', at: '오늘 10:12', outcome: 'question' },
    { label: '위험 감지', detail: '자동 탐지', at: '오늘 07:00', outcome: 'pending' },
  ];

  it('interpretation_confirmed가 없으면 정적 activity를 그대로 둔다', () => {
    const result = caseTimelineActivity('tranCase', staticActivity, []);
    expect(result).toEqual(staticActivity);
  });

  it('interpretation_confirmed가 있으면 "확인 대기"(outcome:question) 정적 항목을 제거하고 런타임 항목을 앞에 붙인다', () => {
    const events: EvidenceEvent[] = [
      { id: 'e1', type: 'interpretation_confirmed', at: '2026-07-17T10:00:00.000Z', caseId: 'tranCase', summary: '해석 확인 완료' },
    ];
    const result = caseTimelineActivity('tranCase', staticActivity, events);

    expect(result.some((entry) => entry.outcome === 'question')).toBe(false);
    expect(result[0].label).toBe('해석 확인');
    // 위험 감지(outcome:'pending')는 이 이벤트와 무관하므로 남는다.
    expect(result.some((entry) => entry.label === '위험 감지')).toBe(true);
  });

  it('다른 케이스의 interpretation_confirmed는 이 케이스의 정적 activity에 영향을 주지 않는다', () => {
    const events: EvidenceEvent[] = [
      { id: 'e2', type: 'interpretation_confirmed', at: '2026-07-17T10:00:00.000Z', caseId: 'other-case', summary: '무관' },
    ];
    const result = caseTimelineActivity('tranCase', staticActivity, events);
    expect(result).toEqual(staticActivity);
  });
});

describe('filterAudit — §3c 필터 칩(전체/위험/승인/내보내기)', () => {
  const merged = mergedAuditLog([]);

  it('전체는 모든 항목', () => {
    expect(filterAudit(merged, 'all')).toHaveLength(merged.length);
  });

  it('위험 탐지는 risk_flagged만', () => {
    expect(filterAudit(merged, 'risk').every((e) => e.type === 'risk_flagged')).toBe(true);
    expect(filterAudit(merged, 'risk').length).toBeGreaterThan(0);
  });

  it('승인은 요청·완료·반려·에스컬레이션을 포함', () => {
    const approvalTypes = new Set(filterAudit(merged, 'approval').map((e) => e.type));
    const allowed = ['approval_requested', 'approval_decided', 'approval_rejected', 'approval_escalated'];
    expect([...approvalTypes].every((t) => allowed.includes(t))).toBe(true);
  });

  it('내보내기는 exported만 — 시드의 export_0031이 잡힌다', () => {
    const exports = filterAudit(merged, 'export');
    expect(exports.every((e) => e.type === 'exported')).toBe(true);
    expect(exports.some((e) => e.summary?.includes('export_0031'))).toBe(true);
  });
});

describe('caseTimelineActivity — 재생 런 존재 확인(PR #14 리뷰 P1: 없는 runKey로 이동하는 버튼 방지)', () => {
  it('RUN_CONFIGS에 없는 evidenceRef(#4791)는 runRef를 채우지 않는다', () => {
    const event: EvidenceEvent = {
      id: 'evt-1',
      type: 'interpretation_confirmed',
      at: new Date().toISOString(),
      caseId: 'nguyen',
      summary: '해석 확인됨',
      evidenceRef: '#4791', // mocks/threads.ts 실제 시드값 — RUN_CONFIGS.runKey엔 없음
    };
    const activity = caseTimelineActivity('nguyen', [], [event]);
    expect(activity[0].runRef).toBeUndefined();
  });

  it('RUN_CONFIGS에 실제로 있는 evidenceRef(#4788)는 runRef를 그대로 채운다', () => {
    const event: EvidenceEvent = {
      id: 'evt-2',
      type: 'interpretation_confirmed',
      at: new Date().toISOString(),
      caseId: 'nguyen',
      summary: '해석 확인됨',
      evidenceRef: '#4788', // RUN_CONFIGS에 실제로 존재하는 runKey
    };
    const activity = caseTimelineActivity('nguyen', [], [event]);
    expect(activity[0].runRef).toBe('#4788');
  });

  it('evidenceRef가 없는 이벤트는 runRef도 없다', () => {
    const event: EvidenceEvent = {
      id: 'evt-3',
      type: 'package_reply',
      at: new Date().toISOString(),
      caseId: 'nguyen',
      summary: '회신 도착',
    };
    const activity = caseTimelineActivity('nguyen', [], [event]);
    expect(activity[0].runRef).toBeUndefined();
  });
});
