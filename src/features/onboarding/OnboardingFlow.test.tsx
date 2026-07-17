import { act } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';
import { useCompanyStore } from '@/stores/companyStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';

// 4.1 DoD — "E2E: 근로자 1명 등록→첫 카드 도달". O1~O4를 순서대로 통과해 O5 로딩(각본
// 기반 2700ms)까지 지나면 nguyen 케이스가 caseStore에 반영되고 첫 브리핑 카드가 보인다.
describe('OnboardingFlow — O1~O5 E2E', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
    useCompanyStore.getState().reset();
    useEvidenceStore.getState().reset();
    useRoleStore.getState().reset();
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('전화인증→역할선택→사업장정보→첫근로자등록→브리핑 생성까지 통과하면 nguyen 케이스가 등록된다', () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/onboarding'] });
    render(<RouterProvider router={router} />);

    // O1 — 인증번호 받기 → 6자리 입력 전엔 다음 비활성.
    expect(screen.getByRole('heading', { name: '시작하기' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '다음' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: '인증번호 받기' }));
    fireEvent.change(screen.getByRole('textbox', { name: '인증번호 6자리' }), { target: { value: '123456' } });
    expect(screen.getByRole('button', { name: '다음' })).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: '다음' }));

    // O2 — 역할 선택 전엔 다음 비활성, 담당자 선택 후 진행하면 roleStore에 반영된다.
    expect(screen.getByRole('heading', { name: '어떤 역할로 시작하시나요?' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '다음' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: /^담당자/ }));
    fireEvent.click(screen.getByRole('button', { name: '다음' }));
    expect(useRoleStore.getState().role).toBe('manager');

    // O3 — 4필드 사전 채움, 그대로 다음.
    expect(screen.getByRole('heading', { name: '사업장 정보' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '다음' }));

    // O4 — 기본 경로(직접 입력)로 첫 근로자 등록.
    expect(screen.getByRole('heading', { name: '첫 근로자를 등록하세요' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '등록하고 브리핑 만들기' }));

    // O5 로딩(각본 2700ms) → 완료.
    act(() => {
      vi.advanceTimersByTime(2700);
    });

    expect(screen.getByRole('heading', { name: '첫 브리핑이 준비됐어요' })).toBeInTheDocument();
    expect(screen.getByText('체류기간 연장 서류 요청')).toBeInTheDocument();
    expect(useCaseStore.getState().cases.nguyen).toBeDefined();
    expect(useEvidenceStore.getState().events.some((e) => e.type === 'plan_created')).toBe(true);

    // 완료 CTA로 홈(브리핑)에 도달 — 승인 큐에 방금 등록된 근로자 케이스가 보인다.
    fireEvent.click(screen.getByRole('button', { name: '오늘 브리핑 보기' }));
    expect(router.state.location.pathname).toBe('/');
  });

  // R1.1 — O3 입력이 더 이상 버려지지 않고 companyStore.profile에 실제로 반영된다.
  it('O3 사업장명을 바꾸면 회사 프로필에 반영된다', () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/onboarding'] });
    render(<RouterProvider router={router} />);

    fireEvent.click(screen.getByRole('button', { name: '인증번호 받기' }));
    fireEvent.change(screen.getByRole('textbox', { name: '인증번호 6자리' }), { target: { value: '123456' } });
    fireEvent.click(screen.getByRole('button', { name: '다음' }));

    fireEvent.click(screen.getByRole('button', { name: /^담당자/ }));
    fireEvent.click(screen.getByRole('button', { name: '다음' }));

    fireEvent.change(screen.getByRole('textbox', { name: '사업장명' }), { target: { value: '테스트 물류' } });
    fireEvent.click(screen.getByRole('button', { name: '다음' }));
    fireEvent.click(screen.getByRole('button', { name: '등록하고 브리핑 만들기' }));

    act(() => {
      vi.advanceTimersByTime(2700);
    });

    expect(useCompanyStore.getState().profile.name).toBe('테스트 물류');
  });

  it('O2에서 대표를 선택하면 owner로 진행된다', () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/onboarding'] });
    render(<RouterProvider router={router} />);

    fireEvent.click(screen.getByRole('button', { name: '인증번호 받기' }));
    fireEvent.change(screen.getByRole('textbox', { name: '인증번호 6자리' }), { target: { value: '999999' } });
    fireEvent.click(screen.getByRole('button', { name: '다음' }));

    fireEvent.click(screen.getByRole('button', { name: /^대표/ }));
    fireEvent.click(screen.getByRole('button', { name: '다음' }));
    expect(useRoleStore.getState().role).toBe('owner');
  });
});
