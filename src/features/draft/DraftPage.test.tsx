import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { DraftPage } from './DraftPage';
import { useRoleStore } from '@/stores/roleStore';

function renderAt(caseId: string) {
  return render(
    <MemoryRouter initialEntries={[`/case/${caseId}/draft`]}>
      <Routes>
        <Route path="/case/:caseId/draft" element={<DraftPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

// M3 초안 화면 — 7단계 §6 역할 분기(운영급 RBAC 확장): manager/owner는 편집성 액션(수정
// 요청·승인 이동)에 닿고, viewer는 읽기만 한다.
describe('DraftPage — 역할 분기', () => {
  afterEach(() => useRoleStore.getState().reset());

  it('manager는 수정 요청·승인 검토로 이동 버튼을 모두 본다', () => {
    renderAt('nguyen');
    expect(screen.getByRole('button', { name: '수정 요청' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '승인 검토로 이동' })).toBeInTheDocument();
  });

  it('viewer는 편집성 버튼이 없고 읽기 전용 안내만 본다', () => {
    useRoleStore.getState().setRole('viewer');
    renderAt('nguyen');
    expect(screen.queryByRole('button', { name: '수정 요청' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '승인 검토로 이동' })).not.toBeInTheDocument();
    expect(screen.getByText('열람자 권한으로는 초안을 읽기만 할 수 있습니다.')).toBeInTheDocument();
  });
});
