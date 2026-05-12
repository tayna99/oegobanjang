// PC Dashboard — 오늘 할 일 탭 리뉴얼
// 레퍼런스: 요약 카드 + 업무 큐 테이블(checkbox) + 우측 슬라이드 패널

// 구 TopBar (이제 index.html의 AppTopBar가 사용됨, 하위 호환용 stub)
const TopBar = () => null;

// 오늘 처리할 외국인 고용 업무 — 상단 요약 카드 (레퍼런스 기준 아이콘+숫자)
const TodaySummaryNew = ({ counts }) => {
  const cards = [
    {
      label: '체류기간 임박', count: counts.visa, unit: '명',
      color: '#EF4444', bg: '#FEF2F2',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="9" stroke="#EF4444" strokeWidth="1.8"/>
          <path d="M12 7v5l3 3" stroke="#EF4444" strokeWidth="1.8" strokeLinecap="round"/>
        </svg>
      ),
    },
    {
      label: '서류 보완 필요', count: counts.docs, unit: '건',
      color: '#F97316', bg: '#FFF7ED',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" stroke="#F97316" strokeWidth="1.8" strokeLinejoin="round"/>
          <path d="M14 2v6h6M12 12v4M12 10h.01" stroke="#F97316" strokeWidth="1.8" strokeLinecap="round"/>
        </svg>
      ),
    },
    {
      label: '신규 채용 준비', count: counts.recruitment || 1, unit: '건',
      color: '#10B981', bg: '#ECFDF5',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <circle cx="9" cy="8" r="3.5" stroke="#10B981" strokeWidth="1.8"/>
          <path d="M3 20c0-3.866 2.686-6 6-6s6 2.134 6 6" stroke="#10B981" strokeWidth="1.8" strokeLinecap="round"/>
          <path d="M17 6l1.5 1.5L21 5" stroke="#10B981" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
    },
    {
      label: '컨택 대기', count: counts.contact || 4, unit: '건',
      color: '#8B5CF6', bg: '#F5F3FF',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M4 4h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H6l-4 4V5a1 1 0 0 1 1-1z" stroke="#8B5CF6" strokeWidth="1.8" strokeLinejoin="round"/>
        </svg>
      ),
    },
    {
      label: '응답 도착', count: counts.reply || 2, unit: '건',
      color: '#0EA5E9', bg: '#F0F9FF',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="#0EA5E9" strokeWidth="1.8" strokeLinejoin="round"/>
          <path d="M8 10h8M8 14h4" stroke="#0EA5E9" strokeWidth="1.8" strokeLinecap="round"/>
        </svg>
      ),
    },
    {
      label: '승인 대기', count: counts.approval, unit: '건',
      color: '#F59E0B', bg: '#FFFBEB',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="#F59E0B" strokeWidth="1.8" strokeLinejoin="round"/>
        </svg>
      ),
    },
    {
      label: '행정사 검토 준비', count: counts.handoff, unit: '건',
      color: '#6366F1', bg: '#EEF2FF',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M9 11l3 3L22 4" stroke="#6366F1" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke="#6366F1" strokeWidth="1.8" strokeLinecap="round"/>
        </svg>
      ),
    },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 10, marginBottom: 24 }}>
      {cards.map(c => (
        <div key={c.label} style={{
          background: '#fff', borderRadius: 12, padding: '16px',
          border: '1px solid var(--semantic-line-normal-alternative)',
          boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
          display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: c.bg,
            display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {c.icon}
          </div>
          <div>
            <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)', fontWeight: 500, marginBottom: 2 }}>
              {c.label}
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
              <span style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.03em', color: c.color, lineHeight: 1 }}>
                {c.count}
              </span>
              <span style={{ fontSize: 13, color: 'var(--semantic-label-alternative)', fontWeight: 500 }}>{c.unit}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

// 업무 큐 아이템 타입별 아이콘
const TASK_TYPE_ICON = {
  visa_document_request: (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M12 2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V6l-4-4z" stroke="#1B3FA0" strokeWidth="1.5" strokeLinejoin="round"/>
      <path d="M12 2v4h4M8 10h4M8 13h2" stroke="#1B3FA0" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),
  recruitment: (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <circle cx="8" cy="6" r="3" stroke="#10B981" strokeWidth="1.5"/>
      <path d="M3 17c0-3 2-4.5 5-4.5s5 1.5 5 4.5" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M14 3l1.5 1.5L18 2" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  contact: (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M3 3h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H5l-3 3V4a1 1 0 0 1 1-1z" stroke="#8B5CF6" strokeWidth="1.5" strokeLinejoin="round"/>
    </svg>
  ),
  contract_termination: (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <rect x="3" y="3" width="14" height="14" rx="2" stroke="#F97316" strokeWidth="1.5"/>
      <path d="M7 10h6M7 13h4" stroke="#F97316" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),
};

const TASK_STATUS_STYLE = {
  approval_required: { label: '승인 필요',   bg: '#FFF7ED', fg: '#C2410C', dot: '#F97316' },
  review_required:   { label: '검토 필요',   bg: '#FFFBEB', fg: '#B45309', dot: '#F59E0B' },
  pending_approval:  { label: '승인 대기',   bg: '#FFF7ED', fg: '#C2410C', dot: '#F97316' },
  replied:           { label: '응답 도착',   bg: '#ECFDF5', fg: '#065F46', dot: '#10B981' },
  in_progress:       { label: '진행 중',     bg: '#EFF6FF', fg: '#1D4ED8', dot: '#3B82F6' },
  draft:             { label: '초안',        bg: '#F5F3FF', fg: '#5B21B6', dot: '#8B5CF6' },
};

// 우측 슬라이드 패널 — 업무 상세
const TaskDetailPanel = ({ task, worker, onClose, onOpenDocReq, onApprove }) => {
  if (!task) return null;
  const st = TASK_STATUS_STYLE[task.status] || TASK_STATUS_STYLE.in_progress;
  const workerCases = CASES.filter(c => c.workerId === worker?.id);
  const missingDocs = worker ? Object.entries(worker.docs).filter(([,v]) => v !== 'ok') : [];

  return (
    <aside style={{
      width: 380, flexShrink: 0,
      background: '#fff',
      borderLeft: '1px solid var(--semantic-line-normal-alternative)',
      height: '100%', overflowY: 'auto',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* 헤더 */}
      <div style={{ padding: '18px 20px 14px',
        borderBottom: '1px solid var(--semantic-line-normal-alternative)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ padding: '2px 10px', borderRadius: 99, fontSize: 12, fontWeight: 600,
            background: st.bg, color: st.fg }}>{st.label}</span>
          <button onClick={onClose} style={{ background: 'transparent', border: 0,
            cursor: 'pointer', color: 'var(--semantic-label-alternative)', padding: 4, borderRadius: 6 }}>
            <Icon name="close" size={16}/>
          </button>
        </div>
        <div style={{ fontSize: 16, fontWeight: 700, lineHeight: 1.4, marginBottom: 4 }}>
          {task.title}
        </div>
        <div style={{ fontSize: 13, color: 'var(--semantic-label-alternative)' }}>
          {task.dDay ? `기한 D-${task.dDay}` : ''}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* 왜 확인이 필요한가요 */}
        <div style={{ padding: '12px 14px', borderRadius: 10,
          background: '#F8FAFF', border: '1px solid #DBEAFE' }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: '#1D4ED8', marginBottom: 6,
            display: 'flex', alignItems: 'center', gap: 5 }}>
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6.5" stroke="#1D4ED8" strokeWidth="1.4"/>
              <path d="M8 7v4M8 5.5h.01" stroke="#1D4ED8" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
            왜 확인이 필요한가요?
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {workerCases.slice(0, 2).map(c => (
              <div key={c.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 6,
                fontSize: 12.5, color: '#1E40AF', lineHeight: 1.5 }}>
                <span style={{ marginTop: 3, width: 5, height: 5, borderRadius: 99, background: '#3B82F6', flexShrink: 0 }}/>
                {c.summary}
              </div>
            ))}
          </div>
        </div>

        {/* AI가 준비한 일 */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--semantic-label-alternative)',
            marginBottom: 8, display: 'flex', alignItems: 'center', gap: 5,
            textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
              <path d="M8 1l1.5 4.5H14l-3.75 2.75L11.5 13 8 10.25 4.5 13l1.25-4.75L2 5.5h4.5L8 1z" stroke="#1B3FA0" strokeWidth="1.3" strokeLinejoin="round"/>
            </svg>
            AI가 준비한 일
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {[
              '필수 서류 체크리스트 검토 완료',
              '유사 케이스 기반 보완 포인트 도출 완료',
            ].map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8,
                fontSize: 13, color: 'var(--semantic-label-neutral)' }}>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <path d="M3 8l3.5 3.5 6.5-7" stroke="#10B981" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                {item}
              </div>
            ))}
          </div>
        </div>

        {/* 누락 서류 */}
        {missingDocs.length > 0 && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--semantic-label-alternative)',
                textTransform: 'uppercase', letterSpacing: '0.05em' }}>누락 서류</div>
              <span style={{ fontSize: 11.5, fontWeight: 600, color: '#EF4444',
                background: '#FEF2F2', padding: '1px 8px', borderRadius: 99 }}>
                {missingDocs.length}건
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {missingDocs.map(([k]) => (
                <div key={k} style={{ padding: '8px 10px', borderRadius: 8,
                  background: '#FFF7ED', border: '1px solid #FED7AA',
                  fontSize: 12.5, color: '#C2410C', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                    <path d="M8 5v4M8 11h.01" stroke="#C2410C" strokeWidth="1.5" strokeLinecap="round"/>
                    <path d="M8 1L1 14h14L8 1z" stroke="#C2410C" strokeWidth="1.4" strokeLinejoin="round"/>
                  </svg>
                  {k}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 다음 할 일 */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--semantic-label-alternative)',
            marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>다음 할 일</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {[
              { text: worker ? (worker.name.split('.')[0] + ' 서류 수령 및 검토') : '서류 수령 및 검토', tag: '오늘' },
            ].map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 10px', borderRadius: 8, background: '#F8FAFF',
                border: '1px solid #DBEAFE', fontSize: 13, color: 'var(--semantic-label-normal)' }}>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <rect x="1.5" y="1.5" width="13" height="13" rx="2" stroke="#3B82F6" strokeWidth="1.4"/>
                  <path d="M4 8l3 3 5-5" stroke="#3B82F6" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <span style={{ flex: 1 }}>{item.text}</span>
                <span style={{ fontSize: 11, color: '#1D4ED8', fontWeight: 600,
                  background: '#DBEAFE', padding: '1px 7px', borderRadius: 99 }}>{item.tag}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 업무 기록 */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--semantic-label-alternative)',
            marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>업무 기록</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {[
              { date: '5/15', text: '서류 요청 메시지 발송' },
              { date: '5/16', text: '근로자 확인 응답 수신' },
            ].map((ev, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, fontSize: 12.5 }}>
                <span style={{ color: 'var(--semantic-label-alternative)', flexShrink: 0, width: 28 }}>{ev.date}</span>
                <span style={{ color: 'var(--semantic-label-neutral)' }}>{ev.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 하단 CTA */}
      <div style={{ padding: '14px 20px', borderTop: '1px solid var(--semantic-line-normal-alternative)',
        display: 'flex', flexDirection: 'column', gap: 8 }}>
        {task.type === 'visa_document_request' && (
          <button onClick={() => onOpenDocReq && onOpenDocReq('act_003')}
            style={{
              width: '100%', padding: '12px', borderRadius: 10,
              background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
              color: '#fff', border: 0, cursor: 'pointer', fontFamily: 'inherit',
              fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
              boxShadow: '0 2px 10px rgba(27,63,160,0.3)',
            }}>
            <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
              <path d="M17 11v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h6M13 3h5v5M8 12l9-9" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            대표 승인 요청
          </button>
        )}
        {task.type !== 'visa_document_request' && (
          <button onClick={() => onApprove && onApprove(task.id)}
            style={{
              width: '100%', padding: '12px', borderRadius: 10,
              background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
              color: '#fff', border: 0, cursor: 'pointer', fontFamily: 'inherit',
              fontSize: 14, fontWeight: 700,
              boxShadow: '0 2px 10px rgba(27,63,160,0.3)',
            }}>
            승인 요청 보내기
          </button>
        )}
      </div>
    </aside>
  );
};

// 오늘의 업무 큐 메인 테이블
const taskTypeForRisk = (riskType) => ({
  visa_expiry: 'visa_document_request',
  missing_document: 'visa_document_request',
  contract_visa_conflict: 'contract_termination',
  reporting_deadline: 'contract_termination',
  quota_review: 'recruitment',
  candidate_readiness: 'recruitment',
}[riskType] || 'contact');

const taskFromBriefingItem = (item, actionsById) => {
  const primaryAction = item.primary_action || item.next_action_ids?.map(id => actionsById[id]).find(Boolean);
  return {
    id: item.item_id,
    caseId: item.case_id,
    actionId: primaryAction?.action_id,
    type: taskTypeForRisk(item.risk_type),
    title: item.case_title || item.risk_type,
    worker: item.subject_display_name || item.subject_display_id || item.subject_id,
    workerId: item.subject_display_id,
    status: primaryAction?.status || 'in_progress',
    dDay: item.risk_timing_label || (item.d_day !== null && item.d_day !== undefined ? `D-${item.d_day}` : '확인 필요'),
    nextAction: primaryAction?.label || '확인',
  };
};

const TodayTaskQueue = ({ onSelectTask, selectedTaskId, apiBriefing }) => {
  const actionsById = Object.fromEntries((apiBriefing?.recommended_actions || []).map(action => [action.action_id, action]));
  const apiTasks = (apiBriefing?.items || []).map(item => taskFromBriefingItem(item, actionsById));
  const tasks = apiTasks.length ? apiTasks : [
    {
      id: 'q_001', type: 'visa_document_request',
      title: '체류기간 연장 서류 요청',
      worker: 'Nguyen V.', workerId: 'w_001',
      status: 'approval_required', dDay: 'D-30',
      nextAction: '초안 보기',
    },
    {
      id: 'q_002', type: 'recruitment',
      title: '신규 베트남 E-9 3명 채용 요청',
      worker: '송출회사 요청서',workerId: null,
      status: 'in_progress', dDay: '이번 주',
      nextAction: '요청서 보기',
    },
    {
      id: 'q_003', type: 'visa_document_request',
      title: '후보자 입국 전 서류 요청',
      worker: 'Candidate A', workerId: null,
      status: 'pending_approval', dDay: '5/20',
      nextAction: '승인 요청',
    },
    {
      id: 'q_004', type: 'contract_termination',
      title: '계약 종료 확인',
      worker: 'Tran T. H.', workerId: 'w_003',
      status: 'replied', dDay: '5/12',
      nextAction: '응답 요약',
    },
  ];

  return (
    <div style={{ background: '#fff', borderRadius: 12, overflow: 'hidden',
      border: '1px solid var(--semantic-line-normal-alternative)',
      boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
      {/* 테이블 헤더 */}
      <div style={{
        display: 'grid', gridTemplateColumns: '36px 1fr 140px 100px 80px 120px 32px',
        padding: '10px 16px', gap: 12,
        fontSize: 12, fontWeight: 600, color: 'var(--semantic-label-alternative)',
        background: 'var(--semantic-background-normal-alternative)',
        borderBottom: '1px solid var(--semantic-line-normal-alternative)',
      }}>
        <div/>
        <div>업무</div>
        <div>대상</div>
        <div>상태</div>
        <div>기한</div>
        <div>다음 처리</div>
        <div/>
      </div>

      {/* 행 */}
      {tasks.map((task, i) => {
        const st = TASK_STATUS_STYLE[task.status] || TASK_STATUS_STYLE.in_progress;
        const isSelected = selectedTaskId === task.id;
        const icon = TASK_TYPE_ICON[task.type] || TASK_TYPE_ICON.contact;

        return (
          <div
            key={task.id}
            onClick={() => onSelectTask(task)}
            style={{
              display: 'grid', gridTemplateColumns: '36px 1fr 140px 100px 80px 120px 32px',
              padding: '14px 16px', gap: 12, alignItems: 'center',
              borderBottom: i < tasks.length - 1 ? '1px solid var(--semantic-line-normal-alternative)' : 0,
              cursor: 'pointer',
              background: isSelected ? '#EFF6FF' : 'transparent',
              transition: 'background .12s',
            }}
            onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = '#F8FAFC'; }}
            onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
          >
            {/* 체크박스 */}
            <div style={{
              width: 18, height: 18, borderRadius: 5,
              border: '1.5px solid var(--semantic-line-normal-normal)',
              background: '#fff', cursor: 'pointer', flexShrink: 0,
            }}/>

            {/* 업무명 + 아이콘 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
              <div style={{ width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                background: 'var(--semantic-fill-alternative)',
                display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {icon}
              </div>
              <span style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--semantic-label-normal)',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {task.title}
              </span>
            </div>

            {/* 대상 */}
            <div style={{ fontSize: 13, color: 'var(--semantic-label-neutral)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {task.worker}
            </div>

            {/* 상태 뱃지 */}
            <div>
              <span style={{ padding: '3px 10px', borderRadius: 99, fontSize: 12, fontWeight: 600,
                background: st.bg, color: st.fg, whiteSpace: 'nowrap' }}>
                {st.label}
              </span>
            </div>

            {/* 기한 */}
            <div style={{ fontSize: 13, fontWeight: 600,
              color: task.dDay?.startsWith('D-') && parseInt(task.dDay.slice(2)) <= 30 ? '#EF4444' : 'var(--semantic-label-neutral)' }}>
              {task.dDay}
            </div>

            {/* 다음 처리 버튼 */}
            <div>
              <button style={{
                padding: '5px 12px', borderRadius: 7, fontSize: 12.5, fontWeight: 600,
                border: '1px solid var(--semantic-line-normal-normal)',
                background: '#fff', cursor: 'pointer', fontFamily: 'inherit',
                color: 'var(--semantic-label-neutral)',
                display: 'flex', alignItems: 'center', gap: 5, whiteSpace: 'nowrap',
              }}>
                {task.nextAction === '초안 보기' && (
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                    <path d="M10 2H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V5l-3-3z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
                  </svg>
                )}
                {task.nextAction === '요청서 보기' && (
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                    <path d="M10 2H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V5l-3-3z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
                  </svg>
                )}
                {task.nextAction === '승인 요청' && (
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                    <path d="M8 1l1.5 4.5H14l-3.75 2.75 1.25 4.75L8 10.25 4.5 13l1.25-4.75L2 5.5h4.5L8 1z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/>
                  </svg>
                )}
                {task.nextAction === '응답 요약' && (
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                    <path d="M2 2h12a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H5l-4 4V3a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
                  </svg>
                )}
                {task.nextAction}
              </button>
            </div>

            {/* 더보기 */}
            <div style={{ color: 'var(--semantic-label-alternative)', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="4" r="1.2" fill="currentColor"/>
                <circle cx="8" cy="8" r="1.2" fill="currentColor"/>
                <circle cx="8" cy="12" r="1.2" fill="currentColor"/>
              </svg>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// AI briefing ribbon
const BriefingBanner = ({ generatedAt, onRegenerate }) => (
  <div style={{
    display: 'flex', alignItems: 'center', gap: 14,
    padding: '14px 18px', borderRadius: 12, marginBottom: 20,
    background: 'linear-gradient(90deg, rgba(27,63,160,0.07), rgba(0,191,165,0.04))',
    border: '1px solid rgba(27,63,160,0.15)',
  }}>
    <div style={{
      width: 36, height: 36, borderRadius: 10,
      background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)', color: '#fff',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontWeight: 800, fontSize: 14, flexShrink: 0,
    }}>반</div>
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--semantic-label-normal)', marginBottom: 2 }}>
        오늘 브리핑이 준비되었습니다
      </div>
      <div style={{ fontSize: 12.5, color: 'var(--semantic-label-neutral)', lineHeight: 1.5 }}>
        외고반장이 7개 케이스를 정리했습니다. 즉시 확인 1건, 우선 확인 3건, 승인 대기 5건. 모든 판단의 근거는 항목 클릭으로 확인할 수 있습니다.
      </div>
    </div>
    <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', flexShrink: 0 }}>{generatedAt}</span>
    <Button variant="outlined" size="small" leadingIcon={<Icon name="refresh" size={14}/>} onClick={onRegenerate}>
      다시 생성
    </Button>
  </div>
);

// 기존 컴포넌트들 — workers/cases 탭용으로 유지
const TodaySummary = TodaySummaryNew;

const DDayBar = ({ dNum, severity }) => {
  const sev = SEVERITY_PALETTE[severity];
  const window = 60;
  const pct = Math.max(0, Math.min(100, 50 + (-dNum / window) * 50));
  const isPast = dNum < 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ position: 'relative', flex: 1, height: 4, borderRadius: 999, background: 'var(--semantic-fill-alternative)', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${pct}%`, background: sev.dot, opacity: isPast ? 1 : 0.7 }}/>
        <div style={{ position: 'absolute', left: '50%', top: -2, bottom: -2, width: 1, background: 'var(--semantic-label-alternative)', opacity: 0.4 }}/>
      </div>
      <span style={{ fontSize: 11, fontWeight: 600, color: sev.fg, fontVariantNumeric: 'tabular-nums', minWidth: 30, textAlign: 'right' }}>{dNum < 0 ? `D+${Math.abs(dNum)}` : `D-${dNum}`}</span>
    </div>
  );
};

const FilterBar = ({ severityFilter, onClear, onSetDensity, density }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
    <div style={{ display: 'flex', gap: 6 }}>
      <Chip active={!severityFilter} onClick={onClear}>전체</Chip>
      <Chip count={1}>즉시 확인</Chip>
      <Chip count={3}>우선 확인</Chip>
      <Chip count={2}>확인 필요</Chip>
      <Chip count={1}>참고</Chip>
    </div>
    <div style={{ width: 1, height: 16, background: 'var(--semantic-line-normal-neutral)', margin: '0 4px' }}/>
    <div style={{ display: 'flex', gap: 6 }}>
      <Chip>전체 라인</Chip>
      <Chip>승인 대기만</Chip>
      <Chip>서류 보완 필요</Chip>
    </div>
    <div style={{ flex: 1 }}/>
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', marginRight: 4 }}>밀도</span>
      <Chip active={density === 'compact'}      onClick={() => onSetDensity('compact')}>compact</Chip>
      <Chip active={density === 'comfortable'}  onClick={() => onSetDensity('comfortable')}>comfy</Chip>
    </div>
  </div>
);

const WorkerRiskTable = ({ workers, cases, selectedId, onSelect, severityFilter, density }) => {
  const rowsByWorker = workers.map(w => ({
    worker: w, cases: cases.filter(c => c.workerId === w.id),
  })).filter(r => r.cases.length > 0).sort((a, b) => {
    const order = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
    return Math.min(...a.cases.map(c => order[c.severity])) - Math.min(...b.cases.map(c => order[c.severity]));
  });

  return (
    <Card padded={false} style={{ overflow: 'hidden' }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 0.8fr 1fr 1.1fr 1fr 1.4fr 0.9fr',
        padding: '10px 18px', gap: 12, fontSize: 12, fontWeight: 500, color: 'var(--semantic-label-alternative)',
        borderBottom: '1px solid var(--semantic-line-normal-neutral)', background: 'var(--semantic-background-normal-alternative)' }}>
        <div>근로자</div><div>국적·체류</div><div>체류만료 / D-day</div><div>계약 종료</div>
        <div>서류</div><div>위험도 / 케이스</div><div style={{ textAlign: 'right' }}>다음 처리</div>
      </div>
      {rowsByWorker.map(({ worker, cases: wc }, i) => {
        const topCase = [...wc].sort((a,b) => ({ CRITICAL:0,HIGH:1,MEDIUM:2,LOW:3 }[a.severity] - { CRITICAL:0,HIGH:1,MEDIUM:2,LOW:3 }[b.severity]))[0];
        const dNum = dDayNum(worker.visaExpiry);
        const isCritical = topCase.severity === 'CRITICAL';
        const isSelected = selectedId === worker.id;
        const docMissing = Object.values(worker.docs).filter(s => s !== 'ok').length;
        const sev = SEVERITY_PALETTE[topCase.severity];
        return (
          <div key={worker.id} onClick={() => onSelect(worker.id)} style={{
            display: 'grid', gridTemplateColumns: '1.6fr 0.8fr 1fr 1.1fr 1fr 1.4fr 0.9fr',
            padding: density === 'compact' ? '10px 18px' : '14px 18px', gap: 12,
            alignItems: 'center', minHeight: density === 'compact' ? 52 : 64,
            borderBottom: i < rowsByWorker.length - 1 ? '1px solid var(--semantic-line-normal-alternative)' : 0,
            cursor: 'pointer', position: 'relative',
            background: isSelected ? 'rgba(0,102,255,0.04)' : 'transparent', transition: 'background .15s',
          }}
          onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'var(--semantic-fill-alternative)'; }}
          onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}>
            <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: isCritical ? sev.dot : 'transparent' }}/>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Avatar name={worker.name} initial={worker.avatar} size={36} hue={i}/>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--semantic-label-normal)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  {worker.name}
                  <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--semantic-label-alternative)' }}>· {worker.nameKo}</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', marginTop: 1 }}>{worker.line}</div>
              </div>
            </div>
            <div style={{ fontSize: 13, color: 'var(--semantic-label-neutral)' }}>
              <div>{worker.flag} {worker.nationality}</div>
              <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)', marginTop: 2 }}>{worker.visaType}</div>
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>{fmtDate(worker.visaExpiry)}</div>
              <div style={{ marginTop: 4 }}><DDayBar dNum={dNum} severity={topCase.severity}/></div>
            </div>
            <div style={{ fontSize: 13, fontVariantNumeric: 'tabular-nums' }}>
              {fmtDate(worker.contractEnd)}
              <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', marginTop: 2 }}>{dDay(worker.contractEnd)}</div>
            </div>
            <div style={{ display: 'flex', gap: 4 }}>
              {Object.entries(worker.docs).map(([k, v]) => (
                <span key={k} title={`${k}: ${v}`} style={{
                  width: 22, height: 22, borderRadius: 6, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  background: v === 'ok' ? 'rgba(0,191,64,0.12)' : v === 'expired' ? 'rgba(255,66,66,0.12)' : 'rgba(255,146,0,0.12)',
                  color: v === 'ok' ? '#006E25' : v === 'expired' ? '#B00C0C' : '#9C5800',
                  fontSize: 10, fontWeight: 600,
                }}>{k[0]}</span>
              ))}
              {docMissing > 0 && <span style={{ fontSize: 11, color: 'var(--semantic-status-cautionary)', alignSelf: 'center', marginLeft: 4, fontWeight: 600 }}>+{docMissing} 보완</span>}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <RiskPill level={topCase.severity} dDay={dDay(worker.visaExpiry)} compact/>
              <span style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)' }}>
                {wc.length === 1 ? topCase.label : `${topCase.label} 외 ${wc.length - 1}건`}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              {topCase.actions.length > 0 && (
                <Button variant="outlined" size="small" trailingIcon={<Icon name="chevronRight" size={12}/>}>처리</Button>
              )}
            </div>
          </div>
        );
      })}
    </Card>
  );
};

Object.assign(window, {
  TopBar, TodaySummary, TodaySummaryNew, BriefingBanner,
  WorkerRiskTable, FilterBar, DDayBar,
  TodayTaskQueue, TaskDetailPanel,
});
