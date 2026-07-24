import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchNotifications, markNotificationRead } from './notifications';
import type { NotificationDto } from './notifications';

describe('notifications 어댑터 — R5.4', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  const dto: NotificationDto = {
    id: 'nt_1',
    type: 'N01',
    priority: 'P1',
    title: '승인 요청 1건',
    body: '체류 만료 임박 · 승인 전에는 외부로 발송되지 않습니다',
    deeplink_path: 'case/cs1/approve',
    channel: 'push',
    status: 'queued',
    case_id: 'cs1',
    run_id: null,
    created_at: '2026-07-20T09:00:00Z',
    read_at: null,
  };

  it('fetchNotifications는 snake_case 응답을 camelCase 레코드로 변환한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify([dto]), { status: 200 })) as unknown as typeof fetch;

    const result = await fetchNotifications();

    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      id: 'nt_1',
      type: 'N01',
      priority: 'P1',
      title: '승인 요청 1건',
      body: '체류 만료 임박 · 승인 전에는 외부로 발송되지 않습니다',
      deeplinkPath: 'case/cs1/approve',
      channel: 'push',
      status: 'queued',
      caseId: 'cs1',
      runId: null,
      createdAt: '2026-07-20T09:00:00Z',
      readAt: null,
    });
  });

  it('markNotificationRead는 POST /api/v1/notifications/{id}/read를 호출하고 갱신된 레코드를 반환한다', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ ...dto, read_at: '2026-07-20T09:05:00Z' }), { status: 200 }));
    global.fetch = fetchMock as unknown as typeof fetch;

    const result = await markNotificationRead('nt_1');

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/notifications/nt_1/read'),
      expect.objectContaining({ method: 'POST' }),
    );
    expect(result.readAt).toBe('2026-07-20T09:05:00Z');
  });

  it('비2xx 응답은 ApiError를 던진다', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ detail: '알림을 찾을 수 없습니다' }), { status: 404 })) as unknown as typeof fetch;

    await expect(markNotificationRead('nope')).rejects.toMatchObject({ status: 404 });
  });
});
