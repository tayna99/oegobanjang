import { useSessionStore } from '@/stores/sessionStore';
import { apiFetch } from './client';

// GET /api/v1/notifications, POST /api/v1/notifications/{id}/read 어댑터 — R5.4.
// backend/app/schemas/notification.py NotificationOut 그대로(snake_case) — citations.ts/
// briefings.ts와 동일 관례: DTO(snake_case) → 도메인 레코드(camelCase) 변환은 이 파일 안에서만.
export interface NotificationDto {
  id: string;
  type: string;
  priority: string;
  title: string;
  body: string;
  deeplink_path: string;
  channel: string;
  status: string;
  case_id: string | null;
  run_id: string | null;
  created_at: string;
  read_at: string | null;
}

export interface NotificationRecord {
  id: string;
  type: string;
  priority: string;
  title: string;
  body: string;
  deeplinkPath: string;
  channel: string;
  status: string;
  caseId: string | null;
  runId: string | null;
  createdAt: string;
  readAt: string | null;
}

function toNotificationRecord(dto: NotificationDto): NotificationRecord {
  return {
    id: dto.id,
    type: dto.type,
    priority: dto.priority,
    title: dto.title,
    body: dto.body,
    deeplinkPath: dto.deeplink_path,
    channel: dto.channel,
    status: dto.status,
    caseId: dto.case_id,
    runId: dto.run_id,
    createdAt: dto.created_at,
    readAt: dto.read_at,
  };
}

// 본인 수신함만(company_id+recipient_user_id는 서버가 세션에서 도출) — 최신순.
export async function fetchNotifications(): Promise<NotificationRecord[]> {
  const token = useSessionStore.getState().token ?? undefined;
  const dtos = await apiFetch<NotificationDto[]>('/api/v1/notifications', { token });
  return dtos.map(toNotificationRecord);
}

export async function markNotificationRead(id: string): Promise<NotificationRecord> {
  const token = useSessionStore.getState().token ?? undefined;
  const dto = await apiFetch<NotificationDto>(`/api/v1/notifications/${encodeURIComponent(id)}/read`, {
    method: 'POST',
    token,
  });
  return toNotificationRecord(dto);
}
