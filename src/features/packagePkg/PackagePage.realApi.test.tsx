import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

// R2.6 — API_MODE를 'real'로 모듈 목(dataSeed.realApi.test.ts와 동일 관례).
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { PackagePage } from './PackagePage';
import { useApprovalStore } from '@/stores/approvalStore';
import { useEvidenceStore } from '@/stores/evidenceStore';

// 코드리뷰 지적(PR #20 P1): real 모드 내비게이션은 라우트 파라미터에 실제 case_id
// (예: 'cs_batbayar')를 싣고 온다 — mocks/packages.ts의 REAL_CASE_ID_ALIASES를 거쳐야
// mock 콘텐츠(batbayar)를 찾는다.
function renderAt(path = '/package/cs_batbayar') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/package/:packageId" element={<PackagePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('PackagePage — 링크 재발급 real 모드(R2.6)', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    useApprovalStore.getState().reset();
    useEvidenceStore.getState().reset();
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('링크 재발급 클릭 시 POST /api/v1/packages/{실제 case_id}/link를 호출한다(mock id가 아니다)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          case_id: 'cs_batbayar',
          link_token: 'tok_new',
          issued_at: '2026-07-17T09:00:00Z',
          expires_at: '2026-07-24T09:00:00Z',
        }),
        { status: 201 },
      ),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    renderAt();
    fireEvent.click(screen.getByRole('button', { name: '링크 재발급' }));

    await waitFor(() =>
      // 코드리뷰 회귀(PR #20 P1): 이전엔 pkg.packageId('batbayar', mock 콘텐츠에 박힌 값)를
      // 그대로 보내 실제 DB에 없는 케이스로 404였다 — 라우트의 실제 case_id를 보내야 한다.
      expect(fetchMock).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/packages/cs_batbayar/link',
        expect.objectContaining({ method: 'POST' }),
      ),
    );
    // 로컬 UI(열람 이력·만료 안내 재계산용 evidence)는 두 모드 공통으로 즉시 반영된다.
    expect(useEvidenceStore.getState().events.some((e) => e.type === 'package_link_issued')).toBe(true);
  });
});
