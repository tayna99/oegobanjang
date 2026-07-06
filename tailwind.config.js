/** @type {import('tailwindcss').Config} */
// 값의 단일 출처는 src/styles/tokens.css (v3 :root). 여기서는 var()로만 참조한다.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--canvas)',
        surface: { DEFAULT: 'var(--surface)', dim: 'var(--surface-dim)' },
        ink: 'var(--ink)',
        muted: 'var(--muted)',
        faint: 'var(--faint)',
        hairline: 'var(--hairline)',
        primary: { DEFAULT: 'var(--primary)', press: 'var(--primary-press)' },
        critical: 'var(--critical)',
        warning: 'var(--warning)',
        pending: 'var(--pending)',
        info: 'var(--info)',
        success: 'var(--success)',
        neutral: 'var(--neutral)',
        pendbg: 'var(--pendbg)',
        succbg: 'var(--succbg)',
      },
      borderRadius: {
        in: 'var(--r-in)',
        chip: 'var(--r-chip)',
        card: 'var(--r-card)',
        sheet: 'var(--r-sheet)',
      },
      spacing: {
        // 탭바 높이(62px) — h-tabbar/pb-tabbar 양쪽에서 씀(height는 기본적으로
        // spacing 스케일을 상속하므로 여기 한 번만 등록하면 둘 다 사용 가능).
        tabbar: 'var(--tabbar-h)',
      },
      fontSize: {
        // 탭바 라벨 폰트 크기(11px, 탭별기획 §0.2 "라벨 11/600").
        'tabbar-label': 'var(--tabbar-label-fs)',
      },
      boxShadow: {
        card: 'var(--sh-card)',
        lift: 'var(--sh-lift)',
        sheet: 'var(--sh-sheet)',
      },
      transitionDuration: {
        fast: 'var(--fast)',
        std: 'var(--std)',
        slow: 'var(--slow)',
      },
      transitionTimingFunction: {
        'e-in': 'var(--e-in)',
        'e-std': 'var(--e-std)',
      },
      fontFamily: {
        sans: [
          'Pretendard Variable',
          'Pretendard',
          'system-ui',
          '-apple-system',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
};
