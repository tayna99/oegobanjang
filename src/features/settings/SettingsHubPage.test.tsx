import { fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { useCompanyStore } from '@/stores/companyStore';
import { useRoleStore } from '@/stores/roleStore';

function renderAt(path: string) {
  return render(<RouterProvider router={createMemoryRouter(routeConfig, { initialEntries: [path] })} />);
}

// 설정 허브 — 7단계 §6 역할 분기(운영급 RBAC 확장).
describe('SettingsHubPage', () => {
  afterEach(() => {
    useRoleStore.getState().reset();
    useCompanyStore.getState().reset();
  });

  it('viewer는 설정에 진입할 수 없다', async () => {
    useRoleStore.getState().setRole('viewer');
    renderAt('/settings');
    expect(await screen.findByText('열람자 권한으로는 설정에 진입할 수 없습니다.')).toBeInTheDocument();
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
});
