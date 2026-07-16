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

  it('caseStore.docUpdates(해석 확인 결과)를 문서 상태 라벨에 오버레이해 보여준다', () => {
    // threadStore.confirmInterpretation → caseStore.applyInterpretationUpdates 오케스트레이션의
    // 결과가 실제 M2 시트 UI에 반영되는지 검증한다(2.2 DoD — "해석 확인 시 상태 갱신").
    useCaseStore.getState().applyInterpretationUpdates('tranCase', [
      { updateId: 'tran-doc-contract', field: '표준근로계약서', from: '누락', to: '회사 확인 필요', badgeTone: 'pending' },
      { updateId: 'tran-doc-passport', field: '여권 사본', from: '누락', to: '제출 예정 · 내일', badgeTone: 'pending' },
    ]);
    render(
      <MemoryRouter initialEntries={['/case/tranCase']}>
        <Routes>
          <Route path="/case/:caseId" element={<CaseSheetPage />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText('회사 확인 필요')).toBeInTheDocument();
    expect(screen.getByText('제출 예정 · 내일')).toBeInTheDocument();
    expect(screen.queryByText('누락')).not.toBeInTheDocument();
  });
});
