import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';

// 디자인 토큰(v3 :root)의 이름→값 맵을 스냅샷으로 고정한다.
// 값이 바뀌면 스냅샷이 깨져 의도치 않은 토큰 드리프트를 잡는다. (M0.2 DoD)
// vitest cwd = 프로젝트 루트이므로 상대경로로 읽는다.
it('tokens.css의 디자인 토큰이 v3 :root와 일치한다', () => {
  const css = readFileSync('src/styles/tokens.css', 'utf-8');
  // 기준 :root 블록만 파싱한다 (@media reduced-motion 오버라이드는 제외).
  const rootBlock = css.match(/:root\s*\{([^}]*)\}/)?.[1] ?? '';
  const tokens = Object.fromEntries(
    [...rootBlock.matchAll(/--([\w-]+)\s*:\s*([^;]+);/g)].map((m) => [
      m[1],
      m[2].trim(),
    ]),
  );
  // 빈 맵이 조용히 통과하지 않도록 가드.
  expect(Object.keys(tokens).length).toBeGreaterThan(15);
  expect(tokens).toMatchSnapshot();
});
