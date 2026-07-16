import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup, configure } from '@testing-library/react';

// findBy* 기본 대기(1000ms)는 39개 파일 병렬 실행 시 jsdom 환경 경합으로
// /case/:caseId loader(비동기) 첫 렌더가 넘길 수 있다 — 결정적 실패를 막기 위해 상향.
// 개별 테스트의 명시 timeout 없이도 전역으로 적용된다.
configure({ asyncUtilTimeout: 15000 });

afterEach(() => {
  cleanup();
});
