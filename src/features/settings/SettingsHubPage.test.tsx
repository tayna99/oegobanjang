import { fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { NotificationSettingsPage } from '@/features/settings/NotificationSettingsPage';
import { SettingsHubPage } from '@/features/settings/SettingsHubPage';
import { useCompanyStore } from '@/stores/companyStore';
import { useRoleStore } from '@/stores/roleStore';

function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      { path: '/', element: <div>홈</div> },
      { path: '/settings', element: <SettingsHubPage /> },
      { path: '/settings/notifications', element: <NotificationSettingsPage /> },
    ],
    { initialEntries: [path] },
  );
  return render(<RouterProvider router={router} />);
}

// 설정 허브 — 7단계 §6 역할 분기(운영급 RBAC 확장).
describe('SettingsHubPage', () => {
  afterEach(() => {
    useRoleStore.getState().reset();
    useCompanyStore.getState().reset();
  });

  it('viewer는 설정에 진입할 수 없다 — 헤더는 유지되고 권한 배지 안내가 뜬다', async () => {
    useRoleStore.getState().setRole('viewer');
    renderAt('/settings');
    expect(await screen.findByRole('heading', { name: '설정' })).toBeInTheDocument();
    expect(screen.getByText('열람자 권한으로는 설정에 진입할 수 없습니다.')).toBeInTheDocument();
    expect(screen.getByText('설정 변경은 대표·담당자만 가능합니다.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '뒤로' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /브리핑으로/ })).not.toBeInTheDocument();
  });

  it('manager는 구성원 관리만 보고 위임 관리·승인 정책 섹션은 없다', async () => {
    renderAt('/settings');
    expect(await screen.findByRole('button', { name: /구성원 관리/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /위임 관리/ })).not.toBeInTheDocument();
    expect(screen.queryByText('승인 정책')).not.toBeInTheDocument();
  });

  it('owner는 위임 관리·승인 정책 섹션을 모두 보고 정책을 전환할 수 있다', async () => {
    useRoleStore.getState().setRole('owner');
    renderAt('/settings');
    expect(await screen.findByRole('button', { name: /위임 관리/ })).toBeInTheDocument();

    const ownerOnlyBtn = screen.getByRole('button', { name: '대표만 승인' });
    fireEvent.click(ownerOnlyBtn);
    expect(useCompanyStore.getState().approvalPolicy).toBe('owner_only');
    expect(ownerOnlyBtn).toHaveAttribute('aria-pressed', 'true');
  });

  it('알림 행이 알림 설정 화면으로 이동한다', async () => {
    renderAt('/settings');
    const notiRow = await screen.findByRole('button', { name: /알림/ });
    expect(notiRow).toHaveTextContent('브리핑 08:00');
    fireEvent.click(notiRow);
    expect(await screen.findByText('아침 브리핑 시각')).toBeInTheDocument();
  });
});
