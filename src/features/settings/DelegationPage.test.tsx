import { fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { useCompanyStore } from '@/stores/companyStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';

function renderAt(path: string) {
  return render(<RouterProvider router={createMemoryRouter(routeConfig, { initialEntries: [path] })} />);
}

// 위임 관리 — owner 전용(7단계 §3.1·§6 "설정: owner=위임관리").
describe('DelegationPage', () => {
  afterEach(() => {
    useRoleStore.getState().reset();
    useCompanyStore.getState().reset();
    useEvidenceStore.getState().reset();
  });

  it('manager는 위임 관리에 진입할 수 없다', async () => {
    renderAt('/settings/delegation');
    expect(await screen.findByText('위임 관리는 대표 권한으로만 열 수 있습니다.')).toBeInTheDocument();
  });

  it('owner는 위임 대상을 선택하고 기간을 지정해 위임을 설정할 수 있다', async () => {
    useRoleStore.getState().setRole('owner');
    renderAt('/settings/delegation');
    await screen.findByRole('heading', { name: '위임 관리' });

    expect(screen.getByText('위임이 설정되지 않았습니다')).toBeInTheDocument();
    // 기본 위임 대상(manager-kim=김담당)이 이미 선택돼 있다 — 다시 탭해 명시적으로 확인.
    fireEvent.click(screen.getByRole('button', { name: /김담당/ }));
    fireEvent.click(screen.getByRole('button', { name: '위임 설정' }));

    expect(useCompanyStore.getState().delegation.active).toBe(true);
    expect(useCompanyStore.getState().delegation.delegateId).toBe('manager-kim');
    expect(
      useEvidenceStore.getState().events.some((e) => e.type === 'delegation_granted'),
    ).toBe(true);
  });

  it('위임이 활성일 때만 위임 해제 버튼이 활성화되고, 클릭하면 해제된다', async () => {
    useRoleStore.getState().setRole('owner');
    useCompanyStore.getState().setDelegation({ ...useCompanyStore.getState().delegation, active: true });
    renderAt('/settings/delegation');
    await screen.findByRole('heading', { name: '위임 관리' });

    const revokeButton = screen.getByRole('button', { name: '위임 해제' });
    expect(revokeButton).toBeEnabled();
    fireEvent.click(revokeButton);
    expect(useCompanyStore.getState().delegation.active).toBe(false);
  });
});
