import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchCaseDetail, fetchCases, toCaseCard, type CaseDetailDto, type CaseDto } from './cases';

// R2.3 — lib/api/cases.ts는 순수 fetch+DTO 변환만 한다(toCaseCard는 case.py CaseOut을 그대로 매핑).
describe('lib/api/cases', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  function makeCaseDto(overrides: Partial<CaseDto> = {}): CaseDto {
    return {
      id: 'case_001',
      case_code: 'case_001',
      title: '체류기간 연장 서류 요청',
      severity: 'HIGH',
      state: 'risk_review',
      agent_stage: 'drafted',
      due_date: '2026-08-01',
      approval_required: true,
      prepared_by: 'agent',
      prepared_run_id: 'run_001',
      worker: { display_name: 'Nguyen Van A', nationality: 'VN', team: '제조1팀' },
      primary_action: { action_id: 'act_1', label: '초안 보기', state: 'ready', requires_approval: false, kind: 'draft' },
      secondary_action: { action_id: 'act_2', label: '보내기 승인', state: 'locked', requires_approval: true, kind: 'approve' },
      ...overrides,
    };
  }

  it('fetchCases는 /api/v1/cases를 호출하고 CaseCard[]로 변환한다', async () => {
    const dtos = [makeCaseDto(), makeCaseDto({ id: 'case_002', case_code: 'case_002', worker: null })];
    const mockFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(dtos), { status: 200 }));
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await fetchCases();

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/cases',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) }),
    );
    expect(result).toHaveLength(2);

    const [first, second] = result;
    expect(first.caseId).toBe('case_001');
    expect(first.caseCode).toBe('case_001');
    expect(typeof first.dDay).toBe('number'); // due_date -> calcDday(진짜 오늘 기준, 결정론 불가라 타입만 확인
    expect(first.severity).toBe('HIGH');
    expect(first.state).toBe('risk_review');
    expect(second.workerRef).toBeUndefined();
  });

  it('toCaseCard: worker가 null이면 workerRef는 undefined', () => {
    const card = toCaseCard(makeCaseDto({ worker: null }));
    expect(card.workerRef).toBeUndefined();
  });

  it('toCaseCard: primary_action/secondary_action이 null이면 문서화된 기본값으로 대체한다', () => {
    const card = toCaseCard(makeCaseDto({ id: 'case_003', primary_action: null, secondary_action: null }));

    expect(card.primaryAction).toEqual({
      actionId: 'case_003-detail',
      label: '상세 보기',
      state: 'ready',
      requiresApproval: false,
      kind: 'detail',
    });
    expect(card.secondaryAction).toEqual({
      actionId: 'case_003-confirm',
      label: '케이스 확인 완료',
      state: 'ready',
      requiresApproval: false,
      kind: 'confirm',
    });
  });

  it('toCaseCard: due_date가 null이면 dDay는 undefined', () => {
    const card = toCaseCard(makeCaseDto({ due_date: null }));
    expect(card.dDay).toBeUndefined();
  });

  it('toCaseCard: 아직 API 응답에 없는 필드는 지어내지 않고 undefined로 남긴다', () => {
    const card = toCaseCard(makeCaseDto());
    expect(card.stayExpiryDate).toBeUndefined();
    expect(card.missingDocCount).toBeUndefined();
    expect(card.assignee).toBeUndefined();
    expect(card.evidenceCompleteness).toBeUndefined();
    expect(card.preparedRunRef).toBeUndefined();
  });
});

// SD-6 — fetchCaseDetail 확장분(checked_items/next_wake/documents). 승인·근거수·pending
// approval은 R2.4에서 이미 배선됐고 여기선 테스트가 없었다 — 새 필드와 함께 신설한다.
describe('lib/api/cases — fetchCaseDetail(SD-6)', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
  });

  function makeCaseDetailDto(overrides: Partial<CaseDetailDto> = {}): CaseDetailDto {
    return {
      id: 'cs1',
      case_code: 'case_001',
      title: '체류기간 연장 서류 요청',
      severity: 'HIGH',
      state: 'approval_pending',
      agent_stage: 'awaiting_approval',
      due_date: '2026-08-09',
      approval_required: true,
      prepared_by: 'agent',
      prepared_run_id: null,
      worker: null,
      primary_action: null,
      secondary_action: null,
      usable_citation_count: 2,
      guard_note: null,
      pending_approval: null,
      checked_items: [{ label: '체류만료일', value: '2026.08.09 · D-30' }],
      next_wake: '다음: 발송 후 2일간 응답 없으면 리마인드 여부를 판단합니다',
      documents: [
        { doc_type: '여권 사본', status: 'missing', due_date: null, expires_at: null },
        { doc_type: '재직증명서', status: 'received', due_date: null, expires_at: '2030-01-01' },
      ],
      ...overrides,
    };
  }

  it('checked_items/next_wake/documents를 mock CaseSheet과 같은 필드명으로 변환한다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(makeCaseDetailDto()), { status: 200 }));
    global.fetch = fetchMock as unknown as typeof fetch;

    const result = await fetchCaseDetail('cs1');

    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/v1/cases/cs1'), expect.any(Object));
    expect(result.checkedItems).toEqual([{ label: '체류만료일', value: '2026.08.09 · D-30' }]);
    expect(result.nextWake).toBe('다음: 발송 후 2일간 응답 없으면 리마인드 여부를 판단합니다');
    expect(result.docs).toEqual([
      { name: '여권 사본', status: 'missing', statusLabel: '누락' },
      { name: '재직증명서', status: 'received', statusLabel: '확보' },
    ]);
  });

  it('next_wake가 null이면 undefined로, documents가 빈 배열이면 그대로 빈 배열로 변환한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(makeCaseDetailDto({ next_wake: null, documents: [], checked_items: [] })), { status: 200 }),
    ) as unknown as typeof fetch;

    const result = await fetchCaseDetail('cs4');
    expect(result.nextWake).toBeUndefined();
    expect(result.docs).toEqual([]);
    expect(result.checkedItems).toEqual([]);
  });

  it('알 수 없는 문서 상태값은 원문 그대로를 라벨로 폴백한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify(
          makeCaseDetailDto({ documents: [{ doc_type: '기타 서류', status: 'unknown_status', due_date: null, expires_at: null }] }),
        ),
        { status: 200 },
      ),
    ) as unknown as typeof fetch;

    const result = await fetchCaseDetail('cs5');
    expect(result.docs).toEqual([{ name: '기타 서류', status: 'unknown_status', statusLabel: 'unknown_status' }]);
  });
});
