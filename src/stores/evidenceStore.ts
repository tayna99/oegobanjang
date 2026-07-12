import { create } from 'zustand';
import type { EvidenceEvent } from '@/types';

interface EvidenceStoreState {
  events: readonly EvidenceEvent[];
  /** append-only. 수정·삭제 액션은 존재하지 않는다 (감사 무결성). 정정도 새 이벤트로. */
  append: (event: EvidenceEvent) => void;
  reset: () => void;
}

export const useEvidenceStore = create<EvidenceStoreState>((set) => ({
  events: [],
  append: (event) =>
    set((s) => {
      // id 중복 방지 — 같은 id 재append(더블탭·재진입)는 no-op. append-only 보장은 유지되고
      // 중복 키/이중 노드만 막는다(코드리뷰 A5 교정).
      if (s.events.some((existing) => existing.id === event.id)) return s;
      // 이벤트를 동결해 사후 변형을 막는다.
      return { events: [...s.events, Object.freeze({ ...event })] };
    }),
  reset: () => set({ events: [] }),
}));
