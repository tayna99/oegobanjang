import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

// R2.6 — API_MODE를 'real'로 모듈 목(dataSeed.realApi.test.ts와 동일 관례). 서버가 만료를
// 강제한다는 것(클라이언트 isLinkExpired가 아니라 GET /api/v1/packages/{caseId}/link의
// 200/404)을 검증한다.
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { ExpertLinkPage } from './ExpertLinkPage';
import { useEvidenceStore } from '@/stores/evidenceStore';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/link/:packageId" element={<ExpertLinkPage />} />
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
    global.fetch = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ case_id: 'batbayar', issued_at: '2026-07-10T00:00:00Z', expires_at: '2026-07-24T00:00:00Z' }),
          { status: 200 },
        ),
      ) as unknown as typeof fetch;

    renderAt('/link/batbayar');

    expect(await screen.findByRole('heading', { name: '행정사 검토 요청서' })).toBeInTheDocument();
    expect(useEvidenceStore.getState().events.some((e) => e.type === 'package_link_viewed')).toBe(false);
  });

  it('서버가 404를 반환하면 만료 안내를 보여준다(클라이언트 가드가 아니라 서버 강제)', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ detail: '링크를 찾을 수 없습니다' }), { status: 404 })) as unknown as typeof fetch;

    renderAt('/link/batbayar');

    expect(await screen.findByText('링크가 만료되었습니다')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '행정사 검토 요청서' })).not.toBeInTheDocument();
  });

  it('존재하지 않는 packageId는 서버 호출 없이 즉시 안내만 보여준다', async () => {
    const fetchMock = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;

    renderAt('/link/no-such-package');

    expect(screen.getByText('링크를 찾을 수 없습니다.')).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).not.toHaveBeenCalled());
  });
});
