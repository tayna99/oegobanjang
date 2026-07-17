/// <reference types="vite/client" />

// R2.1 — mock/실서버 전환 플래그(NEXT_ROADMAP 2.1). 기본은 미설정(=mock 유지).
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_USE_REAL_API?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
