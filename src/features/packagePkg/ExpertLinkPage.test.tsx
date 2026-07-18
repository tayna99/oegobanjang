import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useEvidenceStore } from '@/stores/evidenceStore';

afterEach(() => {
  useEvidenceStore.getState().reset();
  vi.doUnmock('@/lib/packageLink');
  vi.resetModules();
});

// vi.resetModules()(afterEach)가 매 테스트마다 모듈 그래프를 새로 만들기 때문에, 이 파일
// 상단에서 정적 import한 useEvidenceStore는 두 번째 테스트부터 renderAt()이 동적으로 다시
// import하는 ExpertLinkPage가 실제로 쓰는 스토어 인스턴스와 달라진다(서로 다른 싱글턴).
// renderAt이 그 시점의 evidenceStore를 함께 동적 import해 반환해야 "그 렌더가 실제로 건드린
// 스토어"를 테스트가 정확히 관찰할 수 있다.
async function renderAt(path: string) {
  const { ExpertLinkPage } = await import('./ExpertLinkPage');
  const { useEvidenceStore: freshEvidenceStore } = await import('@/stores/evidenceStore');
  const rendered = render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/link/:linkToken" element={<ExpertLinkPage />} />
      </Routes>
    </MemoryRouter>,
  );
  return { ...rendered, useEvidenceStore: freshEvidenceStore };
}

// 행정사 무인증 링크 뷰(7단계 §1·§4) — Shell 챙 없음, 만료·열람 로그.
describe('ExpertLinkPage', () => {
  it('유효한 링크는 로그인 없이 검토 요청서를 보여주고 열람 로그를 남긴다', async () => {
    const { useEvidenceStore: store } = await renderAt('/link/batbayar');
    expect(await screen.findByRole('heading', { name: '행정사 검토 요청서' })).toBeInTheDocument();
    // Shell 없음 — 모바일 탭바/헤더가 렌더되지 않는다.
    expect(screen.queryByRole('navigation', { name: '모바일 탭바' })).not.toBeInTheDocument();

    expect(
      store.getState().events.some((e) => e.type === 'package_link_viewed' && e.caseId === 'batbayar'),
    ).toBe(true);
  });

  it('존재하지 않는 packageId면 링크를 찾을 수 없다는 안내만 보여준다', async () => {
    const { useEvidenceStore: store } = await renderAt('/link/no-such-package');
    expect(screen.getByText('링크를 찾을 수 없습니다.')).toBeInTheDocument();
    expect(store.getState().events.some((e) => e.type === 'package_link_viewed')).toBe(false);
  });

  it('만료된 링크는 만료 안내만 보여주고 열람 로그를 남기지 않는다', async () => {
    vi.doMock('@/lib/packageLink', () => ({ isLinkExpired: () => true }));
    const { useEvidenceStore: store } = await renderAt('/link/batbayar');
    expect(await screen.findByText('링크가 만료되었습니다')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '행정사 검토 요청서' })).not.toBeInTheDocument();
    expect(store.getState().events.some((e) => e.type === 'package_link_viewed')).toBe(false);
  });
});

// 구조화된 회신(PC 4e 확장, 2026-07-13) — 계정 없이도 evidence(package_reply)가 남는다.
describe('ExpertLinkPage — 구조화된 회신', () => {
  it('상세 내용 없이는 회신 보내기가 비활성이다', async () => {
    await renderAt('/link/batbayar');
    expect(await screen.findByRole('button', { name: '회신 보내기' })).toBeDisabled();
  });

  it('자주 쓰는 요청을 눌러 채우고 보내면 evidence(package_reply)가 기록되고 확인 문구로 바뀐다', async () => {
    const { useEvidenceStore: store } = await renderAt('/link/batbayar');
    fireEvent.click(await screen.findByRole('button', { name: '재직증명서 원본이 추가로 필요합니다' }));
    fireEvent.click(screen.getByRole('button', { name: '회신 보내기' }));

    expect(screen.getByText('회신을 보냈습니다')).toBeInTheDocument();
    const event = store.getState().events.find((e) => e.type === 'package_reply');
    expect(event?.caseId).toBe('batbayar');
    expect(event?.summary).toContain('보완 요청');
    expect(event?.summary).toContain('재직증명서 원본이 추가로 필요합니다');
  });

  it('회신 유형을 검토 완료로 바꾸면 evidence 요약에 반영된다', async () => {
    const { useEvidenceStore: store } = await renderAt('/link/batbayar');
    fireEvent.click(await screen.findByRole('button', { name: '검토 완료' }));
    fireEvent.change(screen.getByRole('textbox', { name: '상세 내용' }), { target: { value: '문제 없이 확인했습니다' } });
    fireEvent.click(screen.getByRole('button', { name: '회신 보내기' }));

    const event = store.getState().events.find((e) => e.type === 'package_reply');
    expect(event?.summary).toContain('검토 완료');
  });
});
