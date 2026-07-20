import { useSessionStore } from '@/stores/sessionStore';
import { apiFetch } from './client';

// POST /api/v1/outbox("실행 확인") 어댑터 — R3 stage ②(MESSAGING_CHANNELS.md §1 각주² 실체화).
// DispatchQueuePage의 real-mode "발송 실행" 버튼이 이 함수를 부른다 — mock 모드는 여전히
// approvalStore.dispatch()(로컬 mock)만 쓴다(변경 없음). action_id는 실제 승인된
// next_actions.id(send_message)여야 하며, 백엔드가 승인 게이트·발송 창·idempotency를 전부
// 구조적으로 강제한다(backend/app/services/outbox.py).
export interface OutboxDispatchResultDto {
  id: string;
  channel: string;
  status: string;
  external_id: string | null;
}

export async function executeDispatch(actionId: string): Promise<OutboxDispatchResultDto> {
  const token = useSessionStore.getState().token ?? undefined;
  return apiFetch<OutboxDispatchResultDto>('/api/v1/outbox', {
    method: 'POST',
    token,
    body: { action_id: actionId },
  });
}
