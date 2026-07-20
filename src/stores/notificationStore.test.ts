import { afterEach, describe, expect, it, vi } from 'vitest';
import { unreadNotificationCount, useNotificationStore } from './notificationStore';
import type { NotificationRecord } from '@/lib/api/notifications';

function record(overrides: Partial<NotificationRecord> = {}): NotificationRecord {
  return {
    id: 'nt_1',
    type: 'N01',
    priority: 'P1',
    title: '승인 요청 1건',
    body: '체류 만료 임박',
    deeplinkPath: 'case/cs1/approve',
    channel: 'push',
    status: 'queued',
    caseId: 'cs1',
    runId: null,
    createdAt: '2026-07-20T09:00:00Z',
    readAt: null,
    ...overrides,
  };
}

describe('notificationStore — R5.4', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    useNotificationStore.getState().reset();
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('초기 상태는 빈 배열이다 — mock 모드가 이 값을 절대 채우지 않으므로 unreadNotifications가 항상 0', () => {
    expect(useNotificationStore.getState().records).toEqual([]);
    expect(unreadNotificationCount(useNotificationStore.getState().records)).toBe(0);
  });

  it('hydrate는 records를 전량 교체한다', () => {
    useNotificationStore.getState().hydrate([record(), record({ id: 'nt_2', readAt: '2026-07-20T09:10:00Z' })]);
    expect(useNotificationStore.getState().records).toHaveLength(2);
    useNotificationStore.getState().hydrate([record({ id: 'nt_3' })]);
    expect(useNotificationStore.getState().records.map((r) => r.id)).toEqual(['nt_3']);
  });

  it('unreadNotificationCount는 readAt이 null인 레코드만 센다', () => {
    const records = [record({ id: 'a', readAt: null }), record({ id: 'b', readAt: '2026-07-20T09:00:00Z' }), record({ id: 'c', readAt: null })];
    expect(unreadNotificationCount(records)).toBe(2);
  });

  it('markRead는 서버 응답으로 로컬 레코드를 교체한다', async () => {
    useNotificationStore.getState().hydrate([record()]);
    global.fetch = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            id: 'nt_1',
            type: 'N01',
            priority: 'P1',
            title: '승인 요청 1건',
            body: '체류 만료 임박',
            deeplink_path: 'case/cs1/approve',
            channel: 'push',
            status: 'queued',
            case_id: 'cs1',
            run_id: null,
            created_at: '2026-07-20T09:00:00Z',
            read_at: '2026-07-20T09:05:00Z',
          }),
          { status: 200 },
        ),
      ) as unknown as typeof fetch;

    await useNotificationStore.getState().markRead('nt_1');

    expect(useNotificationStore.getState().records[0].readAt).toBe('2026-07-20T09:05:00Z');
  });

  it('markRead 실패는 로컬 상태를 그대로 두고 콘솔에만 남긴다', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    useNotificationStore.getState().hydrate([record()]);
    global.fetch = vi.fn().mockRejectedValue(new Error('network down')) as unknown as typeof fetch;

    await expect(useNotificationStore.getState().markRead('nt_1')).resolves.toBeUndefined();

    expect(consoleError).toHaveBeenCalled();
    expect(useNotificationStore.getState().records[0].readAt).toBeNull();
  });
});
