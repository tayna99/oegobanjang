import { describe, expect, it } from 'vitest';
import { DEMO_TODAY, isLinkExpired, LINK_VALIDITY_DAYS } from './packageLink';
import { HANDOFF_PACKAGES } from '@/mocks/packages';
import type { EvidenceEvent } from '@/types';

const batbayar = HANDOFF_PACKAGES.batbayar; // createdAt: '2026-07-06'

describe('isLinkExpired — 7단계 §4 만료형(기본 7일) + 재발급', () => {
  it(`발급 후 ${LINK_VALIDITY_DAYS}일 이내면 만료되지 않는다`, () => {
    expect(isLinkExpired(batbayar, [])).toBe(false);
  });

  it(`발급 후 ${LINK_VALIDITY_DAYS}일이 지나면 만료된다`, () => {
    const oldPkg = { ...batbayar, createdAt: '2026-06-01' };
    expect(isLinkExpired(oldPkg, [])).toBe(true);
  });

  it('재발급 이벤트가 있으면 원래 발급일과 무관하게 항상 유효하다', () => {
    const oldPkg = { ...batbayar, createdAt: '2026-06-01' };
    const events: EvidenceEvent[] = [
      {
        id: 'reissue-1',
        type: 'package_link_issued',
        at: new Date().toISOString(),
        caseId: oldPkg.packageId,
      },
    ];
    expect(isLinkExpired(oldPkg, events)).toBe(false);
  });

  it('DEMO_TODAY는 앱 전역이 공유하는 고정 데모 날짜다', () => {
    expect(DEMO_TODAY).toBe('2026-07-10');
  });
});
