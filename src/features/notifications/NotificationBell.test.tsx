import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, useLocation, type Location } from 'react-router-dom';
import { useEffect } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { NotificationBell } from './NotificationBell';
import { useNotificationStore } from '@/stores/notificationStore';
import type { NotificationRecord } from '@/lib/api/notifications';

function LocationRecorder({ onChange }: { onChange: (location: Location) => void }) {
  const location = useLocation();
  useEffect(() => {
    onChange(location);
  }, [location, onChange]);
  return null;
}

function renderBell() {
  let current: Location | undefined;
  render(
    <MemoryRouter initialEntries={['/']}>
      <LocationRecorder onChange={(l) => (current = l)} />
      <NotificationBell />
    </MemoryRouter>,
  );
  return { getLocation: () => current };
}

function record(overrides: Partial<NotificationRecord> = {}): NotificationRecord {
  return {
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
    ...overrides,
  };
}

describe('NotificationBell — R5.4', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    useNotificationStore.getState().reset();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('mock 모드에서는 읽지 않은 알림 배지가 없다(빈 스토어)', () => {
    renderBell();
    expect(screen.getByRole('button', { name: '알림 센터' })).toBeInTheDocument();
  });

  it('읽지 않은 알림이 있으면 버튼 aria-label에 건수가 반영된다', () => {
    useNotificationStore.getState().hydrate([record(), record({ id: 'nt_2' })]);
    renderBell();
    expect(screen.getByRole('button', { name: '알림 센터, 읽지 않은 알림 2건' })).toBeInTheDocument();
  });

  it('버튼을 누르면 알림 목록이 담긴 시트가 열린다', () => {
    useNotificationStore.getState().hydrate([record()]);
    renderBell();
    fireEvent.click(screen.getByRole('button', { name: /알림 센터/ }));
    expect(screen.getByText('승인 요청 1건')).toBeInTheDocument();
  });

  it('알림이 없으면 빈 상태 문구를 보여준다', () => {
    renderBell();
    fireEvent.click(screen.getByRole('button', { name: '알림 센터' }));
    expect(screen.getByText('아직 도착한 알림이 없습니다.')).toBeInTheDocument();
  });

  it('알림을 선택하면 딥링크 경로로 이동하고 읽음 처리를 시도한다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
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
    );
    global.fetch = fetchMock as unknown as typeof fetch;
    useNotificationStore.getState().hydrate([record()]);

    const { getLocation } = renderBell();
    fireEvent.click(screen.getByRole('button', { name: /알림 센터/ }));
    fireEvent.click(screen.getByText('승인 요청 1건'));

    expect(getLocation()?.pathname).toBe('/case/cs1/approve');
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/notifications/nt_1/read'),
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('이미 읽은 알림을 선택하면 다시 읽음 처리를 시도하지 않는다', () => {
    const fetchMock = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;
    useNotificationStore.getState().hydrate([record({ readAt: '2026-07-20T09:05:00Z' })]);

    renderBell();
    fireEvent.click(screen.getByRole('button', { name: '알림 센터' }));
    fireEvent.click(screen.getByText('승인 요청 1건'));

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
