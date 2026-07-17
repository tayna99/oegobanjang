import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

// R2.4 — real 모드에서 CASE_SHEETS(mock)가 없어도 카드 기반 최소 렌더 + "검토 계속" 버튼이
// 동작해야 한다(퍼널 유지, plans/HANDOFF.md 참조). ExpertLinkPage.realApi.test.tsx와 동일 관례.
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { CaseReviewPage } from './CaseReviewPage';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import type { CaseCard } from '@/types';

// mocks/fixtures.ts에 없는 real 전용 caseId — CASE_SHEETS 미스를 재현한다.
const CARD: CaseCard = {
  caseId: 'cs_real_only',
  caseCode: 'case_099',
  title: '서버 전용 케이스',
  severity: 'HIGH',
  state: 'approval_pending',
  approvalRequired: true,
  primaryAction: { actionId: 'act1', label: '승인하기', state: 'ready', requiresApproval: true, kind: 'approve' },
  secondaryAction: { actionId: 'act1-detail', label: '상세', state: 'ready', requiresApproval: false, kind: 'detail' },
  preparedBy: 'rule',
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

function renderAt(path = '/case/cs_real_only') {
  useCaseStore.getState().upsert(CARD);
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/case/:caseId" element={<CaseReviewPage />} />
        <Route path="/case/:caseId/approve" element={<div>최종 승인 화면</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CaseReviewPage — real 모드(R2.4)', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    useCaseStore.getState().reset();
    useEvidenceStore.getState().reset();
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('mock 시트가 없어도 카드 정보로 렌더하고 "검토 계속"으로 승인 화면에 갈 수 있다', async () => {
    global.fetch = vi.fn((input: string | URL | Request, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/api/v1/cases/cs_real_only')) {
        return Promise.resolve(
          jsonResponse({
            id: 'cs_real_only', case_code: 'case_099', title: '서버 전용 케이스', severity: 'HIGH',
            state: 'approval_pending', agent_stage: null, due_date: null, approval_required: true,
            prepared_by: 'rule', prepared_run_id: null, worker: null, primary_action: null, secondary_action: null,
            usable_citation_count: 3, guard_note: '체류기간 만료 경과 — 확인 필요', pending_approval: null,
          }),
        );
      }
      if (url.endsWith('/api/v1/evidence') && (init?.method ?? 'GET') === 'GET') {
        return Promise.resolve(jsonResponse([]));
      }
      return Promise.resolve(jsonResponse({}, 201));
    }) as unknown as typeof fetch;

    renderAt();

    expect(await screen.findByText('서버 전용 케이스')).toBeInTheDocument();
    // 시트가 없으므로 "왜 확인이 필요한가요" mock 콘텐츠 섹션은 생략된다.
    expect(screen.queryByText('왜 확인이 필요한가요')).not.toBeInTheDocument();
    // guardNote는 서버에서 보강돼 그대로 노출된다.
    expect(await screen.findByText('체류기간 만료 경과 — 확인 필요')).toBeInTheDocument();

    const continueButton = await screen.findByRole('button', { name: '검토 계속' });
    continueButton.click();
    expect(await screen.findByText('최종 승인 화면')).toBeInTheDocument();
  });
});
