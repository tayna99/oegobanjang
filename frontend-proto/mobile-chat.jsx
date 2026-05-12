// 사장님 모바일 — 오늘 브리핑 홈 (카드형) + Live Agent 연결
// 레퍼런스: 흰 배경, 상단 로고바, 오늘 브리핑 섹션, 하단 탭바

/* ─── 하단 탭바 아이콘 ─────────────────────────────────────── */
const BOTTOM_TAB_ICONS = {
  home: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M3 9.5L12 3l9 6.5V21a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z"
        stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/>
      <path d="M9 22V12h6v10" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/>
    </svg>
  ),
  workers: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <circle cx="9" cy="7" r="4" stroke="currentColor" strokeWidth="1.7"/>
      <path d="M2 21c0-4 3.134-6 7-6s7 2 7 6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/>
      <circle cx="18" cy="8" r="3" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M22 21c0-3-1.5-5-4-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),
  contact: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M4 4h16a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H6l-3 3V5a1 1 0 0 1 1-1z"
        stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round"/>
    </svg>
  ),
  cases: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M7 3h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"
        stroke="currentColor" strokeWidth="1.7"/>
      <path d="M9 8h6M9 12h6M9 16h3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  ),
  more: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <circle cx="5" cy="12" r="1.5" fill="currentColor"/>
      <circle cx="12" cy="12" r="1.5" fill="currentColor"/>
      <circle cx="19" cy="12" r="1.5" fill="currentColor"/>
    </svg>
  ),
};

/* ─── 하단 탭바 ──────────────────────────────────────────────── */
const BottomTabBar = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'home',    label: '홈',    badge: 0 },
    { id: 'workers', label: '근로자', badge: 0 },
    { id: 'contact', label: '컨택',  badge: 2 },
    { id: 'cases',   label: '케이스', badge: 0 },
    { id: 'more',    label: '더보기', badge: 0 },
  ];

  return (
    <div style={{
      background: 'rgba(255,255,255,0.96)',
      backdropFilter: 'blur(24px)',
      borderTop: '1px solid var(--semantic-line-normal-alternative)',
      display: 'flex',
      paddingBottom: 6,
      flexShrink: 0,
    }}>
      {tabs.map(tab => {
        const active = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            style={{
              flex: 1, display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center',
              gap: 3, padding: '10px 0 4px',
              border: 0, background: 'transparent', cursor: 'pointer',
              fontFamily: 'inherit',
              color: active ? '#1B3FA0' : 'var(--semantic-label-alternative)',
              position: 'relative',
            }}
          >
            <div style={{ position: 'relative' }}>
              {BOTTOM_TAB_ICONS[tab.id]}
              {tab.badge > 0 && (
                <span style={{
                  position: 'absolute', top: -3, right: -5,
                  minWidth: 15, height: 15, padding: '0 3px',
                  borderRadius: 999, background: '#EF4444', color: '#fff',
                  fontSize: 9, fontWeight: 700,
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                }}>{tab.badge}</span>
              )}
            </div>
            <span style={{ fontSize: 10, fontWeight: active ? 700 : 500 }}>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
};

/* ─── 승인 태스크 카드 ────────────────────────────────────────── */
const ApprovalTaskCard = ({ task, onViewDraft, onApprove, approved, completed }) => {
  const statusMap = {
    approval_required: { label: '승인 필요', bg: 'rgba(245,158,11,0.10)', color: '#9C5800', bd: '#F59E0B', topBd: '#F59E0B' },
    review_required:   { label: '검토 필요', bg: 'rgba(59,130,246,0.08)', color: '#1B3FA0', bd: '#3B82F6', topBd: '#3B82F6' },
    replied:           { label: '응답 도착', bg: 'rgba(16,185,129,0.08)', color: '#006E25', bd: '#10B981', topBd: '#10B981' },
  };
  const s = statusMap[task.status] || statusMap.approval_required;

  /* 완료 상태 */
  if (completed) {
    return (
      <div style={{
        background: '#F0FDF4', borderRadius: 16,
        border: '1px solid rgba(16,185,129,0.3)',
        padding: '14px 16px',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <div style={{ width: 32, height: 32, borderRadius: 999,
          background: 'rgba(16,185,129,0.15)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16 }}>✓</div>
        <div>
          <div style={{ fontSize: 13.5, fontWeight: 700, color: '#006E25' }}>{task.title}</div>
          <div style={{ fontSize: 12, color: '#059669', marginTop: 1 }}>처리 완료 · 판단 기록에 저장됨</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      background: '#fff', borderRadius: 16, overflow: 'hidden',
      border: '1px solid var(--semantic-line-normal-alternative)',
      boxShadow: '0 1px 6px rgba(0,0,0,0.06)',
      borderTop: `3px solid ${s.topBd}`,
    }}>
      <div style={{ padding: '14px 16px' }}>
        {/* 상태 배지 + D-day */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
          <span style={{ fontSize: 14 }}>{task.flag}</span>
          <span style={{
            padding: '2px 9px', borderRadius: 99, fontSize: 11.5, fontWeight: 700,
            background: s.bg, color: s.color,
          }}>{s.label}</span>
          {task.dDay !== null && task.dDay !== undefined && (
            <span style={{ marginLeft: 'auto', fontSize: 12.5, fontWeight: 700,
              color: task.dDay <= 14 ? '#B00C0C' : '#9C5800' }}>
              D-{task.dDay}
            </span>
          )}
        </div>

        {/* 제목 */}
        <div style={{ fontSize: 15.5, fontWeight: 700, color: 'var(--semantic-label-normal)',
          marginBottom: 4, letterSpacing: '-0.012em', lineHeight: 1.35 }}>
          {task.title}
        </div>

        {/* 하이라이트 */}
        {task.highlight && (
          <div style={{ fontSize: 13, fontWeight: 600, color: s.color, marginBottom: 4 }}>
            {task.highlight}
          </div>
        )}

        {/* 본문 */}
        <div style={{ fontSize: 13, color: 'var(--semantic-label-neutral)', lineHeight: 1.55 }}>
          {task.body}
        </div>
      </div>

      {/* 액션 버튼 영역 */}
      <div style={{ padding: '0 16px 14px', display: 'flex', gap: 8 }}>
        {/* 초안 보기 (컨택 스레드) */}
        {task.threadId && (
          <button onClick={() => onViewDraft(task)} style={{
            flex: 1, padding: '10px 0', borderRadius: 10, fontSize: 13, fontWeight: 600,
            background: 'var(--semantic-fill-alternative)',
            color: 'var(--semantic-label-normal)',
            border: '1px solid var(--semantic-line-normal-alternative)',
            cursor: 'pointer', fontFamily: 'inherit',
          }}>
            초안 보기
          </button>
        )}
        {/* 검토 자료 보기 (채용) */}
        {task.recruitId && !task.threadId && (
          <button onClick={() => onViewDraft(task)} style={{
            flex: 1, padding: '10px 0', borderRadius: 10, fontSize: 13, fontWeight: 600,
            background: 'var(--semantic-fill-alternative)',
            color: 'var(--semantic-label-normal)',
            border: '1px solid var(--semantic-line-normal-alternative)',
            cursor: 'pointer', fontFamily: 'inherit',
          }}>
            검토 자료 보기
          </button>
        )}
        {/* 응답 요약 */}
        {task.status === 'replied' && (
          <button style={{
            flex: 1, padding: '10px 0', borderRadius: 10, fontSize: 13, fontWeight: 600,
            background: 'var(--semantic-fill-alternative)',
            color: 'var(--semantic-label-normal)',
            border: '1px solid var(--semantic-line-normal-alternative)',
            cursor: 'pointer', fontFamily: 'inherit',
          }}>
            응답 요약 보기
          </button>
        )}
        {/* 승인하기 */}
        {(task.status === 'approval_required' || task.status === 'review_required') && !approved && (
          <button onClick={() => onApprove(task)} style={{
            flex: 1, padding: '10px 0', borderRadius: 10, fontSize: 13, fontWeight: 700,
            background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
            color: '#fff', border: 0, cursor: 'pointer', fontFamily: 'inherit',
          }}>
            승인하기
          </button>
        )}
        {/* 승인됨 */}
        {(task.status === 'approval_required' || task.status === 'review_required') && approved && (
          <div style={{
            flex: 1, padding: '10px 0', borderRadius: 10, fontSize: 13, fontWeight: 700,
            background: 'rgba(16,185,129,0.10)', color: '#006E25',
            border: '1px solid rgba(16,185,129,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
          }}>
            ✓ 승인됨
          </div>
        )}
      </div>

      {/* 안전 문구 */}
      <div style={{ padding: '0 16px 12px',
        fontSize: 11, color: 'var(--semantic-label-alternative)',
        display: 'flex', alignItems: 'center', gap: 4 }}>
        <Icon name="shield" size={11}/>
        승인 전에는 외부로 발송되지 않습니다
      </div>
    </div>
  );
};

/* ─── 모바일 브리핑 홈 ────────────────────────────────────────── */
const MobileBriefingHome = ({ onOpenDraft }) => {
  const tasks = window.MOBILE_APPROVAL_TASKS || [];
  const [activeBottomTab, setActiveBottomTab] = React.useState('home');
  const [approvedIds, setApprovedIds] = React.useState(new Set());
  const [completeIds, setCompleteIds] = React.useState(new Set());
  const [liveAgentTask, setLiveAgentTask] = React.useState(null);
  const [draftTask, setDraftTask] = React.useState(null);      // 초안 보기 화면
  const [completeTask, setCompleteTask] = React.useState(null); // 승인 완료 화면

  const handleViewDraft = (task) => {
    // 초안 보기 화면으로 전환
    const thread = (window.CONTACT_THREADS || []).find(t => t.id === task.threadId);
    setDraftTask({ task, thread });
  };

  const handleApprove = (task) => {
    setApprovedIds(prev => new Set([...prev, task.id]));
    // 승인하기 → 초안 보기로 이동 (컨택 스레드가 있을 때)
    if (task.threadId) {
      const thread = (window.CONTACT_THREADS || []).find(t => t.id === task.threadId);
      setDraftTask({ task, thread });
    }
  };

  const handleDraftApprove = () => {
    // 초안 승인 → 승인 완료 화면
    if (draftTask) {
      setCompleteTask(draftTask.task);
      setCompleteIds(prev => new Set([...prev, draftTask.task.id]));
      setDraftTask(null);
    }
  };

  const handleAgentApprove = () => {
    if (liveAgentTask) {
      setCompleteTask(liveAgentTask);
      setCompleteIds(prev => new Set([...prev, liveAgentTask.id]));
      setLiveAgentTask(null);
    }
  };

  /* 승인 완료 화면 */
  if (completeTask) {
    return (
      <div style={{ height: '100%', position: 'relative' }}>
        <ApprovalCompleteScreen
          task={completeTask}
          onBack={() => setCompleteTask(null)}
          onViewLog={() => setCompleteTask(null)}
        />
      </div>
    );
  }

  /* 초안 보기 화면 */
  if (draftTask) {
    return (
      <div style={{ height: '100%', position: 'relative' }}>
        <MobileDraftView
          task={draftTask.task}
          thread={draftTask.thread}
          onBack={() => setDraftTask(null)}
          onApprove={handleDraftApprove}
        />
      </div>
    );
  }

  /* Live Agent 화면 */
  if (liveAgentTask) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, minHeight: 0 }}>
          <LiveAgentProgressScreen
            taskId={liveAgentTask.id}
            onBack={() => setLiveAgentTask(null)}
            onApprove={handleAgentApprove}
          />
        </div>
      </div>
    );
  }

  const pendingCount = tasks.filter(t =>
    !completeIds.has(t.id) &&
    (t.status === 'approval_required' || t.status === 'review_required')
  ).length;

  /* 탭별 빈 화면 */
  const renderTabContent = () => {
    if (activeBottomTab !== 'home') {
      const labels = { workers: '근로자', contact: '컨택', cases: '케이스', more: '더보기' };
      return (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          color: 'var(--semantic-label-alternative)', gap: 8 }}>
          <div style={{ fontSize: 36 }}>
            {activeBottomTab === 'workers' ? '👤' :
             activeBottomTab === 'contact' ? '💬' :
             activeBottomTab === 'cases'   ? '📋' : '⋯'}
          </div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{labels[activeBottomTab]}</div>
          <div style={{ fontSize: 12 }}>PC 화면에서 확인할 수 있습니다</div>
        </div>
      );
    }

    return (
      <>
        {/* AI 브리핑 메시지 버블 */}
        <div style={{
          margin: '16px 14px 0',
          padding: '12px 14px', borderRadius: 14,
          background: 'linear-gradient(110deg, rgba(27,63,160,0.06), rgba(0,191,165,0.05))',
          border: '1px solid rgba(27,63,160,0.15)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 6 }}>
            <div style={{
              width: 24, height: 24, borderRadius: 7,
              background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontSize: 11, fontWeight: 800, flexShrink: 0,
            }}>반</div>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#1B3FA0' }}>AI 반장</span>
            <span style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', marginLeft: 2 }}>
              · 오늘 08:00
            </span>
          </div>
          <div style={{ fontSize: 13.5, color: 'var(--semantic-label-normal)', lineHeight: 1.6 }}>
            대표님, 오늘 확인이 필요한 외국인 고용 업무가{' '}
            <strong style={{ color: '#1B3FA0' }}>{pendingCount}건</strong> 있습니다.
            각 카드를 확인하고 승인해 주세요.
          </div>
        </div>

        {/* 섹션 타이틀 */}
        <div style={{ padding: '18px 14px 8px',
          fontSize: 13, fontWeight: 700, color: 'var(--semantic-label-normal)',
          display: 'flex', alignItems: 'center', gap: 7 }}>
          승인 대기 업무
          {pendingCount > 0 && (
            <span style={{ padding: '2px 8px', borderRadius: 99, fontSize: 11, fontWeight: 700,
              background: 'rgba(245,158,11,0.14)', color: '#9C5800',
              border: '1px solid rgba(245,158,11,0.35)' }}>
              {pendingCount}건
            </span>
          )}
        </div>

        {/* 카드 목록 */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 14px 16px',
          display: 'flex', flexDirection: 'column', gap: 12 }}>
          {tasks.map(task => (
            <ApprovalTaskCard
              key={task.id}
              task={task}
              approved={approvedIds.has(task.id)}
              completed={completeIds.has(task.id)}
              onViewDraft={handleViewDraft}
              onApprove={handleApprove}
            />
          ))}
          {tasks.length === 0 && (
            <div style={{ padding: '40px 0', textAlign: 'center',
              fontSize: 14, color: 'var(--semantic-label-alternative)' }}>
              오늘 확인할 업무가 없습니다 ✓
            </div>
          )}
          {completeIds.size > 0 && (
            <div style={{ padding: '10px 0', textAlign: 'center',
              fontSize: 12.5, color: 'var(--semantic-label-alternative)' }}>
              {completeIds.size}건 처리 완료 · 판단 기록에 저장되었습니다
            </div>
          )}
        </div>
      </>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%',
      background: '#F8FAFC', fontFamily: 'inherit' }}>

      {/* 상단 로고 헤더 */}
      <div style={{
        padding: '0 16px',
        paddingTop: 42, /* dynamic island(top:18 + h:36) - bezel padding(13) ≈ 41 */
        paddingBottom: 0,
        background: '#fff',
        borderBottom: '1px solid var(--semantic-line-normal-alternative)',
        flexShrink: 0,
      }}>
        {/* 로고 + 알림 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <div style={{
              width: 30, height: 30, borderRadius: 9,
              background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontWeight: 900, fontSize: 14,
            }}>반</div>
            <span style={{ fontSize: 18, fontWeight: 800, color: '#1B3FA0',
              letterSpacing: '-0.02em' }}>외고반장</span>
          </div>
          <div style={{ flex: 1 }}/>
          <div style={{ position: 'relative', padding: 4 }}>
            <Icon name="bell" size={22} color="var(--semantic-label-neutral)"/>
            {pendingCount > 0 && (
              <span style={{ position: 'absolute', top: 0, right: 0,
                width: 15, height: 15, borderRadius: 999,
                background: '#EF4444', color: '#fff',
                fontSize: 9, fontWeight: 700,
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                {pendingCount}
              </span>
            )}
          </div>
        </div>

        {/* 오늘 브리핑 타이틀 + 사업장 선택 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          paddingBottom: 14 }}>
          <div>
            <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.022em',
              color: 'var(--semantic-label-normal)', lineHeight: 1.2 }}>
              오늘 브리핑
            </div>
            <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', marginTop: 2 }}>
              2026년 5월 11일 (월)
            </div>
          </div>
          {/* 사업장 선택 칩 */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '6px 11px', borderRadius: 99,
            background: 'var(--semantic-fill-alternative)',
            border: '1px solid var(--semantic-line-normal-alternative)',
            cursor: 'pointer',
          }}>
            <div style={{ width: 16, height: 16, borderRadius: 4,
              background: 'var(--semantic-primary-normal)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontSize: 9, fontWeight: 700 }}>한</div>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--semantic-label-normal)' }}>
              한별제조
            </span>
            <Icon name="chevronDown" size={12} color="var(--semantic-label-alternative)"/>
          </div>
        </div>
      </div>

      {/* 메인 콘텐츠 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {renderTabContent()}
      </div>

      {/* 하단 탭바 */}
      <BottomTabBar activeTab={activeBottomTab} onTabChange={setActiveBottomTab}/>
    </div>
  );
};

/* ─── 레거시 챗봇형 (보존) ──────────────────────────────────── */
const MobileChat = MobileBriefingHome;
const MobileChatLegacy = MobileChat;

Object.assign(window, {
  MobileChat,
  MobileChatLegacy,
  MobileBriefingHome,
  ApprovalTaskCard,
});
