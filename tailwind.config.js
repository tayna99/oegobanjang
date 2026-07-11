/** @type {import('tailwindcss').Config} */
// 값의 단일 출처는 src/styles/tokens.css (v3 :root). 여기서는 var()로만 참조한다.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--canvas)',
        surface: { DEFAULT: 'var(--surface)', dim: 'var(--surface-dim)', press: 'var(--surface-press)' },
        ink: 'var(--ink)',
        muted: 'var(--muted)',
        faint: 'var(--faint)',
        hairline: 'var(--hairline)',
        primary: { DEFAULT: 'var(--primary)', press: 'var(--primary-press)' },
        critical: { DEFAULT: 'var(--critical)', text: 'var(--critical-text)' },
        warning: { DEFAULT: 'var(--warning)', text: 'var(--warning-text)' },
        pending: 'var(--pending)',
        info: 'var(--info)',
        success: 'var(--success)',
        neutral: 'var(--neutral)',
        pendbg: 'var(--pendbg)',
        succbg: 'var(--succbg)',
        critbg: 'var(--critbg)',
        warnbg: 'var(--warnbg)',
        infobg: 'var(--infobg)',
        neutbg: 'var(--neutbg)',
      },
      borderRadius: {
        in: 'var(--r-in)',
        chip: 'var(--r-chip)',
        card: 'var(--r-card)',
        sheet: 'var(--r-sheet)',
        badge: 'var(--r-badge)',
      },
      spacing: {
        // 탭바 높이(62px) — h-tabbar/pb-tabbar 양쪽에서 씀(height는 기본적으로
        // spacing 스케일을 상속하므로 여기 한 번만 등록하면 둘 다 사용 가능).
        tabbar: 'var(--tabbar-h)',
        // 버튼(프로토타입 v3 .btn) — h-btn/h-btn-sm, px-btn-x, gap-btn-gap.
        btn: 'var(--btn-h)',
        'btn-sm': 'var(--btn-h-sm)',
        'btn-x': 'var(--btn-px)',
        'btn-gap': 'var(--btn-gap)',
        // 배지(프로토타입 v3 .bdg) — py-badge-y, gap-badge-gap.
        'badge-y': 'var(--badge-py)',
        'badge-gap': 'var(--badge-gap)',
        // SafetyNotice(프로토타입 v3 .safety) — gap-safety-gap.
        'safety-gap': 'var(--safety-gap)',
        // 탭바 도트 인디케이터 지름(7px, 프로토타입 v3 .dot) — w-dot/h-dot.
        dot: 'var(--dot-size)',
      },
      fontSize: {
        // 탭바 라벨 폰트 크기(11px, 탭별기획 §0.2 "라벨 11/600").
        'tabbar-label': 'var(--tabbar-label-fs)',
        // 버튼 기본 폰트(15px, 프로토타입 v3 .btn) — sm은 Tailwind 기본 text-sm(14px)로 충분.
        btn: 'var(--btn-fs)',
        // SafetyNotice 폰트(13px, 프로토타입 v3 .safety).
        safety: 'var(--safety-fs)',
      },
      maxHeight: {
        sheet: 'var(--sheet-max-h)',
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
