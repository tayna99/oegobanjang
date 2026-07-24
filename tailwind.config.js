/** @type {import('tailwindcss').Config} */
// 값의 단일 출처는 src/styles/tokens.css (Montage v2). 여기서는 var()로만 참조한다.
// 유틸리티 이름은 v1과 동일하게 유지해 소비 파일(20여개)을 건드리지 않는다
// (docs/DESIGN_SYNC_AUDIT_2026-07-11.md §3 매핑표 그대로 적용, M2.5.1).
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--color-bg-normal)',
        surface: {
          DEFAULT: 'var(--color-bg-alternative)',
          dim: 'var(--color-bg-canvas-alt)',
          press: 'var(--color-surface-press)',
        },
        ink: 'var(--color-label-normal)',
        muted: 'var(--color-label-neutral)',
        faint: 'var(--color-label-assistive)',
        hairline: 'var(--color-line-solid-normal)',
        line: 'var(--color-line-normal)',
        primary: { DEFAULT: 'var(--color-primary-normal)', press: 'var(--color-primary-strong)' },
        // Toggle 잠금 상태 전용(2026-07-17) — 일반 primary와 구분되는 반투명 트랙.
        toggleLocked: 'var(--toggle-locked-bg)',
        critical: { DEFAULT: 'var(--chip-critical-fg)', text: 'var(--chip-critical-fg)' },
        warning: { DEFAULT: 'var(--chip-high-fg)', text: 'var(--chip-high-fg)' },
        success: 'var(--chip-positive-fg)',
        neutral: 'var(--chip-neutral-fg)',
        approval: 'var(--chip-approval-fg)',
        medium: 'var(--chip-medium-fg)',
        critbg: 'var(--chip-critical-bg)',
        warnbg: 'var(--chip-high-bg)',
        succbg: 'var(--chip-positive-bg)',
        neutbg: 'var(--chip-neutral-bg)',
        approvalbg: 'var(--chip-approval-bg)',
        medbg: 'var(--chip-medium-bg)',
        // 선택형 카드(라디오) 선택 배경 틴트 — rail-focus/approvalbg(PC 워크벤치 탭)와는 별개.
        selectbg: 'var(--color-selection-tint)',
        draft: 'var(--chip-draft-fg)',
        draftbg: 'var(--chip-draft-bg)',
        detected: 'var(--chip-detected-fg)',
        detectedbg: 'var(--chip-detected-bg)',
        // 라벨 계층 확장(2.5.4b): subtle=.61(부제·비활성 탭), dim=.43(타임스탬프·해시).
        subtle: 'var(--color-label-alternative)',
        dim: 'var(--color-label-muted43)',
        track: 'var(--color-track)',
        dimmer: 'var(--color-material-dimmer)',
        'inverse-bg': 'var(--color-inverse-bg)',
        'inverse-label': 'var(--color-inverse-label)',
      },
      borderRadius: {
        in: 'var(--r-btn)',
        'btn-sm': 'var(--r-btn-sm)',
        chip: 'var(--r-pill)',
        badge: 'var(--r-chip)',
        card: 'var(--r-card)',
        sheet: 'var(--r-sheet)',
      },
      spacing: {
        // 탭바 높이(62px) — h-tabbar/pb-tabbar 양쪽에서 씀.
        tabbar: 'var(--tabbar-h)',
        // 버튼 — h-btn/h-btn-sm, px-btn-x, gap-btn-gap.
        btn: 'var(--btn-h)',
        'btn-sm': 'var(--btn-h-sm)',
        'btn-x': 'var(--btn-px)',
        'btn-gap': 'var(--btn-gap)',
        // Chip — py-badge-y, gap-badge-gap.
        'badge-y': 'var(--chip-py)',
        'badge-gap': 'var(--chip-gap)',
        // SafetyNotice — gap-safety-gap.
        'safety-gap': 'var(--safety-gap)',
        // 탭바 도트 인디케이터 지름(7px, 프로토타입 v3 .dot) — w-dot/h-dot.
        dot: 'var(--dot-size)',
      },
      fontSize: {
        // 탭바 라벨(11px), 버튼 기본(15px), SafetyNotice(13px) — 이 프로젝트 전용 치수.
        'tabbar-label': 'var(--tabbar-label-fs)',
        btn: 'var(--btn-fs)',
        safety: 'var(--safety-fs)',
        // Montage 타입 스케일 — [size, {lineHeight, letterSpacing}] 튜플. 2.5.3 리스킨에서 소비.
        heading1: ['var(--fs-heading1)', { lineHeight: 'var(--lh-heading1)', letterSpacing: 'var(--ls-heading1)' }],
        heading2: ['var(--fs-heading2)', { lineHeight: 'var(--lh-heading2)', letterSpacing: 'var(--ls-heading2)' }],
        body1: ['var(--fs-body1)', { lineHeight: 'var(--lh-body1)', letterSpacing: 'var(--ls-body1)' }],
        body2: ['var(--fs-body2)', { lineHeight: 'var(--lh-body2)', letterSpacing: 'var(--ls-body2)' }],
        label1: ['var(--fs-label1)', { lineHeight: 'var(--lh-label1)', letterSpacing: 'var(--ls-label1)' }],
        caption1: ['var(--fs-caption1)', { lineHeight: 'var(--lh-caption1)', letterSpacing: 'var(--ls-caption1)' }],
        // PC 밀도 타입램프(결정 2026-07-11) — 2.5.4+ PC 화면에서 소비.
        'pc-2xs': 'var(--fs-pc-2xs)',
        'pc-xs': 'var(--fs-pc-xs)',
        'pc-sm': 'var(--fs-pc-sm)',
        'pc-md': 'var(--fs-pc-md)',
      },
      maxHeight: {
        sheet: 'var(--sheet-max-h)',
      },
      boxShadow: {
        xsmall: 'var(--shadow-xsmall)',
        card: 'var(--shadow-medium)',
        lift: 'var(--shadow-large)',
        sheet: 'var(--sh-sheet)',
        // rules/design.md v2 §4: 아웃라인 버튼/칩은 border 대신 inset box-shadow(레이아웃 시프트 방지).
        outline: 'inset 0 0 0 1px var(--color-line-normal)',
        'outline-strong': 'inset 0 0 0 1.5px var(--color-line-normal)',
        // PC 워크벤치(디자인 §3b): 선택 행 좌측 2px 인디케이터 / primary 1px 아웃라인 / 현재 단계 링.
        'rail-active': 'inset 2px 0 0 var(--color-primary-normal)',
        'rail-focus': 'inset 0 0 0 1px var(--color-primary-normal)',
        'step-current': '0 0 0 4px var(--chip-approval-bg)',
        // 선택형 카드(라디오) 전용 — rail-focus(1px)보다 두꺼운 2px 링(rules/design.md §4).
        'select-ring': 'inset 0 0 0 2px var(--color-primary-normal)',
        'select-ring-idle': 'inset 0 0 0 1.5px var(--color-line-strong)',
      },
      transitionDuration: {
        fast: 'var(--fast)',
        std: 'var(--std)',
        slow: 'var(--slow)',
        btn: 'var(--btn-dur)',
        chip: 'var(--chip-dur)',
      },
      transitionTimingFunction: {
        'e-in': 'var(--e-in)',
        'e-std': 'var(--e-std)',
        v2: 'var(--e-v2)',
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
