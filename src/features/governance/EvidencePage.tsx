import { useSeedEvidence } from '@/lib/dataSeed';
import { useIsDesktop } from '@/lib/useIsDesktop';
import { GovernancePage } from './GovernancePage';
import { GlobalEvidencePage } from './GlobalEvidencePage';

// /evidence 컨테이너 — 데스크톱은 PC 거버넌스(§3c, 2.5.5), 모바일은 M8 전역 판단 기록(2.3).
export function EvidencePage() {
  const isDesktop = useIsDesktop();
  useSeedEvidence();
  return isDesktop ? <GovernancePage /> : <GlobalEvidencePage />;
}
