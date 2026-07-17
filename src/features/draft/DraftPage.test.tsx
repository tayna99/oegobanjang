import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { DraftPage } from './DraftPage';
import { DRAFTS } from '@/mocks/drafts';
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

// R1.7 DoD — "고정 revisedText 토글 → 편집 가능한 수정 요청 UI".
describe('DraftPage — 수정 요청(R1.7)', () => {
  afterEach(() => useRoleStore.getState().reset());

  it('시트를 열면 부드러운 톤 제안으로 미리 채워진 편집창을 보여준다', () => {
    renderAt('nguyen');
    fireEvent.click(screen.getByRole('button', { name: '수정 요청' }));
    const textarea = screen.getByRole('textbox', { name: '수정 요청 문구' }) as HTMLTextAreaElement;
    expect(textarea.value).toBe(DRAFTS.nguyen.revisedText);
  });

  it('문구를 직접 고쳐 반영하면 그 편집 결과가 그대로 표시된다', () => {
    renderAt('nguyen');
    fireEvent.click(screen.getByRole('button', { name: '수정 요청' }));
    const textarea = screen.getByRole('textbox', { name: '수정 요청 문구' });
    fireEvent.change(textarea, { target: { value: '제가 직접 다시 쓴 문구입니다.' } });
    fireEvent.click(screen.getByRole('button', { name: '수정 반영' }));

    expect(screen.getByText('제가 직접 다시 쓴 문구입니다.')).toBeInTheDocument();
    expect(screen.getByText('수정 반영')).toBeInTheDocument(); // 상태 Chip
  });

  it('빈 문구로는 반영할 수 없다', () => {
    renderAt('nguyen');
    fireEvent.click(screen.getByRole('button', { name: '수정 요청' }));
    const textarea = screen.getByRole('textbox', { name: '수정 요청 문구' });
    fireEvent.change(textarea, { target: { value: '   ' } });
    expect(screen.getByRole('button', { name: '수정 반영' })).toBeDisabled();
  });

  it('언어를 다시 전환하면 편집 반영이 해제되고 원문으로 돌아간다', () => {
    renderAt('nguyen');
    fireEvent.click(screen.getByRole('button', { name: '수정 요청' }));
    fireEvent.click(screen.getByRole('button', { name: '수정 반영' })); // 제안 문구 그대로 반영

    fireEvent.click(screen.getByRole('button', { name: '베트남어' }));
    expect(screen.queryByText(DRAFTS.nguyen.revisedText)).not.toBeInTheDocument();
    expect(screen.getByText('승인 전')).toBeInTheDocument();
  });
});
