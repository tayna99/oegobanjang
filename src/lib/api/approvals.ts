import { apiFetch } from './client';

// POST /api/v1/approvals · /approvals/{id}/approve|reject 응답 DTO(백엔드
// backend/app/schemas/approval.py의 ApprovalOut/ApprovalDecisionResponse 그대로, snake_case) —
// R2.4, NEXT_ROADMAP 2.4.
export interface ApprovalDto {
  id: string;
  company_id: string;
  case_id: string;
  action_id: string;
  status: string;
  idempotency_key: string | null;
  reason: string | null;
  requested_at: string;
  decided_at: string | null;
  decided_by_user_id: string | null;
}

export interface ApprovalDecisionResponseDto {
  approval: ApprovalDto;
  case_state: string;
}

export interface DecisionBody {
  idempotencyKey: string;
  identityMethod: 'pin' | 'biometric';
  pin?: string;
  onBehalfOfUserId?: string;
  reason?: string;
}

function toRequestBody(body: DecisionBody) {
  return {
    idempotency_key: body.idempotencyKey,
    identity_method: body.identityMethod,
    pin: body.pin,
    on_behalf_of_user_id: body.onBehalfOfUserId,
    reason: body.reason,
  };
}

export async function createApprovalRequest(actionId: string): Promise<ApprovalDecisionResponseDto> {
  return apiFetch<ApprovalDecisionResponseDto>('/api/v1/approvals', {
    method: 'POST',
    body: JSON.stringify({ action_id: actionId }),
  });
}

export async function approveApproval(approvalId: string, body: DecisionBody): Promise<ApprovalDecisionResponseDto> {
  return apiFetch<ApprovalDecisionResponseDto>(`/api/v1/approvals/${approvalId}/approve`, {
    method: 'POST',
    body: JSON.stringify(toRequestBody(body)),
  });
}

export async function rejectApproval(approvalId: string, body: DecisionBody): Promise<ApprovalDecisionResponseDto> {
  return apiFetch<ApprovalDecisionResponseDto>(`/api/v1/approvals/${approvalId}/reject`, {
    method: 'POST',
    body: JSON.stringify(toRequestBody(body)),
  });
}
