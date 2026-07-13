import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useEvidenceStore } from '@/stores/evidenceStore';

afterEach(() => {
  useEvidenceStore.getState().reset();
  vi.doUnmock('@/lib/packageLink');
  vi.resetModules();
});

async function renderAt(path: string) {
  const { ExpertLinkPage } = await import('./ExpertLinkPage');
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/link/:packageId" element={<ExpertLinkPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

// 행정사 무인증 링크 뷰(7단계 §1·§4) — Shell 챙 없음, 만료·열람 로그.
describe('ExpertLinkPage', () => {
  it('유효한 링크는 로그인 없이 검토 요청서를 보여주고 열람 로그를 남긴다', async () => {
    await renderAt('/link/batbayar');
    expect(await screen.findByRole('heading', { name: '행정사 검토 요청서' })).toBeInTheDocument();
    // Shell 없음 — 모바일 탭바/헤더가 렌더되지 않는다.
    expect(screen.queryByRole('navigation', { name: '모바일 탭바' })).not.toBeInTheDocument();

    expect(
      useEvidenceStore.getState().events.some((e) => e.type === 'package_link_viewed' && e.caseId === 'batbayar'),
    ).toBe(true);
  });

  it('존재하지 않는 packageId면 링크를 찾을 수 없다는 안내만 보여준다', async () => {
    await renderAt('/link/no-such-package');
    expect(screen.getByText('링크를 찾을 수 없습니다.')).toBeInTheDocument();
    expect(useEvidenceStore.getState().events.some((e) => e.type === 'package_link_viewed')).toBe(false);
  });

  it('만료된 링크는 만료 안내만 보여주고 열람 로그를 남기지 않는다', async () => {
    vi.doMock('@/lib/packageLink', () => ({ isLinkExpired: () => true }));
    await renderAt('/link/batbayar');
    expect(await screen.findByText('링크가 만료되었습니다')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '행정사 검토 요청서' })).not.toBeInTheDocument();
    expect(useEvidenceStore.getState().events.some((e) => e.type === 'package_link_viewed')).toBe(false);
  });
});
