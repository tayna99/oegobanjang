import { act } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { routeConfig } from '@/router';
import { DISPATCH_CATALOG } from '@/mocks/dispatch';
import { useApprovalStore } from '@/stores/approvalStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';

function mockViewport(desktop: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: desktop,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

// R1.4 — 큐가 approvalStore에서 파생되므로, 렌더 전에 카탈로그 항목의 실제 승인 액션을
// 승인 완료 상태로 만들어 둔다(이전 버전의 자동 선승인 useEffect를 테스트 쪽에서 대체).
function approveAll(actionIds: string[] = DISPATCH_CATALOG.map((e) => e.actionId)) {
  for (const actionId of actionIds) {
    useApprovalStore.getState().requestApproval(actionId);
    useApprovalStore.getState().decide(actionId, 'approved', `${actionId}:test:approved`);
  }
}

function renderAt(path: string) {
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

afterEach(() => {
  delete (window as { matchMedia?: unknown }).matchMedia;
  useRoleStore.getState().reset();
});

describe('DispatchQueuePage (PC 4d)', () => {
  beforeEach(() => {
    mockViewport(true);
    useEvidenceStore.getState().reset();
    useApprovalStore.getState().reset();
  });

  it('승인 완료된 항목만 실행 대기 큐에 나타나고, 오늘 실행 이력을 함께 보여준다', () => {
    approveAll();
    renderAt('/cases/dispatch');
    expect(screen.getByRole('heading', { name: '발송 실행' })).toBeInTheDocument();
    expect(screen.getByText(`실행 대기 ${DISPATCH_CATALOG.length}건 · 오늘 실행 2건`)).toBeInTheDocument();
    expect(screen.getByText('서류요청 메시지 발송 (VN)')).toBeInTheDocument();
    expect(screen.getByText('실행 완료 · 응답 수신')).toBeInTheDocument();
  });

  // R1.4 핵심 — "승인=상태 전이, 실행=담당자 확인" 분리가 이 화면에서 실제로 강제된다.
  // approvalStore가 승인되지 않았다고 보는 항목은 애초에 화면에 도착하지 않는다.
  it('승인되지 않은 항목은 큐에 나타나지 않는다', () => {
    approveAll(['nguyen-approve', 'siti-approve']); // batbayar-handoff-export는 미승인 상태로 남긴다
    renderAt('/cases/dispatch');
    expect(screen.getByText(`실행 대기 2건 · 오늘 실행 2건`)).toBeInTheDocument();
    expect(screen.queryByText('행정사 검토 패키지 전달')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '링크 발급' })).not.toBeInTheDocument();
  });

  it('발송 실행(mock)을 누르면 evidence(dispatch_executed)가 남고 큐에서 사라진다', () => {
    approveAll();
    renderAt('/cases/dispatch');
    const executeButtons = screen.getAllByRole('button', { name: '발송 실행 (mock)' });
    fireEvent.click(executeButtons[0]);

    expect(
      useEvidenceStore.getState().events.some((e) => e.type === 'dispatch_executed' && e.caseId === 'nguyen'),
    ).toBe(true);
    expect(screen.getByText(`실행 대기 ${DISPATCH_CATALOG.length - 1}건 · 오늘 실행 2건`)).toBeInTheDocument();
  });

  // 큐가 approvalStore를 직접 구독해 파생되므로, 승인이 취소되면(예: 다른 화면에서 반려)
  // 다음 렌더에서 즉시 대기 목록에서 빠진다 — 화면이 자체 상태로 "한번 도착한 항목"을
  // 붙들고 있지 않는다.
  it('실행 대기 중 승인 상태가 바뀌면 파생 큐에서 즉시 사라진다', () => {
    approveAll();
    renderAt('/cases/dispatch');
    expect(screen.getByText('서류요청 메시지 발송 (VN)')).toBeInTheDocument();

    act(() => {
      useApprovalStore.setState((s) => ({
        approvals: { ...s.approvals, 'nguyen-approve': { ...s.approvals['nguyen-approve'], status: 'pending' } },
      }));
    });

    expect(screen.queryByText('서류요청 메시지 발송 (VN)')).not.toBeInTheDocument();
  });

  it('행정사 패키지 전달 항목은 "링크 발급" 버튼을 보여준다', () => {
    approveAll();
    renderAt('/cases/dispatch');
    expect(screen.getByRole('button', { name: '링크 발급' })).toBeInTheDocument();
  });

  it('열람자·대표 권한으로는 안내 문구만 보인다', () => {
    useRoleStore.getState().setRole('viewer');
    renderAt('/cases/dispatch');
    expect(screen.getByText('발송 실행 큐는 담당자 권한으로만 이용할 수 있습니다.')).toBeInTheDocument();
  });

  it('비데스크톱에서는 PC 유도 안내만 보인다', () => {
    mockViewport(false);
    renderAt('/cases/dispatch');
    expect(screen.getByText('발송 실행 큐는 PC에서 이용해 주세요')).toBeInTheDocument();
  });
});
