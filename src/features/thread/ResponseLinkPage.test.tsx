import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ResponseLinkPage } from './ResponseLinkPage';

// R3 stage ② — 근로자 응답 링크(무인증). MESSAGING_CHANNELS.md §3. ExpertLinkPage.realApi.test.tsx와
// 동일한 관례(fetch 목킹, 서버가 만료를 강제한다) — 이 화면은 애초에 mock 모드가 없다(항상 backend 왕복).
function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/response/:token" element={<ResponseLinkPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ResponseLinkPage', () => {
  const originalFetch = global.fetch;
  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  const viewBody = {
    thread_id: 'th1',
    worker: { display_name: 'Nguyen Van A', nationality: '베트남' },
    lang: 'vi',
    prompt: '서류를 보내주세요.',
    choices: { received: '확인했습니다 (서류 준비 완료)', not_yet: '아직 준비 중입니다' },
  };

  it('유효한 토큰이면 프롬프트와 버튼 선택지를 보여준다', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(viewBody), { status: 200 })) as unknown as typeof fetch;

    renderAt('/response/tok_valid');

    expect(await screen.findByText('서류를 보내주세요.')).toBeInTheDocument();
    expect(screen.getByText('Nguyen Van A님')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '확인했습니다 (서류 준비 완료)' })).toBeInTheDocument();
  });

  it('만료·미발급 토큰은 만료 안내를 보여준다', async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ detail: '없음' }), { status: 404 })) as unknown as typeof fetch;

    renderAt('/response/no-such-token');

    expect(await screen.findByText('링크가 만료되었습니다')).toBeInTheDocument();
  });

  it('버튼 선택 후 보내기를 누르면 POST하고 완료 화면을 보여준다', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(viewBody), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ received: true }), { status: 201 }));
    global.fetch = fetchMock as unknown as typeof fetch;

    renderAt('/response/tok_valid');
    await screen.findByText('서류를 보내주세요.');

    fireEvent.click(screen.getByRole('button', { name: '확인했습니다 (서류 준비 완료)' }));
    fireEvent.click(screen.getByRole('button', { name: '보내기' }));

    await waitFor(() => expect(screen.getByText('응답이 전달되었습니다')).toBeInTheDocument());

    expect(fetchMock).toHaveBeenLastCalledWith(
      'http://localhost:8000/api/v1/response-link/tok_valid',
      expect.objectContaining({ method: 'POST' }),
    );
    const body = JSON.parse(fetchMock.mock.calls[1][1]?.body as string);
    expect(body).toEqual({ choice: 'received', free_text: undefined });
  });

  it('선택도 자유입력도 없으면 보내기 버튼이 비활성화된다', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(viewBody), { status: 200 })) as unknown as typeof fetch;

    renderAt('/response/tok_valid');
    await screen.findByText('서류를 보내주세요.');

    expect(screen.getByRole('button', { name: '보내기' })).toBeDisabled();
  });
});
