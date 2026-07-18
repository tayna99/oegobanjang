import { useSessionStore } from '@/stores/sessionStore';
import { apiFetch } from './client';

// GET /api/v1/delegations/mine 어댑터(R2.4) — backend/app/schemas/delegation.py의 DelegationOut.
export interface MyDelegation {
  delegatorUserId: string;
  delegatorName: string;
  endsAt: string;
}

interface DelegationOutDto {
  delegation_id: string;
  delegator_user_id: string;
  delegator_name: string;
  ends_at: string;
}

export async function fetchMyDelegation(): Promise<MyDelegation | null> {
  const token = useSessionStore.getState().token ?? undefined;
  const dto = await apiFetch<DelegationOutDto | null>('/api/v1/delegations/mine', { token });
  if (dto === null) return null;
  return { delegatorUserId: dto.delegator_user_id, delegatorName: dto.delegator_name, endsAt: dto.ends_at };
}
