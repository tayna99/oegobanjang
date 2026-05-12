// AI 반장 챗봇 — 워크톡 스타일 중앙 팝업 모달
// 헤더 버튼 클릭 → 화면 중앙 팝업 형태로 열림

const AI_MOCK_RESPONSES = {
  nguyen: {
    type: 'case-summary',
    worker: 'Nguyen V.',
    flag: '🇻🇳',
    sev: 'HIGH',
    items: [
      'E-9 체류만료 D-30 (2026.06.07)',
      '여권 사본 누락',
      '외국인등록증 사본 누락',
      '베트남어 서류 요청 초안 준비 완료',
    ],
  },
  기한: {
    type: 'deadline-list',
    items: [
      { name: 'Bayar M.',     flag: '🇲🇳', label: '체류만료 초과 D+3',  sev: 'CRITICAL' },
      { name: 'Nguyen V.',    flag: '🇻🇳', label: '체류만료 D-30',      sev: 'HIGH' },
      { name: 'Tran T. H.',   flag: '🇻🇳', label: '계약종료 D-45',      sev: 'MEDIUM' },
    ],
  },
  서류: {
    type: 'doc-gap-list',
    items: [
      { name: 'Nguyen V.', flag: '🇻🇳', missing: ['여권 사본', '외국인등록증 사본'] },
      { name: 'Mohammad I.', flag: '🇧🇩', missing: ['재계약 근로계약서'] },
    ],
  },
};

const getMockResponse = (text) => {
  if (text.includes('Nguyen') || text.includes('nguyen') || text.includes('응우옌')) {
    return AI_MOCK_RESPONSES.nguyen;
  }
  if (text.includes('기한') || text.includes('임박') || text.includes('만료')) {
    return AI_MOCK_RESPONSES['기한'];
  }
  if (text.includes('서류') || text.includes('누락')) {
    return AI_MOCK_RESPONSES['서류'];
  }
  return { type: 'generic', text: '담당자 확인이 필요한 내용입니다. 판단 기록을 확인하세요.' };
};

// AI 아바타 (그라디언트 원형)
const AIAvatar = ({ size = 34 }) => (
  <div style={{
    width: size, height: size, borderRadius: 999, flexShrink: 0,
    background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: '#fff', fontWeight: 800, fontSize: size * 0.38,
    boxShadow: '0 2px 8px rgba(27,63,160,0.3)',
  }}>반</div>
);

const AIChatMessage = ({ msg }) => {
  if (msg.role === 'user') {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'flex-end', gap: 6, marginBottom: 8 }}>
        <span style={{ fontSize: 11, color: '#aaa', marginBottom: 2 }}>나</span>
        <div style={{
          padding: '10px 14px', borderRadius: '18px 18px 4px 18px',
          background: '#1B3FA0', color: '#fff',
          fontSize: 13.5, lineHeight: 1.5, maxWidth: '72%',
          boxShadow: '0 2px 8px rgba(27,63,160,0.25)',
        }}>
          {msg.text}
        </div>
      </div>
    );
  }

  const r = msg.response;

  const BubbleWrapper = ({ children }) => (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, marginBottom: 10 }}>
      <AIAvatar size={32}/>
      <div style={{
        padding: '11px 14px', borderRadius: '4px 18px 18px 18px',
        background: '#fff', border: '1px solid #e8ecf4',
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        maxWidth: '78%',
      }}>
        {children}
      </div>
    </div>
  );

  if (r?.type === 'case-summary') {
    const sev = SEVERITY_PALETTE[r.sev];
    return (
      <BubbleWrapper>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
          <span style={{ fontSize: 14 }}>{r.flag}</span>
          <span style={{ fontSize: 13.5, fontWeight: 700, color: '#1a1a2e' }}>{r.worker}</span>
          <span style={{ padding: '2px 7px', borderRadius: 5, fontSize: 11, fontWeight: 600,
            background: sev.bg, color: sev.fg }}>{r.sev}</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          {r.items.map((item, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 7,
              fontSize: 12.5, color: i === 0 ? '#b45309' : '#555' }}>
              <span>{i === 0 ? '⚠' : '·'}</span>
              {item}
            </div>
          ))}
        </div>
      </BubbleWrapper>
    );
  }

  if (r?.type === 'deadline-list') {
    return (
      <BubbleWrapper>
        <div style={{ fontSize: 12, color: '#888', marginBottom: 8, fontWeight: 500 }}>
          이번 주 기한 임박 건
        </div>
        {r.items.map((item, i) => {
          const sev = SEVERITY_PALETTE[item.sev];
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8,
              padding: '7px 0', borderBottom: i < r.items.length - 1 ? '1px solid #f0f0f0' : 0 }}>
              <span style={{ fontSize: 13 }}>{item.flag}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a2e', flex: 1 }}>{item.name}</span>
              <span style={{ padding: '2px 7px', borderRadius: 5, fontSize: 11, fontWeight: 600,
                background: sev.bg, color: sev.fg }}>{item.label}</span>
            </div>
          );
        })}
      </BubbleWrapper>
    );
  }

  if (r?.type === 'doc-gap-list') {
    return (
      <BubbleWrapper>
        <div style={{ fontSize: 12, color: '#888', marginBottom: 8, fontWeight: 500 }}>
          서류 누락 현황
        </div>
        {r.items.map((item, i) => (
          <div key={i} style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a2e', marginBottom: 4 }}>
              {item.flag} {item.name}
            </div>
            {item.missing.map((m, j) => (
              <div key={j} style={{ display: 'flex', alignItems: 'center', gap: 6,
                fontSize: 12, color: '#9C5800', marginBottom: 2 }}>
                <span>⚠</span> {m} 누락
              </div>
            ))}
          </div>
        ))}
      </BubbleWrapper>
    );
  }

  return (
    <BubbleWrapper>
      <div style={{ fontSize: 13.5, color: '#444', lineHeight: 1.55 }}>
        {r?.text || msg.text}
      </div>
    </BubbleWrapper>
  );
};

// ✦ 스파클 아이콘 (SVG)
const SparkleIcon = ({ size = 18, color = '#fff' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path d="M12 2L13.5 8.5L20 10L13.5 11.5L12 18L10.5 11.5L4 10L10.5 8.5L12 2Z"
      fill={color} stroke={color} strokeWidth="0.5" strokeLinejoin="round"/>
    <path d="M19 2L19.8 4.2L22 5L19.8 5.8L19 8L18.2 5.8L16 5L18.2 4.2L19 2Z"
      fill={color} opacity="0.7"/>
  </svg>
);

// 헤더 버튼 (워크톡 알약형 스타일)
const AIReflexButton = ({ onClick }) => (
  <button onClick={onClick} style={{
    display: 'flex', alignItems: 'center', gap: 7,
    padding: '8px 16px', borderRadius: 999, border: 0, cursor: 'pointer',
    background: 'linear-gradient(135deg, #1B3FA0 0%, #00BFA5 100%)',
    color: '#fff', fontWeight: 700, fontSize: 13.5, fontFamily: 'inherit',
    boxShadow: '0 3px 12px rgba(27,63,160,0.35)',
    letterSpacing: '-0.01em', whiteSpace: 'nowrap',
    transition: 'opacity 0.15s, transform 0.15s',
  }}
    onMouseEnter={e => { e.currentTarget.style.opacity = '0.9'; e.currentTarget.style.transform = 'scale(1.03)'; }}
    onMouseLeave={e => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.transform = 'scale(1)'; }}
  >
    <SparkleIcon size={15} color="#fff"/>
    AI 반장
  </button>
);

// 중앙 팝업 모달 (워크톡 스타일)
const AIChatPanel = ({ open, onClose }) => {
  const [messages, setMessages] = React.useState([
    {
      id: 0, role: 'ai',
      response: { type: 'generic', text: '안녕하세요! 오늘 외고 업무 관련해서 궁금한 것을 물어보세요. 근로자 현황, 기한 임박 건, 서류 누락 등을 확인할 수 있어요.' },
    }
  ]);
  const [input, setInput] = React.useState('');
  const messagesEndRef = React.useRef(null);
  const suggestions = ['Nguyen 현황 알려줘', '이번 주 기한 임박 건?', '서류 누락 목록 보여줘'];

  React.useEffect(() => {
    if (open) {
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    }
  }, [messages, open]);

  const send = (text) => {
    if (!text.trim()) return;
    const userMsg = { id: Date.now(), role: 'user', text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setTimeout(() => {
      const response = getMockResponse(text);
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'ai', response }]);
    }, 600);
  };

  if (!open) return null;

  return (
    <>
      {/* 반투명 오버레이 */}
      <div onClick={onClose} style={{
        position: 'fixed', inset: 0,
        background: 'rgba(10,20,60,0.38)', zIndex: 990,
        backdropFilter: 'blur(3px)',
      }}/>

      {/* 팝업 모달 본체 */}
      <div style={{
        position: 'fixed',
        top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        width: 440, height: 580,
        zIndex: 991,
        background: '#f4f6fb',
        borderRadius: 20,
        boxShadow: '0 24px 80px rgba(0,0,0,0.22)',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
        animation: 'aiChatFadeIn 0.22s cubic-bezier(0.4,0,0.2,1)',
      }}>
        <style>{`
          @keyframes aiChatFadeIn {
            from { opacity: 0; transform: translate(-50%, -48%) scale(0.96); }
            to   { opacity: 1; transform: translate(-50%, -50%) scale(1); }
          }
        `}</style>

        {/* 헤더 */}
        <div style={{
          background: 'linear-gradient(135deg, #1B3FA0 0%, #00BFA5 100%)',
          padding: '14px 16px 12px',
          display: 'flex', alignItems: 'center', gap: 10,
          flexShrink: 0,
        }}>
          {/* 좌: 아바타 + 이름 */}
          <AIAvatar size={36}/>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#fff', lineHeight: 1.2 }}>AI 반장</div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.75)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 6, height: 6, borderRadius: 999, background: '#7FFFCC', display: 'inline-block' }}/>
              한별제조 · 실시간
            </div>
          </div>
          {/* 우: 캡처 · 상점 · 설정 + 닫기 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {['캡처', '상점', '설정'].map(t => (
              <button key={t} style={{
                background: 'transparent', border: 0, cursor: 'pointer',
                color: 'rgba(255,255,255,0.85)', fontSize: 12, fontFamily: 'inherit', fontWeight: 500,
                padding: '2px 0',
              }}>{t}</button>
            ))}
            <button onClick={onClose} style={{
              background: 'rgba(255,255,255,0.2)', border: 0, cursor: 'pointer',
              width: 26, height: 26, borderRadius: 999,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontSize: 15, fontWeight: 700, fontFamily: 'inherit',
            }}>✕</button>
          </div>
        </div>

        {/* 메시지 목록 */}
        <div style={{
          flex: 1, overflowY: 'auto', padding: '14px 14px 6px',
          display: 'flex', flexDirection: 'column',
        }}>
          {messages.map(msg => <AIChatMessage key={msg.id} msg={msg}/>)}
          <div ref={messagesEndRef}/>
        </div>

        {/* 빠른 질문 칩 */}
        <div style={{ padding: '6px 14px 4px', display: 'flex', gap: 6, flexWrap: 'wrap', flexShrink: 0 }}>
          {suggestions.map(s => (
            <button key={s} onClick={() => send(s)} style={{
              padding: '5px 12px', borderRadius: 999, fontSize: 12, fontWeight: 500,
              background: '#fff', color: '#1B3FA0',
              border: '1.5px solid rgba(27,63,160,0.22)', cursor: 'pointer',
              fontFamily: 'inherit', whiteSpace: 'nowrap',
              boxShadow: '0 1px 4px rgba(27,63,160,0.08)',
            }}>{s}</button>
          ))}
        </div>

        {/* 입력창 (워크톡 스타일: 파란 테두리 + 스파클 + 전송) */}
        <div style={{ padding: '8px 12px 14px', flexShrink: 0, background: '#f4f6fb' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 0,
            background: '#fff', borderRadius: 12,
            border: '2px solid #1B3FA0',
            overflow: 'hidden',
            boxShadow: '0 2px 8px rgba(27,63,160,0.10)',
          }}>
            {/* 스파클 아이콘 (왼쪽) */}
            <div style={{
              padding: '0 10px', display: 'flex', alignItems: 'center',
            }}>
              <SparkleIcon size={18} color="#1B3FA0"/>
            </div>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') send(input); }}
              placeholder="외고 업무 관련 질문..."
              style={{
                flex: 1, border: 0, outline: 'none', background: 'transparent',
                fontFamily: 'inherit', fontSize: 14,
                color: '#1a1a2e', padding: '11px 0',
              }}
            />
            {/* 전송 버튼 (파란 원형 화살표) */}
            <button
              onClick={() => send(input)}
              style={{
                margin: '5px 8px',
                width: 34, height: 34, borderRadius: 999, border: 0, cursor: 'pointer',
                background: input.trim()
                  ? 'linear-gradient(135deg, #1B3FA0, #00BFA5)'
                  : '#c8d4e8',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0, transition: 'background 0.15s',
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M5 12h14M12 5l7 7-7 7" stroke="#fff" strokeWidth="2.5"
                  strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

// 플로팅 챗 버튼 (모바일 우측 하단 고정)
const FloatingChatButton = ({ onClick }) => (
  <button onClick={onClick} style={{
    position: 'fixed', bottom: 88, right: 16, zIndex: 290,
    display: 'flex', alignItems: 'center', gap: 7,
    padding: '12px 18px', borderRadius: 999, border: 0, cursor: 'pointer',
    background: 'linear-gradient(135deg, #1B3FA0 0%, #00BFA5 100%)',
    color: '#fff', fontWeight: 700, fontSize: 14, fontFamily: 'inherit',
    boxShadow: '0 4px 20px rgba(27,63,160,0.45)',
    letterSpacing: '-0.01em',
  }}>
    <SparkleIcon size={17} color="#fff"/>
    AI 반장
  </button>
);

Object.assign(window, { AIChatPanel, FloatingChatButton, AIReflexButton });
