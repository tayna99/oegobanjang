import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { OfflineBanner } from './OfflineBanner';

describe('OfflineBanner', () => {
  it('전달된 lastSyncedAt이 텍스트에 그대로 나타난다', () => {
    render(<OfflineBanner lastSyncedAt="14:32" />);
    expect(screen.getByText(/마지막 업데이트/)).toBeInTheDocument();
    // lastSyncedAt은 자체 span으로 분리돼 있다 — 1.3 BriefingScreen 오프라인 테스트가
    // getByText(정확한 시각)로 단독 조회해야 하기 때문(get-node-text는 직계 텍스트 노드만 본다).
    expect(screen.getByText('14:32')).toBeInTheDocument();
  });

  it('"오프라인" 텍스트가 항상 보인다', () => {
    render(<OfflineBanner lastSyncedAt="09:00" />);
    expect(screen.getByText(/오프라인/)).toBeInTheDocument();
  });
});
