import { act } from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RunPage } from './RunPage';

describe('RunPage', () => {
  it('/case/:caseId/approve로 진입하면 해당 케이스의 approval RunConfig를 렌더한다', async () => {
    render(
      <MemoryRouter initialEntries={['/case/nguyen/approve']}>
        <Routes>
          <Route path="/case/:caseId/approve" element={<RunPage />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText('승인 전 확인')).toBeInTheDocument();
  });

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

  describe('스트리밍 중 승인 버튼 disabled 통합 테스트', () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it('/case/:caseId/approve 진입 시 스트리밍 중에는 승인 버튼이 disabled이고, 스트리밍 완료 후 enabled로 바뀐다', async () => {
      render(
        <MemoryRouter initialEntries={['/case/nguyen/approve']}>
          <Routes>
            <Route path="/case/:caseId/approve" element={<RunPage />} />
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByRole('button', { name: '승인' })).toBeDisabled();

      act(() => {
        vi.advanceTimersByTime(430 * 3);
      });

      expect(screen.getByRole('button', { name: '승인' })).toBeEnabled();
    });
  });
});
