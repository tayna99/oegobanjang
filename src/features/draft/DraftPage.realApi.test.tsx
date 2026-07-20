import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

// SD-5 — real 모드는 mocks/drafts.ts 대신 GET /api/v1/cases/{id}/draft에서 초안을 가져온다.
// CaseReviewPage.realApi.test.tsx와 동일 관례(vi.mock('@/lib/api/config', ...)).
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { DraftPage } from './DraftPage';
import { useRoleStore } from '@/stores/roleStore';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function renderAt(caseId = 'cs_real_draft') {
  return render(
    <MemoryRouter initialEntries={[`/case/${caseId}/draft`]}>
      <Routes>
        <Route path="/case/:caseId/draft" element={<DraftPage />} />
        <Route path="/case/:caseId/approve" element={<div>최종 승인 화면</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function mockDraftFetch(caseId: string, body: unknown, status = 200) {
  global.fetch = vi.fn((input: string | URL | Request) => {
    const url = String(input);
    if (url.endsWith(`/api/v1/cases/${caseId}/draft`)) {
      return Promise.resolve(jsonResponse(body, status));
    }
    return Promise.resolve(jsonResponse({}, 404));
  }) as unknown as typeof fetch;
}

describe('DraftPage — real 모드(SD-5)', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    useRoleStore.getState().reset();
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('서버 초안을 렌더한다 — 제목은 purpose, 원본(is_revised=false) 언어만 탭으로 노출', async () => {
    mockDraftFetch('cs_real_draft', {
      draft_id: 'drf1',
      channel: 'Zalo',
      purpose: '서류 요청 메시지',
      status: 'draft',
      langs: [
        { lang: 'ko', text: '한국어 원문', is_revised: false },
        { lang: 'vi', text: '베트남어 원문', is_revised: false },
        { lang: 'ko', text: '수정된 한국어', is_revised: true },
      ],
    });

    renderAt();

    expect(await screen.findByText('서류 요청 메시지')).toBeInTheDocument();
    expect(screen.getByText('Zalo 초안')).toBeInTheDocument();
    expect(screen.getByText('한국어 원문')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '한국어' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '베트남어' })).toBeInTheDocument();
    // is_revised 변형은 탭으로 노출하지 않는다(원본만 노출 — 위 설계 결정 주석 참고).
    expect(screen.queryByText('수정된 한국어')).not.toBeInTheDocument();
  });

  it('언어 탭 전환이 서버 데이터로도 동작한다', async () => {
    mockDraftFetch('cs_real_draft', {
      draft_id: 'drf1',
      channel: 'Zalo',
      purpose: '서류 요청 메시지',
      status: 'draft',
      langs: [
        { lang: 'ko', text: '한국어 원문', is_revised: false },
        { lang: 'vi', text: '베트남어 원문', is_revised: false },
      ],
    });

    renderAt();
    await screen.findByText('한국어 원문');
    fireEvent.click(screen.getByRole('button', { name: '베트남어' }));
    expect(screen.getByText('베트남어 원문')).toBeInTheDocument();
    expect(screen.queryByText('한국어 원문')).not.toBeInTheDocument();
  });

  it('수정 요청 시트는 서버 revisedText가 없으므로 현재 활성 언어 텍스트로 미리 채운다', async () => {
    mockDraftFetch('cs_real_draft', {
      draft_id: 'drf1',
      channel: 'Zalo',
      purpose: '서류 요청 메시지',
      status: 'draft',
      langs: [{ lang: 'ko', text: '한국어 원문', is_revised: false }],
    });

    renderAt();
    await screen.findByText('한국어 원문');
    fireEvent.click(screen.getByRole('button', { name: '수정 요청' }));
    const textarea = screen.getByRole('textbox', { name: '수정 요청 문구' }) as HTMLTextAreaElement;
    expect(textarea.value).toBe('한국어 원문');
  });

  it('승인 검토로 이동 버튼이 실 caseId로 라우팅된다', async () => {
    mockDraftFetch('cs_real_draft', {
      draft_id: 'drf1',
      channel: 'Zalo',
      purpose: '서류 요청 메시지',
      status: 'draft',
      langs: [{ lang: 'ko', text: '한국어 원문', is_revised: false }],
    });

    renderAt();
    await screen.findByText('한국어 원문');
    fireEvent.click(screen.getByRole('button', { name: '승인 검토로 이동' }));
    expect(await screen.findByText('최종 승인 화면')).toBeInTheDocument();
  });

  it('초안이 없으면(404) 안내 문구를 보여준다', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(jsonResponse({ detail: '초안을 찾을 수 없습니다' }, 404)),
    ) as unknown as typeof fetch;

    renderAt();
    expect(await screen.findByText('초안을 찾을 수 없습니다.')).toBeInTheDocument();
  });
});
