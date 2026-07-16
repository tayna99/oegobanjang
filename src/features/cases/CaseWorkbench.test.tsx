import { act } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';

// jsdom에는 matchMedia가 없다 — useIsDesktop 분기 덕에 기존 모바일 테스트는
// 워크벤치를 전혀 만나지 않는다. 여기서는 데스크톱을 명시적으로 흉내낸다.
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
  useEvidenceStore.getState().reset();
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

afterEach(() => {
  // 다른 테스트 파일 환경을 오염시키지 않도록 원복.
  delete (window as { matchMedia?: unknown }).matchMedia;
  useRoleStore.getState().reset();
});

describe('CaseWorkbench (PC, M2.5.4 DoD)', () => {
  beforeEach(() => {
    mockViewport(true);
  });

  it('3열(목록 레일·상세·AI 레일)을 렌더하고 첫 케이스를 기본 선택한다', () => {
    renderAt('/cases');

    expect(screen.getByRole('region', { name: '케이스 워크벤치' })).toBeInTheDocument();
    const listRail = screen.getByRole('navigation', { name: '케이스 목록 레일' });
    const detail = screen.getByRole('region', { name: '케이스 상세' });
    const evidenceRail = screen.getByRole('complementary', { name: 'AI·근거 레일' });
    expect(listRail).toBeInTheDocument();
    expect(evidenceRail).toBeInTheDocument();

    // 자동 선택: 그룹·정렬 규칙(lib/cases)상 첫 케이스 = siti(승인 대기·HIGH·D-3).
    expect(
      within(detail).getByRole('heading', { name: '고용변동 신고 기한 임박' }),
    ).toBeInTheDocument();
    // CTA는 데이터 구동 라벨 그대로(카피 창작 금지) + 근거 있음 → 잠금 아님.
    expect(within(detail).getByRole('button', { name: '승인하기' })).toBeEnabled();
    // 진행 스테퍼의 현재 단계.
    expect(within(screen.getByRole('list', { name: '진행 단계' })).getByText('승인 대기')).toBeInTheDocument();
    // 고정 가드레일 문구 2종.
    expect(within(detail).getByText('승인 전에는 외부 발송이 차단됩니다.')).toBeInTheDocument();
    expect(within(evidenceRail).getByText('가능/불가능 판단은 제공하지 않습니다.')).toBeInTheDocument();
  });

  // PC 4a 델타(2026-07-13) — 목록 레일에 담당·서류 준비율을 노출한다.
  it('목록 행에 담당자와 서류 준비율 분수를 보여준다', () => {
    renderAt('/cases');
    const listRail = screen.getByRole('navigation', { name: '케이스 목록 레일' });
    expect(within(listRail).getByRole('button', { name: '체류기간 연장 서류 요청' })).toHaveTextContent('담당 김담당');
    expect(within(listRail).getByRole('button', { name: '계약 만료 사전 모니터링' })).toHaveTextContent('담당 —');
  });

  it('목록 행 클릭이 URL(/case/:caseId)과 상세 패널을 동기화한다', async () => {
    const router = renderAt('/cases');
    const listRail = screen.getByRole('navigation', { name: '케이스 목록 레일' });

    fireEvent.click(within(listRail).getByRole('button', { name: /체류기간 만료 경과/ }));

    // /case/:caseId loader가 비동기라 router state보다 DOM 커밋이 늦을 수 있다 — DOM 기준으로 대기.
    // 전체 스위트 병렬 부하에서 기본 1초가 모자랄 수 있어 여유를 준다.
    await screen.findByRole('heading', { name: '체류기간 만료 경과 · 행정사 검토' });
    expect(router.state.location.pathname).toBe('/case/batbayar');
    const detail = screen.getByRole('region', { name: '케이스 상세' });
    // bayar 가드노트가 상세에 노출된다.
    expect(within(detail).getByText(/행정사 검토로만 진행됩니다/)).toBeInTheDocument();
  });

  it('필터 컨텍스트가 행 클릭 후에도 목록 레일에 유지된다', async () => {
    const router = renderAt('/cases?filter=approval');
    const listRail = screen.getByRole('navigation', { name: '케이스 목록 레일' });

    fireEvent.click(within(listRail).getByRole('button', { name: /체류기간 연장 서류 요청/ }));
    await screen.findByRole('heading', { name: '체류기간 연장 서류 요청' });
    await waitFor(() => expect(router.state.location.pathname).toBe('/case/nguyen'));

    const railAfter = screen.getByRole('navigation', { name: '케이스 목록 레일' });
    expect(within(railAfter).getByRole('button', { name: /^승인 대기 \d/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    // 승인 대기 프리셋: siti·nguyen만 남는다(6인 로스터).
    expect(within(railAfter).queryByRole('button', { name: /계약-체류 만료일 불일치/ })).not.toBeInTheDocument();
  });

  it('딥링크 /case/:caseId가 해당 케이스를 선택 상태로 연다', async () => {
    renderAt('/case/tranCase');
    // /case/:caseId 라우트는 loader(validateIdParam)가 있어 첫 렌더가 비동기다.
    const detail = await screen.findByRole('region', { name: '케이스 상세' });
    expect(
      within(detail).getByRole('heading', { name: '계약-체류 만료일 불일치 검토' }),
    ).toBeInTheDocument();
  });

  // 3.3 케이스 에이전트 활동 타임라인(런 체이닝)+nextWake.
  it('케이스 타임라인이 런 체인(#4788→#4712)과 nextWake를 렌더한다', async () => {
    renderAt('/case/nguyen');
    await screen.findByRole('region', { name: '케이스 상세' });
    const timeline = screen.getByRole('region', { name: '케이스 타임라인' });

    // 체인 렌더: 자동 실행 → 이전 승인 발송, 두 런이 시간 역순으로 모두 보인다.
    expect(within(timeline).getByText('#4788')).toBeInTheDocument();
    expect(within(timeline).getByText('#4712')).toBeInTheDocument();
    expect(within(timeline).getByText('서류요청 준비 · D-30 감지로 자동 실행 — 초안 생성 후 승인 대기')).toBeInTheDocument();
    // nextWake 조건 문구.
    expect(within(timeline).getByText('다음: 발송 후 2일간 응답 없으면 리마인드 여부를 판단합니다')).toBeInTheDocument();
  });

  // NEXT_ROADMAP D-3 회귀: CASE_SHEETS 정적 activity만 읽던 케이스 타임라인이 이제
  // evidenceStore(행정사 회신·해석 확인)를 실시간으로 병합해 보여준다.
  it('행정사 회신(package_reply) evidence가 케이스 타임라인에 정적 이력보다 먼저 실시간으로 나타난다', async () => {
    renderAt('/case/batbayar');
    await screen.findByRole('region', { name: '케이스 상세' });
    const timeline = screen.getByRole('region', { name: '케이스 타임라인' });

    // 진입 시점: 정적 activity(위험 감지)만 있고 행정사 회신은 없다.
    expect(within(timeline).queryByText(/행정사 회신/)).not.toBeInTheDocument();
    expect(within(timeline).getByText(/위험 감지 · CRITICAL/)).toBeInTheDocument();

    act(() => {
      useEvidenceStore.getState().append({
        id: 'batbayar-package-reply-1',
        type: 'package_reply',
        at: new Date().toISOString(),
        caseId: 'batbayar',
        summary: '김앤리 행정사무소 회신 · 보완 요청 · 재직증명서 원본이 추가로 필요합니다',
        actor: '김앤리 행정사무소',
      });
    });

    // 리렌더 없이도(zustand 구독) 즉시 타임라인 최상단에 반영된다 — 정적 activity(위험 감지)
    // 앞에 붙는다(D-6 미해결이라 실시각 비교는 하지 않고, 항상 최신 취급).
    const entries = within(timeline).getAllByRole('listitem');
    expect(entries[0]).toHaveTextContent(
      '행정사 회신 · 김앤리 행정사무소 회신 · 보완 요청 · 재직증명서 원본이 추가로 필요합니다',
    );
    expect(entries[1]).toHaveTextContent('위험 감지 · CRITICAL');
  });

  it('타임라인의 판단 기록 #을 누르면 재생 런(/run/:id)으로 진입한다', async () => {
    const router = renderAt('/case/nguyen');
    await screen.findByRole('region', { name: '케이스 상세' });
    const timeline = screen.getByRole('region', { name: '케이스 타임라인' });

    fireEvent.click(within(timeline).getByRole('button', { name: '판단 기록 #4788 재생 열기' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/run/4788'));
  });

  it('검색어가 목록 레일을 제목·근로자명 기준으로 거른다', () => {
    renderAt('/cases');
    fireEvent.change(screen.getByRole('searchbox', { name: '케이스 검색' }), {
      target: { value: '존재하지않는검색어' },
    });
    const listRail = screen.getByRole('navigation', { name: '케이스 목록 레일' });
    expect(within(listRail).getByText('조건에 맞는 케이스가 없습니다')).toBeInTheDocument();

    // 근로자명 매칭("이름, 케이스 검색" — §3b placeholder): 제목엔 없는 이름으로도 찾는다.
    fireEvent.change(screen.getByRole('searchbox', { name: '케이스 검색' }), {
      target: { value: 'Nguyen' },
    });
    expect(within(listRail).getByRole('button', { name: /체류기간 연장 서류 요청/ })).toBeInTheDocument();
  });

  // M2 ActionBar 역할 분기(7단계 §6, 운영급 RBAC 확장).
  it('owner는 승인하기(primary)만 보고 상세 보기(secondary)는 숨는다', () => {
    useRoleStore.getState().setRole('owner');
    renderAt('/cases');
    const detail = screen.getByRole('region', { name: '케이스 상세' });
    expect(within(detail).getByRole('button', { name: '승인하기' })).toBeInTheDocument();
    expect(within(detail).queryByRole('button', { name: '상세 보기' })).not.toBeInTheDocument();
  });

  it('viewer는 승인하기·상세 보기 버튼이 전부 없다', () => {
    useRoleStore.getState().setRole('viewer');
    renderAt('/cases');
    const detail = screen.getByRole('region', { name: '케이스 상세' });
    expect(within(detail).queryByRole('button', { name: '승인하기' })).not.toBeInTheDocument();
    expect(within(detail).queryByRole('button', { name: '상세 보기' })).not.toBeInTheDocument();
  });
});

describe('CaseWorkbench 모바일 게이트 (모바일 회귀 없음)', () => {
  it('비데스크톱에서는 워크벤치가 마운트되지 않고 기존 모바일 목록이 렌더된다', () => {
    mockViewport(false);
    renderAt('/cases');

    expect(screen.queryByRole('region', { name: '케이스 워크벤치' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '케이스' })).toBeInTheDocument();
  });
});
