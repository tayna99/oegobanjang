import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

// R2.3 DoD — API_MODE를 모듈 목으로 'real'로 켠다(vi.mock은 파일 전체에 호이스트되어 apiFetch를
// 경유하는 모든 import가 동일하게 관측한다 — StepPhoneAuth.realApi.test.tsx와 동일한 관례).
vi.mock('./api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { useSeedCases, useSeedEvidence, useSeedNotifications, useSeedThreadDetail, useSeedThreads } from './dataSeed';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useNotificationStore } from '@/stores/notificationStore';
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
  latest_interpretation_status: null,
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

const EVIDENCE_DTO = {
  id: 'evt_1',
  company_id: 'cmp1',
  event_no: 4790,
  type: 'role_granted',
  at: '2026-07-17T09:00:00Z',
  case_id: null,
  summary: '역할 부여',
  input_hash: null,
  actor_display: '김담당',
};

describe('useSeedEvidence — 실 API 모드(R2.5)', () => {
  afterEach(() => {
    useEvidenceStore.getState().reset();
    vi.restoreAllMocks();
  });

  it('evidenceStore가 비어있으면 GET /api/v1/evidence로 hydrate한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse([EVIDENCE_DTO])) as unknown as typeof fetch;

    renderHook(() => useSeedEvidence());

    await waitFor(() => expect(useEvidenceStore.getState().events).toHaveLength(1));
    expect(useEvidenceStore.getState().events[0].id).toBe('evt_1');
  });

  it('스토어에 이미 이벤트가 있으면 fetch하지 않는다', () => {
    // hydrate로 미리 채운다(append는 real 모드에서 그 자체로 POST를 쏘므로, "이미 채워진
    // 상태"를 만드는 이 준비 단계에서는 서버로 아무 것도 보내지 않는 쪽을 써야 아래
    // fetchMock 단언이 useSeedEvidence만의 동작을 본다).
    useEvidenceStore.getState().hydrate([{ id: 'existing', type: 'role_granted', at: '2026-07-17T09:00:00Z', summary: '기존' }]);
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([EVIDENCE_DTO]));
    global.fetch = fetchMock as unknown as typeof fetch;

    renderHook(() => useSeedEvidence());

    expect(fetchMock).not.toHaveBeenCalled();
  });
});

const NOTIFICATION_DTO = {
  id: 'nt_1',
  type: 'N01',
  priority: 'P1',
  title: '승인 요청 1건',
  body: '체류 만료 임박',
  deeplink_path: 'case/cs1/approve',
  channel: 'push',
  status: 'queued',
  case_id: 'cs1',
  run_id: null,
  created_at: '2026-07-20T09:00:00Z',
  read_at: null,
};

describe('useSeedNotifications — 실 API 모드(R5.4)', () => {
  afterEach(() => {
    useNotificationStore.getState().reset();
    vi.restoreAllMocks();
  });

  it('부팅 시 GET /api/v1/notifications로 hydrate한다', async () => {
    global.fetch = vi.fn().mockResolvedValue(jsonResponse([NOTIFICATION_DTO])) as unknown as typeof fetch;

    renderHook(() => useSeedNotifications());

    await waitFor(() => expect(useNotificationStore.getState().records).toHaveLength(1));
    expect(useNotificationStore.getState().records[0].id).toBe('nt_1');
  });
});
