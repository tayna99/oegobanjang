// Shared primitives — Buttons, Chips, Badges, RiskPill, etc.
// All values pulled from Montage tokens in colors_and_type.css.

const Button = ({ variant = 'solid', size = 'medium', children, onClick, disabled, fullWidth, leadingIcon, trailingIcon, danger }) => {
  const base = {
    fontFamily: 'inherit', border: 0, cursor: disabled ? 'not-allowed' : 'pointer',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6,
    width: fullWidth ? '100%' : 'fit-content', whiteSpace: 'nowrap',
    transition: 'background-color .2s ease, color .2s ease, box-shadow .2s ease',
  };
  const sizes = {
    small:  { padding: '6px 12px', borderRadius: 8,  fontSize: 13, fontWeight: 600 },
    medium: { padding: '9px 16px', borderRadius: 10, fontSize: 14, fontWeight: 600 },
    large:  { padding: '12px 24px',borderRadius: 12, fontSize: 16, fontWeight: 700 },
  };
  let palette;
  if (disabled) {
    palette = { background: 'var(--semantic-interaction-disable)', color: 'var(--semantic-label-assistive)' };
  } else if (variant === 'solid' && danger) {
    palette = { background: 'var(--semantic-status-negative)', color: '#fff' };
  } else if (variant === 'solid') {
    palette = { background: 'var(--semantic-primary-normal)', color: '#fff' };
  } else if (variant === 'tonal') {
    palette = { background: 'var(--semantic-fill-normal)', color: 'var(--semantic-label-normal)' };
  } else if (variant === 'outlined') {
    palette = { background: 'transparent', color: 'var(--semantic-label-normal)', boxShadow: 'inset 0 0 0 1px var(--semantic-line-normal-normal)' };
  } else { // ghost
    palette = { background: 'transparent', color: 'var(--semantic-label-neutral)' };
  }
  return (
    <button onClick={disabled ? undefined : onClick} aria-disabled={disabled}
      style={{ ...base, ...sizes[size], ...palette }}
      onMouseEnter={e => { if (variant === 'ghost' && !disabled) e.currentTarget.style.background = 'var(--semantic-fill-normal)'; }}
      onMouseLeave={e => { if (variant === 'ghost') e.currentTarget.style.background = 'transparent'; }}
    >
      {leadingIcon}
      <span>{children}</span>
      {trailingIcon}
    </button>
  );
};

const Chip = ({ active, onClick, children, count }) => (
  <button onClick={onClick} style={{
    fontFamily: 'inherit', fontWeight: 500, border: 0, cursor: 'pointer',
    display: 'inline-flex', alignItems: 'center', gap: 6,
    padding: '7px 12px', borderRadius: 8, fontSize: 13,
    background: active ? 'var(--semantic-inverse-background)' : 'var(--semantic-fill-alternative)',
    color: active ? 'var(--semantic-inverse-label)' : 'var(--semantic-label-normal)',
    transition: 'all .2s ease', whiteSpace: 'nowrap',
  }}>
    <span>{children}</span>
    {count !== undefined && (
      <span style={{
        fontSize: 12, fontWeight: 600, padding: '0 5px', borderRadius: 4, lineHeight: '16px',
        background: active ? 'rgba(255,255,255,0.16)' : 'var(--semantic-fill-strong)',
        color: 'inherit',
      }}>{count}</span>
    )}
  </button>
);

// Risk severity tokens — used everywhere severity appears.
const SEVERITY_PALETTE = {
  CRITICAL: { label: '즉시 확인',  bg: 'rgba(255,66,66,0.10)',   bd: 'rgba(255,66,66,0.32)',  fg: '#B00C0C', dot: '#FF4242', accent: 'var(--semantic-status-negative)' },
  HIGH:     { label: '우선 확인',  bg: 'rgba(255,146,0,0.10)',   bd: 'rgba(255,146,0,0.32)',  fg: '#9C5800', dot: '#FF9200', accent: 'var(--semantic-status-cautionary)' },
  MEDIUM:   { label: '확인 필요',  bg: 'rgba(0,102,255,0.07)',   bd: 'rgba(0,102,255,0.22)',  fg: '#0054D1', dot: '#0066FF', accent: 'var(--semantic-primary-normal)' },
  LOW:      { label: '참고',       bg: 'rgba(112,115,124,0.06)', bd: 'rgba(112,115,124,0.20)',fg: '#46474C', dot: '#878A93', accent: 'var(--semantic-label-neutral)' },
};

const RiskPill = ({ level, dDay, compact }) => {
  const p = SEVERITY_PALETTE[level];
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: compact ? '2px 7px' : '4px 10px', borderRadius: 6,
      fontSize: compact ? 11 : 12, fontWeight: 600, lineHeight: 1.4,
      background: p.bg, color: p.fg,
      border: `1px solid ${p.bd}`,
    }}>
      <span style={{ width: 6, height: 6, borderRadius: 999, background: p.dot, flexShrink: 0 }} />
      {p.label}{dDay && <span style={{ opacity: 0.85, fontWeight: 500 }}> · {dDay}</span>}
    </span>
  );
};

const StatusBadge = ({ tone, children }) => {
  const tones = {
    pending:  { bg: 'rgba(255,146,0,0.10)', fg: '#9C5800' },
    approved: { bg: 'rgba(0,191,64,0.10)',  fg: '#006E25' },
    draft:    { bg: 'var(--semantic-fill-alternative)', fg: 'var(--semantic-label-neutral)' },
    info:     { bg: 'rgba(0,102,255,0.08)', fg: '#0054D1' },
    expired:  { bg: 'rgba(255,66,66,0.10)', fg: '#B00C0C' },
  };
  const t = tones[tone] || tones.draft;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '3px 8px', borderRadius: 6, fontSize: 12, fontWeight: 500,
      background: t.bg, color: t.fg, whiteSpace: 'nowrap',
    }}>{children}</span>
  );
};

const Avatar = ({ name, initial, size = 36, hue = 0 }) => {
  const palettes = [
    'linear-gradient(135deg,#0066FF,#00AEFF)',
    'linear-gradient(135deg,#6541F2,#CB59FF)',
    'linear-gradient(135deg,#FF5E00,#FF9200)',
    'linear-gradient(135deg,#00BF40,#58CF04)',
    'linear-gradient(135deg,#0098B2,#00BDDE)',
    'linear-gradient(135deg,#E846CD,#F553DA)',
  ];
  return (
    <div style={{
      width: size, height: size, borderRadius: 999, flexShrink: 0,
      background: palettes[hue % palettes.length],
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      color: '#fff', fontWeight: 700, fontSize: size * 0.42,
      letterSpacing: '-0.01em',
    }}>{initial || name?.[0]}</div>
  );
};

// Tiny stroke icon set — minimal subset built inline. No emoji.
const Icon = ({ name, size = 18, stroke = 1.6, color = 'currentColor' }) => {
  const paths = {
    bell:        <><path d="M6 8a6 6 0 1 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9z"/><path d="M10 21a2 2 0 0 0 4 0"/></>,
    search:      <><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>,
    plus:        <><path d="M12 5v14M5 12h14"/></>,
    check:       <><path d="m5 12 5 5L20 7"/></>,
    close:       <><path d="m6 6 12 12M18 6 6 18"/></>,
    chevronRight:<><path d="m9 6 6 6-6 6"/></>,
    chevronLeft: <><path d="m15 6-6 6 6 6"/></>,
    chevronDown: <><path d="m6 9 6 6 6-6"/></>,
    chevronUp:   <><path d="m18 15-6-6-6 6"/></>,
    arrowUpRight:<><path d="M7 17 17 7M9 7h8v8"/></>,
    filter:      <><path d="M3 5h18M6 12h12M10 19h4"/></>,
    sort:        <><path d="M8 4v16M8 4l-4 4M8 4l4 4M16 20V4M16 20l-4-4M16 20l4-4"/></>,
    settings:    <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></>,
    file:        <><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/></>,
    fileMissing: <><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M9 14h6M9 17h4"/></>,
    fileCheck:   <><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6m-9 6 2 2 4-4"/></>,
    user:        <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    users:       <><circle cx="9" cy="8" r="3.5"/><path d="M2 21a7 7 0 0 1 14 0"/><circle cx="17" cy="9" r="2.5"/><path d="M16 21a6 6 0 0 1 6-6"/></>,
    calendar:    <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></>,
    clock:       <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    alertTri:    <><path d="m12 4 10 17H2L12 4z"/><path d="M12 10v5M12 18v.5"/></>,
    alertCircle: <><circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16v.5"/></>,
    shield:      <><path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3z"/></>,
    paperPlane:  <><path d="M21 3 3 11l7 2 2 7 9-17z"/><path d="m10 13 5-5"/></>,
    handshake:   <><path d="m12 12-2-2-3 3 5 5 4-4"/><path d="m6 13-3-3 4-4 4 4"/><path d="m18 13 3-3-4-4-4 4"/></>,
    log:         <><path d="M5 4h14v16H5z"/><path d="M9 8h6M9 12h6M9 16h4"/></>,
    refresh:     <><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/></>,
    bookmark:    <><path d="M6 3h12v18l-6-4-6 4z"/></>,
    download:    <><path d="M12 4v12m0 0 4-4m-4 4-4-4M4 20h16"/></>,
    eye:         <><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></>,
    sparkle:     <><path d="m12 3 1.8 5.4 5.4 1.8-5.4 1.8L12 17.4l-1.8-5.4-5.4-1.8 5.4-1.8z"/><path d="M19 4l.7 2 2 .7-2 .7L19 9l-.7-2-2-.7 2-.7z"/></>,
    phone:       <><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/></>,
    chat:        <><path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></>,
    desktop:     <><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></>,
    mobile:      <><rect x="7" y="3" width="10" height="18" rx="2"/><path d="M11 18h2"/></>,
    flag:        <><path d="M5 21V4M5 4h12l-3 4 3 4H5"/></>,
    moon:        <><path d="M21 13A9 9 0 1 1 11 3a7 7 0 0 0 10 10z"/></>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round"
      style={{ flexShrink: 0, display: 'inline-block', verticalAlign: 'middle' }}>
      {paths[name] || null}
    </svg>
  );
};

const Card = ({ children, padded = true, hover, style, ...rest }) => (
  <div style={{
    background: 'var(--semantic-background-elevated-normal)',
    border: '1px solid var(--semantic-line-normal-neutral)',
    borderRadius: 16, padding: padded ? 20 : 0,
    transition: 'box-shadow .2s, border-color .2s',
    ...style,
  }}
    onMouseEnter={hover ? (e) => { e.currentTarget.style.boxShadow = 'var(--shadow-medium)'; e.currentTarget.style.borderColor = 'transparent'; } : undefined}
    onMouseLeave={hover ? (e) => { e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.borderColor = 'var(--semantic-line-normal-neutral)'; } : undefined}
    {...rest}
  >{children}</div>
);

const SectionTitle = ({ children, eyebrow, action }) => (
  <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 16 }}>
    <div>
      {eyebrow && <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--semantic-label-alternative)', marginBottom: 4, letterSpacing: '0.04em', textTransform: 'uppercase' }}>{eyebrow}</div>}
      <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.012em', color: 'var(--semantic-label-normal)' }}>{children}</div>
    </div>
    {action}
  </div>
);

// Brand stamp — '외고반장' with the 반 monogram + Wanted-style underscore
const BrandMark = ({ size = 26, color }) => (
  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontWeight: 800, fontSize: size, letterSpacing: '-0.025em', color: color || 'var(--semantic-label-strong)' }}>
    <span style={{
      width: size + 4, height: size + 4, borderRadius: (size + 4) / 4,
      background: 'var(--semantic-primary-normal)', color: '#fff',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.62, fontWeight: 800,
    }}>반</span>
    <span>외고반장</span>
  </span>
);

// Severity color helpers (used in row borders, dots)
const sevColor = (level) => SEVERITY_PALETTE[level]?.dot || '#878A93';

Object.assign(window, {
  Button, Chip, RiskPill, StatusBadge, Avatar, Icon, Card, SectionTitle, BrandMark,
  SEVERITY_PALETTE, sevColor,
});
