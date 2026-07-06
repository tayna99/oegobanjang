import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { OfflineBanner } from './OfflineBanner';

describe('OfflineBanner', () => {
  it('전달된 lastSyncedAt이 텍스트에 그대로 나타난다', () => {
    render(<OfflineBanner lastSyncedAt="14:32" />);
    expect(screen.getByText(/마지막 업데이트 14:32/)).toBeInTheDocument();
  });

  it('"오프라인" 텍스트가 항상 보인다', () => {
    render(<OfflineBanner lastSyncedAt="09:00" />);
    expect(screen.getByText(/오프라인/)).toBeInTheDocument();
  });
});
