import { CASE_CARDS } from '@/mocks/fixtures';
import { RUN_CONFIGS } from '@/mocks/runs';

// 커맨드 바 최소 매핑(R1.6, NEXT_ROADMAP 1.6) — 자연어 파싱은 아직 없다(실 LLM 기반 의도
// 분류는 R4 몫). 입력에 케이스 워커명이 포함되면 그 워커의 실제 승인 런으로 바로 연결하고,
// 매칭이 없으면 기존 기본값(급한 케이스 정리, #4797)으로 폴백한다 — "항상 #4797"이던 이전
// 동작보다 한 단계만 더 똑똑해진 매핑이다.
export const DEFAULT_COMMAND_RUN_KEY = '4797';

// mode:'approval' + caseId가 있는 런만 대상 — replay(#4712/#4788)는 과거 재생용이라
// 새 요청의 목적지로 삼지 않는다.
const CASE_RUN_KEYWORDS: { keyword: string; runKey: string }[] = RUN_CONFIGS.filter(
  (config) => config.mode === 'approval' && config.caseId,
).flatMap((config) => {
  const card = CASE_CARDS.find((c) => c.caseId === config.caseId);
  const firstName = card?.workerRef?.displayName.split(' ')[0];
  return firstName ? [{ keyword: firstName.toLowerCase(), runKey: config.runKey }] : [];
});

export function resolveCommandRunKey(input: string): string {
  const normalized = input.trim().toLowerCase();
  if (!normalized) return DEFAULT_COMMAND_RUN_KEY;
  const matched = CASE_RUN_KEYWORDS.find(({ keyword }) => normalized.includes(keyword));
  return matched?.runKey ?? DEFAULT_COMMAND_RUN_KEY;
}
