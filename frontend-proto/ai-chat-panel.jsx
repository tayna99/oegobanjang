// AI 반장 챗봇 사이드 패널 — PC 우측 슬라이드인 형태.
// 워크비자 "워크톡" 스타일 플로팅 버튼으로 열림.
// 목 응답만 제공 (실제 API 연결 없음).

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

const AIChatMessage = ({ msg }) => {
  if (msg.role === 'user') {
    return (
      <div style={{ alignSelf: 'flex-end', maxWidth: '80%' }}>
        <div style={{ padding: '9px 13px', borderRadius: '16px 16px 4px 16px',
          background: 'var(--semantic-primary-normal)', color: '#fff',
          fontSize: 13.5, lineHeight: 1.45 }}>
          {msg.text}
        </div>
      </div>
    );
  }

  const r = msg.response;

  if (r?.type === 'case-summary') {
    const sev = SEVERITY_PALETTE[r.sev];
    return (
      <div style={{ alignSelf: 'flex-start', maxWidth: '90%' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
          <div style={{ width: 26, height: 26, borderRadius: 999, flexShrink: 0,
            background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)', color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 700, fontSize: 11, marginBottom: 2 }}>반</div>
          <div style={{ padding: '12px 14px', borderRadius: '4px 16px 16px 16px',
            background: '#fff', border: '1px solid var(--semantic-line-normal-alternative)',
            boxShadow: 'var(--shadow-xsmall)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <span style={{ fontSize: 14 }}>{r.flag}</span>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--semantic-label-normal)' }}>{r.worker}</span>
              <span style={{ padding: '2px 7px', borderRadius: 5, fontSize: 11, fontWeight: 600,
                background: sev.bg, color: sev.fg }}>{r.sev}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {r.items.map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 7,
                  fontSize: 12.5, color: 'var(--semantic-label-neutral)' }}>
                  <span style={{ fontSize: 12, color: i === 0 ? sev.fg : 'var(--semantic-label-alternative)' }}>
                    {i === 0 ? '⚠' : '·'}
                  </span>
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (r?.type === 'deadline-list') {
    return (
      <div style={{ alignSelf: 'flex-start', maxWidth: '92%' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
          <div style={{ width: 26, height: 26, borderRadius: 999, flexShrink: 0,
            background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)', color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 700, fontSize: 11, marginBottom: 2 }}>반</div>
          <div style={{ padding: '12px 14px', borderRadius: '4px 16px 16px 16px',
            background: '#fff', border: '1px solid var(--semantic-line-normal-alternative)',
            boxShadow: 'var(--shadow-xsmall)' }}>
            <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', marginBottom: 8, fontWeight: 500 }}>
              이번 주 기한 임박 건
            </div>
            {r.items.map((item, i) => {
              const sev = SEVERITY_PALETTE[item.sev];
              return (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8,
                  padding: '7px 0', borderBottom: i < r.items.length - 1 ? '1px solid var(--semantic-line-normal-alternative)' : 0 }}>
                  <span style={{ fontSize: 13 }}>{item.flag}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--semantic-label-normal)', flex: 1 }}>{item.name}</span>
                  <span style={{ padding: '2px 7px', borderRadius: 5, fontSize: 11, fontWeight: 600,
                    background: sev.bg, color: sev.fg }}>{item.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  if (r?.type === 'doc-gap-list') {
    return (
      <div style={{ alignSelf: 'flex-start', maxWidth: '92%' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
          <div style={{ width: 26, height: 26, borderRadius: 999, flexShrink: 0,
            background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)', color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 700, fontSize: 11, marginBottom: 2 }}>반</div>
          <div style={{ padding: '12px 14px', borderRadius: '4px 16px 16px 16px',
            background: '#fff', border: '1px solid var(--semantic-line-normal-alternative)',
            boxShadow: 'var(--shadow-xsmall)' }}>
            <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', marginBottom: 8, fontWeight: 500 }}>
              서류 누락 현황
            </div>
            {r.items.map((item, i) => (
              <div key={i} style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--semantic-label-normal)', marginBottom: 4 }}>
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
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ alignSelf: 'flex-start', maxWidth: '90%' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
        <div style={{ width: 26, height: 26, borderRadius: 999, flexShrink: 0,
          background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)', color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 700, fontSize: 11, marginBottom: 2 }}>반</div>
        <div style={{ padding: '10px 13px', borderRadius: '4px 16px 16px 16px',
          background: '#fff', border: '1px solid var(--semantic-line-normal-alternative)',
          boxShadow: 'var(--shadow-xsmall)',
          fontSize: 13, color: 'var(--semantic-label-neutral)', lineHeight: 1.5 }}>
          {r?.text || msg.text}
        </div>
      </div>
    </div>
  );
};

const AIChatPanel = ({ open, onClose }) => {
  const [messages, setMessages] = React.useState([
    {
      id: 0, role: 'ai',
      response: { type: 'generic', text: '안녕하세요! 오늘 외고 업무 관련해서 궁금한 것을 물어보세요.' },
    }
  ]);
  const [input, setInput] = React.useState('');
  const messagesEndRef = React.useRef(null);
  const suggestions = ['Nguyen 현황 알려줘', '이번 주 기한 임박 건?', '서류 누락 목록 보여줘'];

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = (text) => {
    const userMsg = { id: Date.now(), role: 'user', text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setTimeout(() => {
      const response = getMockResponse(text);
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'ai', response }]);
    }, 600);
  };

  return (
    <>
      {/* 오버레이 */}
      {open && (
        <div onClick={onClose} style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.18)', zIndex: 299,
        }}/>
      )}

      {/* 패널 본체 */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0,
        width: 380, zIndex: 300,
        background: 'var(--semantic-background-normal-alternative)',
        boxShadow: '-4px 0 32px rgba(0,0,0,0.14)',
        display: 'flex', flexDirection: 'column',
        transform: open ? 'translateX(0)' : 'translateX(100%)',
        transition: 'transform 0.28s cubic-bezier(0.4,0,0.2,1)',
      }}>

        {/* 헤더 */}
        <div style={{ padding: '16px 18px',
          background: 'rgba(255,255,255,0.95)', backdropFilter: 'blur(20px)',
          borderBottom: '1px solid var(--semantic-line-normal-neutral)',
          display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
          <div style={{ width: 34, height: 34, borderRadius: 999,
            background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontWeight: 800, fontSize: 14 }}>반</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.2 }}>AI 반장</div>
            <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)',
              display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 6, height: 6, borderRadius: 999, background: '#10B981' }}/>
              한별제조 · 실시간 응답
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 0,
            cursor: 'pointer', padding: 6, borderRadius: 8,
            color: 'var(--semantic-label-alternative)' }}>
            <Icon name="close" size={18}/>
          </button>
        </div>

        {/* 메시지 목록 */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '14px 14px 8px',
          display: 'flex', flexDirection: 'column', gap: 10 }}>
          {messages.map(msg => <AIChatMessage key={msg.id} msg={msg}/>)}
          <div ref={messagesEndRef}/>
        </div>

        {/* 빠른 질문 칩 */}
        <div style={{ padding: '8px 14px 4px', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {suggestions.map(s => (
            <button key={s} onClick={() => send(s)} style={{
              padding: '5px 11px', borderRadius: 999, fontSize: 12, fontWeight: 500,
              background: '#fff', color: '#1B3FA0',
              border: '1px solid rgba(27,63,160,0.28)', cursor: 'pointer',
              fontFamily: 'inherit', whiteSpace: 'nowrap',
            }}>{s}</button>
          ))}
        </div>

        {/* 입력창 */}
        <div style={{ padding: '8px 12px 16px',
          background: '#fff',
          borderTop: '1px solid var(--semantic-line-normal-alternative)',
          display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8,
            padding: '9px 14px', borderRadius: 999,
            background: 'var(--semantic-fill-alternative)' }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && input.trim()) send(input); }}
              placeholder="외고 업무 관련 질문..."
              style={{ flex: 1, border: 0, background: 'transparent', outline: 'none',
                fontFamily: 'inherit', fontSize: 14, color: 'var(--semantic-label-normal)' }}
            />
          </div>
          <button onClick={() => { if (input.trim()) send(input); }} style={{
            width: 38, height: 38, borderRadius: 999, border: 0, cursor: 'pointer',
            background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Icon name="paperPlane" size={16} color="#fff"/>
          </button>
        </div>
      </div>
    </>
  );
};

// 플로팅 챗 버튼 (모바일 전용)
const FloatingChatButton = ({ onClick }) => (
  <button onClick={onClick} style={{
    position: 'fixed', bottom: 28, right: 20, zIndex: 290,
    width: 52, height: 52, borderRadius: 999, border: 0, cursor: 'pointer',
    background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
    boxShadow: '0 4px 16px rgba(27,63,160,0.4)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  }}>
    <Icon name="sparkle" size={22} color="#fff"/>
  </button>
);

Object.assign(window, { AIChatPanel, FloatingChatButton });
