import { useState } from 'react';

export interface CommandBarProps {
  suggestions?: string[];
}

// 1단계 스펙 §0.3 CommandBar — 제출 시 M9 에이전트 런 시작이 최종 동작이지만
// 런 엔진(1.5)이 아직 없어 지금은 입력을 비우기만 한다.
export function CommandBar({ suggestions }: CommandBarProps) {
  const [value, setValue] = useState('');

  return (
    <div>
      {suggestions && suggestions.length > 0 && (
        <div className="mb-2 flex gap-1.5 overflow-x-auto">
          {suggestions.slice(0, 3).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setValue(s)}
              className="whitespace-nowrap rounded-chip border border-hairline bg-canvas px-3.5 py-2 text-sm text-muted"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setValue('');
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
