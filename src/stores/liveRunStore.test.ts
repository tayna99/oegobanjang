import { afterEach, describe, expect, it, vi } from 'vitest';

// 스토어 로직만 검증한다 — 프레임 파싱 자체는 lib/api/runs.test.ts가 이미 검증했으므로
// streamCommandRun을 목으로 대체해 "콜백이 오면 스토어가 정확히 어떻게 바뀌는가"만 본다
// (dataSeed.realApi.test.ts류의 fetch-level 통합 테스트와는 레이어를 분리하는 이 저장소 관례).
const handlersByCall: Array<Parameters<typeof import('@/lib/api/runs').streamCommandRun>[1]> = [];
const streamCommandRunMock = vi.fn((_params, handlers) => {
  handlersByCall.push(handlers);
  return { cancel: vi.fn() };
});
vi.mock('@/lib/api/runs', () => ({ streamCommandRun: (...args: unknown[]) => streamCommandRunMock(...(args as [never, never])) }));

import { useLiveRunStore } from './liveRunStore';

describe('liveRunStore — SD-4', () => {
  afterEach(() => {
    useLiveRunStore.getState().reset();
    handlersByCall.length = 0;
    streamCommandRunMock.mockClear();
  });

  it('run_created가 오면 즉시 promise를 resolve하고 스트리밍 항목을 만든다', async () => {
    const promise = useLiveRunStore.getState().startCommandRun({ companyId: 'cmp1', message: '이번 주 만료 확인' });
    handlersByCall[0]?.onRunCreated?.('run_1');

    await expect(promise).resolves.toBe('run_1');
    expect(useLiveRunStore.getState().runs.run_1).toMatchObject({
      runId: 'run_1',
      message: '이번 주 만료 확인',
      status: 'streaming',
      steps: [],
    });
  });

  it('step 프레임이 오는 순서대로 steps 배열에 누적된다', async () => {
    const promise = useLiveRunStore.getState().startCommandRun({ companyId: 'cmp1', message: 'x' });
    handlersByCall[0]?.onRunCreated?.('run_2');
    await promise;

    handlersByCall[0]?.onStep?.({ kind: 'thinking', label: '1단계', detail: '' });
    handlersByCall[0]?.onStep?.({ kind: 'tool_call', label: '2단계', detail: '' });

    expect(useLiveRunStore.getState().runs.run_2.steps.map((s) => s.label)).toEqual(['1단계', '2단계']);
  });

  it('structured → done 순서로 오면 finalAnswer·approvalRequired·status가 반영된다', async () => {
    const promise = useLiveRunStore.getState().startCommandRun({ companyId: 'cmp1', message: 'x' });
    handlersByCall[0]?.onRunCreated?.('run_3');
    await promise;

    handlersByCall[0]?.onStructured?.({
      answer: { final_response: '답변입니다', citations: [], missing_evidence: false, risk_flags: [] },
      approval: { required: true, status: 'PENDING', blocked_actions: [], reason: '' },
    });
    handlersByCall[0]?.onDone?.({ run_id: 'run_3', status: 'waiting_approval', approval_required: true });

    expect(useLiveRunStore.getState().runs.run_3).toMatchObject({
      status: 'done',
      finalAnswer: '답변입니다',
      approvalRequired: true,
      runStatus: 'waiting_approval',
    });
  });

  it('route.should_run=false면 blocked를 표시한다', async () => {
    const promise = useLiveRunStore.getState().startCommandRun({ companyId: 'cmp1', message: 'x' });
    handlersByCall[0]?.onRunCreated?.('run_4');
    await promise;

    handlersByCall[0]?.onRoute?.({ should_run: false, intent: 'forbidden' });

    expect(useLiveRunStore.getState().runs.run_4).toMatchObject({ blocked: true, blockedIntent: 'forbidden' });
  });

  it('run_created 이전에 onError가 오면 promise가 reject된다(런 자체가 생성되지 않음)', async () => {
    const promise = useLiveRunStore.getState().startCommandRun({ companyId: 'cmp1', message: 'x' });
    handlersByCall[0]?.onError?.('요청 실패 (403)');

    await expect(promise).rejects.toThrow('요청 실패 (403)');
    expect(Object.keys(useLiveRunStore.getState().runs)).toHaveLength(0);
  });

  it('run_created 이후 onError가 오면 이미 생성된 항목을 error 상태로 바꾼다', async () => {
    const promise = useLiveRunStore.getState().startCommandRun({ companyId: 'cmp1', message: 'x' });
    handlersByCall[0]?.onRunCreated?.('run_5');
    await promise;

    handlersByCall[0]?.onError?.('rag 서비스 실패');

    expect(useLiveRunStore.getState().runs.run_5).toMatchObject({ status: 'error', errorDetail: 'rag 서비스 실패' });
  });

  it('startCommandRun은 streamCommandRun을 정확히 1회만 호출한다(중복 실행 방지)', async () => {
    const promise = useLiveRunStore.getState().startCommandRun({ companyId: 'cmp1', message: 'x' });
    handlersByCall[0]?.onRunCreated?.('run_6');
    await promise;

    expect(streamCommandRunMock).toHaveBeenCalledTimes(1);
  });
});
