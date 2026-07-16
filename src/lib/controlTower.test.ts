import { describe, expect, it } from 'vitest';
import { controlTowerKpis, rowAction } from './controlTower';
import { CASE_CARDS, CASE_SHEETS } from '@/mocks/fixtures';
import type { CaseCard } from '@/types';

describe('controlTowerKpis — §3a KPI 파생(디자인 값과 일치)', () => {
  const kpis = controlTowerKpis(CASE_CARDS, CASE_SHEETS);

  it('활성 케이스 = 로스터 6', () => {
    expect(kpis.activeCases).toBe(6);
  });

  it('고위험 (C+H) = 3 (batbayar CRITICAL · nguyen/siti HIGH)', () => {
    expect(kpis.highRisk).toBe(3);
  });

  it('D-day 임박 (≤7일) = 2 (batbayar D+2 · siti D-3)', () => {
    expect(kpis.dDayImminent).toBe(2);
  });

  it('근거 부족 = 0 — 승인 필요 케이스는 모두 실사용 근거를 갖는다', () => {
    expect(kpis.evidenceShort).toBe(0);
  });

  it('승인 필요한데 근거 0건이면 근거 부족으로 센다', () => {
    const noEvidenceCase: CaseCard = { ...CASE_CARDS.find((c) => c.caseId === 'nguyen')!, caseId: 'x' };
    const sheets = { ...CASE_SHEETS, x: { ...CASE_SHEETS.nguyen, caseId: 'x', citations: [] } };
    expect(controlTowerKpis([noEvidenceCase], sheets).evidenceShort).toBe(1);
  });
});

describe('rowAction — C10 교정(고위험은 처리 버튼 대신 검토)', () => {
  it('blocked(고위험 batbayar)는 "검토"', () => {
    const batbayar = CASE_CARDS.find((c) => c.caseId === 'batbayar')!;
    expect(batbayar.state).toBe('blocked');
    expect(rowAction(batbayar)).toEqual({ kind: 'review', label: '검토' });
  });

  it('approval_pending은 "승인"', () => {
    const nguyen = CASE_CARDS.find((c) => c.caseId === 'nguyen')!;
    expect(rowAction(nguyen)).toEqual({ kind: 'approve', label: '승인' });
  });

  it('그 외(draft/risk_review)는 "보기"', () => {
    const oyunaa = CASE_CARDS.find((c) => c.caseId === 'oyunaa')!;
    expect(rowAction(oyunaa)).toEqual({ kind: 'view', label: '보기' });
  });
});
