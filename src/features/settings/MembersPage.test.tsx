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

// 구성원 관리 — 7단계 §2 매트릭스(구성원 초대/역할변경: owner CU, manager 초대만).
describe('MembersPage', () => {
  afterEach(() => {
    useRoleStore.getState().reset();
    useCompanyStore.getState().reset();
    useEvidenceStore.getState().reset();
  });

  it('viewer는 구성원 관리에 진입할 수 없다', async () => {
    useRoleStore.getState().setRole('viewer');
    renderAt('/settings/members');
    expect(await screen.findByText('열람자 권한으로는 구성원 관리에 진입할 수 없습니다.')).toBeInTheDocument();
  });

  it('manager는 기존 구성원 목록을 보지만 역할 변경·제거 버튼은 없다', async () => {
    renderAt('/settings/members');
    expect(await screen.findByText('김담당')).toBeInTheDocument();
    expect(screen.getByText('김대표')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /역할 변경/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /제거/ })).not.toBeInTheDocument();
  });

  it('manager도 초대는 할 수 있고, 초대 시 구성원 목록에 반영되고 evidence가 남는다', async () => {
    renderAt('/settings/members');
    await screen.findByText('김담당');

    fireEvent.change(screen.getByRole('textbox', { name: '초대할 구성원 이름' }), {
      target: { value: '박신입' },
    });
    fireEvent.click(screen.getByRole('button', { name: '담당자' }));
    fireEvent.click(screen.getByRole('button', { name: '초대' }));

    expect(screen.getByText('박신입')).toBeInTheDocument();
    expect(useCompanyStore.getState().members.some((m) => m.name === '박신입' && m.role === 'manager')).toBe(true);
    const types = useEvidenceStore.getState().events.map((e) => e.type);
    expect(types).toContain('member_invited');
    expect(types).toContain('role_granted');
  });

  it('owner는 역할 변경·제거 버튼을 보고 사용할 수 있다', async () => {
    useRoleStore.getState().setRole('owner');
    renderAt('/settings/members');
    await screen.findByText('최감사');

    fireEvent.click(screen.getByRole('button', { name: '최감사 역할 변경' }));
    expect(useCompanyStore.getState().members.find((m) => m.name === '최감사')?.role).toBe('manager');

    fireEvent.click(screen.getByRole('button', { name: '최감사 제거' }));
    expect(useCompanyStore.getState().members.some((m) => m.name === '최감사')).toBe(false);
  });
});
