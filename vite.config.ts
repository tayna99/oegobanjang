import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    // 저장소 루트 밖(.claude/worktrees, .codex/worktrees, .review-pr* 등 병렬 세션용
    // 중첩 체크아웃)의 동일 이름 테스트 파일까지 vitest 기본 glob이 주워 담아 같은
    // 테스트가 여러 벌 동시 실행되던 문제를 근본 교정 — 진짜 테스트는 전부 src/ 아래.
    include: ['src/**/*.{test,spec}.?(c|m)[jt]s?(x)'],
    // 공유 브라우저 전역과 cold transform으로 인한 파일 간 간헐적 flaky를 방지한다.
    fileParallelism: false,
  },
});
