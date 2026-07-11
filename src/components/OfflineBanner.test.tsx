import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { OfflineBanner } from './OfflineBanner';

// 경고형 재설계(2.5.4b, Montage 공용 컴포넌트 §4) 계약:
// 오렌지 배너 + 고정 카피 + onRetry가 있을 때만 "재시도" 링크.
describe('OfflineBanner', () => {
  it('경고형 고정 카피를 렌더한다', () => {
    render(<OfflineBanner />);
    expect(screen.getByText('오프라인 상태입니다 · 재연결 시 자동 동기화')).toBeInTheDocument();
  });

  it('onRetry가 있으면 재시도 버튼을 렌더하고 클릭 시 호출한다', () => {
    const onRetry = vi.fn();
    render(<OfflineBanner onRetry={onRetry} />);
    fireEvent.click(screen.getByRole('button', { name: '재시도' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('onRetry가 없으면 재시도 버튼이 없다', () => {
    render(<OfflineBanner lastSyncedAt="14:32" />);
    expect(screen.queryByRole('button', { name: '재시도' })).not.toBeInTheDocument();
  });
});
