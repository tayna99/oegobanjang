// Screen 4: Approval Center — 승인 대기 큐
// SVG 아키텍처 기준: pending-first 강조, "승인 시 내부 패키지만 생성" 명시

const SEVERITY_PALETTE_AC = {
  CRITICAL: { bg: '#FEE2E2', fg: '#7F1D1D', dot: '#EF4444' },
  HIGH:     { bg: '#FFEDD5', fg: '#7C2D12', dot: '#F97316' },
  MEDIUM:   { bg: '#FEF9C3', fg: '#713F12', dot: '#EAB308' },
  LOW:      { bg: '#D1FAE5', fg: '#065F46', dot: '#10B981' },
};

const TYPE_LABEL = {
  document_request: '서류 요청',
  handoff_package:  '행정사 자료',
  report_filing:    '신고서 자료',
};

function ApprovalStatusBadge({ status }) {
  const styles = {
    pending:  { bg: '#EFF6FF', fg: '#1D4ED8', label: '승인 대기' },
    approved: { bg: '#D1FAE5', fg: '#065F46', label: '승인 완료' },
    rejected: { bg: '#FEE2E2', fg: '#7F1D1D', label: '반려' },
    revised:  { bg: '#F3E8FF', fg: '#6B21A8', label: '수정 요청' },
  };
  const s = styles[status] || styles.pending;
  return (
    <span style={{
      padding: '2px 9px', borderRadius: 99, fontSize: 11.5, fontWeight: 600,
      background: s.bg, color: s.fg,
    }}>{s.label}</span>
  );
}

function EvidenceGradePill({ grade }) {
  const p = EVIDENCE_GRADE_PALETTE[grade];
  if (!p) return null;
  return (
    <span style={{
      padding: '1px 7px', borderRadius: 99, fontSize: 11, fontWeight: 700,
      background: p.bg, color: p.fg, border: `1px solid ${p.border}`,
      fontVariantNumeric: 'tabular-nums',
    }}>
      {grade} <span style={{ fontWeight: 400 }}>{p.label}</span>
    </span>
  );
}

function ApprovalItemCard({ item, onApprove, onRevise, onExpand, expanded }) {
  const sev = SEVERITY_PALETTE_AC[item.severity] || SEVERITY_PALETTE_AC.LOW;
  const isPending = item.status === 'pending';
  const cit = item.citationIds?.map(id => CITATIONS[id]).filter(Boolean) || [];

  return (
    <div style={{
      background: '#fff',
      border: `1px solid ${isPending ? '#BFDBFE' : 'var(--semantic-line-normal-alternative)'}`,
      borderLeft: `4px solid ${sev.dot}`,
      borderRadius: 12,
      marginBottom: 12,
      boxShadow: isPending ? '0 2px 12px rgba(29,78,216,0.07)' : 'none',
      overflow: 'hidden',
    }}>
      {/* 헤더 */}
      <div
        style={{ padding: '14px 18px', cursor: 'pointer', display: 'flex', gap: 12, alignItems: 'flex-start' }}
        onClick={() => onExpand(item.id)}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
            <span style={{
              fontSize: 11.5, fontWeight: 600, padding: '1px 7px', borderRadius: 99,
              background: sev.bg, color: sev.fg,
            }}>{item.severity}</span>
            <span style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)',
              background: 'var(--semantic-fill-alternative)', padding: '1px 8px', borderRadius: 99, fontWeight: 500 }}>
              {TYPE_LABEL[item.type] || item.type}
            </span>
            <ApprovalStatusBadge status={item.status}/>
          </div>
          <div style={{ fontSize: 14.5, fontWeight: 700, color: 'var(--semantic-label-normal)', marginBottom: 4 }}>
            {item.title}
          </div>
          <div style={{ fontSize: 13, color: 'var(--semantic-label-neutral)', display: 'flex', gap: 10 }}>
            <span>{item.flag} {item.worker}</span>
            <span>·</span>
            <span>채널: {item.channel}</span>
            <span>·</span>
            <span style={{ color: 'var(--semantic-label-alternative)' }}>
              {new Date(item.requestedAt).toLocaleString('ko-KR', { hour: '2-digit', minute: '2-digit' })} · {item.requestedBy}
            </span>
          </div>
        </div>
        <Icon name={expanded ? 'chevronUp' : 'chevronDown'} size={16} color="var(--semantic-label-alternative)"/>
      </div>

      {/* 펼침 영역 */}
      {expanded && (
        <div style={{ borderTop: '1px solid var(--semantic-line-normal-alternative)', padding: '14px 18px' }}>
          <p style={{ fontSize: 13.5, color: 'var(--semantic-label-neutral)', lineHeight: 1.65, marginBottom: 14 }}>
            {item.summary}
          </p>

          {/* 근거 citations */}
          {cit.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--semantic-label-alternative)',
                marginBottom: 6, letterSpacing: '0.04em', textTransform: 'uppercase' }}>근거 자료</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                {cit.map(c => (
                  <div key={c.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 8,
                    padding: '8px 10px', borderRadius: 8,
                    background: 'var(--semantic-background-normal-alternative)' }}>
                    <EvidenceGradePill grade={c.grade}/>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--semantic-label-normal)',
                        marginBottom: 2 }}>{c.title}</div>
                      <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)' }}>{c.source}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 안전 원칙 배너 */}
          <div style={{ padding: '8px 12px', borderRadius: 8, marginBottom: 14,
            background: 'rgba(255,146,0,0.07)', border: '1px solid rgba(255,146,0,0.22)',
            fontSize: 12.5, color: '#9C5800', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Icon name="shield" size={13}/>
            {item.note}
          </div>

          {/* 액션 버튼 */}
          {isPending ? (
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => onRevise(item.id)} style={{
                padding: '8px 16px', borderRadius: 8, border: '1px solid var(--semantic-line-normal-normal)',
                background: '#fff', cursor: 'pointer', fontFamily: 'inherit',
                fontSize: 13, fontWeight: 600, color: 'var(--semantic-label-neutral)',
              }}>수정 요청</button>
              <button onClick={() => onApprove(item.id)} style={{
                padding: '8px 20px', borderRadius: 8, border: 0,
                background: 'linear-gradient(135deg, #1B3FA0, #00BFA5)',
                color: '#fff', cursor: 'pointer', fontFamily: 'inherit',
                fontSize: 13, fontWeight: 700,
                boxShadow: '0 2px 8px rgba(27,63,160,0.28)',
              }}>승인하기</button>
            </div>
          ) : (
            <div style={{ fontSize: 12.5, color: 'var(--semantic-label-alternative)', textAlign: 'right' }}>
              {item.status === 'approved'
                ? `✓ ${item.approvedBy || '담당자'} 승인 · ${new Date(item.approvedAt).toLocaleString('ko-KR')}`
                : '처리 완료'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ApprovalCenterView() {
  const [approvals, setApprovals] = React.useState(APPROVAL_QUEUE);
  const [expandedId, setExpandedId] = React.useState(APPROVAL_QUEUE[0]?.id || null);
  const [filter, setFilter] = React.useState('pending');

  const handleApprove = (id) => {
    setApprovals(prev => prev.map(a => a.id === id
      ? { ...a, status: 'approved', approvedAt: new Date().toISOString(), approvedBy: '김인사 차장' }
      : a
    ));
  };
  const handleRevise = (id) => {
    setApprovals(prev => prev.map(a => a.id === id ? { ...a, status: 'revised' } : a));
  };

  const filtered = filter === 'all' ? approvals : approvals.filter(a => a.status === filter);
  const pendingCount = approvals.filter(a => a.status === 'pending').length;

  return (
    <div style={{ maxWidth: 760, margin: '0 auto' }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <h2 style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.02em', margin: 0 }}>
            승인 센터
          </h2>
          {pendingCount > 0 && (
            <span style={{ padding: '2px 10px', borderRadius: 99, fontSize: 12, fontWeight: 700,
              background: '#1B3FA0', color: '#fff' }}>대기 {pendingCount}건</span>
          )}
        </div>
        <p style={{ fontSize: 13.5, color: 'var(--semantic-label-alternative)', margin: 0, lineHeight: 1.6 }}>
          AI가 생성한 액션을 검토하고 승인하세요. 승인 전까지 외부로 아무것도 발송되지 않습니다.
        </p>
      </div>

      {/* 안전 원칙 배너 (상단 고정) */}
      <div style={{
        padding: '10px 16px', borderRadius: 10, marginBottom: 20,
        background: 'linear-gradient(90deg, rgba(27,63,160,0.07), rgba(0,191,165,0.07))',
        border: '1px solid rgba(27,63,160,0.18)',
        display: 'flex', alignItems: 'center', gap: 8,
        fontSize: 13, color: '#1B3FA0', fontWeight: 500,
      }}>
        <Icon name="shield" size={15} color="#1B3FA0"/>
        승인해도 외부 전송 없음 — 내부 패키지만 생성됩니다. AI는 판정자가 아니라 검토 도우미입니다.
      </div>

      {/* 필터 탭 */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16 }}>
        {[['pending', '승인 대기'], ['approved', '승인 완료'], ['all', '전체']].map(([v, label]) => (
          <button key={v} onClick={() => setFilter(v)} style={{
            padding: '6px 14px', borderRadius: 8, border: 0, cursor: 'pointer',
            fontFamily: 'inherit', fontSize: 13, fontWeight: 600,
            background: filter === v ? '#1B3FA0' : 'var(--semantic-fill-alternative)',
            color: filter === v ? '#fff' : 'var(--semantic-label-neutral)',
          }}>
            {label}
            {v === 'pending' && pendingCount > 0 && (
              <span style={{ marginLeft: 5, fontSize: 11, fontWeight: 700,
                background: filter === 'pending' ? 'rgba(255,255,255,0.25)' : '#EF4444',
                color: filter === 'pending' ? '#fff' : '#fff',
                padding: '0 5px', borderRadius: 99 }}>{pendingCount}</span>
            )}
          </button>
        ))}
      </div>

      {/* 카드 목록 */}
      {filtered.length === 0 ? (
        <div style={{ padding: 60, textAlign: 'center', color: 'var(--semantic-label-alternative)',
          fontSize: 14, fontWeight: 500 }}>
          대기 중인 승인 건이 없습니다.
        </div>
      ) : (
        filtered.map(item => (
          <ApprovalItemCard
            key={item.id}
            item={item}
            expanded={expandedId === item.id}
            onExpand={(id) => setExpandedId(prev => prev === id ? null : id)}
            onApprove={handleApprove}
            onRevise={handleRevise}
          />
        ))
      )}
    </div>
  );
}

Object.assign(window, { ApprovalCenterView });
