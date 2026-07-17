import { act } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';
import { useCompanyStore } from '@/stores/companyStore';
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

function renderAt(path: string) {
  useCaseStore.getState().reset();
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

afterEach(() => {
  delete (window as { matchMedia?: unknown }).matchMedia;
  useRoleStore.getState().reset();
  useCompanyStore.getState().reset();
});

// 사장님(owner) PC 최소화면(4f) — "승인은 모바일에서".
describe('HomePage — owner PC 분기(4f)', () => {
  beforeEach(() => mockViewport(true));

  it('owner가 PC에서 홈에 오면 컨트롤 타워 대신 최소화면을 본다', () => {
    useRoleStore.getState().setRole('owner');
    renderAt('/');
    expect(screen.queryByLabelText('에이전트 파이프라인')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '이번 달 운영 리포트' })).toBeInTheDocument();
    expect(screen.getByText(/승인은 모바일 앱에서 처리해 주세요/)).toBeInTheDocument();
  });

  it('manager가 PC에서 홈에 오면 기존 컨트롤 타워를 그대로 본다', () => {
    renderAt('/');
    expect(screen.queryByRole('heading', { name: '이번 달 운영 리포트' })).not.toBeInTheDocument();
  });

  it('구성원 목록과 위임 설정 진입 버튼을 보여준다', () => {
    useRoleStore.getState().setRole('owner');
    renderAt('/');
    expect(screen.getByText('김담당')).toBeInTheDocument();
    expect(screen.getByText('이대표')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '위임 설정' }));
    expect(screen.getByRole('heading', { name: '위임 관리' })).toBeInTheDocument();
  });

  it('승인 대기 케이스가 있으면 건수와 함께 배너를 보여준다', () => {
    useRoleStore.getState().setRole('owner');
    renderAt('/');
    // 시드 로스터에는 승인 대기 케이스가 있다(nguyen/siti 등).
    expect(screen.getByText(/승인 대기 \d+건이 있습니다/)).toBeInTheDocument();
  });
});

// R1.8 DoD — "MONTHLY_REPORT 하드코딩 → 스토어 파생값".
describe('OwnerHomeWorkbench — 월간 리포트 파생(R1.8)', () => {
  beforeEach(() => mockViewport(true));
  afterEach(() => useEvidenceStore.getState().reset());

  it('완료·승인된 케이스가 없으면 처리한 케이스 0건으로 시작한다(픽스처 6인은 전부 미완료)', () => {
    useRoleStore.getState().setRole('owner');
    renderAt('/');
    const processedTile = screen.getByText('처리한 케이스').closest('div');
    expect(processedTile?.textContent).toContain('0건');
  });

  it('agent가 준비한 케이스를 승인 완료로 전이하면 처리한 케이스·사전 감지 수치에 반영된다', () => {
    useRoleStore.getState().setRole('owner');
    renderAt('/');

    // nguyen은 preparedBy:'agent' — human_approved로 전이하면 "처리 1건 · 사전 감지 1건(100%)".
    act(() => {
      useCaseStore.getState().transition('nguyen', 'human_approved');
    });

    const processedTile = screen.getByText('처리한 케이스').closest('div');
    expect(processedTile?.textContent).toContain('1건');

    const proactiveTile = screen.getByText('사전 감지').closest('div');
    expect(proactiveTile?.textContent).toContain('1건');
    expect(proactiveTile?.textContent).toContain('(100%)');
  });

  it('승인 없는 외부 발송은 evidence에 근거 없는 dispatch_executed가 없는 한 0건이다', () => {
    useRoleStore.getState().setRole('owner');
    renderAt('/');
    expect(screen.getByText(/승인 없는 외부 발송 0건/)).toBeInTheDocument();
  });
});
