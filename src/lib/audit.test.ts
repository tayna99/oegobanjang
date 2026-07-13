import { describe, expect, it } from 'vitest';
import { AUDIT_TYPE_LABEL, AUDIT_TYPE_TONE, filterAudit, mergedAuditLog } from './audit';
import { EVIDENCE_SEED } from '@/mocks/evidence';
import type { EvidenceEvent, EvidenceType } from '@/types';

const ALL_TYPES: EvidenceType[] = [
  'intent_classified', 'plan_created', 'tool_executed', 'rag_retrieved', 'risk_flagged',
  'approval_requested', 'approval_decided', 'approval_rejected', 'review_started',
  'checklist_completed', 'exported', 'final_response_generated',
  // 7단계 §5 권한 이벤트(운영급 RBAC 확장).
  'role_granted', 'role_changed', 'member_invited', 'member_removed',
  'delegation_granted', 'delegation_revoked', 'approval_escalated',
  'package_link_issued', 'package_link_viewed',
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
