// API 접속점(R2.1, NEXT_ROADMAP 2.1) — mock/실서버 전환 스위치. 기본은 꺼짐(mock 그대로) —
// 기존 데모 대본·테스트가 이 플래그의 영향을 받지 않아야 한다(플래그를 켠 상태만 새 코드
// 경로를 탄다).
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
export const USE_REAL_API = import.meta.env.VITE_USE_REAL_API === 'true';
