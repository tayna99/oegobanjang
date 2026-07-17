// R2.1 API 클라이언트 계층 — mock/실서버 전환 플래그(plans/ROADMAP.md R2.1, NEXT_ROADMAP §2).
// 기본값은 반드시 'mock'이어야 한다 — 기존 424개 프론트 테스트와 8단계 데모 대본 전부가
// mock 세계관(caseStore/threadStore/evidenceStore를 mocks/*.ts로 시딩)을 전제로 하므로,
// 'real'은 명시적 opt-in(.env의 VITE_API_MODE=real)일 때만 켜진다. 이 플래그를 참조하지
// 않는 화면·스토어는 지금까지처럼 그대로 mock으로 동작한다(2.1~2.6이 순차로 real 분기를 늘려간다).
export type ApiMode = 'mock' | 'real';

// `import.meta.env.MODE !== 'test'` 가드: Vite는 .env.local을 mode==='test'에서 제외한다고
// 문서화돼 있지만, 이 저장소의 vitest 실행 경로에서는 실제로 그 예외가 적용되지 않아
// 개발자가 실서버 검증용으로 만든 .env.local(VITE_API_MODE=real)이 테스트 스위트에 그대로
// 새어 들어가는 것을 확인했다(R2.1) — 테스트는 로컬 dotfile과 무관하게 항상 mock이어야 하므로
// vitest의 MODE==='test' 신호를 명시적으로 우선한다.
export const API_MODE: ApiMode =
  import.meta.env.MODE !== 'test' && import.meta.env.VITE_API_MODE === 'real' ? 'real' : 'mock';

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
