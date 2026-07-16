import { HANDOFF_PACKAGES, type HandoffPackage } from './packages';
import type { ExpertAccount, ExpertMembership, Tenant } from '@/types';

// 행정사 화이트라벨 시드(7-1) — 멀티테넌트 + 영속 expert 계정. 김앤리 행정사무소가
// 그린푸드·한빛 두 회사에 연결돼, 개인 대시보드에서 두 회사 검토 대기를 통합해 본다.
export const TENANTS: Tenant[] = [
  { id: 'greenfood', name: '그린푸드 제조' },
  { id: 'hanbit', name: '한빛식품' },
];

export const EXPERT_ACCOUNTS: ExpertAccount[] = [
  // brandColor: Montage cyan-30 램프값 — 앱 primary(파랑)와 구분되게 둔 "행정사 제공 브랜드색"(데이터).
  { id: 'expert-kimlee', officeName: '김앤리 행정사무소', brandInitial: '김', brandColor: '#006F82' },
];

export const EXPERT_MEMBERSHIPS: ExpertMembership[] = [
  { expertId: 'expert-kimlee', tenantId: 'greenfood' },
  { expertId: 'expert-kimlee', tenantId: 'hanbit' },
];

export function expertAccountFor(expertId: string | undefined): ExpertAccount | undefined {
  return expertId ? EXPERT_ACCOUNTS.find((e) => e.id === expertId) : undefined;
}

export function tenantFor(tenantId: string | undefined): Tenant | undefined {
  return tenantId ? TENANTS.find((t) => t.id === tenantId) : undefined;
}

// 대시보드용 — expert가 속한 tenant별로 자기에게 온(recipient 일치) 패키지를 묶는다.
export interface ExpertTenantGroup {
  tenant: Tenant;
  packages: HandoffPackage[];
}

export function packagesForExpert(expertId: string): ExpertTenantGroup[] {
  const account = expertAccountFor(expertId);
  if (!account) return [];
  const tenantIds = EXPERT_MEMBERSHIPS.filter((m) => m.expertId === expertId).map((m) => m.tenantId);
  return tenantIds
    .map((tid) => tenantFor(tid))
    .filter((t): t is Tenant => Boolean(t))
    .map((tenant) => ({
      tenant,
      packages: Object.values(HANDOFF_PACKAGES).filter(
        (pkg) => pkg.tenantId === tenant.id && pkg.recipient === account.officeName,
      ),
    }))
    .filter((group) => group.packages.length > 0);
}

// 패키지가 어느 expert의 것인지(패키지 뷰의 브랜드·소속 회사 헤더용).
export function expertForPackage(pkg: HandoffPackage): ExpertAccount | undefined {
  return EXPERT_ACCOUNTS.find((e) => e.officeName === pkg.recipient);
}
