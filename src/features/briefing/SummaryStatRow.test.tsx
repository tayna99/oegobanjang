import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SummaryStatRow } from './SummaryStatRow';
import { IconDoc } from '@/components/icons';

describe('SummaryStatRow', () => {
  it('전달된 통계 타일을 전부 렌더한다', () => {
    const onClick = vi.fn();
    render(
      <SummaryStatRow
        stats={[{ icon: IconDoc, label: '서류 보완', count: 2, unit: '건', onClick }]}
      />,
    );
    expect(screen.getByText('서류 보완')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('건')).toBeInTheDocument();
  });

  it('타일을 탭하면 onClick이 실행된다', () => {
    const onClick = vi.fn();
    render(<SummaryStatRow stats={[{ icon: IconDoc, label: '서류 보완', count: 2, unit: '건', onClick }]} />);
    fireEvent.click(screen.getByText('서류 보완'));
    expect(onClick).toHaveBeenCalledOnce();
  });
});
