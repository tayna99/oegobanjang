import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { DEMO_PIN } from '@/lib/pin';
import { useApprovalStore } from '@/stores/approvalStore';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';

// 4.3 승인 본인확인 PIN 목업 + 대리 승인 배지 — DoD "승인 이벤트에 결정자·본인/대리 기록".
// approvalFlow.test.tsx는 깔때기 자체(체크리스트 게이트·상태 전이)를 검증하므로, 여기서는
// PIN 게이트의 형식/불일치 분기와 본인/대리 액터 표기만 다룬다.
describe('4.3 승인 PIN + 대리 승인', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
    useApprovalStore.getState().reset();
    useEvidenceStore.getState().reset();
    useRoleStore.getState().reset();
  });

  function checkAllChecklist() {
    for (const box of within(screen.getByRole('list')).getAllByRole('checkbox')) {
      fireEvent.click(box);
    }
  }

  it('PIN 형식이 잘못되면 에러를 보여주고 승인은 진행되지 않는다', async () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] });
    render(<RouterProvider router={router} />);
    await screen.findByRole('heading', { name: '최종 승인' });
    checkAllChecklist();

    fireEvent.click(screen.getByRole('button', { name: '승인하기' }));
    await screen.findByText('본인확인 PIN');
    fireEvent.change(screen.getByRole('textbox', { name: '본인확인 PIN' }), { target: { value: '12a' } });
    fireEvent.click(screen.getByRole('button', { name: '확인' }));

    expect(screen.getByText('숫자 4자리를 입력하세요.')).toBeInTheDocument();
    expect(useCaseStore.getState().cases.nguyen.state).toBe('approval_pending');
  });

  it('PIN이 일치하지 않으면 재시도할 수 있고, 맞는 PIN을 넣으면 승인이 완료된다', async () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] });
    render(<RouterProvider router={router} />);
    await screen.findByRole('heading', { name: '최종 승인' });
    checkAllChecklist();

    fireEvent.click(screen.getByRole('button', { name: '승인하기' }));
    await screen.findByText('본인확인 PIN');
    fireEvent.change(screen.getByRole('textbox', { name: '본인확인 PIN' }), { target: { value: '9999' } });
    fireEvent.click(screen.getByRole('button', { name: '확인' }));
    expect(screen.getByText('PIN이 일치하지 않습니다. 다시 입력해주세요.')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('textbox', { name: '본인확인 PIN' }), { target: { value: DEMO_PIN } });
    fireEvent.click(screen.getByRole('button', { name: '확인' }));

    await screen.findByRole('heading', { name: '승인 이력' });
    expect(router.state.location.pathname).toBe('/case/nguyen/history');
  });

  it('대리 승인 체크박스를 체크하면 이력에 위임 배지가 기록된다', async () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] });
    render(<RouterProvider router={router} />);
    await screen.findByRole('heading', { name: '최종 승인' });
    checkAllChecklist();

    fireEvent.click(screen.getByRole('checkbox', { name: /대리 승인으로 처리/ }));
    fireEvent.click(screen.getByRole('button', { name: '승인하기' }));
    await screen.findByText('본인확인 PIN');
    fireEvent.change(screen.getByRole('textbox', { name: '본인확인 PIN' }), { target: { value: DEMO_PIN } });
    fireEvent.click(screen.getByRole('button', { name: '확인' }));

    await screen.findByRole('heading', { name: '승인 이력' });
    // 운영급 RBAC 확장(7단계 §5 "누가(역할)") — actor에 역할 라벨이 접두된다.
    expect(screen.getByText('담당자 김담당 (대리 승인 · 위임: 김대표)')).toBeInTheDocument();

    await waitFor(() =>
      expect(
        useEvidenceStore
          .getState()
          .events.find((e) => e.type === 'approval_decided' && e.caseId === 'nguyen')?.actor,
      ).toBe('담당자 김담당 (대리 승인 · 위임: 김대표)'),
    );
  });

  it('owner 역할로 승인하면 대리 체크박스가 없고 본인 확인 완료로 기록된다', async () => {
    useRoleStore.getState().setRole('owner');
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] });
    render(<RouterProvider router={router} />);
    await screen.findByRole('heading', { name: '최종 승인' });

    expect(screen.queryByRole('checkbox', { name: /대리 승인으로 처리/ })).not.toBeInTheDocument();

    checkAllChecklist();
    fireEvent.click(screen.getByRole('button', { name: '승인하기' }));
    await screen.findByText('본인확인 PIN');
    fireEvent.change(screen.getByRole('textbox', { name: '본인확인 PIN' }), { target: { value: DEMO_PIN } });
    fireEvent.click(screen.getByRole('button', { name: '확인' }));

    await screen.findByRole('heading', { name: '승인 이력' });
    expect(screen.getByText('대표 김대표 (본인 확인 완료)')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/case/nguyen/history');
  });

  it('PIN 시트를 닫았다가 다시 열면 이전 입력·에러가 남지 않는다', async () => {
    render(
      <RouterProvider
        router={createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] })}
      />,
    );
    await screen.findByRole('heading', { name: '최종 승인' });
    checkAllChecklist();

    fireEvent.click(screen.getByRole('button', { name: '승인하기' }));
    await screen.findByText('본인확인 PIN');
    fireEvent.change(screen.getByRole('textbox', { name: '본인확인 PIN' }), { target: { value: '9999' } });
    fireEvent.click(screen.getByRole('button', { name: '확인' }));
    expect(screen.getByText('PIN이 일치하지 않습니다. 다시 입력해주세요.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '시트 닫기' }));
    fireEvent.click(screen.getByRole('button', { name: '승인하기' }));
    await screen.findByText('본인확인 PIN');
    expect(screen.queryByText('PIN이 일치하지 않습니다. 다시 입력해주세요.')).not.toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: '본인확인 PIN' })).toHaveValue('');
  });
});
