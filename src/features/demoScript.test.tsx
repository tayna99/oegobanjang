import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { RUN_CONFIGS } from '@/mocks/runs';
import { useApprovalStore } from '@/stores/approvalStore';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';

// 3.4 데모 폴리시 — reference/specs/8단계_데모시나리오_v1.md의 4막 대본이 코드에서 그대로
// 시연 가능한지 스모크로 고정한다. 승인 깔때기(3막) 자체의 깊은 검증은 approvalFlow.test가
// 담당하므로, 여기서는 4막 각 비트가 "도달·렌더 가능"한지와 데모 정책(가드레일 비은폐)만 본다.
// 데모는 모바일 퍼스트라 matchMedia를 목업하지 않는다(useIsDesktop=false → 모바일 화면).
describe('데모 스모크 — 8단계 4막 대본', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
    useApprovalStore.getState().reset();
    useEvidenceStore.getState().reset();
  });

  // 1막. 알림이 먼저 온다 — 딥링크로 M1 브리핑(승인 큐 중심)에 진입한다.
  it('1막: 홈 진입 시 승인 큐 브리핑이 열린다', async () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/'] });
    render(<RouterProvider router={router} />);

    await screen.findByText(/내가 처리할 승인 \d건/);
    expect(screen.getByRole('region', { name: '승인 큐' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: '에이전트 진행 중' })).toBeInTheDocument();
  });

  // 2막. 브리핑 → 프로액티브 런 재생 → 케이스 → 초안.
  it('2막: 프로액티브 재생은 읽기 전용·가드레일 정지를 보여주고, 케이스에 VN/KR 초안이 있다', async () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/run/4788'] });
    render(<RouterProvider router={router} />);

    await screen.findByText('서류요청 준비 (재생)');
    // 재생 뷰는 읽기 전용(승인 버튼 없음) + 발송 직전 가드레일 정지 스텝.
    expect(screen.queryByRole('button', { name: '승인' })).not.toBeInTheDocument();
    await screen.findByText('발송 전 정지 · 승인 요청 생성');

    // 케이스 상세 → 근로자에겐 베트남어, 담당자에겐 한국어 토글.
    router.navigate('/case/nguyen');
    await screen.findByRole('heading', { name: '사례 검토' });
    expect(screen.getByText(/Xin chào Nguyen/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '한국어' }));
    expect(screen.getByText(/안녕하세요 Nguyen 씨/)).toBeInTheDocument();
  });

  // 3막. 승인 — 근거 게이트·성급한 승인 방지 문구가 시연 상태로 살아있다(깊은 검증은 approvalFlow.test).
  it('3막: 승인 화면은 발송 차단 문구와 체크리스트 게이트를 갖춘다', async () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/case/nguyen/approve'] });
    render(<RouterProvider router={router} />);

    await screen.findByRole('heading', { name: '최종 승인' });
    expect(screen.getByText('승인 전에는 외부 발송이 차단됩니다.')).toBeInTheDocument();
    // 체크리스트 미완 시 승인 불가 → 4/4 후 활성.
    expect(screen.getByRole('button', { name: '승인하기' })).toBeDisabled();
    for (const box of screen.getAllByRole('checkbox')) fireEvent.click(box);
    expect(screen.getByRole('button', { name: '승인하기' })).toBeEnabled();
  });

  // 4막. 커맨드 바 → 에이전트 런 진입. (런의 가드레일 스트리밍·결과 카드→케이스 연결은
  // RunPage.test가 가짜 타이머로 결정적으로 검증하므로, 스모크는 진입까지만 확인해
  // 실시간 스트리밍 대기로 스위트 부하를 키우지 않는다.)
  it('4막: 커맨드 바 제출 → 커맨드 런(#4797)에 진입한다', async () => {
    const router = createMemoryRouter(routeConfig, { initialEntries: ['/'] });
    render(<RouterProvider router={router} />);
    await screen.findByText(/내가 처리할 승인 \d건/);

    // 자연어로 부리기 — MVP는 파싱 없이 항상 커맨드 데모 런(#4797)으로 진입.
    fireEvent.change(screen.getByPlaceholderText('AI에게 요청하기'), {
      target: { value: '이번 달 급한 직원만 정리해줘' },
    });
    fireEvent.click(screen.getByRole('button', { name: '전송' }));

    await screen.findByText('이번 달 급한 직원 정리');
    await waitFor(() => expect(router.state.location.pathname).toBe('/run/4797'));
  });

  // 데모 정책(8단계 §2 line 88): 가드레일이 작동한 것도 숨기지 않고 단계로 보여준다 —
  // 프로액티브 재생·커맨드 런 두 데모 런 모두 guardrail 스텝을 구조적으로 갖는다.
  it('데모 정책: 프로액티브·커맨드 데모 런 모두 가드레일 스텝을 노출한다', () => {
    const replay = RUN_CONFIGS.find((config) => config.runKey === '4788');
    const command = RUN_CONFIGS.find((config) => config.runKey === '4797');
    expect(replay?.steps.some((step) => step.kind === 'guardrail')).toBe(true);
    expect(command?.steps.some((step) => step.kind === 'guardrail')).toBe(true);
  });
});
