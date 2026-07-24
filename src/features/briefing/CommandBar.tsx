import { useState } from 'react';
import { API_MODE } from '@/lib/api/config';
import { resolveCommandRunKey } from '@/lib/commandBar';
import { useNav } from '@/lib/nav';

export interface CommandBarProps {
  suggestions?: string[];
}

// 1단계 스펙 §0.3 CommandBar — 제출 시 M9 에이전트 런을 시작한다. R1.6부터 입력→런
// 매핑(lib/commandBar.resolveCommandRunKey)이 케이스 워커명을 인식해 해당 승인 런으로
// 연결하고, 매칭이 없으면 기존 기본값(#4797, "이번 달 급한 직원만 정리해줘")으로 폴백한다
// — mock 모드 전용 경로다. real 모드(R4.1)는 /run/live(RunLivePage)로 이동해 실제 백엔드
// SSE 런(POST /api/v1/runs/stream)을 시작한다 — resolveCommandRunKey는 건드리지 않는다.
// 추천 칩은 입력만 채우지 않고 즉시 제출한다.
export function CommandBar({ suggestions }: CommandBarProps) {
  const [value, setValue] = useState('');
  const nav = useNav();

  const submit = (text: string) => {
    setValue('');
    if (API_MODE === 'real') {
      if (!text.trim()) return; // backend message: Field(min_length=1) — 공백만 제출 시 422 방지
      nav.toLiveRun(text);
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
