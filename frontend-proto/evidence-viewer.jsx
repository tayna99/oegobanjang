// Screen 7: Evidence Viewer — citation 원본 + grade A~F 시각화
// SVG 아키텍처 기준: grade 색상, missing/stale flag, "refresh queue" 액션

function EvidenceGradeBlock({ grade }) {
  const palette = EVIDENCE_GRADE_PALETTE;
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 20 }}>
      {Object.entries(palette).map(([g, p]) => (
        <div key={g} style={{
          padding: '4px 12px', borderRadius: 99,
          background: p.bg, color: p.fg,
          border: `1px solid ${p.border}`,
          fontSize: 12, fontWeight: 700,
          display: 'flex', alignItems: 'center', gap: 5,
          opacity: grade === g ? 1 : 0.38,
          transform: grade === g ? 'scale(1.08)' : 'none',
          transition: 'all .15s',
        }}>
          <span style={{ fontWeight: 800 }}>{g}</span>
          <span style={{ fontWeight: 400 }}>{p.label}</span>
        </div>
      ))}
    </div>
  );
}

function CitationCard({ cit, highlighted, onRefresh }) {
  const [open, setOpen] = React.useState(false);
  const p = EVIDENCE_GRADE_PALETTE[cit.grade] || EVIDENCE_GRADE_PALETTE['C'];
  const isWeak = ['D', 'E', 'F'].includes(cit.grade);

  return (
    <div style={{
      background: '#fff',
      border: `1px solid ${highlighted ? p.border : 'var(--semantic-line-normal-alternative)'}`,
      borderLeft: `4px solid ${p.border}`,
      borderRadius: 12,
      marginBottom: 10,
      boxShadow: highlighted ? '0 2px 12px rgba(0,0,0,0.08)' : 'none',
      overflow: 'hidden',
    }}>
      {/* 헤더 */}
      <div
        onClick={() => setOpen(v => !v)}
        style={{ padding: '14px 16px', cursor: 'pointer', display: 'flex', gap: 10, alignItems: 'flex-start' }}
      >
        {/* Grade 뱃지 */}
        <span style={{
          width: 30, height: 30, borderRadius: 8, flexShrink: 0,
          background: p.bg, color: p.fg, border: `1px solid ${p.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 800, fontSize: 14,
        }}>{cit.grade}</span>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--semantic-label-normal)' }}>
              {cit.title}
            </span>
            {isWeak && (
              <span style={{ fontSize: 11, fontWeight: 600, padding: '1px 7px', borderRadius: 99,
                background: '#FEE2E2', color: '#7F1D1D' }}>
                참고용 / 데모용
              </span>
            )}
            {highlighted && (
              <span style={{ fontSize: 11, fontWeight: 600, padding: '1px 7px', borderRadius: 99,
                background: '#EFF6FF', color: '#1D4ED8' }}>
                현재 답변에 사용됨
              </span>
            )}
          </div>
          <div style={{ fontSize: 12.5, color: 'var(--semantic-label-alternative)' }}>
            {cit.source} · 최종 업데이트 {cit.updated}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={e => { e.stopPropagation(); onRefresh(cit.id); }}
            style={{
              padding: '4px 10px', borderRadius: 6, fontSize: 11.5, fontWeight: 600,
              border: '1px solid var(--semantic-line-normal-normal)',
              background: '#fff', cursor: 'pointer', fontFamily: 'inherit',
              color: 'var(--semantic-label-neutral)', whiteSpace: 'nowrap',
            }}
          >
            refresh 큐 추가
          </button>
          <Icon name={open ? 'chevronUp' : 'chevronDown'} size={14} color="var(--semantic-label-alternative)"/>
        </div>
      </div>

      {/* 펼침: 원본 chunk */}
      {open && (
        <div style={{
          borderTop: '1px solid var(--semantic-line-normal-alternative)',
          padding: '14px 16px',
          background: 'var(--semantic-background-normal-alternative)',
        }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--semantic-label-alternative)',
            marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            원본 청크
          </div>
          <blockquote style={{
            margin: 0, padding: '10px 14px',
            background: '#fff', borderRadius: 8,
            borderLeft: `3px solid ${p.border}`,
            fontSize: 13.5, lineHeight: 1.7, color: 'var(--semantic-label-normal)',
            fontStyle: 'normal',
          }}>
            {cit.snippet}
          </blockquote>
          <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)' }}>
              Publisher: {cit.source}
            </span>
            <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)' }}>·</span>
            <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)' }}>
              URL: {cit.url}
            </span>
            <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)' }}>·</span>
            <span style={{ padding: '1px 7px', borderRadius: 99, fontSize: 11, fontWeight: 600,
              background: p.bg, color: p.fg, border: `1px solid ${p.border}` }}>
              Grade {cit.grade} — {p.label}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function EvidenceViewerView() {
  const [selectedCase, setSelectedCase] = React.useState('case_002');
  const [refreshQueue, setRefreshQueue] = React.useState(new Set());

  const caseObj = CASES.find(c => c.id === selectedCase);
  const citIds = caseObj?.citationIds || [];
  const citations = citIds.map(id => CITATIONS[id]).filter(Boolean);

  const handleRefresh = (citId) => {
    setRefreshQueue(prev => new Set([...prev, citId]));
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 6 }}>
          Evidence Viewer
        </h2>
        <p style={{ fontSize: 13.5, color: 'var(--semantic-label-alternative)', margin: 0, lineHeight: 1.6 }}>
          AI 답변의 근거 자료 원본을 확인하세요. Grade D/F는 참고용·데모용으로만 사용됩니다.
        </p>
      </div>

      {/* Grade 범례 */}
      <div style={{ marginBottom: 20, padding: '14px 16px', borderRadius: 10,
        background: 'var(--semantic-background-normal-alternative)',
        border: '1px solid var(--semantic-line-normal-alternative)' }}>
        <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--semantic-label-alternative)',
          marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Evidence Grade 기준
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {Object.entries(EVIDENCE_GRADE_PALETTE).map(([g, p]) => (
            <span key={g} style={{
              padding: '3px 10px', borderRadius: 99, fontSize: 12, fontWeight: 600,
              background: p.bg, color: p.fg, border: `1px solid ${p.border}`,
            }}>
              {g} {p.label}
            </span>
          ))}
        </div>
      </div>

      {/* 케이스 선택 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--semantic-label-alternative)',
          marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>케이스 선택</div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {CASES.map(c => (
            <button key={c.id} onClick={() => setSelectedCase(c.id)} style={{
              padding: '5px 12px', borderRadius: 8, fontSize: 12.5, fontWeight: 500,
              border: '1px solid var(--semantic-line-normal-normal)',
              background: selectedCase === c.id ? '#1B3FA0' : '#fff',
              color: selectedCase === c.id ? '#fff' : 'var(--semantic-label-neutral)',
              cursor: 'pointer', fontFamily: 'inherit',
            }}>{c.label}</button>
          ))}
        </div>
      </div>

      {/* 케이스 요약 */}
      {caseObj && (
        <div style={{ marginBottom: 18, padding: '12px 16px', borderRadius: 10,
          background: '#EFF6FF', border: '1px solid #BFDBFE',
          fontSize: 13.5, color: '#1E40AF', lineHeight: 1.6 }}>
          <strong>{caseObj.label}</strong> — {caseObj.summary}
        </div>
      )}

      {/* refresh 큐 알림 */}
      {refreshQueue.size > 0 && (
        <div style={{ marginBottom: 14, padding: '8px 14px', borderRadius: 8,
          background: '#D1FAE5', border: '1px solid #6EE7B7',
          fontSize: 13, color: '#065F46', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Icon name="check" size={14} color="#065F46"/>
          {refreshQueue.size}건이 refresh 큐에 추가되었습니다.
        </div>
      )}

      {/* Citation 목록 */}
      {citations.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--semantic-label-alternative)',
          fontSize: 14 }}>이 케이스에 연결된 근거 자료가 없습니다.</div>
      ) : (
        citations.map((cit, i) => (
          <CitationCard
            key={cit.id}
            cit={cit}
            highlighted={i === 0}
            onRefresh={handleRefresh}
          />
        ))
      )}

      {/* 전체 citations 구분선 */}
      {citations.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--semantic-label-alternative)',
            textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
            전체 근거 자료 ({Object.keys(CITATIONS).length}건)
          </div>
          {Object.values(CITATIONS)
            .filter(c => !citIds.includes(c.id))
            .map(cit => (
              <CitationCard key={cit.id} cit={cit} highlighted={false} onRefresh={handleRefresh}/>
            ))
          }
        </div>
      )}
    </div>
  );
}

Object.assign(window, { EvidenceViewerView });
