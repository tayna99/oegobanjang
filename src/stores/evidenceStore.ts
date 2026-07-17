import { create } from 'zustand';
import { createEvidenceEvent } from '@/lib/api/evidence';
import { API_MODE } from '@/lib/api/config';
import type { EvidenceEvent, EvidenceType } from '@/types';

// 무인증 화면(ExpertLinkPage/PackagePage의 재발급)에서 나오는 타입 — 전용 패키지 링크
// 엔드포인트(lib/api/packages.ts)가 자기 트랜잭션 안에서 직접 기록하므로, 이 스토어의 일반
// real-모드 경로로 다시 보내지 않는다(백엔드도 이 타입들을 POST /api/v1/evidence에서
// 422로 거부한다 — services/evidence.py ALLOWED_EVIDENCE_TYPES와 이중 방어).
const PACKAGE_LINK_EVIDENCE_TYPES: ReadonlySet<EvidenceType> = new Set<EvidenceType>([
  'package_link_issued',
  'package_link_viewed',
  'package_reply',
]);

interface EvidenceStoreState {
  events: readonly EvidenceEvent[];
  /** append-only. 수정·삭제 액션은 존재하지 않는다 (감사 무결성). 정정도 새 이벤트로. */
  append: (event: EvidenceEvent) => void;
  /** real 모드 시드 전용(lib/dataSeed.useSeedEvidence) — 서버로 재기록하지 않는다. */
  hydrate: (events: readonly EvidenceEvent[]) => void;
  reset: () => void;
}

export const useEvidenceStore = create<EvidenceStoreState>((set) => ({
  events: [],
  append: (event) => {
    set((s) => {
      // id 중복 방지 — 같은 id 재append(더블탭·재진입)는 no-op. append-only 보장은 유지되고
      // 중복 키/이중 노드만 막는다(코드리뷰 A5 교정).
      if (s.events.some((existing) => existing.id === event.id)) return s;
      // 이벤트를 동결해 사후 변형을 막는다.
      return { events: [...s.events, Object.freeze({ ...event })] };
    });
    // real 모드 서버 기록 — 로컬 상태는 위에서 이미 낙관적으로 갱신했다(감사 로그는 승인과
    // 달리 게이트가 아니므로 낙관적 갱신이 안전, GOTCHAS §2는 승인 결정에만 적용). 실패해도
    // 화면은 그대로 동작하고 콘솔에만 남긴다(dataSeed.ts의 기존 관례와 동일).
    if (API_MODE === 'real' && !PACKAGE_LINK_EVIDENCE_TYPES.has(event.type)) {
      createEvidenceEvent(event).catch((err: unknown) => console.error('[evidenceStore] 서버 기록 실패', err));
    }
  },
  hydrate: (events) =>
    set((s) => {
      const existingIds = new Set(s.events.map((e) => e.id));
      const fresh = events.filter((e) => !existingIds.has(e.id)).map((e) => Object.freeze({ ...e }));
      if (fresh.length === 0) return s;
      return { events: [...s.events, ...fresh] };
    }),
  reset: () => set({ events: [] }),
}));
