import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { CaseSheetPage } from './CaseSheetPage';
import { useCaseStore } from '@/stores/caseStore';

describe('CaseSheetPage', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
  });

  it('caseId에 맞는 케이스 시트를 연다(배경으로 M1 브리핑도 함께 렌더)', () => {
    render(
      <MemoryRouter initialEntries={['/case/nguyen']}>
        <Routes>
          <Route path="/case/:caseId" element={<CaseSheetPage />} />
        </Routes>
      </MemoryRouter>,
    );
    // 배경(M1 브리핑 카드)과 시트(CaseSheet h3)가 같은 케이스 제목을 각자 렌더하므로
    // getByText는 모호해진다 — getAllByText로 "적어도 하나 이상 보인다"만 확인하고,
    // 시트에만 있는 내용(체크리스트 항목)으로 시트가 실제로 열렸는지 구분한다.
    expect(screen.getAllByText('Nguyen V. 체류기간 연장 서류 요청').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('체류만료일')).toBeInTheDocument(); // CaseSheet의 AICheckedBlock 전용 내용
    expect(screen.getByText(/오늘 확인이 필요한 업무가/)).toBeInTheDocument();
  });

  it('존재하지 않는 caseId면 시트를 열지 않는다(시트 내용 없이 배경만)', () => {
    render(
      <MemoryRouter initialEntries={['/case/nope']}>
        <Routes>
          <Route path="/case/:caseId" element={<CaseSheetPage />} />
        </Routes>
      </MemoryRouter>,
    );
    // 배경(M1)의 top3 카드에도 동일 라벨 "승인하기" 버튼(nguyen)이 항상 존재하므로
    // role/name 쿼리로는 시트 개폐를 구분할 수 없다 — CaseSheet 전용 블록 헤더로 구분한다.
    expect(screen.queryByText('AI가 확인한 내용')).not.toBeInTheDocument();
  });

  it('caseStore.docUpdates(해석 확인 결과)를 문서 상태 라벨에 오버레이해 보여준다', () => {
    // threadStore.confirmInterpretation → caseStore.applyInterpretationUpdates 오케스트레이션의
    // 결과가 실제 M2 시트 UI에 반영되는지 검증한다(2.2 DoD — "해석 확인 시 상태 갱신").
    useCaseStore.getState().applyInterpretationUpdates('tranCase', [
      { field: '표준근로계약서', from: '누락', to: '회사 확인 필요', badgeTone: 'pending' },
      { field: '여권 사본', from: '누락', to: '제출 예정 · 내일', badgeTone: 'pending' },
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
