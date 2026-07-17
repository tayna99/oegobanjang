import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchCases, toCaseCard, type CaseDto } from './cases';

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

    expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/v1/cases', expect.objectContaining({ headers: expect.any(Headers) }));
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
