/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** R2.1 — 'real'이면 lib/api/config.ts의 API_MODE가 실서버 호출을 켠다. 기본은 mock. */
  readonly VITE_API_MODE?: string;
  /** R2.1 — 실서버 모드에서 backend/ 베이스 URL. 기본은 로컬 uvicorn(8000). */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
