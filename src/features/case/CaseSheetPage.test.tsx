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
    expect(screen.getAllByText('체류기간 연장 서류 요청').length).toBeGreaterThanOrEqual(1);
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
});
