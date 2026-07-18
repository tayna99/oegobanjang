import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

// 코드리뷰 회귀(PR #19 P1): real 모드에서는 role이 서버 멤버십으로 정해지므로, mock 데모용
// 역할 전환 버튼이 그대로 노출되면 로그인한 사용자가 클릭만으로 viewer→manager→owner
// 자기 승급이 가능했다 — vi.mock은 파일 전체에 호이스트되어 Shell.tsx의 import도 동일하게
// 관측한다(dataSeed.realApi.test.ts와 동일한 관례).
vi.mock('./lib/api/config', () => ({ API_BASE_URL: 'http://localhost:8000', API_MODE: 'real' }));

import { Shell } from './Shell';

function renderShell(initialPath: string) {
  const router = createMemoryRouter(
    [{ element: <Shell />, children: [{ index: true, element: <p>M1 자리</p> }] }],
    { initialEntries: [initialPath] },
  );
  return render(<RouterProvider router={router} />);
}

describe('Shell — 실 API 모드(PR #19 리뷰 회귀)', () => {
  it('역할 전환 버튼을 렌더하지 않는다(자기 승급 경로 차단)', () => {
    renderShell('/');
    expect(screen.queryByRole('button', { name: /로 보기 전환/ })).not.toBeInTheDocument();
  });
});
