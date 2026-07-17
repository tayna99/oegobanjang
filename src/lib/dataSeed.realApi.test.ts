import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

// R2.3 DoD — USE_REAL_API를 모듈 목으로 켠다(vi.mock은 파일 전체에 호이스트되어 apiFetch를
// 경유하는 모든 import가 동일하게 관측한다 — StepPhoneAuth.realApi.test.tsx와 동일한 관례).
vi.mock('./api/config', () => ({ API_BASE_URL: 'http://localhost:8000', USE_REAL_API: true }));

import { useSeedCases, useSeedThreadDetail, useSeedThreads } from './dataSeed';
import { useCaseStore } from '@/stores/caseStore';
import { useThreadStore } from '@/stores/threadStore';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status });
}

const CASE_DTO = {
  id: 'case_001',
  case_code: 'case_001',
  title: '체류기간 연장 서류 요청',
  severity: 'HIGH',
  state: 'risk_review',
  agent_stage: 'collecting',
  due_date: null,
  approval_required: true,
  prepared_by: 'agent',
  prepared_run_id: null,
  worker: null,
  primary_action: null,
  secondary_action: null,
};

const THREAD_DTO = {
  id: 'thread_001',
  worker: { display_name: 'Nguyen Van A', nationality: '베트남', team: '제조1팀' },
  channel: 'zalo',
  last_message_at: '2026-07-10T02:00:00Z',
  message_count: 2,
};

const THREAD_DETAIL_DTO = {
  id: 'thread_001',
  worker: { display_name: 'Nguyen Van A', nationality: '베트남', team: '제조1팀' },
  channel: 'zalo',
  messages: [
    {
      id: 'msg_1',
      direction: 'inbound',
      channel: 'zalo',
      lang: 'vi',
      body_original: 'Xin chào',
      body_ko: '안녕하세요',
      received_at: '2026-07-10T02:00:00Z',
      created_at: '2026-07-10T02:00:00Z',
      interpretation: null,
    },
  ],
};

describe('useSeedCases / useSeedThreads — 실 API 모드(R2.3)', () => {
  afterEach(() => {
    useCaseStore.getState().reset();
    useThreadStore.getState().reset();
    vi.restoreAllMocks();
  });

  it('caseStore가 비어있으면 GET /api/v1/cases로 시드한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse([CASE_DTO])) as unknown as typeof fetch;

    renderHook(() => useSeedCases());

    await waitFor(() => expect(useCaseStore.getState().cases.case_001).toBeDefined());
    expect(useCaseStore.getState().cases.case_001.title).toBe(CASE_DTO.title);
  });

  it('threadStore가 비어있으면 GET /api/v1/threads로 시드한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse([THREAD_DTO])) as unknown as typeof fetch;

    renderHook(() => useSeedThreads());

    await waitFor(() => expect(useThreadStore.getState().threads.thread_001).toBeDefined());
    expect(useThreadStore.getState().threads.thread_001.workerRef.displayName).toBe('Nguyen Van A');
  });

  it('스토어에 이미 데이터가 있으면 fetch하지 않는다', () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([CASE_DTO]));
    global.fetch = fetchMock as unknown as typeof fetch;
    useCaseStore.getState().upsert({
      caseId: 'existing',
      caseCode: 'case_existing',
      title: '기존',
      severity: 'LOW',
      state: 'draft',
      approvalRequired: false,
      primaryAction: { actionId: 'a', label: 'a', state: 'ready', requiresApproval: false, kind: 'detail' },
      secondaryAction: { actionId: 'b', label: 'b', state: 'ready', requiresApproval: false, kind: 'confirm' },
      preparedBy: 'rule',
    });

    renderHook(() => useSeedCases());

    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('useSeedThreadDetail — 실 API 모드(R2.3)', () => {
  afterEach(() => {
    useThreadStore.getState().reset();
    vi.restoreAllMocks();
  });

  it('threadId가 있으면 GET /api/v1/threads/:id로 목록의 가벼운 요약을 상세로 교체한다', async () => {
    useThreadStore.getState().upsert({
      threadId: 'thread_001',
      workerRef: { displayName: 'Nguyen Van A', nationality: '베트남', maskLevel: 'masked' },
      channel: 'zalo',
      channelLabel: 'Zalo',
      messages: [],
      interpretationStatus: 'none',
      preview: '메시지 2건',
      timeLabel: '',
    });
    global.fetch = vi.fn().mockResolvedValue(jsonResponse(THREAD_DETAIL_DTO)) as unknown as typeof fetch;

    renderHook(() => useSeedThreadDetail('thread_001'));

    await waitFor(() => expect(useThreadStore.getState().threads.thread_001.messages).toHaveLength(1));
    expect(useThreadStore.getState().threads.thread_001.messages[0].body).toBe('안녕하세요');
  });

  it('threadId가 undefined면 fetch하지 않는다', () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(THREAD_DETAIL_DTO));
    global.fetch = fetchMock as unknown as typeof fetch;

    renderHook(() => useSeedThreadDetail(undefined));

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
