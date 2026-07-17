import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { API_MODE } from '@/lib/api/config';
import { router } from '@/router';
import { useSessionStore } from '@/stores/sessionStore';
import './index.css';

// R2.2 — real 모드에서 저장된 세션 토큰이 있으면 부팅 시 1회 복원한다(새로고침 시 manager로
// 되돌아가던 M-6 문제의 해소 지점). mock 모드에서는 아무 일도 하지 않는다.
if (API_MODE === 'real') {
  void useSessionStore.getState().restore();
}

const rootEl = document.getElementById('root');
if (!rootEl) throw new Error('root element not found');

createRoot(rootEl).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
