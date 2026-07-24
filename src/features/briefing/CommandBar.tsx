import { useState } from 'react';
import { API_MODE } from '@/lib/api/config';
import { resolveCommandRunKey } from '@/lib/commandBar';
import { useNav } from '@/lib/nav';
import { useLiveRunStore } from '@/stores/liveRunStore';
import { useSessionStore } from '@/stores/sessionStore';

export interface CommandBarProps {
  suggestions?: string[];
}

// 1단계 스펙 §0.3 CommandBar — 제출 시 M9 에이전트 런을 시작한다. R1.6부터 입력→런
// 매핑(lib/commandBar.resolveCommandRunKey)이 케이스 워커명을 인식해 해당 승인 런으로
// 연결하고, 매칭이 없으면 기존 기본값(#4797, "이번 달 급한 직원만 정리해줘")으로 폴백한다
// — 실 자연어 파싱은 R4(LLM 기반 의도 분류) 몫. 추천 칩은 입력만 채우지 않고 즉시 제출한다.
//
// SD-4 — real 모드는 mock 매핑 대신 POST /runs/stream을 실제로 연다(liveRunStore가 소유).
// run_id는 서버가 첫 프레임으로 알려줄 때까지 모르므로, 그 프레임이 도착한 뒤에만
// nav.toRun(runId)한다 — RunPage가 같은 스트림을 다시 열지 않고 이어받는다(중복 실행 방지,
// stores/liveRunStore.ts 설계 주석 참조).
export function CommandBar({ suggestions }: CommandBarProps) {
  const [value, setValue] = useState('');
  const nav = useNav();
  const startCommandRun = useLiveRunStore((s) => s.startCommandRun);
  const companyId = useSessionStore((s) => s.companyId);

  const submit = (text: string) => {
    setValue('');
    if (API_MODE === 'real') {
      if (!text.trim() || !companyId) return; // 세션 복원 전(companyId 없음)이면 조용히 무시.
      startCommandRun({ companyId, message: text })
        .then((runId) => nav.toRun(runId))
        .catch((err: unknown) => console.error('[CommandBar] 런 시작 실패', err));
      return;
    }
    nav.toRun(resolveCommandRunKey(text));
  };

  return (
    <div>
      {suggestions && suggestions.length > 0 && (
        <div className="mb-2 flex gap-1.5 overflow-x-auto">
          {suggestions.slice(0, 3).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => submit(s)}
              className="whitespace-nowrap rounded-chip border border-hairline bg-canvas px-3.5 py-2 text-label1 text-muted"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(value);
        }}
        className="flex gap-2"
      >
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="AI에게 요청하기"
          className="h-btn flex-1 rounded-in bg-surface px-4 text-btn text-ink outline-none focus:bg-canvas focus:ring-2 focus:ring-primary"
        />
        <button
          type="submit"
          aria-label="전송"
          className="h-btn w-11 shrink-0 rounded-in bg-surface text-muted"
        >
          →
        </button>
      </form>
    </div>
  );
}
