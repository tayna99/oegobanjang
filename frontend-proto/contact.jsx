// 메시지 관리 탭 — 다국어 컨택 관리 화면.
// 근로자별 채널 + VN/KR 초안 + 예상 응답 시나리오.

const ContactStatusBadge = ({ status }) => {
  const map = {
    draft:            { label: '초안',      bg: 'rgba(107,114,128,0.12)', color: '#374151' },
    pending_approval: { label: '승인 대기', bg: 'rgba(245,158,11,0.12)',  color: '#9C5800' },
    sent:             { label: '발송 완료', bg: 'rgba(59,130,246,0.12)',  color: '#1B3FA0' },
    replied:          { label: '응답 도착', bg: 'rgba(16,185,129,0.12)', color: '#006E25' },
  };
  const s = map[status] || map.draft;
  return (
    <span style={{ padding: '3px 8px', borderRadius: 6, fontSize: 11.5, fontWeight: 600,
      background: s.bg, color: s.color }}>
      {s.label}
    </span>
  );
};

const ChannelIcon = ({ channel }) => {
  const map = {
    Zalo:    { label: 'Z', bg: '#0068FF', color: '#fff' },
    SMS:     { label: 'S', bg: '#6B7280', color: '#fff' },
    Kakao:   { label: 'K', bg: '#FEE500', color: '#3C1E1E' },
    WhatsApp:{ label: 'W', bg: '#25D366', color: '#fff' },
  };
  const c = map[channel] || map.SMS;
  return (
    <span style={{ width: 20, height: 20, borderRadius: 5,
      background: c.bg, color: c.color,
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 10, fontWeight: 800, flexShrink: 0 }}>
      {c.label}
    </span>
  );
};

const ContactThreadList = ({ threads, selectedId, onSelect }) => (
  <div style={{
    width: 260, flexShrink: 0,
    borderRight: '1px solid var(--semantic-line-normal-neutral)',
    display: 'flex', flexDirection: 'column',
    background: 'var(--semantic-background-normal-alternative)',
    overflowY: 'auto',
  }}>
    <div style={{ padding: '16px 16px 10px',
      fontSize: 12, fontWeight: 600, color: 'var(--semantic-label-alternative)',
      letterSpacing: '0.04em', textTransform: 'uppercase',
      borderBottom: '1px solid var(--semantic-line-normal-alternative)',
    }}>
      컨택 목록 · {threads.length}건
    </div>
    {threads.map(t => (
      <button key={t.id} onClick={() => onSelect(t.id)} style={{
        display: 'flex', alignItems: 'flex-start', gap: 10,
        padding: '14px 16px', border: 0, cursor: 'pointer',
        fontFamily: 'inherit', textAlign: 'left',
        background: selectedId === t.id
          ? 'rgba(27,63,160,0.06)'
          : 'transparent',
        borderBottom: '1px solid var(--semantic-line-normal-alternative)',
        borderLeft: selectedId === t.id ? '3px solid #1B3FA0' : '3px solid transparent',
        transition: 'background .15s',
      }}>
        <div style={{ width: 36, height: 36, borderRadius: 999, flexShrink: 0,
          background: 'linear-gradient(135deg, #1B3FA0, #6541F2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontWeight: 700, fontSize: 14 }}>
          {t.workerName[0]}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--semantic-label-normal)' }}>
              {t.workerName}
            </span>
            <span style={{ fontSize: 12 }}>{t.flag}</span>
            <ChannelIcon channel={t.channel}/>
          </div>
          <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: 4 }}>
            {t.lastMessage}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <ContactStatusBadge status={t.status}/>
            <span style={{ fontSize: 11, color: 'var(--semantic-label-alternative)' }}>{t.updatedAt}</span>
          </div>
        </div>
      </button>
    ))}
  </div>
);

const ResponseScenarioCards = ({ scenarios }) => (
  <div style={{ marginTop: 16 }}>
    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--semantic-label-neutral)',
      marginBottom: 8, letterSpacing: '0.02em' }}>
      예상 응답 시나리오
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
      {scenarios.map((s, i) => {
        const colors = [
          { bg: 'rgba(16,185,129,0.08)', bd: 'rgba(16,185,129,0.24)', fg: '#006E25', dot: '#10B981' },
          { bg: 'rgba(59,130,246,0.08)', bd: 'rgba(59,130,246,0.24)', fg: '#1B3FA0', dot: '#3B82F6' },
          { bg: 'rgba(245,158,11,0.08)', bd: 'rgba(245,158,11,0.24)', fg: '#9C5800', dot: '#F59E0B' },
        ];
        const c = colors[i] || colors[0];
        return (
          <div key={s.type} style={{ padding: '10px 12px', borderRadius: 10,
            background: c.bg, border: `1px solid ${c.bd}` }}>
            <div style={{ fontSize: 11.5, fontWeight: 700, color: c.fg, marginBottom: 4 }}>
              {s.label}
            </div>
            <div style={{ fontSize: 12, color: 'var(--semantic-label-neutral)', lineHeight: 1.45 }}>
              {s.desc}
            </div>
          </div>
        );
      })}
    </div>
  </div>
);

const DraftPreviewPanel = ({ thread, onApprove }) => {
  const [langTab, setLangTab] = React.useState('vi');
  const [approved, setApproved] = React.useState(false);

  const langLabels = { ko: '한국어', vi: 'Tiếng Việt', bn: 'বাংলা' };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column',
      background: 'var(--semantic-background-elevated-normal)',
      overflowY: 'auto' }}>

      {/* 패널 헤더 */}
      <div style={{ padding: '20px 24px 16px',
        borderBottom: '1px solid var(--semantic-line-normal-neutral)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <span style={{ fontSize: 20 }}>{thread.flag}</span>
          <div>
            <div style={{ fontSize: 17, fontWeight: 700, color: 'var(--semantic-label-normal)', letterSpacing: '-0.015em' }}>
              {thread.workerName}
            </div>
            <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)' }}>
              {thread.nationality} · {thread.channel} · {thread.workerNameKo}
            </div>
          </div>
          <div style={{ flex: 1 }}/>
          <ContactStatusBadge status={thread.status}/>
        </div>

        <div style={{ padding: '8px 12px', borderRadius: 8,
          background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.24)',
          fontSize: 12.5, color: '#9C5800', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="shield" size={13}/>
          승인 전에는 외부로 발송되지 않습니다. 담당자 검토용 초안입니다.
        </div>
      </div>

      {/* 언어 탭 + 초안 내용 */}
      <div style={{ padding: '0 24px', flex: 1 }}>
        <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--semantic-line-normal-alternative)',
          marginBottom: 16 }}>
          {Object.entries(thread.draftMessage).map(([lang]) => (
            <button key={lang} onClick={() => setLangTab(lang)} style={{
              padding: '10px 14px', border: 0, background: 'transparent', cursor: 'pointer',
              fontFamily: 'inherit', fontSize: 13, fontWeight: 600,
              color: langTab === lang ? '#1B3FA0' : 'var(--semantic-label-alternative)',
              borderBottom: `2px solid ${langTab === lang ? '#1B3FA0' : 'transparent'}`,
              transition: 'color .15s, border-color .15s',
            }}>
              {langLabels[lang] || lang}
            </button>
          ))}
        </div>

        <div style={{
          padding: '16px 18px', borderRadius: 12,
          background: langTab === 'ko'
            ? 'rgba(27,63,160,0.04)'
            : 'rgba(0,191,165,0.04)',
          border: langTab === 'ko'
            ? '1px solid rgba(27,63,160,0.16)'
            : '1px solid rgba(0,191,165,0.16)',
          marginBottom: 16,
        }}>
          <pre style={{
            fontFamily: 'inherit', fontSize: 14, lineHeight: 1.8,
            whiteSpace: 'pre-wrap', margin: 0, color: 'var(--semantic-label-normal)',
          }}>
            {thread.draftMessage[langTab]}
          </pre>
        </div>

        <ResponseScenarioCards scenarios={thread.scenarios}/>
      </div>

      {/* 하단 액션 바 */}
      <div style={{ padding: '16px 24px 20px',
        borderTop: '1px solid var(--semantic-line-normal-neutral)',
        display: 'flex', gap: 8, justifyContent: 'flex-end', flexShrink: 0 }}>
        <Button variant="ghost" size="medium">나중에 보기</Button>
        <Button variant="outlined" size="medium">수정 요청</Button>
        {approved
          ? (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '8px 16px', borderRadius: 10, fontSize: 14, fontWeight: 600,
              background: 'rgba(16,185,129,0.12)', color: '#006E25' }}>
              <Icon name="check" size={14}/> 승인됨
            </span>
          )
          : (
            <Button variant="solid" size="medium"
              leadingIcon={<Icon name="check" size={14}/>}
              onClick={() => setApproved(true)}>
              보내기 승인
            </Button>
          )
        }
      </div>
    </div>
  );
};

const MultilingualContactView = () => {
  const threads = window.CONTACT_THREADS;
  const [selectedThreadId, setSelectedThreadId] = React.useState(threads[0]?.id || null);
  const selectedThread = threads.find(t => t.id === selectedThreadId);

  return (
    <div>
      {/* 헤더 */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em',
          color: 'var(--semantic-label-normal)', marginBottom: 6 }}>
          메시지 관리
        </div>
        <div style={{ fontSize: 14, color: 'var(--semantic-label-alternative)' }}>
          근로자별 다국어 컨택 초안을 확인하고 승인합니다.
        </div>
      </div>

      {/* 좌·우 분할 레이아웃 */}
      <div style={{
        display: 'flex', height: 'calc(100vh - 260px)', minHeight: 480,
        border: '1px solid var(--semantic-line-normal-neutral)',
        borderRadius: 16, overflow: 'hidden',
        background: 'var(--semantic-background-elevated-normal)',
        boxShadow: 'var(--shadow-small)',
      }}>
        <ContactThreadList
          threads={threads}
          selectedId={selectedThreadId}
          onSelect={setSelectedThreadId}
        />
        {selectedThread
          ? <DraftPreviewPanel thread={selectedThread}/>
          : (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--semantic-label-alternative)' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 36, marginBottom: 12 }}>💬</div>
                <div style={{ fontSize: 14 }}>컨택 항목을 선택하세요.</div>
              </div>
            </div>
          )
        }
      </div>
    </div>
  );
};

Object.assign(window, { MultilingualContactView });
