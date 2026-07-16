import { act } from 'react';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { BriefingHomePage } from './BriefingHomePage';
import { useCaseStore } from '@/stores/caseStore';
import { useRoleStore } from '@/stores/roleStore';
import { useThreadStore } from '@/stores/threadStore';
import { CASE_CARDS } from '@/mocks/fixtures';

describe('BriefingHomePage', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
    useThreadStore.getState().reset();
  });
  afterEach(() => useRoleStore.getState().reset());

  it('caseStore가 비어 있으면 CASE_CARDS로 시드하고 렌더한다', () => {
    render(
      <MemoryRouter>
        <BriefingHomePage />
      </MemoryRouter>,
    );
    expect(Object.keys(useCaseStore.getState().cases)).toHaveLength(CASE_CARDS.length);
    expect(screen.getByText('체류기간 연장 서류 요청')).toBeInTheDocument();
  });

  it('이미 caseStore에 데이터가 있으면 다시 시드하지 않는다', () => {
    useCaseStore.getState().upsert({ ...CASE_CARDS[0], title: '수정된 제목' });
    render(
      <MemoryRouter>
        <BriefingHomePage />
      </MemoryRouter>,
    );
    expect(screen.queryByText('수정된 제목')).toBeInTheDocument();
  });

  // 4.2 역할 분기 — owner 홈은 승인 필요 카드만(visibleCardsForRole, lib/briefing.ts 기존 로직).
  it('owner 역할이면 승인 필요 카드만 보인다', () => {
    useRoleStore.getState().setRole('owner');
    render(
      <MemoryRouter>
        <BriefingHomePage />
      </MemoryRouter>,
    );
    // nguyen(approvalRequired: true)은 보이고, tranCase(approvalRequired: false)는 숨는다.
    expect(screen.getByText('체류기간 연장 서류 요청')).toBeInTheDocument();
    expect(screen.queryByText('계약-체류 만료일 불일치 검토')).not.toBeInTheDocument();
  });

  it('threadStore의 pending_review(응답 도착) 스레드 수가 통계에 실계산으로 반영된다', () => {
    render(
      <MemoryRouter>
        <BriefingHomePage />
      </MemoryRouter>,
    );
    // mocks/threads.ts THREADS 시드 기준 pending_review는 'tran' 1건뿐이다.
    const stat = screen.getByRole('button', { name: /응답 도착/ });
    expect(within(stat).getByText('1')).toBeInTheDocument();
  });

  it('Tran 응답 해석을 확인 처리하면 응답 도착 통계 숫자가 줄어든다', () => {
    render(
      <MemoryRouter>
        <BriefingHomePage />
      </MemoryRouter>,
    );
    act(() => {
      const tran = useThreadStore.getState().threads['tran'];
      const updateIds = tran.interpretation?.updates.map((u) => u.updateId) ?? [];
      useThreadStore.getState().confirmInterpretation('tran', updateIds);
    });
    const stat = screen.getByRole('button', { name: /응답 도착/ });
    expect(within(stat).getByText('0')).toBeInTheDocument();
  });

  it('owner 역할이면 응답 도착 통계도 숨겨진다(통계 숨김 규칙과 동일)', () => {
    useRoleStore.getState().setRole('owner');
    render(
      <MemoryRouter>
        <BriefingHomePage />
      </MemoryRouter>,
    );
    expect(screen.queryByRole('button', { name: /응답 도착/ })).not.toBeInTheDocument();
  });
});
