// 채용 준비 탭 — 신규 고용 준비 상태 점검 화면.
// 후보자 추천·점수화 없음. 준비 상태 체크가 핵심.

const ReadinessBar = ({ pct }) => (
  <div style={{ marginTop: 10 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
      <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', fontWeight: 500 }}>준비 완료도</span>
      <span style={{ fontSize: 13, fontWeight: 700,
        color: pct >= 80 ? '#006E25' : pct >= 50 ? '#1B3FA0' : '#9C5800' }}>
        {pct}%
      </span>
    </div>
    <div style={{ height: 6, borderRadius: 999, background: 'var(--semantic-fill-alternative)', overflow: 'hidden' }}>
      <div style={{
        height: '100%', borderRadius: 999,
        background: pct >= 80
          ? 'linear-gradient(90deg, #10B981, #059669)'
          : 'linear-gradient(90deg, #1B3FA0, #00BFA5)',
        width: `${pct}%`, transition: 'width 0.4s ease',
      }}/>
    </div>
  </div>
);

const RecruitStatusBadge = ({ status }) => {
  const map = {
    in_progress:     { label: '준비 중',        bg: 'rgba(59,130,246,0.12)',  color: '#1B3FA0' },
    review_required: { label: '검토 필요',       bg: 'rgba(245,158,11,0.12)', color: '#9C5800' },
    done:            { label: '완료',            bg: 'rgba(16,185,129,0.12)', color: '#006E25' },
  };
  const s = map[status] || map.in_progress;
  return (
    <span style={{ padding: '3px 8px', borderRadius: 6, fontSize: 11.5, fontWeight: 600,
      background: s.bg, color: s.color }}>
      {s.label}
    </span>
  );
};

const WorkforceChecklist = ({ tasks, doneCount, totalCount }) => (
  <div style={{ marginTop: 14 }}>
    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--semantic-label-neutral)',
      marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
      <span>남은 작업</span>
      <span style={{ color: 'var(--semantic-label-alternative)' }}>{doneCount}/{totalCount} 완료</span>
    </div>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {tasks.map((t, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 10px', borderRadius: 8,
          background: 'var(--semantic-background-normal-alternative)',
          border: '1px solid var(--semantic-line-normal-alternative)',
        }}>
          <div style={{ width: 18, height: 18, borderRadius: 5,
            border: '1.5px solid var(--semantic-line-normal-normal)',
            background: 'var(--semantic-background-elevated-normal)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0 }}>
          </div>
          <span style={{ fontSize: 13, color: 'var(--semantic-label-neutral)' }}>{t}</span>
        </div>
      ))}
    </div>
  </div>
);

const RecruitmentRequestCard = ({ req, onRequestReview }) => (
  <div style={{
    background: 'var(--semantic-background-elevated-normal)',
    border: '1px solid var(--semantic-line-normal-neutral)',
    borderRadius: 16, padding: '20px 22px',
    boxShadow: 'var(--shadow-small)',
    position: 'relative', overflow: 'hidden',
  }}>
    {/* 상단 컬러 바 */}
    <div style={{
      position: 'absolute', top: 0, left: 0, right: 0, height: 3,
      background: req.status === 'review_required'
        ? 'linear-gradient(90deg, #F59E0B, #FBBF24)'
        : 'linear-gradient(90deg, #1B3FA0, #00BFA5)',
    }}/>

    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: 4 }}>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <div style={{ padding: '3px 8px', borderRadius: 6, fontSize: 11.5, fontWeight: 700,
            background: 'rgba(27,63,160,0.10)', color: '#1B3FA0' }}>
            {req.type} · {req.headcount}명
          </div>
          <RecruitStatusBadge status={req.status}/>
        </div>
        <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.015em',
          color: 'var(--semantic-label-normal)', marginBottom: 4 }}>
          {req.title}
        </div>
        <div style={{ fontSize: 13, color: 'var(--semantic-label-alternative)' }}>
          {req.worksite} · {req.line}
          {req.note && (
            <span style={{ marginLeft: 8, color: '#9C5800', fontWeight: 500 }}>· {req.note}</span>
          )}
        </div>
      </div>
      <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 16 }}>
        <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', marginBottom: 2 }}>마감</div>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--semantic-label-normal)' }}>
          {fmtDate(req.deadline)}
        </div>
      </div>
    </div>

    <ReadinessBar pct={req.readiness}/>

    <WorkforceChecklist
      tasks={req.remainingTasks}
      doneCount={req.doneTaskCount}
      totalCount={req.totalTaskCount}
    />

    <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
      <Button variant="outlined" size="small"
        leadingIcon={<Icon name="file" size={13}/>}>
        요청서 보기
      </Button>
      <Button variant="outlined" size="small"
        leadingIcon={<Icon name="check" size={13}/>}
        onClick={() => onRequestReview(req.id)}>
        행정사 검토 요청
      </Button>
      <div style={{ flex: 1 }}/>
      {req.readiness < 100 && (
        <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)',
          alignSelf: 'center' }}>
          남은 작업 {req.remainingTasks.length}개
        </span>
      )}
    </div>
  </div>
);

const RecruitmentReadinessView = () => {
  const reqs = window.RECRUITMENT_REQUESTS;
  const [reviewRequested, setReviewRequested] = React.useState(new Set());

  const handleRequestReview = (id) => {
    setReviewRequested(prev => new Set([...prev, id]));
  };

  return (
    <div>
      {/* 헤더 */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em',
          color: 'var(--semantic-label-normal)', marginBottom: 6 }}>
          채용 준비
        </div>
        <div style={{ fontSize: 14, color: 'var(--semantic-label-alternative)' }}>
          신규 고용 준비 상태를 점검합니다. 후보자 점수화나 추천은 하지 않습니다.
        </div>
      </div>

      {/* 요약 배너 */}
      <div style={{
        padding: '14px 18px', borderRadius: 12, marginBottom: 24,
        background: 'linear-gradient(90deg, rgba(27,63,160,0.06), rgba(0,191,165,0.04))',
        border: '1px solid rgba(27,63,160,0.18)',
        display: 'flex', alignItems: 'center', gap: 14,
      }}>
        <div style={{ width: 36, height: 36, borderRadius: 10,
          background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon name="people" size={18} color="#fff"/>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--semantic-label-normal)', marginBottom: 2 }}>
            신규 채용 준비 {reqs.length}건 진행 중
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--semantic-label-neutral)' }}>
            검토 필요 {reqs.filter(r => r.status === 'review_required').length}건 · 준비 중 {reqs.filter(r => r.status === 'in_progress').length}건
          </div>
        </div>
      </div>

      {/* 채용 요청 카드 목록 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {reqs.map(req => (
          <RecruitmentRequestCard
            key={req.id}
            req={req}
            onRequestReview={handleRequestReview}
          />
        ))}
      </div>
    </div>
  );
};

Object.assign(window, { RecruitmentReadinessView });
