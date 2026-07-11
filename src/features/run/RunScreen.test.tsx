import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RunScreen } from './RunScreen';
import type { RunViewState } from './RunScreen';

const STREAMING_STATE: RunViewState = {
  status: 'default',
  mode: 'approval',
  title: '승인 전 확인',
  question: '이 메시지로 컨택할까요?',
  altLabel: '수정 요청',
  engineStatus: 'streaming',
  steps: [
    { kind: 'tool_call', label: '근로자 프로필 확인 완료', detail: 'Nguyen Van A' },
    { kind: 'guardrail', label: '가드레일', detail: '정부 포털 제출 불가' },
  ],
};

describe('RunScreen', () => {
  it('loading 상태에서는 분석 중 문구를 보여준다', () => {
    render(<RunScreen state={{ status: 'loading' }} />);
    expect(screen.getByText('분석 중…')).toBeInTheDocument();
  });

  it('스트리밍 완료 전에는 승인 버튼이 disabled다(DoD)', () => {
    render(<RunScreen state={STREAMING_STATE} />);
    expect(screen.getByRole('button', { name: '승인' })).toBeDisabled();
  });

  it('스트리밍이 완료되면 승인 버튼이 활성화된다', () => {
    render(<RunScreen state={{ ...STREAMING_STATE, engineStatus: 'done' }} />);
    expect(screen.getByRole('button', { name: '승인' })).not.toBeDisabled();
  });

  it('guardrail 스텝은 StepTimeline을 통해 다른 스텝과 구분되게 렌더된다(DoD)', () => {
    render(<RunScreen state={STREAMING_STATE} />);
    const guardrailItem = screen.getByText('정부 포털 제출 불가').closest('li');
    const toolCallItem = screen.getByText('Nguyen Van A').closest('li');
    // 세로형 재설계(2.5.4b): 가드레일 구분은 li 배경이 아니라 경고 톤 칩·라벨이다.
    // (이 목 스텝은 label도 '가드레일'이라 kind 칩과 텍스트가 중복 — 클래스로 칩을 판별한다.)
    const guardrailTexts = within(guardrailItem as HTMLElement).getAllByText('가드레일');
    expect(guardrailTexts.some((el) => el.className.includes('bg-warnbg'))).toBe(true);
    expect(within(toolCallItem as HTMLElement).queryByText('가드레일')).not.toBeInTheDocument();
  });

  it('readOnly(replay)에서는 승인/대안 버튼을 렌더하지 않는다', () => {
    render(<RunScreen state={{ ...STREAMING_STATE, engineStatus: 'done', readOnly: true }} />);
    expect(screen.queryByRole('button', { name: '승인' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '수정 요청' })).not.toBeInTheDocument();
  });

  it('offline 상태에서는 오프라인 배너와 승인 불가 안내를 보여준다', () => {
    render(<RunScreen state={{ status: 'offline', lastSyncedAt: '10:00' }} />);
    expect(screen.getByText('오프라인 상태입니다 · 재연결 시 자동 동기화')).toBeInTheDocument();
    expect(screen.getByText('오프라인 상태에서는 승인을 진행할 수 없습니다.')).toBeInTheDocument();
  });

  it('error(out_of_scope) 상태에서는 행정사 검토 요청 CTA를 보여주고 onAlt를 호출한다', () => {
    const onAlt = vi.fn();
    render(
      <RunScreen
        state={{ status: 'error', reason: 'out_of_scope', message: '범위 밖 요청입니다.' }}
        onAlt={onAlt}
      />,
    );
    expect(screen.getByText('범위 밖 요청입니다.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '행정사 검토 요청' }));
    expect(onAlt).toHaveBeenCalledOnce();
  });
});
