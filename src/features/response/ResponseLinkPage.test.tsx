import { fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { routeConfig } from '@/router';
import { useThreadStore } from '@/stores/threadStore';
import { threadBadge } from '@/lib/threads';

function renderAt(path: string) {
  return render(<RouterProvider router={createMemoryRouter(routeConfig, { initialEntries: [path] })} />);
}

// 근로자 응답 링크 — docs/DESIGN_SYNC_AUDIT_2026-07-17.md §3, GOTCHAS §3(원문 미노출).
describe('ResponseLinkPage', () => {
  afterEach(() => {
    useThreadStore.getState().reset();
  });

  it('유효한 토큰은 발신자·원문 카드·모국어 선택지를 Shell 없이 보여준다', async () => {
    renderAt('/response/nguyen-stay-extension');
    expect(await screen.findByText('Quản lý Kim Min-su')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Tôi đã xác nhận' })).toBeInTheDocument();
    // Shell 바깥 형제 라우트 — 모바일 탭바(브리핑/케이스/메시지/기록) 링크가 없어야 한다.
    expect(screen.queryByRole('link', { name: '브리핑' })).not.toBeInTheDocument();
  });

  it('프리셋을 선택하지 않으면 보내기가 비활성이다(자유 입력만으로는 활성화되지 않는다)', async () => {
    renderAt('/response/nguyen-stay-extension');
    const submit = await screen.findByRole('button', { name: 'Gửi câu trả lời' });
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Nội dung thêm'), { target: { value: '월요일에 가겠습니다' } });
    expect(submit).toBeDisabled();
  });

  it('프리셋을 선택하면 보내기가 활성화되고, 제출하면 threadStore에 응답 도착 상태가 반영된다', async () => {
    renderAt('/response/nguyen-stay-extension');
    fireEvent.click(await screen.findByRole('radio', { name: 'Tôi đã xác nhận' }));
    const submit = screen.getByRole('button', { name: 'Gửi câu trả lời' });
    expect(submit).not.toBeDisabled();

    fireEvent.click(submit);
    expect(await screen.findByText('Đã gửi câu trả lời')).toBeInTheDocument();

    const thread = useThreadStore.getState().threads.nguyen;
    expect(thread.messages).toHaveLength(1);
    expect(thread.messages[0].direction).toBe('in');
    expect(thread.messages[0].body).toBe('Tôi đã xác nhận');
    expect(thread.interpretationStatus).toBe('pending_review');
    expect(threadBadge(thread).label).toBe('응답 도착');
  });

  it('preview에는 응답 원문이 절대 담기지 않는다', async () => {
    renderAt('/response/nguyen-stay-extension');
    fireEvent.click(await screen.findByRole('radio', { name: 'Vui lòng gửi lại' }));
    fireEvent.click(screen.getByRole('button', { name: 'Gửi câu trả lời' }));
    await screen.findByText('Đã gửi câu trả lời');

    const thread = useThreadStore.getState().threads.nguyen;
    expect(thread.preview).toBe('응답이 도착했습니다');
    expect(thread.preview).not.toContain('Vui lòng gửi lại');
  });

  it('제출해도 케이스 상태는 바뀌지 않는다(isFinal:false 계약 — M6 해석 큐로만 들어간다)', async () => {
    renderAt('/response/nguyen-stay-extension');
    fireEvent.click(await screen.findByRole('radio', { name: 'Tôi có câu hỏi' }));
    fireEvent.click(screen.getByRole('button', { name: 'Gửi câu trả lời' }));
    await screen.findByText('Đã gửi câu trả lời');

    const thread = useThreadStore.getState().threads.nguyen;
    expect(thread.interpretation).toBeUndefined();
  });

  it('만료된 토큰은 만료 안내만 보여준다', async () => {
    renderAt('/response/expired-demo');
    expect(await screen.findByText('Liên kết đã hết hạn')).toBeInTheDocument();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
  });

  it('이미 응답한 토큰은 이전 응답 원문 없이 안내만 보여준다', async () => {
    renderAt('/response/tran-doc-request');
    expect(await screen.findByText('Đã nhận được câu trả lời')).toBeInTheDocument();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
  });

  it('없는 토큰은 링크를 찾을 수 없다는 안내만 보여준다', async () => {
    renderAt('/response/no-such-token');
    expect(await screen.findByText('Không tìm thấy liên kết')).toBeInTheDocument();
  });

  it('언어 토글로 한국어 전환 시 카피와 헤더 서비스명이 함께 바뀐다', async () => {
    renderAt('/response/nguyen-stay-extension');
    expect(await screen.findByText('Ngoại Cao Ban Trưởng')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '한국어' }));
    expect(await screen.findByText('답변 선택')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: '확인했습니다' })).toBeInTheDocument();
    expect(screen.getByText('외고반장')).toBeInTheDocument();
    expect(screen.queryByText('Ngoại Cao Ban Trưởng')).not.toBeInTheDocument();
  });
});

describe('threadStore.receiveInbound (가드레일)', () => {
  afterEach(() => {
    useThreadStore.getState().reset();
  });

  it('존재하지 않는 스레드로 receiveInbound하면 GuardrailError를 던진다', () => {
    expect(() =>
      useThreadStore.getState().receiveInbound('no-such-thread', {
        messageId: 'm1',
        body: 'x',
        lang: 'vi',
        at: '2026-07-17T00:00:00.000Z',
      }),
    ).toThrow();
  });

  it('같은 messageId로 재수신하면 중복 없이 no-op이다', () => {
    useThreadStore.getState().upsert({
      threadId: 't1',
      workerRef: { displayName: 'Test W.', nationality: '베트남', maskLevel: 'masked' },
      channel: 'sms',
      channelLabel: 'SMS',
      messages: [],
      interpretationStatus: 'none',
      preview: '',
      timeLabel: '',
    });
    const inbound = { messageId: 'dup-1', body: 'hello', lang: 'vi', at: '2026-07-17T00:00:00.000Z' };
    useThreadStore.getState().receiveInbound('t1', inbound);
    useThreadStore.getState().receiveInbound('t1', inbound);
    expect(useThreadStore.getState().threads.t1.messages).toHaveLength(1);
  });
});
