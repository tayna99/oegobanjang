import { fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { useCompanyStore } from '@/stores/companyStore';
import { useRoleStore } from '@/stores/roleStore';

function renderAt(path: string) {
  return render(<RouterProvider router={createMemoryRouter(routeConfig, { initialEntries: [path] })} />);
}

// 알림 설정 — 2단계_알림카탈로그_딥링크맵_v1.md §6, docs/DESIGN_SYNC_AUDIT_2026-07-17.md §1.
describe('NotificationSettingsPage', () => {
  afterEach(() => {
    useRoleStore.getState().reset();
    useCompanyStore.getState().reset();
  });

  it('viewer는 알림 설정에 딥링크로 직접 진입해도 차단된다 — 헤더는 유지되고 권한 배지 안내가 뜬다', async () => {
    useRoleStore.getState().setRole('viewer');
    renderAt('/settings/notifications');
    expect(await screen.findByRole('heading', { name: '알림 설정' })).toBeInTheDocument();
    expect(screen.getByText('열람자 권한으로는 알림 설정에 진입할 수 없습니다.')).toBeInTheDocument();
    expect(screen.getByText('알림 설정 변경은 대표·담당자만 가능합니다.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '뒤로' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /브리핑으로/ })).not.toBeInTheDocument();
  });

  it('manager도 승인 요청 즉시 알림 항목을 본다 — 대표 전용이 아니다', async () => {
    renderAt('/settings/notifications');
    const approvalToggle = await screen.findByRole('switch', { name: '승인 요청 즉시 알림' });
    expect(approvalToggle).toBeInTheDocument();
    expect(approvalToggle).toBeDisabled();
    expect(approvalToggle).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByText('성급한 승인을 막기 위해 항상 켜져 있으며, 끌 수 없습니다.')).toBeInTheDocument();
  });

  it('owner도 동일하게 승인 요청 즉시 알림 항목을 본다', async () => {
    useRoleStore.getState().setRole('owner');
    renderAt('/settings/notifications');
    const approvalToggle = await screen.findByRole('switch', { name: '승인 요청 즉시 알림' });
    expect(approvalToggle).toBeDisabled();
  });

  it('승인 요청 즉시 알림 토글은 클릭해도 상태가 바뀌지 않는다', async () => {
    renderAt('/settings/notifications');
    const approvalToggle = await screen.findByRole('switch', { name: '승인 요청 즉시 알림' });
    fireEvent.click(approvalToggle);
    expect(approvalToggle).toHaveAttribute('aria-checked', 'true');
  });

  it('응답 도착 즉시 알림을 끄면 다이제스트 안내가 보이고 스토어에 반영된다', async () => {
    renderAt('/settings/notifications');
    const toggle = await screen.findByRole('switch', { name: '응답 도착 즉시 알림' });
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    fireEvent.click(toggle);
    expect(useCompanyStore.getState().notificationPrefs.responseImmediate).toBe(false);
    expect(await screen.findByText('끄면 즉시 알림 대신 아침 다이제스트로 모아 전달됩니다.')).toBeInTheDocument();
  });

  it('CRITICAL 야간 알림을 끄면 경고 캡션이 보인다', async () => {
    renderAt('/settings/notifications');
    const toggle = await screen.findByRole('switch', { name: 'CRITICAL 야간 알림' });
    fireEvent.click(toggle);
    expect(useCompanyStore.getState().notificationPrefs.criticalNight).toBe(false);
    expect(await screen.findByText('끄면 긴급 항목 확인이 다음 아침까지 늦어질 수 있습니다.')).toBeInTheDocument();
  });

  it('주간 요약은 기본 OFF이고 켜면 스토어에 반영된다', async () => {
    renderAt('/settings/notifications');
    const toggle = await screen.findByRole('switch', { name: '주간 요약' });
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    fireEvent.click(toggle);
    expect(useCompanyStore.getState().notificationPrefs.weeklyDigest).toBe(true);
  });

  it('채널 우선순위 행은 조작할 수 없는 읽기 전용이다', async () => {
    renderAt('/settings/notifications');
    expect(await screen.findByText('읽기 전용')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /채널 우선순위/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('switch', { name: /채널 우선순위/ })).not.toBeInTheDocument();
  });

  it('브리핑 시각을 바꾸면 companyStore에 반영되고 허브와 값을 공유한다', async () => {
    renderAt('/settings/notifications');
    const input = await screen.findByLabelText('브리핑 시각');
    fireEvent.change(input, { target: { value: '09:15' } });
    expect(useCompanyStore.getState().briefingTime).toBe('09:15');
  });
});
