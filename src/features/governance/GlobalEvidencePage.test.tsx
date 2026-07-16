import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { GlobalEvidencePage } from './GlobalEvidencePage';
import { useEvidenceStore } from '@/stores/evidenceStore';

afterEach(() => useEvidenceStore.getState().reset());

function renderAt(path = '/evidence') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <GlobalEvidencePage />
    </MemoryRouter>,
  );
}

// M8 전역 판단 기록(2.3) — 감사 로그 최신순 + 필터 + 상세 시트 + 딥링크 하이라이트, 해시만.
describe('GlobalEvidencePage (M8)', () => {
  it('판단 기록을 최신순으로 렌더한다', () => {
    renderAt();
    expect(screen.getByRole('heading', { name: '판단 기록' })).toBeInTheDocument();
    const items = screen.getAllByRole('listitem');
    expect(items.length).toBeGreaterThan(0);
    // 시드 최신 = 브리핑 생성(2026-07-10) — 첫 항목.
    expect(within(items[0]).getByText('브리핑 생성 완료 · 케이스 6건')).toBeInTheDocument();
  });

  it('필터 칩이 유형별로 거른다 — 승인은 요청/완료/반려만', () => {
    renderAt();
    fireEvent.click(screen.getByRole('button', { name: '승인' }));
    expect(screen.getByText(/승인 요청 생성/)).toBeInTheDocument();
    expect(screen.queryByText(/CRITICAL 탐지/)).not.toBeInTheDocument();
  });

  it('항목 탭 시 상세 시트가 열리고 해시를 표기한다(원문 없음)', () => {
    renderAt();
    fireEvent.click(screen.getByRole('button', { name: /Nguyen Van A · 체류만료 D-30 HIGH 상향/ }));
    expect(screen.getByText('해시')).toBeInTheDocument();
    expect(screen.getByText('sha256:77e0…41cc')).toBeInTheDocument();
    expect(screen.getByText(/INSERT-only로 저장되며 원문·개인정보는 해시로만/)).toBeInTheDocument();
  });

  it('딥링크 ?ref=로 해당 판단 기록을 강조한다', () => {
    renderAt('/evidence?ref=%234789');
    const highlighted = screen.getByRole('button', { name: /서류요청 발송 승인 요청 생성/ });
    expect(highlighted.className).toContain('border-primary');
  });
});
