import { useState } from 'react';
import { useNav } from '@/lib/nav';

export interface CommandBarProps {
  suggestions?: string[];
}

// 1단계 스펙 §0.3 CommandBar — 제출 시 M9 에이전트 런을 시작한다. MVP는 자연어
// 파싱이 없어 제출 내용과 무관하게 항상 command 데모 런(#4790, "이번 달 급한
// 직원만 정리해줘")으로 진입한다 — 실 파싱은 백엔드 단계
// (docs/superpowers/specs/2026-07-06-run-engine-steptimeline-design.md).
export function CommandBar({ suggestions }: CommandBarProps) {
  const [value, setValue] = useState('');
  const nav = useNav();

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
          nav.toRun('4790');
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
