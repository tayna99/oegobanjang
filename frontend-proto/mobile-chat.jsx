// 사장님 모바일 채팅 — UI plan §7. 보고/승인/질문 중심.
// AI 반장 캐릭터는 여기에서만 제한적으로 살아남.

const MobileChat = ({ onApprove, onOpenDocReq }) => {
  const [chat, setChat] = React.useState([]);
  const [step, setStep] = React.useState(0);
  const [pendingApproval, setPendingApproval] = React.useState({ act_003: 'pending', act_001: 'pending' });
  const [showDocDraft, setShowDocDraft] = React.useState(false);

  // Auto-emit briefing on mount
  React.useEffect(() => {
    const seq = [
      { type: 'briefing-greeting', delay: 200 },
      { type: 'briefing-summary', delay: 800 },
      { type: 'case-card', case: 'critical', delay: 1400 },
      { type: 'case-card', case: 'high1', delay: 1800 },
      { type: 'case-card', case: 'high2', delay: 2100 },
      { type: 'quick-actions', delay: 2400 },
    ];
    seq.forEach(s => setTimeout(() => setChat(c => [...c, s]), s.delay));
  }, []);

  const send = (msg) => {
    setChat(c => [...c, { type: 'user', text: msg }]);
    if (msg.includes('승인') || msg.includes('서류')) {
      setTimeout(() => {
        setShowDocDraft(true);
        setChat(c => [...c, { type: 'open-doc-draft' }]);
      }, 600);
    } else if (msg.includes('근거')) {
      setTimeout(() => setChat(c => [...c, { type: 'citation-reply' }]), 600);
    } else {
      setTimeout(() => setChat(c => [...c, { type: 'generic-reply', text: msg }]), 600);
    }
  };

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: 'var(--semantic-background-normal-alternative)',
      fontFamily: 'inherit',
    }}>
      {/* iOS-style top bar */}
      <div style={{
        padding: '10px 16px 12px', display: 'flex', alignItems: 'center', gap: 10,
        background: 'rgba(255,255,255,0.92)',
        backdropFilter: 'blur(32px)',
        borderBottom: '1px solid var(--semantic-line-normal-alternative)',
      }}>
        <div style={{
          width: 38, height: 38, borderRadius: 999,
          background: 'var(--semantic-primary-normal)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontWeight: 800, fontSize: 16,
        }}>반</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.2 }}>외고반장</div>
          <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)', display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: 999, background: 'var(--semantic-status-positive)' }}/>
            한별제조 · 5월 8일 금요일
          </div>
        </div>
        <Icon name="phone" size={18} color="var(--semantic-label-neutral)"/>
        <Icon name="bell" size={18} color="var(--semantic-label-neutral)"/>
      </div>

      {/* Chat scroll */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 14px 8px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {chat.map((m, i) => <ChatMessage key={i} m={m} pendingApproval={pendingApproval}
          onApprove={(id) => { setPendingApproval(p => ({ ...p, [id]: 'approved' })); onApprove?.(id); }}
          onOpenDocDraft={() => setShowDocDraft(true)}/>)}
      </div>

      {/* Quick reply chips + composer */}
      <Composer onSend={send}/>

      {/* Doc draft sheet */}
      {showDocDraft && <DocDraftSheet onClose={() => setShowDocDraft(false)}
        onApprove={(id) => { setPendingApproval(p => ({ ...p, [id]: 'approved' })); setShowDocDraft(false); }}/>}
    </div>
  );
};

const ChatMessage = ({ m, pendingApproval, onApprove, onOpenDocDraft }) => {
  if (m.type === 'user') {
    return (
      <div style={{ alignSelf: 'flex-end', maxWidth: '78%' }}>
        <div style={{
          padding: '9px 13px', borderRadius: '16px 16px 4px 16px',
          background: 'var(--semantic-primary-normal)', color: '#fff',
          fontSize: 14, lineHeight: 1.45,
        }}>{m.text}</div>
      </div>
    );
  }
  if (m.type === 'briefing-greeting') {
    return <Bubble><div style={{ fontSize: 14.5, lineHeight: 1.5 }}>사장님, 좋은 아침입니다.<br/>오늘 먼저 확인할 외국인 고용 업무 <b>5건</b>을 정리했습니다.</div></Bubble>;
  }
  if (m.type === 'briefing-summary') {
    return (
      <Bubble>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 2 }}>
          <SummaryTile sev="CRITICAL" count={1} label="즉시 확인"/>
          <SummaryTile sev="HIGH"     count={3} label="우선 확인"/>
          <SummaryTile sev="MEDIUM"   count={2} label="승인 대기"/>
          <SummaryTile sev="LOW"      count={1} label="검토 자료 준비"/>
        </div>
      </Bubble>
    );
  }
  if (m.type === 'case-card') {
    const data = {
      critical: { name: 'Bayar M.',  flag: '🇲🇳', sev: 'CRITICAL', headline: '체류만료 초과 (D+3)',  body: '체류만료일이 3일 지났습니다. 행정사 검토 자료를 준비했습니다. 사장님 승인 후 담당자에게 전달됩니다.', actId: 'act_001', actLabel: '검토 자료 보기' },
      high1:    { name: 'Nguyen V.', flag: '🇻🇳', sev: 'HIGH',     headline: '체류만료 임박 (D-30)', body: '여권 사본·외국인등록증 사본 보완이 필요합니다. 베트남어 요청문 초안이 준비되어 있습니다.', actId: 'act_003', actLabel: '서류 요청 초안 보기' },
      high2:    { name: 'Tran T. H.', flag: '🇻🇳', sev: 'MEDIUM',   headline: '계약·체류 불일치',     body: '계약종료일이 체류만료일보다 85일 빠릅니다. 담당자 검토가 필요합니다.', actId: null, actLabel: null },
    };
    const d = data[m.case];
    const sev = SEVERITY_PALETTE[d.sev];
    const approved = d.actId && pendingApproval[d.actId] === 'approved';
    return (
      <Bubble compact>
        <div style={{ borderLeft: `3px solid ${sev.dot}`, paddingLeft: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
            <RiskPill level={d.sev} compact/>
            <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)' }}>· {d.flag} {d.name}</span>
          </div>
          <div style={{ fontSize: 14.5, fontWeight: 700, color: 'var(--semantic-label-strong)', marginTop: 4 }}>{d.headline}</div>
          <div style={{ fontSize: 13, color: 'var(--semantic-label-neutral)', marginTop: 4, lineHeight: 1.5 }}>{d.body}</div>
          {d.actId && (
            <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
              <Button variant="tonal" size="small" onClick={onOpenDocDraft}>{d.actLabel}</Button>
              {!approved
                ? <Button variant="solid" size="small" leadingIcon={<Icon name="check" size={12}/>} onClick={() => onApprove(d.actId)}>승인하기</Button>
                : <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '6px 10px', fontSize: 12,
                    background: 'rgba(0,191,64,0.10)', color: '#006E25', borderRadius: 8, fontWeight: 600 }}>
                    <Icon name="check" size={12}/> 승인됨
                  </span>
              }
            </div>
          )}
          <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', marginTop: 8, display: 'flex', alignItems: 'center', gap: 4 }}>
            <Icon name="shield" size={11}/>
            승인 전에는 외부로 발송되지 않습니다
          </div>
        </div>
      </Bubble>
    );
  }
  if (m.type === 'quick-actions') {
    return (
      <Bubble compact>
        <div style={{ fontSize: 13, color: 'var(--semantic-label-neutral)', lineHeight: 1.5, marginBottom: 8 }}>
          더 보고 싶은 항목이 있으면 골라주세요.
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {['승인 대기만 보기', '담당자에게 맡기기', '근거 문서 보기', '나중에 보기'].map(t => (
            <span key={t} style={{
              padding: '6px 11px', borderRadius: 999, fontSize: 12.5, fontWeight: 500,
              background: 'var(--semantic-fill-alternative)', color: 'var(--semantic-label-normal)',
              border: '1px solid var(--semantic-line-normal-alternative)',
            }}>{t}</span>
          ))}
        </div>
      </Bubble>
    );
  }
  if (m.type === 'open-doc-draft') {
    return <Bubble compact>
      <div style={{ fontSize: 13, color: 'var(--semantic-label-neutral)', lineHeight: 1.5 }}>
        Nguyen V.님께 보낼 서류 요청 초안을 띄웠습니다. 한국어와 베트남어 두 가지 모두 준비되어 있어요.
      </div>
    </Bubble>;
  }
  if (m.type === 'citation-reply') {
    return <Bubble compact>
      <div style={{ fontSize: 13, color: 'var(--semantic-label-neutral)', lineHeight: 1.5, marginBottom: 6 }}>
        이 판단의 근거는 다음과 같습니다.
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {[
          { g: 'A', s: '출입국관리법 제25조', t: '체류기간 연장허가' },
          { g: 'B', s: 'HiKorea 안내', t: '체류기간 연장 신청 절차' },
        ].map(c => (
          <div key={c.s} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 8px', borderRadius: 6, background: 'var(--semantic-fill-alternative)' }}>
            <span style={{ fontSize: 10, fontWeight: 700, padding: '1px 5px', borderRadius: 3, background: 'var(--semantic-primary-normal)', color: '#fff' }}>{c.g}</span>
            <span style={{ fontSize: 12, fontWeight: 600 }}>{c.s}</span>
            <span style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)' }}>· {c.t}</span>
          </div>
        ))}
      </div>
    </Bubble>;
  }
  if (m.type === 'generic-reply') {
    return <Bubble compact>
      <div style={{ fontSize: 13, color: 'var(--semantic-label-neutral)', lineHeight: 1.5 }}>
        담당자에게 확인 요청을 전달할 수 있습니다. 승인하시겠어요?
      </div>
    </Bubble>;
  }
  return null;
};

const Bubble = ({ children, compact }) => (
  <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, maxWidth: '88%' }}>
    <div style={{
      width: 26, height: 26, borderRadius: 999, flexShrink: 0,
      background: 'var(--semantic-primary-normal)', color: '#fff',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontWeight: 700, fontSize: 11, marginBottom: 2,
    }}>반</div>
    <div style={{
      padding: compact ? '10px 12px' : '11px 14px',
      borderRadius: '4px 16px 16px 16px',
      background: '#fff',
      border: '1px solid var(--semantic-line-normal-alternative)',
      boxShadow: 'var(--shadow-xsmall)',
    }}>{children}</div>
  </div>
);

const SummaryTile = ({ sev, count, label }) => {
  const p = SEVERITY_PALETTE[sev];
  return (
    <div style={{ padding: '8px 10px', borderRadius: 8, background: p.bg, border: `1px solid ${p.bd}` }}>
      <div style={{ fontSize: 11, color: p.fg, fontWeight: 500 }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 3, marginTop: 2 }}>
        <span style={{ fontSize: 22, fontWeight: 700, color: p.fg, letterSpacing: '-0.02em', lineHeight: 1 }}>{count}</span>
        <span style={{ fontSize: 11, color: p.fg }}>건</span>
      </div>
    </div>
  );
};

const Composer = ({ onSend }) => {
  const [val, setVal] = React.useState('');
  const quick = ['오늘 큰일 있어?', '근거 보여줘', '승인 대기만 보여줘'];
  return (
    <div>
      <div style={{ padding: '8px 14px 6px', display: 'flex', gap: 6, overflowX: 'auto' }}>
        {quick.map(q => (
          <button key={q} onClick={() => onSend(q)} style={{
            padding: '6px 12px', borderRadius: 999, fontSize: 12.5, fontWeight: 500,
            background: '#fff', color: 'var(--semantic-primary-normal)',
            border: '1px solid rgba(0,102,255,0.28)', cursor: 'pointer',
            whiteSpace: 'nowrap', fontFamily: 'inherit',
          }}>{q}</button>
        ))}
      </div>
      <div style={{
        padding: '8px 12px 14px', display: 'flex', gap: 8, alignItems: 'center',
        background: '#fff',
        borderTop: '1px solid var(--semantic-line-normal-alternative)',
      }}>
        <div style={{
          flex: 1, display: 'flex', alignItems: 'center', gap: 8,
          padding: '9px 14px', borderRadius: 999,
          background: 'var(--semantic-fill-alternative)',
        }}>
          <input value={val} onChange={e => setVal(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && val.trim()) { onSend(val); setVal(''); } }}
            placeholder="메시지를 입력하세요"
            style={{ flex: 1, border: 0, background: 'transparent', outline: 'none', fontFamily: 'inherit', fontSize: 14 }}/>
        </div>
        <button onClick={() => { if (val.trim()) { onSend(val); setVal(''); } }} style={{
          width: 38, height: 38, borderRadius: 999, border: 0, cursor: 'pointer',
          background: 'var(--semantic-primary-normal)', color: '#fff',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        }}><Icon name="paperPlane" size={16} color="#fff"/></button>
      </div>
    </div>
  );
};

const DocDraftSheet = ({ onClose, onApprove }) => {
  const [tab, setTab] = React.useState('ko');
  const d = window.DOC_REQUEST_DRAFT;
  return (
    <div style={{
      position: 'absolute', inset: 0,
      background: 'var(--semantic-material-dimmer)',
      display: 'flex', alignItems: 'flex-end', zIndex: 10,
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#fff', width: '100%', borderRadius: '20px 20px 0 0',
        maxHeight: '88%', display: 'flex', flexDirection: 'column',
        animation: 'slideUp .25s ease',
      }}>
        <div style={{ display: 'flex', justifyContent: 'center', padding: '8px 0 4px' }}>
          <div style={{ width: 36, height: 4, borderRadius: 999, background: 'var(--semantic-line-normal-normal)' }}/>
        </div>
        <div style={{ padding: '8px 18px 14px' }}>
          <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', letterSpacing: '0.04em', marginBottom: 2 }}>서류 요청 초안 · 검토용</div>
          <div style={{ fontSize: 17, fontWeight: 700 }}>Nguyen V.님 서류 요청</div>
          <div style={{ fontSize: 12, color: 'var(--semantic-label-neutral)', marginTop: 2 }}>{d.reason} · 제출 기한 {fmtDate(d.dueDate)}</div>
        </div>
        <div style={{ display: 'flex', gap: 4, padding: '0 14px', borderBottom: '1px solid var(--semantic-line-normal-alternative)' }}>
          {[['ko', '한국어'], ['vi', 'Tiếng Việt']].map(([id, label]) => (
            <button key={id} onClick={() => setTab(id)} style={{
              padding: '10px 14px', border: 0, background: 'transparent', cursor: 'pointer', fontFamily: 'inherit',
              fontSize: 13, fontWeight: 600,
              color: tab === id ? 'var(--semantic-primary-normal)' : 'var(--semantic-label-alternative)',
              borderBottom: `2px solid ${tab === id ? 'var(--semantic-primary-normal)' : 'transparent'}`,
            }}>{label}</button>
          ))}
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 18 }}>
          <pre style={{
            fontFamily: 'inherit', fontSize: 13.5, lineHeight: 1.7,
            whiteSpace: 'pre-wrap', margin: 0, color: 'var(--semantic-label-normal)',
          }}>{tab === 'ko' ? d.korean : d.vietnamese}</pre>
        </div>
        <div style={{ padding: 14, borderTop: '1px solid var(--semantic-line-normal-alternative)', display: 'flex', gap: 8 }}>
          <Button variant="tonal" size="medium" fullWidth onClick={onClose}>나중에 보기</Button>
          <Button variant="solid" size="medium" fullWidth leadingIcon={<Icon name="check" size={14}/>} onClick={() => onApprove('act_003')}>
            승인하기
          </Button>
        </div>
        <div style={{ padding: '0 14px 14px', fontSize: 11, color: 'var(--semantic-label-alternative)', textAlign: 'center' }}>
          승인 전에는 외부로 발송되지 않습니다.
        </div>
      </div>
    </div>
  );
};

// 기존 챗봇형은 MobileChatLegacy로 보존
const MobileChatLegacy = MobileChat;

// ─── 모바일 브리핑 홈 (카드형) ────────────────────────────

const ApprovalTaskCard = ({ task, onViewDraft, onApprove }) => {
  const statusMap = {
    approval_required: { label: '승인 필요', bg: 'rgba(245,158,11,0.12)', color: '#9C5800', bd: 'rgba(245,158,11,0.3)' },
    review_required:   { label: '검토 필요', bg: 'rgba(59,130,246,0.10)', color: '#1B3FA0', bd: 'rgba(59,130,246,0.3)' },
    replied:           { label: '응답 도착', bg: 'rgba(16,185,129,0.10)', color: '#006E25', bd: 'rgba(16,185,129,0.3)' },
  };
  const s = statusMap[task.status] || statusMap.approval_required;

  return (
    <div style={{
      background: '#fff', borderRadius: 16, overflow: 'hidden',
      border: '1px solid var(--semantic-line-normal-alternative)',
      boxShadow: 'var(--shadow-small)',
      borderTop: `3px solid ${s.bd.replace('0.3', '0.8')}`,
    }}>
      <div style={{ padding: '14px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
          <span style={{ fontSize: 15 }}>{task.flag}</span>
          <span style={{ padding: '2px 8px', borderRadius: 6, fontSize: 11.5, fontWeight: 600,
            background: s.bg, color: s.color }}>
            {s.label}
          </span>
          {task.dDay !== null && (
            <span style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 700,
              color: task.dDay <= 14 ? '#B00C0C' : '#9C5800' }}>
              D-{task.dDay}
            </span>
          )}
        </div>

        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--semantic-label-normal)',
          marginBottom: 4, letterSpacing: '-0.01em', lineHeight: 1.3 }}>
          {task.title}
        </div>

        <div style={{ fontSize: 12.5, fontWeight: 600, color: s.color, marginBottom: 4 }}>
          {task.highlight}
        </div>

        <div style={{ fontSize: 12.5, color: 'var(--semantic-label-neutral)', lineHeight: 1.5 }}>
          {task.body}
        </div>
      </div>

      <div style={{ padding: '0 16px 14px', display: 'flex', gap: 8 }}>
        {task.threadId && (
          <button onClick={() => onViewDraft(task)} style={{
            flex: 1, padding: '9px 0', borderRadius: 10, fontSize: 13, fontWeight: 600,
            background: 'var(--semantic-fill-alternative)', color: 'var(--semantic-label-normal)',
            border: '1px solid var(--semantic-line-normal-alternative)', cursor: 'pointer',
            fontFamily: 'inherit',
          }}>
            초안 보기
          </button>
        )}
        {task.recruitId && (
          <button onClick={() => onViewDraft(task)} style={{
            flex: 1, padding: '9px 0', borderRadius: 10, fontSize: 13, fontWeight: 600,
            background: 'var(--semantic-fill-alternative)', color: 'var(--semantic-label-normal)',
            border: '1px solid var(--semantic-line-normal-alternative)', cursor: 'pointer',
            fontFamily: 'inherit',
          }}>
            검토 자료 보기
          </button>
        )}
        {task.status === 'replied' && (
          <button style={{
            flex: 1, padding: '9px 0', borderRadius: 10, fontSize: 13, fontWeight: 600,
            background: 'var(--semantic-fill-alternative)', color: 'var(--semantic-label-normal)',
            border: '1px solid var(--semantic-line-normal-alternative)', cursor: 'pointer',
            fontFamily: 'inherit',
          }}>
            응답 요약 보기
          </button>
        )}
        {task.status === 'approval_required' && (
          <button onClick={() => onApprove(task)} style={{
            flex: 1, padding: '9px 0', borderRadius: 10, fontSize: 13, fontWeight: 700,
            background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
            color: '#fff', border: 0, cursor: 'pointer', fontFamily: 'inherit',
          }}>
            승인하기
          </button>
        )}
        {task.status === 'review_required' && (
          <button onClick={() => onApprove(task)} style={{
            flex: 1, padding: '9px 0', borderRadius: 10, fontSize: 13, fontWeight: 700,
            background: 'linear-gradient(135deg, #1B3FA0, #3B82F6)',
            color: '#fff', border: 0, cursor: 'pointer', fontFamily: 'inherit',
          }}>
            승인하기
          </button>
        )}
      </div>
    </div>
  );
};

const MobileBriefingHome = ({ onOpenDraft }) => {
  const tasks = window.MOBILE_APPROVAL_TASKS;
  const [approvedIds, setApprovedIds] = React.useState(new Set());
  const [liveAgentTask, setLiveAgentTask] = React.useState(null);
  const [completeIds, setCompleteIds] = React.useState(new Set());

  const handleViewDraft = (task) => {
    if (task.threadId) setLiveAgentTask(task);
    else if (task.recruitId) onOpenDraft?.(task);
  };

  const handleApprove = (task) => {
    setApprovedIds(prev => new Set([...prev, task.id]));
    if (task.threadId) setLiveAgentTask(task);
  };

  const handleAgentApprove = () => {
    if (liveAgentTask) {
      setCompleteIds(prev => new Set([...prev, liveAgentTask.id]));
      setLiveAgentTask(null);
    }
  };

  // Live Agent 화면
  if (liveAgentTask) {
    return (
      <LiveAgentProgressScreen
        taskId={liveAgentTask.id}
        onBack={() => setLiveAgentTask(null)}
        onApprove={handleAgentApprove}
      />
    );
  }

  const pendingCount = tasks.filter(t => !completeIds.has(t.id)).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%',
      background: 'var(--semantic-background-normal-alternative)', fontFamily: 'inherit' }}>

      {/* 상단 헤더 */}
      <div style={{
        padding: '10px 16px 14px',
        background: 'rgba(255,255,255,0.95)',
        backdropFilter: 'blur(32px)',
        borderBottom: '1px solid var(--semantic-line-normal-alternative)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <div style={{ width: 36, height: 36, borderRadius: 999,
            background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontWeight: 800, fontSize: 15 }}>반</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.2 }}>외고반장</div>
            <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)',
              display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 6, height: 6, borderRadius: 999, background: '#10B981' }}/>
              한별제조 · 오늘 브리핑
            </div>
          </div>
          {pendingCount > 0 && (
            <div style={{ padding: '4px 10px', borderRadius: 999, fontSize: 12, fontWeight: 700,
              background: 'rgba(245,158,11,0.14)', color: '#9C5800',
              border: '1px solid rgba(245,158,11,0.35)' }}>
              승인 필요 {pendingCount}건
            </div>
          )}
        </div>

        {/* AI 브리핑 메시지 */}
        <div style={{ padding: '10px 12px', borderRadius: 12,
          background: 'linear-gradient(90deg, rgba(27,63,160,0.06), rgba(0,191,165,0.04))',
          border: '1px solid rgba(27,63,160,0.15)',
          fontSize: 13, color: 'var(--semantic-label-neutral)', lineHeight: 1.55 }}>
          대표님, 오늘 확인이 필요한 외국인 고용 업무가 <strong>{pendingCount}건</strong> 있습니다.
          각 카드를 확인하고 승인해 주세요.
        </div>
      </div>

      {/* 승인 카드 목록 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 14px',
        display: 'flex', flexDirection: 'column', gap: 12 }}>
        {tasks.filter(t => !completeIds.has(t.id)).map(task => (
          <ApprovalTaskCard
            key={task.id}
            task={task}
            onViewDraft={handleViewDraft}
            onApprove={handleApprove}
          />
        ))}
        {completeIds.size > 0 && (
          <div style={{ padding: '14px 0', textAlign: 'center',
            fontSize: 13, color: 'var(--semantic-label-alternative)' }}>
            ✓ {completeIds.size}건 처리 완료 · 판단 기록에 저장되었습니다.
          </div>
        )}
      </div>

      {/* 하단 여백 (홈 인디케이터용) */}
      <div style={{ height: 20 }}/>
    </div>
  );
};

// MobileChat을 MobileBriefingHome으로 교체 (기존은 MobileChatLegacy로 보존)
const MobileChat = MobileBriefingHome;

Object.assign(window, { MobileChat, MobileChatLegacy, MobileBriefingHome, ApprovalTaskCard });
