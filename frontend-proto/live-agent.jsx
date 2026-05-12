// Live Agent 처리 화면, 모바일 초안 보기, 승인 완료 화면
// 레퍼런스 기준으로 전면 업데이트

/* ─── 예상 응답 아이콘 팔레트 ────────────────────────────────── */
const SCENARIO_STYLE = {
  positive: { icon: '✅', fg: '#166534', bg: '#DCFCE7', bd: '#86EFAC', badge: '확률 높음',  badgeBg: '#DCFCE7', badgeFg: '#166534' },
  question: { icon: '❓', fg: '#9C5800', bg: '#FFF7ED', bd: '#FED7AA', badge: '확률 보통',  badgeBg: '#FFF7ED', badgeFg: '#9C5800' },
  no_reply: { icon: '⏱',  fg: '#6B21A8', bg: '#F5F3FF', bd: '#C4B5FD', badge: '확률 낮음',  badgeBg: '#F5F3FF', badgeFg: '#6B21A8' },
};

/* ─── 모바일 초안 보기 화면 ─────────────────────────────────── */
const MobileDraftView = ({ task, thread, onBack, onApprove }) => {
  const [approved, setApproved] = React.useState(false);

  const handleApprove = () => {
    setApproved(true);
    setTimeout(() => onApprove?.(), 300);
  };

  const missingDocs = ['표준근로계약서 사본', '여권 사본'];
  const scenarios = thread?.scenarios || [
    { type: 'positive', label: '긍정 응답 시', desc: '누락 서류를 제출하고 연장 절차가 진행됩니다.' },
    { type: 'question', label: '추가 질문 시', desc: '필요 정보 안내 후 추가 확인이 진행됩니다.' },
    { type: 'no_reply', label: '응답 지연 시', desc: '리마인드 메시지가 자동 발송됩니다 (3일 후).' },
  ];

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column',
      background: '#F8FAFC', fontFamily: 'inherit' }}>

      {/* 헤더 */}
      <div style={{
        padding: '52px 20px 14px',
        background: '#fff',
        borderBottom: '1px solid var(--semantic-line-normal-alternative)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
          <button onClick={onBack} style={{ background: 'transparent', border: 0,
            cursor: 'pointer', padding: 4, color: 'var(--semantic-label-normal)', borderRadius: 6 }}>
            <Icon name="chevronLeft" size={22}/>
          </button>
          <span style={{ fontSize: 17, fontWeight: 700 }}>초안 보기</span>
        </div>

        {/* 제목 */}
        <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.022em',
          color: 'var(--semantic-label-normal)', lineHeight: 1.3, marginBottom: 10 }}>
          {task?.title || 'Nguyen V. 체류기간 연장 서류 요청'}
        </div>

        {/* 배지 행 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ padding: '3px 10px', borderRadius: 99, fontSize: 12, fontWeight: 600,
            background: '#FEF2F2', color: '#B00C0C' }}>체류만료 D-30</span>
          <span style={{ padding: '3px 10px', borderRadius: 99, fontSize: 12, fontWeight: 600,
            background: '#FFF7ED', color: '#C2410C' }}>누락 서류 2건</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4,
            padding: '3px 10px', borderRadius: 99, fontSize: 12, fontWeight: 500,
            background: '#F0FDF4', color: '#166534',
            border: '1px solid #BBF7D0' }}>
            <Icon name="shield" size={11}/>
            승인 후 Zalo로 발송됩니다
          </span>
        </div>
      </div>

      {/* 스크롤 영역 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 16px 100px' }}>

        {/* AI가 확인한 내용 */}
        <div style={{ background: '#fff', borderRadius: 16,
          border: '1px solid var(--semantic-line-normal-alternative)',
          padding: '14px 16px', marginBottom: 14,
          boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <div style={{ width: 32, height: 32, borderRadius: 10,
              background: 'linear-gradient(135deg, #1B3FA0, #6366F1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                <path d="M10 2l1.5 4.5H16l-3.75 2.75L13.5 14 10 11.25 6.5 14l1.25-4.75L4 6.5h4.5L10 2z"
                  stroke="#fff" strokeWidth="1.5" strokeLinejoin="round"/>
              </svg>
            </div>
            <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--semantic-label-normal)' }}>AI가 확인한 내용</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            {[
              'Nguyen V. · 베트남 · E-9',
              '3일 전 서류 요청 이력 있음',
              '표준근로계약서 사본 누락',
              '여권 사본 누락',
            ].map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 14,
                color: 'var(--semantic-label-neutral)', lineHeight: 1.5 }}>
                <span style={{ marginTop: 4, width: 5, height: 5, borderRadius: 999,
                  background: '#6366F1', flexShrink: 0 }}/>
                {item}
              </div>
            ))}
          </div>
        </div>

        {/* 메시지 초안 */}
        <div style={{ background: '#fff', borderRadius: 16,
          border: '1px solid var(--semantic-line-normal-alternative)',
          overflow: 'hidden', marginBottom: 14,
          boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
          <div style={{ padding: '12px 16px',
            borderBottom: '1px solid var(--semantic-line-normal-alternative)',
            display: 'flex', alignItems: 'center', gap: 8 }}>
            <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
              <path d="M3 4h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H5l-4 4V5a1 1 0 0 1 1-1z"
                stroke="#1B3FA0" strokeWidth="1.6" strokeLinejoin="round"/>
            </svg>
            <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--semantic-label-normal)' }}>메시지 초안</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'stretch' }}>
            {/* VN */}
            <div style={{ padding: '14px 14px' }}>
              <div style={{ display: 'inline-flex', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                background: 'rgba(99,102,241,0.10)', color: '#4F46E5', marginBottom: 8 }}>VN</div>
              <div style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--semantic-label-normal)' }}>
                {thread?.draftMessage?.vi ||
                  'Xin chào Nguyen V.,\nĐể gia hạn thời gian lưu trú (E-9), vui lòng bổ sung các giấy tờ còn thiếu và gửi lại cho chúng tôi.\n\n• Bản sao hợp đồng lao động theo mẫu chuẩn\n• Bản sao hộ chiếu\n\nVui lòng gửi trước ngày 2024-06-10.\nCảm ơn anh.'}
              </div>
            </div>
            {/* 구분선 + 화살표 */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
              padding: '0 6px', color: 'var(--semantic-label-alternative)' }}>
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                <path d="M7 10h6M10 7l3 3-3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
            {/* KR */}
            <div style={{ padding: '14px 14px',
              borderLeft: '1px solid var(--semantic-line-normal-alternative)' }}>
              <div style={{ display: 'inline-flex', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700,
                background: 'rgba(59,130,246,0.10)', color: '#2563EB', marginBottom: 8 }}>KR</div>
              <div style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--semantic-label-normal)' }}>
                {thread?.draftMessage?.ko ||
                  '안녕하세요, Nguyen V.님.\n체류기간 연장(E-9)을 위해 아래 서류를 보완하여 보내주시기 바랍니다.\n\n• 표준근로계약서 사본\n• 여권 사본\n\n2024-06-10까지 제출 부탁드립니다.\n감사합니다.'}
              </div>
            </div>
          </div>
        </div>

        {/* 예상 응답 */}
        <div style={{ background: '#fff', borderRadius: 16,
          border: '1px solid var(--semantic-line-normal-alternative)',
          overflow: 'hidden', marginBottom: 14,
          boxShadow: '0 1px 4px rgba(0,0,0,0.05)' }}>
          <div style={{ padding: '12px 16px',
            borderBottom: '1px solid var(--semantic-line-normal-alternative)',
            display: 'flex', alignItems: 'center', gap: 8 }}>
            <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
              <path d="M3 4h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H5l-4 4V5a1 1 0 0 1 1-1z"
                stroke="#10B981" strokeWidth="1.6" strokeLinejoin="round"/>
            </svg>
            <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--semantic-label-normal)' }}>예상 응답</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 0 }}>
            {scenarios.map((sc, i) => {
              const sty = SCENARIO_STYLE[sc.type] || SCENARIO_STYLE.positive;
              return (
                <div key={i} style={{
                  padding: '14px 12px',
                  borderRight: i < scenarios.length - 1 ? '1px solid var(--semantic-line-normal-alternative)' : 'none',
                }}>
                  <div style={{ fontSize: 18, marginBottom: 6 }}>
                    {sty.icon}
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--semantic-label-normal)',
                    marginBottom: 4, lineHeight: 1.3 }}>
                    {sc.label}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', lineHeight: 1.5,
                    marginBottom: 8 }}>
                    {sc.desc}
                  </div>
                  <span style={{ padding: '2px 8px', borderRadius: 99, fontSize: 11, fontWeight: 600,
                    background: sty.badgeBg, color: sty.badgeFg }}>
                    {sty.badge}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 하단 고정 버튼 */}
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0,
        padding: '12px 16px 28px', background: '#fff',
        borderTop: '1px solid var(--semantic-line-normal-alternative)',
        display: 'flex', gap: 8 }}>
        <button style={{
          flex: 1, padding: '13px 0', borderRadius: 12, fontSize: 14, fontWeight: 600,
          background: '#fff', color: 'var(--semantic-label-normal)',
          border: '1.5px solid var(--semantic-line-normal-normal)', cursor: 'pointer', fontFamily: 'inherit',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
        }}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <path d="M13 3L3 13M3 3h10v10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          수정 요청
        </button>
        <button style={{
          flex: 1, padding: '13px 0', borderRadius: 12, fontSize: 14, fontWeight: 600,
          background: '#fff', color: 'var(--semantic-label-normal)',
          border: '1.5px solid var(--semantic-line-normal-normal)', cursor: 'pointer', fontFamily: 'inherit',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
        }}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.4"/>
            <path d="M5 8h3l1 2 2-4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Live 처리 보기
        </button>
        <button onClick={handleApprove} style={{
          flex: 1.4, padding: '13px 0', borderRadius: 12, fontSize: 14, fontWeight: 700,
          background: approved ? '#059669' : 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
          color: '#fff', border: 0, cursor: 'pointer', fontFamily: 'inherit',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          boxShadow: '0 2px 10px rgba(27,63,160,0.25)',
        }}>
          <svg width="15" height="15" viewBox="0 0 20 20" fill="none">
            <path d="M17 5l-9 9-4-4" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M3 10l5 7 9-12" stroke="#fff" strokeWidth="0" />
          </svg>
          {approved ? '승인 완료' : '보내기 승인'}
        </button>
      </div>
    </div>
  );
};

/* ─── Live Agent 단계 아이템 ─────────────────────────────────── */
const AgentStepItem = ({ stepData, visible, expanded, onToggle }) => {
  const statusIcon = {
    done:        <div style={{ width: 26, height: 26, borderRadius: 999, background: '#10B981',
                   display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                   <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
                     <path d="M3 7l3 3 5-6" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                   </svg>
                 </div>,
    in_progress: <div style={{ width: 26, height: 26, borderRadius: 999, background: '#1B3FA0',
                   display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                   <span style={{ width: 13, height: 13, borderRadius: 999,
                     border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff',
                     display: 'inline-block', animation: 'spin 0.8s linear infinite' }}/>
                 </div>,
    waiting:     <div style={{ width: 26, height: 26, borderRadius: 999,
                   border: '2px solid var(--semantic-line-normal-normal)',
                   background: '#fff',
                   display: 'flex', alignItems: 'center', justifyContent: 'center',
                   color: 'var(--semantic-label-alternative)', fontWeight: 700, fontSize: 12 }}>
                   {stepData.step}
                 </div>,
  };

  const isDone = stepData.status === 'done';
  const isActive = stepData.status === 'in_progress';

  return (
    <div style={{
      opacity: visible ? 1 : 0,
      transform: visible ? 'translateY(0)' : 'translateY(10px)',
      transition: 'opacity 0.3s ease, transform 0.3s ease',
    }}>
      <div onClick={onToggle} style={{
        display: 'flex', alignItems: 'flex-start', gap: 12,
        padding: '12px 0', cursor: 'pointer',
      }}>
        <div style={{ flexShrink: 0, paddingTop: 1 }}>{statusIcon[stepData.status]}</div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 15, fontWeight: isActive || isDone ? 700 : 500,
              color: isDone ? 'var(--semantic-label-normal)' :
                     isActive ? '#1B3FA0' : 'var(--semantic-label-alternative)' }}>
              {stepData.label}
            </span>
            <Icon name={expanded ? 'chevronUp' : 'chevronDown'} size={14}
              color="var(--semantic-label-alternative)"/>
          </div>
          {stepData.detail && !expanded && (
            <div style={{ fontSize: 12.5, color: 'var(--semantic-label-alternative)', marginTop: 2 }}>
              {stepData.detail}
            </div>
          )}
        </div>
      </div>
      {/* 펼침 내용 */}
      {expanded && stepData.expandDetail && (
        <div style={{ marginLeft: 38, marginBottom: 10 }}>
          {stepData.expandDetail}
        </div>
      )}
    </div>
  );
};

/* ─── 승인 완료 화면 ─────────────────────────────────────────── */
const ApprovalCompleteScreen = ({ task, onBack, onViewLog }) => {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column',
      background: '#F8FAFC', fontFamily: 'inherit' }}>

      {/* 헤더 */}
      <div style={{ padding: '52px 20px 14px', background: '#fff',
        borderBottom: '1px solid var(--semantic-line-normal-alternative)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.022em',
            color: 'var(--semantic-label-normal)' }}>컨택 승인 완료</div>
          <span style={{ padding: '4px 10px', borderRadius: 99, fontSize: 12, fontWeight: 600,
            background: '#F0FDF4', color: '#166534', border: '1px solid #BBF7D0' }}>
            행정사 전용
          </span>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 16px 20px' }}>
        {/* 완료 카드 */}
        <div style={{ background: '#fff', borderRadius: 20,
          border: '1px solid var(--semantic-line-normal-alternative)',
          padding: '32px 20px 24px', marginBottom: 24, textAlign: 'center',
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
          {/* 그린 체크 */}
          <div style={{ width: 60, height: 60, borderRadius: 999, background: '#10B981',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 12px', boxShadow: '0 0 0 8px rgba(16,185,129,0.12)' }}>
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <path d="M6 14l6 6 10-12" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          {/* 반짝 효과 */}
          <div style={{ fontSize: 18, marginBottom: 8 }}>✨</div>
          <div style={{ fontSize: 17, fontWeight: 700, color: 'var(--semantic-label-normal)',
            marginBottom: 4 }}>
            {task?.workerName || 'Nguyen V.'}에게 보낼 메시지
          </div>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#10B981', marginBottom: 6 }}>
            승인이 완료되었습니다.
          </div>
          <div style={{ fontSize: 13, color: 'var(--semantic-label-alternative)' }}>
            메시지는 아래 정보로 발송이 예정되었습니다.
          </div>

          {/* 발송 정보 */}
          <div style={{ background: '#F8FAFC', borderRadius: 12,
            border: '1px solid var(--semantic-line-normal-alternative)',
            marginTop: 16, overflow: 'hidden' }}>
            {[
              { icon: '👤', label: '대상', value: task?.workerName || 'Nguyen V.' },
              { icon: '📋', label: '업무', value: task?.title || '체류기간 연장 서류 요청' },
              { icon: '💬', label: '발송 채널', value: 'Zalo' },
              { icon: '🕐', label: '승인 시각', value: '2025.05.22  09:41' },
              { icon: '👤', label: '담당자', value: '승인 완료' },
            ].map((row, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center',
                padding: '11px 14px', gap: 10,
                borderBottom: i < 4 ? '1px solid var(--semantic-line-normal-alternative)' : 'none' }}>
                <span style={{ fontSize: 14, flexShrink: 0 }}>{row.icon}</span>
                <span style={{ fontSize: 13, color: 'var(--semantic-label-alternative)',
                  flex: 1, textAlign: 'left' }}>{row.label}</span>
                <span style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--semantic-label-normal)' }}>
                  {row.value}
                </span>
              </div>
            ))}
          </div>

          {/* 판단 기록 안내 */}
          <div style={{ marginTop: 12, padding: '10px 12px', borderRadius: 10,
            background: '#EFF6FF', border: '1px solid #BFDBFE',
            display: 'flex', alignItems: 'center', gap: 7, textAlign: 'left' }}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6.5" stroke="#1D4ED8" strokeWidth="1.3"/>
              <path d="M8 7v4M8 5.5h.01" stroke="#1D4ED8" strokeWidth="1.3" strokeLinecap="round"/>
            </svg>
            <span style={{ fontSize: 12.5, color: '#1D4ED8', fontWeight: 500 }}>
              이 액션은 판단 기록 #4789에 저장되었습니다.
            </span>
          </div>
        </div>

        {/* 다음 단계 */}
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--semantic-label-normal)',
            marginBottom: 10 }}>다음 단계</div>
          <div style={{ background: '#fff', borderRadius: 16,
            border: '1px solid var(--semantic-line-normal-alternative)',
            overflow: 'hidden' }}>
            {[
              { icon: (
                  <div style={{ width: 36, height: 36, borderRadius: 10, background: '#EFF6FF',
                    display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                      <path d="M17 10l-9 7L3 10" stroke="#1D4ED8" strokeWidth="1.6" strokeLinecap="round"/>
                      <path d="M3 6l7 4 7-4" stroke="#1D4ED8" strokeWidth="1.6" strokeLinecap="round"/>
                    </svg>
                  </div>
                ), label: '발송 예정', desc: '메시지가 외국인에게 발송됩니다.', badge: '예정', badgeBg: '#EFF6FF', badgeFg: '#1D4ED8' },
              { icon: (
                  <div style={{ width: 36, height: 36, borderRadius: 10, background: '#FFF7ED',
                    display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                      <circle cx="10" cy="10" r="7" stroke="#F97316" strokeWidth="1.6"/>
                      <path d="M10 7v3l2 2" stroke="#F97316" strokeWidth="1.6" strokeLinecap="round"/>
                    </svg>
                  </div>
                ), label: '응답 대기', desc: '외국인의 응답을 기다립니다.', badge: '대기', badgeBg: '#F8FAFC', badgeFg: '#6B7280' },
              { icon: (
                  <div style={{ width: 36, height: 36, borderRadius: 10, background: '#F5F3FF',
                    display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                      <path d="M3 4h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H5l-4 4V5a1 1 0 0 1 1-1z"
                        stroke="#7C3AED" strokeWidth="1.6" strokeLinejoin="round"/>
                    </svg>
                  </div>
                ), label: '응답 도착 시 브리핑 반영', desc: '응답 내용이 오늘 브리핑에 반영됩니다.', badge: '예정', badgeBg: '#EFF6FF', badgeFg: '#1D4ED8' },
            ].map((step, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px',
                borderBottom: i < 2 ? '1px solid var(--semantic-line-normal-alternative)' : 'none',
              }}>
                {step.icon}
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--semantic-label-normal)',
                    marginBottom: 1 }}>{step.label}</div>
                  <div style={{ fontSize: 12.5, color: 'var(--semantic-label-alternative)' }}>{step.desc}</div>
                </div>
                <span style={{ padding: '3px 10px', borderRadius: 99, fontSize: 12, fontWeight: 600,
                  background: step.badgeBg, color: step.badgeFg }}>{step.badge}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 하단 버튼 */}
      <div style={{ padding: '12px 16px 28px', background: '#fff',
        borderTop: '1px solid var(--semantic-line-normal-alternative)',
        display: 'flex', gap: 10 }}>
        <button onClick={onViewLog} style={{
          flex: 1, padding: '13px 0', borderRadius: 12, fontSize: 14, fontWeight: 600,
          background: '#fff', color: 'var(--semantic-label-normal)',
          border: '1.5px solid var(--semantic-line-normal-normal)', cursor: 'pointer', fontFamily: 'inherit',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
        }}>
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
            <path d="M13 2H7a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z" stroke="currentColor" strokeWidth="1.4"/>
            <path d="M9 6h2M9 9h2M9 12h1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
          </svg>
          판단 기록 보기
        </button>
        <button onClick={onBack} style={{
          flex: 1, padding: '13px 0', borderRadius: 12, fontSize: 14, fontWeight: 700,
          background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
          color: '#fff', border: 0, cursor: 'pointer', fontFamily: 'inherit',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          boxShadow: '0 2px 10px rgba(27,63,160,0.25)',
        }}>
          <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
            <path d="M8 2H4a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8" stroke="#fff" strokeWidth="1.4"/>
            <path d="M5 8l3 3 5-7" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          오늘 브리핑으로 돌아가기
        </button>
      </div>
    </div>
  );
};

/* ─── Live Agent 진행 화면 (개선) ────────────────────────────── */
const LiveAgentProgressScreen = ({ taskId, onBack, onApprove }) => {
  const [visibleSteps, setVisibleSteps] = React.useState(0);
  const [approved, setApproved] = React.useState(false);
  const [expandedStep, setExpandedStep] = React.useState(null);
  const steps = (window.LIVE_AGENT_STEPS || []).map((s, i) => ({
    ...s,
    expandDetail: i === 2 ? (
      <div style={{ background: 'var(--semantic-background-normal-alternative)', borderRadius: 10,
        padding: '10px 12px', border: '1px solid var(--semantic-line-normal-alternative)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <div style={{ padding: '8px 10px', borderRadius: 8, background: 'rgba(99,102,241,0.06)',
            border: '1px solid rgba(99,102,241,0.15)' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#4F46E5', marginBottom: 4 }}>VN</div>
            <div style={{ fontSize: 11.5, color: 'var(--semantic-label-neutral)', lineHeight: 1.5 }}>
              Xin chào Nguyen V., đây là Workforce Agent từ ngoại고반장...
            </div>
          </div>
          <div style={{ padding: '8px 10px', borderRadius: 8, background: 'rgba(27,63,160,0.04)',
            border: '1px solid rgba(27,63,160,0.12)' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#1B3FA0', marginBottom: 4 }}>KR</div>
            <div style={{ fontSize: 11.5, color: 'var(--semantic-label-neutral)', lineHeight: 1.5 }}>
              안녕하세요 Nguyen V.님, 외고반장 WorkForce Agent입니다...
            </div>
          </div>
        </div>
        <div style={{ marginTop: 8, padding: '5px 10px', borderRadius: 6, background: '#EFF6FF',
          fontSize: 11.5, color: '#1D4ED8', fontWeight: 500 }}>
          메시지 초안 생성 완료 · 100%
        </div>
      </div>
    ) : null,
  }));

  React.useEffect(() => {
    steps.forEach((_, i) => {
      setTimeout(() => setVisibleSteps(v => Math.max(v, i + 1)), i * 350 + 100);
    });
  }, []);

  const handleApprove = () => {
    setApproved(true);
    setTimeout(() => onApprove?.(), 350);
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column',
      background: '#F8FAFC', fontFamily: 'inherit' }}>

      {/* 헤더 */}
      <div style={{ padding: '14px 18px', background: '#fff',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--semantic-line-normal-alternative)',
        display: 'flex', alignItems: 'center', gap: 10 }}>
        <button onClick={onBack} style={{ background: 'transparent', border: 0,
          cursor: 'pointer', padding: 4, borderRadius: 6, color: 'var(--semantic-label-neutral)' }}>
          <Icon name="chevronLeft" size={18}/>
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--semantic-label-normal)' }}>
            Multilingual Contact Agent
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
            <span style={{ width: 7, height: 7, borderRadius: 999, background: '#10B981',
              animation: 'pulse 1.5s infinite' }}/>
            <span style={{ fontSize: 12, color: '#166534', fontWeight: 600 }}>Live</span>
            <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)' }}>· 판단 기록 #4789</span>
          </div>
        </div>
        <button style={{ padding: '5px 10px', borderRadius: 8, fontSize: 12, fontWeight: 600,
          background: '#F0FDF4', color: '#166534', border: '1px solid #BBF7D0', cursor: 'pointer',
          fontFamily: 'inherit' }}>
          행정사 전용
        </button>
      </div>

      {/* 스크롤 콘텐츠 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 18px 100px' }}>

        {/* AI 상태 카드 */}
        <div style={{ background: 'linear-gradient(135deg, rgba(27,63,160,0.06), rgba(99,102,241,0.04))',
          borderRadius: 14, border: '1px solid rgba(27,63,160,0.15)',
          padding: '14px 16px', marginBottom: 16,
          display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 12,
            background: 'linear-gradient(135deg, #1B3FA0, #6366F1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M10 2l1.5 4.5H16l-3.75 2.75L13.5 14 10 11.25 6.5 14l1.25-4.75L4 6.5h4.5L10 2z"
                stroke="#fff" strokeWidth="1.5" strokeLinejoin="round"/>
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#1B3FA0' }}>
              AI가 근로자와 소통 계획을 세우고 있습니다
            </div>
            <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', marginTop: 2 }}>
              Workforce Agent와 협업 중 · 판단 기록 #4789
            </div>
          </div>
          {/* 클립보드 일러스트 */}
          <div style={{ marginLeft: 'auto', opacity: 0.2 }}>
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <rect x="8" y="6" width="24" height="30" rx="3" stroke="#1B3FA0" strokeWidth="2"/>
              <rect x="14" y="2" width="12" height="6" rx="2" stroke="#1B3FA0" strokeWidth="2"/>
              <path d="M14 18h12M14 24h8" stroke="#1B3FA0" strokeWidth="1.5" strokeLinecap="round"/>
              <path d="M12 12l2 2 4-4" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>

        {/* 처리 단계 */}
        <div style={{ background: '#fff', borderRadius: 14,
          border: '1px solid var(--semantic-line-normal-alternative)',
          padding: '14px 16px', marginBottom: 14,
          boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
          {steps.map((s, i) => (
            <div key={s.step}>
              <AgentStepItem
                stepData={s}
                visible={i < visibleSteps}
                expanded={expandedStep === i}
                onToggle={() => setExpandedStep(prev => prev === i ? null : i)}
              />
              {i < steps.length - 1 && (
                <div style={{ width: 1.5, height: 8, background: '#E5E7EB', marginLeft: 12,
                  opacity: i < visibleSteps ? 1 : 0, transition: 'opacity 0.3s' }}/>
              )}
            </div>
          ))}
        </div>

        {/* 예상 응답 시나리오 */}
        {visibleSteps >= 3 && (
          <div style={{ background: '#fff', borderRadius: 14,
            border: '1px solid var(--semantic-line-normal-alternative)',
            overflow: 'hidden', marginBottom: 14,
            animation: 'slideUp .3s ease' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr' }}>
              {[
                { icon: '💬', label: '긍정 응답 시', desc: '다음 단계 안내 메시지 자동 발송', type: 'positive' },
                { icon: '❓', label: '추가 정보 요청 시', desc: '필요 정보 수집을 위한 후속 질문 발송', type: 'question' },
                { icon: '⏱', label: '응답 지연 시', desc: '48시간 후 리마인드 메시지 자동 발송', type: 'no_reply' },
              ].map((sc, i) => {
                const sty = SCENARIO_STYLE[sc.type];
                return (
                  <div key={i} style={{ padding: '14px 12px',
                    borderRight: i < 2 ? '1px solid var(--semantic-line-normal-alternative)' : 'none' }}>
                    <div style={{ fontSize: 20, marginBottom: 6 }}>{sc.icon}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--semantic-label-normal)',
                      marginBottom: 4, lineHeight: 1.3 }}>{sc.label}</div>
                    <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', lineHeight: 1.5 }}>{sc.desc}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 판단 기록 안내 */}
        {visibleSteps >= 3 && (
          <div style={{ padding: '10px 14px', borderRadius: 10, marginBottom: 14,
            background: '#EFF6FF', border: '1px solid #BFDBFE',
            display: 'flex', alignItems: 'center', gap: 7,
            animation: 'fadeIn .4s ease' }}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6.5" stroke="#1D4ED8" strokeWidth="1.3"/>
              <path d="M8 7v4M8 5.5h.01" stroke="#1D4ED8" strokeWidth="1.3" strokeLinecap="round"/>
            </svg>
            <span style={{ fontSize: 12.5, color: '#1D4ED8', fontWeight: 500 }}>
              이 액션은 판단 기록 #4789에 기록되었습니다.
            </span>
          </div>
        )}
      </div>

      {/* 하단 승인 바 */}
      {visibleSteps >= 3 && (
        <div style={{ padding: '12px 18px 24px', background: '#fff',
          borderTop: '1px solid var(--semantic-line-normal-alternative)',
          display: 'flex', flexDirection: 'column', gap: 8,
          animation: 'slideUp .4s ease' }}>
          {approved
            ? (
              <div style={{ padding: '14px', borderRadius: 12, textAlign: 'center',
                background: 'rgba(16,185,129,0.10)', border: '1px solid rgba(16,185,129,0.3)',
                fontSize: 14, fontWeight: 700, color: '#166534' }}>
                ✓ 승인 완료 · 판단 기록 #4789에 저장됨
              </div>
            )
            : (
              <>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button style={{
                    flex: 1, padding: '12px', borderRadius: 12, fontSize: 14, fontWeight: 600,
                    background: '#fff', color: 'var(--semantic-label-normal)',
                    border: '1.5px solid var(--semantic-line-normal-normal)', cursor: 'pointer',
                    fontFamily: 'inherit',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
                  }}>
                    <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
                      <path d="M11 3L3 11M3 3h8v8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                    </svg>
                    Edit Draft
                  </button>
                  <button onClick={handleApprove} style={{
                    flex: 2, padding: '12px', borderRadius: 12, fontSize: 14, fontWeight: 700,
                    background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
                    color: '#fff', border: 0, cursor: 'pointer', fontFamily: 'inherit',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                    boxShadow: '0 2px 10px rgba(27,63,160,0.25)',
                  }}>
                    <svg width="15" height="15" viewBox="0 0 20 20" fill="none">
                      <path d="M3 10l5 7 9-12" stroke="#fff" strokeWidth="0"/>
                      <path d="M17 4l-9 9-4-4" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    이 메시지로 컨택할까요?
                  </button>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button style={{
                    flex: 1, padding: '10px', borderRadius: 10, fontSize: 13, fontWeight: 500,
                    background: '#fff', color: 'var(--semantic-label-alternative)',
                    border: '1px solid var(--semantic-line-normal-alternative)', cursor: 'pointer', fontFamily: 'inherit',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                  }}>
                    <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
                      <rect x="2" y="3" width="10" height="2" rx="1" fill="currentColor"/>
                      <rect x="2" y="6" width="10" height="2" rx="1" fill="currentColor" opacity="0.5"/>
                    </svg>
                    Pause
                  </button>
                  <button style={{
                    flex: 1, padding: '10px', borderRadius: 10, fontSize: 13, fontWeight: 500,
                    background: '#fff', color: 'var(--semantic-label-alternative)',
                    border: '1px solid var(--semantic-line-normal-alternative)', cursor: 'pointer', fontFamily: 'inherit',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                  }}>
                    <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
                      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3"/>
                      <path d="M5 5l4 4M9 5L5 9" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                    </svg>
                    Cancel
                  </button>
                </div>
                <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)', textAlign: 'center' }}>
                  현재 자율성:{' '}
                  <span style={{ color: '#F59E0B', fontWeight: 700 }}>Medium</span>{' '}
                  (승인 필요)
                </div>
              </>
            )
          }
        </div>
      )}

      <style>{`
        @keyframes spin  { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
      `}</style>
    </div>
  );
};

Object.assign(window, { LiveAgentProgressScreen, MobileDraftView, ApprovalCompleteScreen, AgentStepItem });
