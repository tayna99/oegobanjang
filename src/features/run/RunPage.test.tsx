import { act } from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RunPage } from './RunPage';

// M2.6.3부터 /case/:caseId/approve는 ApprovePage(체크리스트)가 담당한다 —
// RunPage는 /run/:runId(재생·명령)만 서빙하므로 caseId 승인 분기 테스트는 제거하고
// 승인 깔때기는 approvalFlow.test.tsx가 검증한다.
describe('RunPage', () => {
  it('/run/:runId(command)로 진입하면 runKey가 일치하는 RunConfig를 렌더한다', async () => {
    render(
      <MemoryRouter initialEntries={['/run/4797']}>
        <Routes>
          <Route path="/run/:runId" element={<RunPage />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText('이번 달 급한 직원 정리')).toBeInTheDocument();
  });

  it('/run/:runId(replay)로 진입하면 즉시 전체 스텝이 렌더되고 승인 버튼이 없다', async () => {
    render(
      <MemoryRouter initialEntries={['/run/4788']}>
        <Routes>
          <Route path="/run/:runId" element={<RunPage />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText('서류요청 준비 (재생)')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '승인' })).not.toBeInTheDocument();
  });

  // 3.1: 프로액티브 런 재생 뷰는 발송 직전 가드레일 정지 스텝을 노출한다("신뢰 자산").
  it('/run/4788(프로액티브 재생)은 가드레일 정지 스텝을 노출한다', async () => {
    render(
      <MemoryRouter initialEntries={['/run/4788']}>
        <Routes>
          <Route path="/run/:runId" element={<RunPage />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText('발송 전 정지 · 승인 요청 생성')).toBeInTheDocument();
    // 가드레일 스텝은 kind 칩('가드레일')으로 다른 스텝과 시각 구분된다.
    expect(screen.getByText('가드레일')).toBeInTheDocument();
  });

  it('일치하는 RunConfig가 없으면 loading 상태를 보여준다', () => {
    render(
      <MemoryRouter initialEntries={['/run/nope']}>
        <Routes>
          <Route path="/run/:runId" element={<RunPage />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText('분석 중…')).toBeInTheDocument();
  });

  describe('명령 런 스트리밍 게이트', () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it('/run/:runId(command) 스트리밍 중에는 승인 버튼이 disabled이고 완료 후 enabled로 바뀐다', async () => {
      render(
        <MemoryRouter initialEntries={['/run/4797']}>
          <Routes>
            <Route path="/run/:runId" element={<RunPage />} />
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByRole('button', { name: '승인' })).toBeDisabled();

      act(() => {
        vi.advanceTimersByTime(430 * 3);
      });

      expect(screen.getByRole('button', { name: '승인' })).toBeEnabled();
    });

    // 3.2: 커맨드 런 완료 후 결과 카드가 처리 대상 케이스를 노출하고, 탭하면 케이스로 연결된다.
    it('/run/4797(command) 완료 후 결과 카드가 대상 케이스를 보여주고 탭하면 케이스로 이동한다', () => {
      render(
        <MemoryRouter initialEntries={['/run/4797']}>
          <Routes>
            <Route path="/run/:runId" element={<RunPage />} />
            <Route path="/case/:caseId" element={<div>케이스 시트: nguyen</div>} />
          </Routes>
        </MemoryRouter>,
      );

      // 스트리밍 중에는 결과 카드가 없다.
      expect(screen.queryByRole('region', { name: '처리 대상 케이스' })).not.toBeInTheDocument();

      act(() => {
        vi.advanceTimersByTime(430 * 3);
      });

      const result = screen.getByRole('region', { name: '처리 대상 케이스' });
      expect(within(result).getByText('처리 대상 케이스 3건')).toBeInTheDocument();
      expect(within(result).getByText('체류기간 연장 서류 요청')).toBeInTheDocument();
      expect(within(result).getByText('고용변동 신고 기한 임박')).toBeInTheDocument();

      fireEvent.click(within(result).getByText('체류기간 연장 서류 요청'));
      expect(screen.getByText('케이스 시트: nguyen')).toBeInTheDocument();
    });
  });
});
