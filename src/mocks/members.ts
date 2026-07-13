import type { CompanyMember } from '@/types';

// 회사(tenant) 구성원 시드 — 7단계 §1 4역할 중 앱에 로그인하는 3역할만(행정사는 계정이 아님).
// 이대표는 공동대표(§3.3) 시연 전용 — 이미 결정된 승인 건의 "다른 owner" 역할.
export const COMPANY_MEMBERS: CompanyMember[] = [
  { id: 'manager-kim', name: '김담당', role: 'manager' },
  { id: 'owner-kim', name: '김대표', role: 'owner' },
  { id: 'owner-lee', name: '이대표', role: 'owner' },
  { id: 'viewer-choi', name: '최감사', role: 'viewer' },
];
