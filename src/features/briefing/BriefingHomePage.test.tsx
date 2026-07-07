import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import { BriefingHomePage } from './BriefingHomePage';
import { useCaseStore } from '@/stores/caseStore';
import { CASE_CARDS } from '@/mocks/fixtures';

describe('BriefingHomePage', () => {
  beforeEach(() => {
    useCaseStore.getState().reset();
  });

  it('caseStore가 비어 있으면 CASE_CARDS로 시드하고 렌더한다', () => {
    render(
      <MemoryRouter>
        <BriefingHomePage />
      </MemoryRouter>,
    );
    expect(Object.keys(useCaseStore.getState().cases)).toHaveLength(CASE_CARDS.length);
    expect(screen.getByText(/Nguyen V\./)).toBeInTheDocument();
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
});
