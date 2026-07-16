import type { Role } from '@/types';

// 역할 표시 라벨 — Shell 토글·evidence actor 접두("담당자 김담당 (본인 확인 완료)")·구성원
// 배지가 공유하는 단일 출처(7단계 §1). 문자열 중복 금지(rules/frontend.md).
export const ROLE_LABEL: Record<Role, string> = { manager: '담당자', owner: '대표', viewer: '열람자' };
