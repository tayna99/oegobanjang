import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StepTimeline } from './StepTimeline';
import type { RunStep } from '@/mocks/runs';

const STEPS: RunStep[] = [
  { kind: 'tool_call', label: '근로자 프로필 확인 완료', detail: 'Nguyen Van A · 베트남' },
  { kind: 'guardrail', label: '가드레일', detail: '정부 포털 제출 불가' },
];

describe('StepTimeline', () => {
  it('각 스텝의 라벨과 상세를 렌더한다', () => {
    render(<StepTimeline steps={STEPS} />);
    expect(screen.getByText('근로자 프로필 확인 완료')).toBeInTheDocument();
    expect(screen.getByText('Nguyen Van A · 베트남')).toBeInTheDocument();
    expect(screen.getByText('가드레일')).toBeInTheDocument();
    expect(screen.getByText('정부 포털 제출 불가')).toBeInTheDocument();
  });

  it('guardrail 스텝은 경고 톤(bg-warnbg)으로, 그 외 스텝은 기본 톤으로 렌더된다', () => {
    render(<StepTimeline steps={STEPS} />);
    const guardrailItem = screen.getByText('정부 포털 제출 불가').closest('li');
    const toolCallItem = screen.getByText('Nguyen Van A · 베트남').closest('li');
    expect(guardrailItem).toHaveClass('bg-warnbg');
    expect(toolCallItem).not.toHaveClass('bg-warnbg');
    expect(toolCallItem).toHaveClass('bg-surface');
  });
});
