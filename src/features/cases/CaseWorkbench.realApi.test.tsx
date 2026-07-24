import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

// SD-6 — real 모드에서 CASE_SHEETS(mock)에 없는 caseId도 선택 시 GET /api/v1/cases/{id}로
// 보강 렌더된다. CaseReviewPage.realApi.test.tsx와 동일 관례(vi.mock('@/lib/api/config', ...)).
vi.mock('@/lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { CaseWorkbench } from './CaseWorkbench';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';
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

function noop() {}

function renderWorkbench() {
  return render(
    <MemoryRouter>
      <CaseWorkbench cards={[CARD]} preset="all" selectedCaseId="cs_real_only" onSelectCase={noop} onSelectFilter={noop} />
    </MemoryRouter>,
  );
}

describe('CaseWorkbench — real 모드(SD-6)', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    useRoleStore.getState().reset();
    useEvidenceStore.getState().reset();
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it('mock 시트가 없어도 서버 상세(checked_items/documents/next_wake)로 상세·레일을 렌더한다', async () => {
    global.fetch = vi.fn((input: string | URL | Request) => {
      const url = String(input);
      if (url.endsWith('/api/v1/cases/cs_real_only')) {
        return Promise.resolve(
          jsonResponse({
            id: 'cs_real_only', case_code: 'case_099', title: '서버 전용 케이스', severity: 'HIGH',
            state: 'approval_pending', agent_stage: null, due_date: null, approval_required: true,
            prepared_by: 'rule', prepared_run_id: null, worker: null, primary_action: null, secondary_action: null,
            usable_citation_count: 2, guard_note: '체류기간 만료 경과 — 확인 필요', pending_approval: null,
            checked_items: [{ label: '체류만료일', value: '2026.08.09 · D-30' }],
            next_wake: '다음: 발송 후 2일간 응답 없으면 리마인드 여부를 판단합니다',
            documents: [{ doc_type: '여권 사본', status: 'missing', due_date: null, expires_at: null }],
          }),
        );
      }
      return Promise.resolve(jsonResponse([]));
    }) as unknown as typeof fetch;

    renderWorkbench();

    // 목록 없이도 상세가 카드 정보로 즉시 렌더된다.
    expect(screen.getByRole('heading', { name: '서버 전용 케이스' })).toBeInTheDocument();
    // guardNote는 서버에서 보강돼 노출된다.
    expect(await screen.findByText('체류기간 만료 경과 — 확인 필요')).toBeInTheDocument();
    // checked_items → "AI가 확인한 내용" 레일 섹션.
    expect(screen.getByText('체류만료일')).toBeInTheDocument();
    expect(screen.getByText('2026.08.09 · D-30')).toBeInTheDocument();
    // documents → "필수 서류 체크리스트" 중앙 섹션.
    expect(screen.getByText('여권 사본')).toBeInTheDocument();
    // usable_citation_count → 헤더 카운트만(개별 근거 레코드 목록은 real 모드에 없음).
    expect(screen.getByText('연결 근거 (2)')).toBeInTheDocument();
    // next_wake → 케이스 타임라인 하단 + "다음 액션 (AI 제안)" 레일 둘 다에 노출된다(mock
    // 모드도 원래 이 두 군데에 같은 문구를 중복 표시한다 — CaseTimeline·EvidenceRail 둘 다
    // sheet.nextWake를 그대로 읽는 기존 설계, SD-6이 새로 만든 중복이 아니다).
    const evidenceRail = screen.getByRole('complementary', { name: 'AI·근거 레일' });
    expect(await within(evidenceRail).findByText('다음: 발송 후 2일간 응답 없으면 리마인드 여부를 판단합니다')).toBeInTheDocument();
    expect(screen.getAllByText('다음: 발송 후 2일간 응답 없으면 리마인드 여부를 판단합니다')).toHaveLength(2);
  });

  it('근거 0건이면 승인 게이트가 잠긴다(real 모드도 mock과 동일 규칙)', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve(
        jsonResponse({
          id: 'cs_real_only', case_code: 'case_099', title: '서버 전용 케이스', severity: 'HIGH',
          state: 'approval_pending', agent_stage: null, due_date: null, approval_required: true,
          prepared_by: 'rule', prepared_run_id: null, worker: null, primary_action: null, secondary_action: null,
          usable_citation_count: 0, guard_note: null, pending_approval: null,
          checked_items: [], next_wake: null, documents: [],
        }),
      ),
    ) as unknown as typeof fetch;

    renderWorkbench();

    expect(await screen.findByText('공식 근거가 연결되지 않았습니다. 승인 전 확인이 필요합니다.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '승인하기' })).toBeDisabled();
  });
});
