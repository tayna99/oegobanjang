// Live Agent 처리 화면 — 승인 직전 화면.
// Multilingual Contact Agent가 처리 단계를 보여주고, 사장님이 승인하는 구조.

const AgentStepItem = ({ stepData, visible }) => {
  const iconMap = {
    done:        <span style={{ color: '#10B981', fontSize: 16 }}>✓</span>,
    in_progress: (
      <span style={{
        width: 16, height: 16, borderRadius: 999,
        border: '2px solid #1B3FA0',
        borderTopColor: 'transparent',
        display: 'inline-block',
        animation: 'spin 0.8s linear infinite',
      }}/>
    ),
    waiting: <span style={{ color: 'var(--semantic-label-alternative)', fontSize: 14 }}>○</span>,
  };
  const colorMap = {
    done:        { label: '#006E25', detail: 'var(--semantic-label-neutral)' },
    in_progress: { label: '#1B3FA0', detail: 'var(--semantic-label-neutral)' },
    waiting:     { label: 'var(--semantic-label-alternative)', detail: 'var(--semantic-label-alternative)' },
  };
  const c = colorMap[stepData.status];

  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 14,
      padding: '12px 0',
      opacity: visible ? 1 : 0,
      transform: visible ? 'translateY(0)' : 'translateY(12px)',
      transition: 'opacity 0.3s ease, transform 0.3s ease',
    }}>
      <div style={{ width: 28, height: 28, borderRadius: 8, flexShrink: 0,
        background: stepData.status === 'done'
          ? 'rgba(16,185,129,0.12)'
          : stepData.status === 'in_progress'
          ? 'rgba(27,63,160,0.12)'
          : 'var(--semantic-fill-alternative)',
        display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {iconMap[stepData.status]}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: c.label, marginBottom: 2 }}>
          {stepData.step}. {stepData.label}
        </div>
        <div style={{ fontSize: 12.5, color: c.detail }}>{stepData.detail}</div>
      </div>
    </div>
  );
};

const LiveAgentProgressScreen = ({ taskId, onBack, onApprove }) => {
  const [visibleSteps, setVisibleSteps] = React.useState(0);
  const [approved, setApproved] = React.useState(false);
  const steps = window.LIVE_AGENT_STEPS;
  const thread = window.CONTACT_THREADS[0]; // Nguyen 케이스

  React.useEffect(() => {
    steps.forEach((_, i) => {
      setTimeout(() => setVisibleSteps(v => Math.max(v, i + 1)), i * 350 + 100);
    });
  }, []);

  const handleApprove = () => {
    setApproved(true);
    setTimeout(() => onApprove?.(), 400);
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column',
      background: 'var(--semantic-background-normal-alternative)',
      fontFamily: 'inherit' }}>

      {/* 상단 헤더 */}
      <div style={{
        padding: '14px 18px',
        background: 'rgba(255,255,255,0.92)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--semantic-line-normal-alternative)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <button onClick={onBack} style={{ background: 'transparent', border: 0,
          cursor: 'pointer', padding: 4, borderRadius: 6,
          color: 'var(--semantic-label-neutral)' }}>
          <Icon name="chevronLeft" size={18}/>
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--semantic-label-normal)', lineHeight: 1.2 }}>
            Multilingual Contact Agent
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
            <span style={{ width: 6, height: 6, borderRadius: 999, background: '#10B981',
              animation: 'pulse 1.5s infinite' }}/>
            <span style={{ fontSize: 11, color: '#006E25', fontWeight: 600 }}>Live</span>
            <span style={{ fontSize: 11, color: 'var(--semantic-label-alternative)' }}>· 판단 기록 #4789</span>
          </div>
        </div>
      </div>

      {/* 스크롤 콘텐츠 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 18px' }}>

        {/* 처리 단계 */}
        <div style={{ background: '#fff', borderRadius: 14,
          border: '1px solid var(--semantic-line-normal-alternative)',
          padding: '14px 16px', marginBottom: 14,
          boxShadow: 'var(--shadow-xsmall)' }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--semantic-label-alternative)',
            letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 4 }}>
            처리 단계
          </div>
          {steps.map((s, i) => (
            <div key={s.step}>
              <AgentStepItem stepData={s} visible={i < visibleSteps}/>
              {i < steps.length - 1 && (
                <div style={{ width: 1, height: 10, background: 'var(--semantic-line-normal-alternative)',
                  marginLeft: 13, opacity: i < visibleSteps ? 1 : 0, transition: 'opacity 0.3s' }}/>
              )}
            </div>
          ))}
        </div>

        {/* 메시지 초안 카드 */}
        {visibleSteps >= 3 && (
          <div style={{
            background: '#fff', borderRadius: 14,
            border: '1px solid rgba(27,63,160,0.2)',
            overflow: 'hidden', marginBottom: 14,
            boxShadow: 'var(--shadow-xsmall)',
            animation: 'slideUp .3s ease',
          }}>
            <div style={{ padding: '10px 14px',
              background: 'linear-gradient(90deg, rgba(27,63,160,0.06), rgba(0,191,165,0.04))',
              borderBottom: '1px solid rgba(27,63,160,0.12)',
              fontSize: 11, fontWeight: 600, color: '#1B3FA0', letterSpacing: '0.04em',
              textTransform: 'uppercase' }}>
              메시지 초안
            </div>
            <div style={{ padding: '12px 14px 8px' }}>
              <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)',
                marginBottom: 4, fontWeight: 500 }}>🇻🇳 Tiếng Việt</div>
              <div style={{ fontSize: 13, lineHeight: 1.65, color: 'var(--semantic-label-normal)',
                padding: '10px 12px', borderRadius: 8,
                background: 'rgba(0,191,165,0.06)',
                border: '1px solid rgba(0,191,165,0.16)' }}>
                Xin chào Nguyen,<br/>
                vui lòng gửi bản sao hợp đồng lao động tiêu chuẩn và hộ chiếu.
              </div>
            </div>
            <div style={{ padding: '0 14px 12px' }}>
              <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)',
                marginBottom: 4, fontWeight: 500 }}>🇰🇷 한국어</div>
              <div style={{ fontSize: 13, lineHeight: 1.65, color: 'var(--semantic-label-normal)',
                padding: '10px 12px', borderRadius: 8,
                background: 'rgba(27,63,160,0.04)',
                border: '1px solid rgba(27,63,160,0.12)' }}>
                안녕하세요 Nguyen 씨,<br/>
                표준근로계약서 사본과 여권 사본을 보내주세요.
              </div>
            </div>
          </div>
        )}

        {/* 예상 응답 시나리오 */}
        {visibleSteps >= 3 && (
          <div style={{ background: '#fff', borderRadius: 14,
            border: '1px solid var(--semantic-line-normal-alternative)',
            padding: '12px 14px', marginBottom: 14,
            animation: 'slideUp .35s ease' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--semantic-label-alternative)',
              letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 10 }}>
              예상 응답 시나리오
            </div>
            {[
              { label: '긍정 응답', icon: '✅', desc: '서류 수신 후 행정사 검토 자료에 반영' },
              { label: '추가 정보 요청', icon: '❓', desc: '필요 서류 형식 기준 재안내' },
              { label: '응답 지연', icon: '⏱', desc: '2일 뒤 리마인드 메시지 제안' },
            ].map(s => (
              <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 0',
                borderBottom: '1px solid var(--semantic-line-normal-alternative)' }}>
                <span style={{ fontSize: 14 }}>{s.icon}</span>
                <div>
                  <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--semantic-label-normal)' }}>
                    {s.label}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)' }}>{s.desc}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 하단 고정 승인 바 */}
      {visibleSteps >= 3 && (
        <div style={{
          padding: '14px 18px',
          background: '#fff',
          borderTop: '1px solid var(--semantic-line-normal-alternative)',
          display: 'flex', flexDirection: 'column', gap: 8,
          animation: 'slideUp .4s ease',
        }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--semantic-label-normal)',
            textAlign: 'center', marginBottom: 2 }}>
            이 메시지로 컨택할까요?
          </div>
          {approved
            ? (
              <div style={{ padding: '12px', borderRadius: 12, textAlign: 'center',
                background: 'rgba(16,185,129,0.10)', border: '1px solid rgba(16,185,129,0.3)',
                fontSize: 14, fontWeight: 700, color: '#006E25' }}>
                ✓ 승인 완료 · 판단 기록 #4789에 저장됨
              </div>
            )
            : (
              <div style={{ display: 'flex', gap: 8 }}>
                <Button variant="outlined" size="medium" fullWidth>수정 요청</Button>
                <Button variant="solid" size="medium" fullWidth
                  leadingIcon={<Icon name="check" size={14}/>}
                  onClick={handleApprove}>
                  보내기 승인
                </Button>
              </div>
            )
          }
          <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', textAlign: 'center' }}>
            승인 전에는 외부로 발송되지 않습니다
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
      `}</style>
    </div>
  );
};

Object.assign(window, { LiveAgentProgressScreen });
