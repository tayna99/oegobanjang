import { useSessionStore } from '@/stores/sessionStore';
import { apiFetch } from './client';

// POST /api/v1/approvals/{id}/approve|reject · POST /api/v1/approvals(R2.4) 어댑터 —
// backend/app/schemas/approval.py의 ApprovalDecisionRequest/ApprovalDecisionResponse 그대로
// (snake_case). PIN 원문은 여기서만 네트워크로 나간다 — 서버가 users.pin_hash와 대조 검증하고
// 저장하지 않는다(backend/app/domain/auth_tokens.py).
export interface DecisionChecklistItem {
  key: string;
  label: string;
  checked: boolean;
}

export interface DecisionBody {
  idempotencyKey: string;
  onBehalfOfUserId?: string;
  identityMethod?: 'pin' | 'biometric';
  pin?: string;
  reason?: string;
  checklist?: DecisionChecklistItem[];
}

interface ApprovalDecisionResponseDto {
  approval: { id: string; status: string };
  case_state: string;
}

function toBody(body: DecisionBody) {
  return {
    idempotency_key: body.idempotencyKey,
    on_behalf_of_user_id: body.onBehalfOfUserId ?? null,
    identity_method: body.identityMethod ?? null,
    pin: body.pin ?? null,
    reason: body.reason ?? null,
    checklist: body.checklist?.map((item) => ({ key: item.key, label: item.label, checked: item.checked })) ?? null,
  };
}

export async function approveApproval(approvalId: string, body: DecisionBody): Promise<{ caseState: string }> {
  const token = useSessionStore.getState().token ?? undefined;
  const dto = await apiFetch<ApprovalDecisionResponseDto>(`/api/v1/approvals/${approvalId}/approve`, {
    method: 'POST',
    token,
    body: toBody(body),
  });
  return { caseState: dto.case_state };
}

export async function rejectApproval(approvalId: string, body: DecisionBody): Promise<{ caseState: string }> {
  const token = useSessionStore.getState().token ?? undefined;
  const dto = await apiFetch<ApprovalDecisionResponseDto>(`/api/v1/approvals/${approvalId}/reject`, {
    method: 'POST',
    token,
    body: toBody(body),
  });
  return { caseState: dto.case_state };
}

// 승인 요청 생성 — manager 세션 전용(서버 정책, request_approval). 이미 pending이면 서버가
// 409를 던진다 — 호출부가 잡아서 "이미 대기 중" 취급으로 이어간다.
export async function createApprovalRequest(actionId: string): Promise<{ approvalId: string; caseState: string }> {
  const token = useSessionStore.getState().token ?? undefined;
  const dto = await apiFetch<ApprovalDecisionResponseDto>('/api/v1/approvals', {
    method: 'POST',
    token,
    body: { action_id: actionId },
  });
  return { approvalId: dto.approval.id, caseState: dto.case_state };
}
