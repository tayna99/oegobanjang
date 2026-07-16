/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 설정 시 승인 decide가 mockApi 대신 src/lib/api.ts를 통해 실 백엔드를 호출한다. */
  readonly VITE_API_BASE_URL?: string;
  /** dev 자동 로그인 대상 전화번호 — 미설정 시 db/seed_demo.sql usr_owner(김대표). */
  readonly VITE_DEV_LOGIN_PHONE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
