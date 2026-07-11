import { create } from 'zustand';

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'oegobanjang-theme';

// jsdom(테스트 환경)엔 matchMedia가 없을 수 있어 존재 여부를 먼저 확인한다.
function prefersDark(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches
  );
}

function readInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'light';
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  return prefersDark() ? 'dark' : 'light';
}

function applyTheme(theme: Theme) {
  if (typeof document === 'undefined') return;
  document.documentElement.dataset.theme = theme;
}

interface ThemeStoreState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

// 다크/라이트 토글 — Montage v2 semantic 토큰이 [data-theme="dark"]로 이미 갈라져
// 있으므로(tokens.css), 여기선 <html data-theme>만 갱신하면 전체 색이 전환된다.
export const useThemeStore = create<ThemeStoreState>((set, get) => {
  const initial = readInitialTheme();
  applyTheme(initial);
  return {
    theme: initial,
    setTheme: (theme) => {
      applyTheme(theme);
      if (typeof window !== 'undefined') window.localStorage.setItem(STORAGE_KEY, theme);
      set({ theme });
    },
    toggleTheme: () => {
      get().setTheme(get().theme === 'dark' ? 'light' : 'dark');
    },
  };
});
