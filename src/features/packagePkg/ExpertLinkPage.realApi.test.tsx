import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

// R2.6 — API_MODE를 'real'로 모듈 목(dataSeed.realApi.test.ts와 동일 관례). 서버가 만료를
// 강제한다는 것(클라이언트 isLinkExpired가 아니라 GET /api/v1/packages/link/{token}의
// 200/404)을 검증한다.
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { ExpertLinkPage } from './ExpertLinkPage';
import { useEvidenceStore } from '@/stores/evidenceStore';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/link/:linkToken" element={<ExpertLinkPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ExpertLinkPage — real 모드(R2.6)', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    useEvidenceStore.getState().reset();
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('서버가 200을 반환하면 검토 요청서를 보여주고, 클라이언트에서 다시 evidence를 남기지 않는다(서버가 이미 기록)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          case_id: 'cs_batbayar',
          link_token: 'tok_valid',
          issued_at: '2026-07-10T00:00:00Z',
          expires_at: '2026-07-24T00:00:00Z',
        }),
        { status: 200 },
      ),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    renderAt('/link/tok_valid');

    // 코드리뷰 지적(PR #20 P1): URL의 값은 이제 case_id가 아니라 회전하는 link_token이라
    // 서버 응답의 caseId를 받아야만(REAL_CASE_ID_ALIASES 경유) 콘텐츠를 찾을 수 있다.
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/packages/link/tok_valid', expect.anything());
    expect(await screen.findByRole('heading', { name: '행정사 검토 요청서' })).toBeInTheDocument();
    expect(useEvidenceStore.getState().events.some((e) => e.type === 'package_link_viewed')).toBe(false);

    // 코드리뷰 회귀(PR #20 P1): 구조화된 회신을 받는 서버 엔드포인트가 아직 없는데도
    // "회신을 보냈습니다"라고 거짓으로 확인해주고 있었다 — real 모드에서는 회신 폼 대신
    // 정직한 "아직 준비 중" 안내만 보여야 한다(회신 보내기 버튼 자체가 없어야 한다).
    expect(screen.getByText('회신 접수는 아직 준비 중입니다')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '회신 보내기' })).not.toBeInTheDocument();
  });

  it('서버가 404를 반환하면 만료 안내를 보여준다(클라이언트 가드가 아니라 서버 강제)', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ detail: '링크를 찾을 수 없습니다' }), { status: 404 })) as unknown as typeof fetch;

    renderAt('/link/tok_valid');

    expect(await screen.findByText('링크가 만료되었습니다')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '행정사 검토 요청서' })).not.toBeInTheDocument();
  });

  // 코드리뷰 회귀(PR #20 P1): link_token은 case_id와 달리 그 자체로는 아무 의미가 없는
  // 값이라, 이전처럼 "mock 콘텐츠에 없는 id면 서버 호출을 건너뛴다"는 최적화를 더는 할 수
  // 없다(어떤 토큰이 유효한지는 서버만 안다) — 존재하지 않는 토큰이라도 반드시 서버에
  // 물어봐야 하고, 존재 비노출 원칙에 따라 결과는 "찾을 수 없음"이 아니라 "만료됨"과 동일한
  // 문구로 보여야 한다.
  it('존재하지 않는 link_token도 서버에 확인하고, 결과는 만료와 동일하게 보여준다', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ detail: '링크를 찾을 수 없습니다' }), { status: 404 }));
    global.fetch = fetchMock as unknown as typeof fetch;

    renderAt('/link/no-such-token');

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/packages/link/no-such-token',
        expect.anything(),
      ),
    );
    expect(await screen.findByText('링크가 만료되었습니다')).toBeInTheDocument();
  });
});
