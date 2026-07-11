import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { CaseSheetPage } from './CaseSheetPage';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';

// M2.6.2: /case/:caseId 모바일은 바텀시트가 아니라 2b 전면 검토 페이지를 연다.
describe('CaseSheetPage', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
    useEvidenceStore.getState().reset();
  });

  function renderAt(path: string) {
    return render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/case/:caseId" element={<CaseSheetPage />} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it('caseId에 맞는 전면 검토 페이지(2b)를 연다 — 승인 버튼 없이 검토 계속만', () => {
    renderAt('/case/nguyen');
    expect(screen.getByRole('heading', { name: '사례 검토' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '체류기간 연장 서류 요청' })).toBeInTheDocument();
    expect(screen.getByText('왜 확인이 필요한가요')).toBeInTheDocument();
    expect(screen.getByText(/누락 서류 \(2\)/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '검토 계속' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '승인하기' })).not.toBeInTheDocument();
  });

  it('검토 진입이 review_started 판단 기록으로 남는다(중복 없이 1건)', () => {
    renderAt('/case/nguyen');
    const events = useEvidenceStore.getState().events.filter((e) => e.type === 'review_started');
    expect(events).toHaveLength(1);
    expect(events[0].caseId).toBe('nguyen');
  });

  it('존재하지 않는 caseId면 빈 상태 안내를 보여준다', () => {
    renderAt('/case/nope');
    expect(screen.getByText('케이스를 찾을 수 없습니다.')).toBeInTheDocument();
  });
});
