import { create } from 'zustand';
import type { Briefing } from '@/lib/api/briefings';

// SD-3 — GET /api/v1/briefings/latest(R2.3에서 구현됐으나 dataSeed.ts:19-25가 명시한 이유로
// 미배선 상태였던) 전용 슬롯. caseStore와 분리하는 이유: caseStore는 "화면 진입 순서와 무관하게
// 항상 전체 케이스가 채워져 있다"는 것을 모든 화면이 전제하는 단일 스토어라, 브리핑 당일
// 랭크 서브셋으로 caseStore를 시드하면 다른 화면이 그걸 "전체"로 오인한다. 이 스토어는 그
// 서브셋(브리핑 메타 + 랭크순 케이스)을 caseStore와 별개로만 보관한다 — mock 모드는 아예
// 쓰지 않는다(브리핑 표시는 지금처럼 caseStore 파생 그대로).
interface BriefingStoreState {
  briefing: Briefing | null;
  hydrate: (briefing: Briefing | null) => void;
  reset: () => void;
}

export const useBriefingStore = create<BriefingStoreState>((set) => ({
  briefing: null,
  hydrate: (briefing) => set({ briefing }),
  reset: () => set({ briefing: null }),
}));
