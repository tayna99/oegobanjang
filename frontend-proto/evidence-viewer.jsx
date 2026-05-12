// 판단 기록 (Evidence Log) — 레퍼런스 기준
// 좌: 체크박스 리스트 + 필터/검색 + 페이지네이션
// 우: 상세 패널 (판단 요약 / 사용한 정보 / 승인 이력 / 이벤트 타임라인)

/* ─── 모의 판단 기록 데이터 ──────────────────────────────────── */
const EVIDENCE_LOG_ITEMS = [
  {
    id: '#4789', title: '체류기간 연장 서류 요청',
    worker: 'Nguyen V.', status: '승인 완료', statusTone: 'approved',
    time: '2024-05-16 10:42',
    summary: '체류만료일(2024-06-30)이 45일 이내로 확인되어, 누락된 서류를 요청하고 외부 발송 전 베트남어 메시지 초안을 생성하여 대표 승인까지 완료했습니다.',
    usedInfo: ['근로자 프로필', '체류 정보', '케이스 정보', '이전 대화 기록', '서류 체크리스트'],
    approvals: [{ actor: '대표 (대표근로계약서)', status: '승인 완료', by: '김대표', time: '2024-05-16 10:42' }],
    timeline: [
      { label: '체류만료일 확인', time: '2024-05-16 10:10' },
      { label: '누락 서류 감지', time: '2024-05-16 10:11' },
      { label: '이전 대화 기록 확인', time: '2024-05-16 10:14' },
      { label: '베트남어 메시지 초안 생성', time: '2024-05-16 10:18' },
      { label: '대표 승인 요청', time: '2024-05-16 10:24' },
      { label: '외부 발송 전 제한 적용', time: '2024-05-16 10:41' },
    ],
    assignee: '김대리 (인사팀)',
  },
  {
    id: '#4790', title: '비자 연장 안내 메시지 발송',
    worker: 'Nguyen V.', status: '외부 발송', statusTone: 'sent',
    time: '2024-05-16 09:31',
    summary: 'Nguyen V. 체류만료일 임박으로 Zalo를 통해 베트남어 안내 메시지를 발송했습니다.',
    usedInfo: ['근로자 프로필', '체류 정보', '이전 대화 기록'],
    approvals: [{ actor: '김대리 (인사팀)', status: '승인 완료', by: '김대리', time: '2024-05-16 09:28' }],
    timeline: [
      { label: '체류 만료 감지', time: '2024-05-16 09:10' },
      { label: '발송 채널 확인 (Zalo)', time: '2024-05-16 09:20' },
      { label: '메시지 초안 생성', time: '2024-05-16 09:25' },
      { label: '담당자 승인', time: '2024-05-16 09:28' },
      { label: '외부 발송 완료', time: '2024-05-16 09:31' },
    ],
    assignee: '김대리 (인사팀)',
  },
  {
    id: '#4788', title: '건강검진 결과 제출 요청',
    worker: 'Tran T. H.', status: '승인 완료', statusTone: 'approved',
    time: '2024-05-15 16:20',
    summary: '고용허가 갱신을 위한 건강검진 결과서 미제출 확인 후 Zalo를 통해 제출 요청 메시지를 발송했습니다.',
    usedInfo: ['근로자 프로필', '서류 체크리스트', '케이스 정보'],
    approvals: [{ actor: '김대리 (인사팀)', status: '승인 완료', by: '김대리', time: '2024-05-15 16:18' }],
    timeline: [
      { label: '서류 누락 감지', time: '2024-05-15 16:05' },
      { label: '메시지 초안 생성', time: '2024-05-15 16:12' },
      { label: '담당자 승인', time: '2024-05-15 16:18' },
      { label: '발송 완료', time: '2024-05-15 16:20' },
    ],
    assignee: '김대리 (인사팀)',
  },
  {
    id: '#4787', title: '근로계약 갱신 안내',
    worker: '김민수', status: '승인 완료', statusTone: 'approved',
    time: '2024-05-15 11:07',
    summary: '계약 만료 60일 전 근로계약 갱신 의향 확인 메시지를 발송했습니다.',
    usedInfo: ['근로자 프로필', '계약 정보'],
    approvals: [{ actor: '김대리 (인사팀)', status: '승인 완료', by: '김대리', time: '2024-05-15 11:05' }],
    timeline: [
      { label: '계약 만료 60일 전 알림', time: '2024-05-15 11:00' },
      { label: '메시지 생성', time: '2024-05-15 11:03' },
      { label: '승인 및 발송', time: '2024-05-15 11:07' },
    ],
    assignee: '김대리 (인사팀)',
  },
  {
    id: '#4786', title: '서류 보완 요청 (급여명세서)',
    worker: 'Candidate A', status: '승인 완료', statusTone: 'approved',
    time: '2024-05-14 15:48',
    summary: '입국 전 서류 패키지 검토 중 급여명세서 누락이 확인되어 보완 요청했습니다.',
    usedInfo: ['서류 체크리스트', '케이스 정보'],
    approvals: [{ actor: '김대리 (인사팀)', status: '승인 완료', by: '김대리', time: '2024-05-14 15:46' }],
    timeline: [
      { label: '서류 패키지 검토', time: '2024-05-14 15:40' },
      { label: '급여명세서 누락 감지', time: '2024-05-14 15:43' },
      { label: '보완 요청 승인', time: '2024-05-14 15:48' },
    ],
    assignee: '김대리 (인사팀)',
  },
  {
    id: '#4785', title: '비자 연장 필요 알림',
    worker: 'Nguyen V.', status: '외부 발송', statusTone: 'sent',
    time: '2024-05-14 10:22',
    summary: 'D-45 알림 자동 발송. 체류기간 연장 서류 준비 시작을 안내했습니다.',
    usedInfo: ['체류 정보'],
    approvals: [],
    timeline: [
      { label: 'D-45 트리거', time: '2024-05-14 10:20' },
      { label: '자동 발송', time: '2024-05-14 10:22' },
    ],
    assignee: '시스템',
  },
  {
    id: '#4784', title: '입국 날짜 변경 안내',
    worker: 'Pham T. A.', status: '승인 완료', statusTone: 'approved',
    time: '2024-05-13 14:11',
    summary: '항공편 변경으로 인한 입국 날짜 수정 사항을 송출회사에 안내했습니다.',
    usedInfo: ['근로자 프로필', '채용 정보'],
    approvals: [{ actor: '김대리 (인사팀)', status: '승인 완료', by: '김대리', time: '2024-05-13 14:09' }],
    timeline: [
      { label: '날짜 변경 확인', time: '2024-05-13 14:05' },
      { label: '안내문 생성', time: '2024-05-13 14:08' },
      { label: '승인 및 발송', time: '2024-05-13 14:11' },
    ],
    assignee: '김대리 (인사팀)',
  },
  {
    id: '#4783', title: '교육 수료증 제출 요청',
    worker: 'Candidate B', status: '승인 완료', statusTone: 'approved',
    time: '2024-05-13 09:05',
    summary: '취업 전 교육 수료증 미제출로 입국 전 서류 패키지 완성을 위해 제출 요청했습니다.',
    usedInfo: ['서류 체크리스트', '채용 정보'],
    approvals: [{ actor: '김대리 (인사팀)', status: '승인 완료', by: '김대리', time: '2024-05-13 09:03' }],
    timeline: [
      { label: '수료증 누락 감지', time: '2024-05-13 09:00' },
      { label: '제출 요청 승인', time: '2024-05-13 09:05' },
    ],
    assignee: '김대리 (인사팀)',
  },
  {
    id: '#4782', title: '체류만료일 임박 알림',
    worker: 'Nguyen V.', status: '외부 발송', statusTone: 'sent',
    time: '2024-05-12 17:33',
    summary: 'D-60 자동 알림 발송. 체류기간 연장 준비 시작을 안내했습니다.',
    usedInfo: ['체류 정보'],
    approvals: [],
    timeline: [
      { label: 'D-60 트리거', time: '2024-05-12 17:30' },
      { label: '자동 발송', time: '2024-05-12 17:33' },
    ],
    assignee: '시스템',
  },
  {
    id: '#4781', title: '표준근로계약서 수령 안내',
    worker: 'Bayar M.', status: '승인 완료', statusTone: 'approved',
    time: '2024-05-12 11:15',
    summary: '재계약 표준근로계약서 원본 수령 확인 및 서명 요청 메시지를 발송했습니다.',
    usedInfo: ['근로자 프로필', '계약 정보', '서류 체크리스트'],
    approvals: [{ actor: '김대리 (인사팀)', status: '승인 완료', by: '김대리', time: '2024-05-12 11:13' }],
    timeline: [
      { label: '계약서 검토', time: '2024-05-12 11:08' },
      { label: '수령 안내 생성', time: '2024-05-12 11:11' },
      { label: '승인 및 발송', time: '2024-05-12 11:15' },
    ],
    assignee: '김대리 (인사팀)',
  },
];

/* ─── 상태 배지 팔레트 ──────────────────────────────────────── */
const LOG_STATUS_STYLE = {
  approved: { label: '승인 완료', bg: '#DCFCE7', fg: '#166534', bd: '#86EFAC' },
  sent:     { label: '외부 발송', fg: '#1D4ED8', bg: '#DBEAFE', bd: '#93C5FD' },
  pending:  { label: '승인 필요', fg: '#9C5800', bg: '#FFF7ED', bd: '#FED7AA' },
  review:   { label: '행정사 검토', fg: '#5B21B6', bg: '#F5F3FF', bd: '#C4B5FD' },
};

/* ─── 우측 상세 패널 ─────────────────────────────────────────── */
const EvidenceDetailPanel = ({ item, onClose }) => {
  if (!item) return null;
  const st = LOG_STATUS_STYLE[item.statusTone] || LOG_STATUS_STYLE.approved;

  return (
    <aside style={{
      width: 460, flexShrink: 0,
      background: '#fff',
      borderLeft: '1px solid var(--semantic-line-normal-alternative)',
      height: '100%', overflowY: 'auto',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* 헤더 */}
      <div style={{ padding: '20px 24px 16px',
        borderBottom: '1px solid var(--semantic-line-normal-alternative)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 15, fontWeight: 800, color: 'var(--semantic-label-normal)',
              letterSpacing: '-0.01em' }}>
              판단 기록 {item.id}
            </span>
            <span style={{
              padding: '2px 9px', borderRadius: 99, fontSize: 12, fontWeight: 600,
              background: st.bg, color: st.fg, border: `1px solid ${st.bd}`,
            }}>{st.label}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {/* 더보기 */}
            <button style={{ background: 'transparent', border: '1px solid var(--semantic-line-normal-alternative)',
              borderRadius: 6, cursor: 'pointer', padding: '4px 8px', color: 'var(--semantic-label-alternative)' }}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                <circle cx="3" cy="8" r="1.5" fill="currentColor"/>
                <circle cx="8" cy="8" r="1.5" fill="currentColor"/>
                <circle cx="13" cy="8" r="1.5" fill="currentColor"/>
              </svg>
            </button>
            <button onClick={onClose} style={{ background: 'transparent', border: 0,
              cursor: 'pointer', color: 'var(--semantic-label-alternative)', padding: 4, borderRadius: 6 }}>
              <Icon name="close" size={16}/>
            </button>
          </div>
        </div>

        {/* 메타 정보 3열 */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12,
          padding: '12px 0', borderBottom: '1px solid var(--semantic-line-normal-alternative)' }}>
          {[
            { label: '담당자', value: item.assignee },
            { label: '대상 근로자', value: item.worker },
            { label: '관련 케이스', value: item.title },
          ].map(kv => (
            <div key={kv.label}>
              <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', marginBottom: 3 }}>
                {kv.label}
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--semantic-label-normal)',
                lineHeight: 1.3 }}>
                {kv.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '18px 24px',
        display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* 판단 요약 */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <div style={{ width: 22, height: 22, borderRadius: 6,
              background: 'rgba(27,63,160,0.10)',
              display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                <path d="M8 1l1.5 4.5H14l-3.75 2.75L11.5 13 8 10.25 4.5 13l1.25-4.75L2 5.5h4.5L8 1z"
                  stroke="#1B3FA0" strokeWidth="1.3" strokeLinejoin="round"/>
              </svg>
            </div>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--semantic-label-normal)' }}>판단 요약</span>
          </div>
          <div style={{ fontSize: 13.5, color: 'var(--semantic-label-neutral)', lineHeight: 1.7,
            padding: '12px 14px', borderRadius: 10,
            background: 'var(--semantic-background-normal-alternative)',
            border: '1px solid var(--semantic-line-normal-alternative)' }}>
            {item.summary}
          </div>
        </div>

        {/* 사용한 정보 */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <div style={{ width: 22, height: 22, borderRadius: 6,
              background: 'rgba(16,185,129,0.10)',
              display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                <path d="M14 2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z"
                  stroke="#10B981" strokeWidth="1.4"/>
                <path d="M6 9h4M6 12h2" stroke="#10B981" strokeWidth="1.3" strokeLinecap="round"/>
              </svg>
            </div>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--semantic-label-normal)' }}>사용한 정보</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {item.usedInfo.map(tag => (
              <span key={tag} style={{
                padding: '4px 10px', borderRadius: 99, fontSize: 12, fontWeight: 500,
                background: 'var(--semantic-fill-alternative)',
                color: 'var(--semantic-label-neutral)',
                border: '1px solid var(--semantic-line-normal-alternative)',
              }}>{tag}</span>
            ))}
          </div>
        </div>

        {/* 승인 이력 */}
        {item.approvals.length > 0 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <div style={{ width: 22, height: 22, borderRadius: 6,
                background: 'rgba(245,158,11,0.10)',
                display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="6" r="3" stroke="#F59E0B" strokeWidth="1.4"/>
                  <path d="M2 14c0-3 2.686-4 6-4s6 1 6 4" stroke="#F59E0B" strokeWidth="1.4" strokeLinecap="round"/>
                </svg>
              </div>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--semantic-label-normal)' }}>승인 이력</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {item.approvals.map((ap, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 12px', borderRadius: 8,
                  background: 'var(--semantic-background-normal-alternative)',
                  border: '1px solid var(--semantic-line-normal-alternative)',
                }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--semantic-label-normal)' }}>
                      {ap.actor}
                    </div>
                    <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)', marginTop: 1 }}>
                      {ap.by} · {ap.time}
                    </div>
                  </div>
                  <span style={{
                    padding: '2px 9px', borderRadius: 99, fontSize: 12, fontWeight: 600,
                    background: '#DCFCE7', color: '#166534',
                  }}>{ap.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 이벤트 타임라인 */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
            <div style={{ width: 22, height: 22, borderRadius: 6,
              background: 'rgba(99,102,241,0.10)',
              display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="6.5" stroke="#6366F1" strokeWidth="1.4"/>
                <path d="M8 5v3l2 2" stroke="#6366F1" strokeWidth="1.4" strokeLinecap="round"/>
              </svg>
            </div>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--semantic-label-normal)' }}>이벤트 타임라인</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {item.timeline.map((ev, i) => (
              <div key={i} style={{ display: 'flex', gap: 12, paddingBottom: 10 }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 3 }}>
                  <div style={{ width: 8, height: 8, borderRadius: 999,
                    background: '#10B981', border: '2px solid #DCFCE7', flexShrink: 0 }}/>
                  {i < item.timeline.length - 1 && (
                    <div style={{ width: 1.5, flex: 1, background: '#D1FAE5', marginTop: 3, minHeight: 12 }}/>
                  )}
                </div>
                <div style={{ paddingBottom: 2 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--semantic-label-normal)' }}>
                    {ev.label}
                  </div>
                  <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)', marginTop: 1 }}>
                    {ev.time}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
};

/* ─── 판단 기록 메인 뷰 ──────────────────────────────────────── */
function EvidenceLogView() {
  const [selectedId, setSelectedId] = React.useState('#4789');
  const [checkedIds, setCheckedIds] = React.useState(new Set());
  const [filterTab, setFilterTab] = React.useState('all');
  const [search, setSearch] = React.useState('');
  const [page, setPage] = React.useState(1);
  const PAGE_SIZE = 10;

  const filterTabs = [
    { id: 'all',      label: '전체' },
    { id: 'approved', label: '승인 필요' },
    { id: 'sent',     label: '외부 발송' },
    { id: 'review',   label: '행정사 검토' },
  ];

  const filtered = EVIDENCE_LOG_ITEMS.filter(item => {
    const matchSearch = !search || item.title.includes(search) || item.worker.includes(search) || item.id.includes(search);
    return matchSearch;
  });

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const selectedItem = EVIDENCE_LOG_ITEMS.find(i => i.id === selectedId);

  const toggleCheck = (id, e) => {
    e.stopPropagation();
    setCheckedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (checkedIds.size === paged.length) setCheckedIds(new Set());
    else setCheckedIds(new Set(paged.map(i => i.id)));
  };

  return (
    <div style={{ display: 'flex', height: '100%', minHeight: 0, gap: 0 }}>
      {/* 좌: 리스트 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* 페이지 타이틀 */}
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 4 }}>
            판단 기록
          </h2>
        </div>

        {/* 필터 탭 + 검색 + 필터 버튼 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          {/* 필터 탭 */}
          <div style={{ display: 'flex', gap: 0, border: '1px solid var(--semantic-line-normal-alternative)',
            borderRadius: 8, overflow: 'hidden', flexShrink: 0 }}>
            {filterTabs.map(tab => (
              <button key={tab.id} onClick={() => setFilterTab(tab.id)} style={{
                padding: '7px 14px', border: 0, cursor: 'pointer', fontFamily: 'inherit',
                fontSize: 13, fontWeight: filterTab === tab.id ? 600 : 500,
                background: filterTab === tab.id ? '#1B3FA0' : '#fff',
                color: filterTab === tab.id ? '#fff' : 'var(--semantic-label-neutral)',
                borderRight: '1px solid var(--semantic-line-normal-alternative)',
              }}>{tab.label}</button>
            ))}
          </div>

          <div style={{ flex: 1 }}/>

          {/* 검색 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '7px 12px',
            background: '#fff', borderRadius: 8, border: '1px solid var(--semantic-line-normal-alternative)',
            width: 260 }}>
            <Icon name="search" size={14} color="var(--semantic-label-alternative)"/>
            <input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
              placeholder="키워드 검색 (사유, 이벤트, 대상 등)"
              style={{ flex: 1, border: 0, background: 'transparent', outline: 'none',
                fontFamily: 'inherit', fontSize: 12.5, color: 'var(--semantic-label-normal)' }}/>
          </div>

          {/* 필터 버튼 */}
          <button style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '7px 12px',
            borderRadius: 8, border: '1px solid var(--semantic-line-normal-alternative)',
            background: '#fff', cursor: 'pointer', fontFamily: 'inherit',
            fontSize: 12.5, fontWeight: 500, color: 'var(--semantic-label-neutral)' }}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M2 4h12M4 8h8M6 12h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            필터
          </button>
        </div>

        {/* 테이블 */}
        <div style={{ background: '#fff', borderRadius: 12, overflow: 'hidden',
          border: '1px solid var(--semantic-line-normal-alternative)',
          boxShadow: '0 1px 4px rgba(0,0,0,0.04)', flex: 1, display: 'flex', flexDirection: 'column' }}>

          {/* 헤더 */}
          <div style={{ display: 'grid', gridTemplateColumns: '36px 120px 1fr 120px 140px 160px',
            padding: '10px 16px', gap: 12,
            fontSize: 12, fontWeight: 600, color: 'var(--semantic-label-alternative)',
            background: 'var(--semantic-background-normal-alternative)',
            borderBottom: '1px solid var(--semantic-line-normal-alternative)' }}>
            <input type="checkbox"
              checked={checkedIds.size === paged.length && paged.length > 0}
              onChange={toggleAll}
              style={{ cursor: 'pointer', accentColor: '#1B3FA0' }}/>
            <div>판단 기록</div>
            <div>제목</div>
            <div>대상 근로자</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              최종 상태
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
              판단 시간
              <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
                <path d="M6 2v8M3 7l3 3 3-3" stroke="#1B3FA0" strokeWidth="1.3" strokeLinecap="round"/>
              </svg>
            </div>
          </div>

          {/* 행 */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {paged.map((item) => {
              const st = LOG_STATUS_STYLE[item.statusTone] || LOG_STATUS_STYLE.approved;
              const isSelected = selectedId === item.id;
              return (
                <div key={item.id} onClick={() => setSelectedId(item.id)} style={{
                  display: 'grid', gridTemplateColumns: '36px 120px 1fr 120px 140px 160px',
                  padding: '12px 16px', gap: 12, cursor: 'pointer',
                  background: isSelected ? 'rgba(27,63,160,0.04)' : '#fff',
                  borderBottom: '1px solid var(--semantic-line-normal-alternative)',
                  borderLeft: isSelected ? '3px solid #1B3FA0' : '3px solid transparent',
                  transition: 'background .12s',
                  alignItems: 'center',
                }}>
                  <input type="checkbox" checked={checkedIds.has(item.id)}
                    onChange={e => toggleCheck(item.id, e)}
                    onClick={e => e.stopPropagation()}
                    style={{ cursor: 'pointer', accentColor: '#1B3FA0' }}/>
                  <span style={{ fontSize: 12.5, fontWeight: 600, color: '#1B3FA0', fontFamily: 'var(--font-mono)' }}>
                    {item.id}
                  </span>
                  <span style={{ fontSize: 13.5, fontWeight: isSelected ? 600 : 500,
                    color: 'var(--semantic-label-normal)', overflow: 'hidden',
                    textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.title}
                  </span>
                  <span style={{ fontSize: 13, color: 'var(--semantic-label-neutral)' }}>
                    {item.worker}
                  </span>
                  <span style={{
                    padding: '3px 9px', borderRadius: 99, fontSize: 12, fontWeight: 600,
                    background: st.bg, color: st.fg, border: `1px solid ${st.bd}`,
                    justifySelf: 'start',
                  }}>{st.label}</span>
                  <span style={{ fontSize: 12.5, color: 'var(--semantic-label-alternative)',
                    fontVariantNumeric: 'tabular-nums' }}>
                    {item.time}
                  </span>
                </div>
              );
            })}
          </div>

          {/* 하단: 총 건수 + 페이지네이션 */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 16px', borderTop: '1px solid var(--semantic-line-normal-alternative)',
            background: '#fafafa' }}>
            <span style={{ fontSize: 12.5, color: 'var(--semantic-label-alternative)' }}>
              전체 235건
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <button onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                style={{ width: 28, height: 28, borderRadius: 6, border: '1px solid var(--semantic-line-normal-alternative)',
                  background: '#fff', cursor: page === 1 ? 'default' : 'pointer',
                  opacity: page === 1 ? 0.4 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon name="chevronLeft" size={13} color="var(--semantic-label-neutral)"/>
              </button>
              {[1, 2, 3, 4, 5].map(n => (
                <button key={n} onClick={() => setPage(n)} style={{
                  width: 28, height: 28, borderRadius: 6, border: '1px solid var(--semantic-line-normal-alternative)',
                  background: page === n ? '#1B3FA0' : '#fff',
                  color: page === n ? '#fff' : 'var(--semantic-label-neutral)',
                  cursor: 'pointer', fontFamily: 'inherit', fontSize: 13, fontWeight: 500,
                }}>{n}</button>
              ))}
              <span style={{ fontSize: 12.5, color: 'var(--semantic-label-alternative)', margin: '0 4px' }}>
                ...
              </span>
              <button onClick={() => setPage(24)} style={{
                width: 28, height: 28, borderRadius: 6, border: '1px solid var(--semantic-line-normal-alternative)',
                background: '#fff', color: 'var(--semantic-label-neutral)',
                cursor: 'pointer', fontFamily: 'inherit', fontSize: 13,
              }}>24</button>
              <button onClick={() => setPage(p => Math.min(24, p + 1))}
                style={{ width: 28, height: 28, borderRadius: 6, border: '1px solid var(--semantic-line-normal-alternative)',
                  background: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon name="chevronRight" size={13} color="var(--semantic-label-neutral)"/>
              </button>
              {/* 페이지당 */}
              <div style={{ marginLeft: 8, display: 'flex', alignItems: 'center', gap: 4,
                padding: '4px 8px', borderRadius: 6, border: '1px solid var(--semantic-line-normal-alternative)',
                background: '#fff', cursor: 'pointer', fontSize: 12, color: 'var(--semantic-label-neutral)' }}>
                10 / 페이지
                <Icon name="chevronDown" size={11} color="var(--semantic-label-alternative)"/>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 우: 상세 패널 */}
      {selectedItem && (
        <div className="panel-enter" style={{ flexShrink: 0 }}>
          <EvidenceDetailPanel item={selectedItem} onClose={() => setSelectedId(null)}/>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { EvidenceLogView, EvidenceViewerView: EvidenceLogView });
