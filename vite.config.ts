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
    // 기본 testTimeout(5000ms)이 전역 asyncUtilTimeout(15000, src/test/setup.ts)보다 낮아
    // 병렬 부하 시 /case/:caseId loader 대기 중 테스트가 먼저 5000ms에 종료되던 플레이크를 막는다.
    testTimeout: 15000,
    hookTimeout: 15000,
    // Shared browser-like globals and cold transforms make parallel files flaky on this MVP suite.
    fileParallelism: false,
  },
});
