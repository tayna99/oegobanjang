// Workers + Cases tab views
// 근로자 목록 (data grid) + 케이스 목록 (severity-grouped cards)

const WorkersView = ({ workers, cases, selectedId, onSelect, search }) => {
  const sevOrder = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
  const getTopSev = (wId) => {
    const wc = cases.filter(c => c.workerId === wId);
    if (!wc.length) return null;
    return wc.sort((a, b) => sevOrder.indexOf(a.severity) - sevOrder.indexOf(b.severity))[0].severity;
  };

  const filtered = !search.trim() ? workers : workers.filter(w =>
    w.name.toLowerCase().includes(search.toLowerCase()) ||
    w.nameKo.includes(search) ||
    w.nationality.includes(search) ||
    w.line.includes(search)
  );

  const stats = [
    { label: '전체 등록',       count: workers.length,                               unit: '명', color: 'var(--semantic-primary-normal)' },
    { label: '즉시·우선 확인', count: workers.filter(w => ['CRITICAL','HIGH'].includes(getTopSev(w.id))).length, unit: '명', color: 'var(--semantic-status-cautionary)' },
    { label: '서류 보완 필요', count: workers.filter(w => Object.values(w.docs).some(v => v !== 'ok')).length,    unit: '명', color: 'var(--semantic-status-negative)' },
    { label: '정상',             count: workers.filter(w => !getTopSev(w.id) || getTopSev(w.id) === 'LOW').length, unit: '명', color: 'var(--semantic-status-positive)' },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--semantic-label-alternative)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 2 }}>
            근로자 목록
          </div>
          <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.018em' }}>한별제조 · {workers.length}명</div>
        </div>
        <Button variant="outlined" size="small" leadingIcon={<Icon name="plus" size={13}/>}>근로자 등록</Button>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 20 }}>
        {stats.map(s => (
          <div key={s.label} style={{ padding: '14px 16px', borderRadius: 12,
            background: 'var(--semantic-background-elevated-normal)',
            border: '1px solid var(--semantic-line-normal-neutral)' }}>
            <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)', marginBottom: 8 }}>{s.label}</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 3 }}>
              <span style={{ fontSize: 26, fontWeight: 700, letterSpacing: '-0.025em', lineHeight: 1, color: s.color }}>{s.count}</span>
              <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)' }}>{s.unit}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Table */}
      <Card padded={false} style={{ overflow: 'hidden' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1.8fr 0.9fr 1fr 1fr 1fr 1fr 0.7fr',
          padding: '10px 18px', gap: 14, fontSize: 12, fontWeight: 500,
          color: 'var(--semantic-label-alternative)',
          borderBottom: '1px solid var(--semantic-line-normal-neutral)',
          background: 'var(--semantic-background-normal-alternative)' }}>
          <div>근로자</div>
          <div>국적·체류</div>
          <div>체류만료 / D-day</div>
          <div>계약 종료</div>
          <div>서류 현황</div>
          <div>위험도</div>
          <div style={{ textAlign: 'right' }}>근속</div>
        </div>

        {filtered.map((w, i) => {
          const topSev = getTopSev(w.id);
          const dNum = dDayNum(w.visaExpiry);
          const isSelected = selectedId === w.id;
          const docMissing = Object.values(w.docs).filter(v => v !== 'ok').length;

          return (
            <div key={w.id} onClick={() => onSelect(w.id)} style={{
              display: 'grid', gridTemplateColumns: '1.8fr 0.9fr 1fr 1fr 1fr 1fr 0.7fr',
              padding: '13px 18px', gap: 14, alignItems: 'center',
              borderBottom: i < filtered.length - 1 ? '1px solid var(--semantic-line-normal-alternative)' : 0,
              cursor: 'pointer', transition: 'background .15s',
              background: isSelected ? 'rgba(0,102,255,0.04)' : 'transparent',
              position: 'relative',
            }}
            onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'var(--semantic-fill-alternative)'; }}
            onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
            >
              {topSev === 'CRITICAL' && (
                <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: SEVERITY_PALETTE.CRITICAL.dot }}/>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Avatar name={w.name} initial={w.avatar} size={36} hue={i}/>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{w.name}
                    <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--semantic-label-alternative)', marginLeft: 6 }}>{w.nameKo}</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', marginTop: 1 }}>{w.line}</div>
                </div>
              </div>
              <div>
                <div style={{ fontSize: 13 }}>{w.flag} {w.nationality}</div>
                <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)', marginTop: 2 }}>{w.visaType}</div>
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>{fmtDate(w.visaExpiry)}</div>
                <div style={{ marginTop: 4 }}><DDayBar dNum={dNum} severity={topSev || 'LOW'}/></div>
              </div>
              <div style={{ fontSize: 13, fontVariantNumeric: 'tabular-nums' }}>
                {fmtDate(w.contractEnd)}
                <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', marginTop: 2 }}>{dDay(w.contractEnd)}</div>
              </div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {Object.entries(w.docs).map(([k, v]) => (
                  <span key={k} title={`${k}: ${v}`} style={{
                    width: 22, height: 22, borderRadius: 5, display: 'inline-flex',
                    alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700,
                    background: v === 'ok' ? 'rgba(0,191,64,0.12)' : v === 'expired' ? 'rgba(255,66,66,0.12)' : 'rgba(255,146,0,0.12)',
                    color: v === 'ok' ? '#006E25' : v === 'expired' ? '#B00C0C' : '#9C5800',
                  }}>{k[0]}</span>
                ))}
                {docMissing > 0 && (
                  <span style={{ fontSize: 11, color: 'var(--semantic-status-cautionary)', fontWeight: 600, alignSelf: 'center', marginLeft: 2 }}>+{docMissing}</span>
                )}
              </div>
              {topSev
                ? <RiskPill level={topSev} compact/>
                : <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', padding: '2px 8px',
                    borderRadius: 6, background: 'rgba(0,191,64,0.10)', color: '#006E25',
                    fontWeight: 500, fontSize: 11 }}>정상</span>
              }
              <div style={{ textAlign: 'right', fontSize: 13, color: 'var(--semantic-label-neutral)' }}>{w.tenure}</div>
            </div>
          );
        })}
      </Card>
    </div>
  );
};

const CasesView = ({ cases, workers, citations, actions }) => {
  const sevOrder = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
  const grouped = sevOrder.map(sev => ({
    sev,
    items: cases.filter(c => c.severity === sev),
  })).filter(g => g.items.length > 0);

  const getWorker = (id) => id ? workers.find(w => w.id === id) : null;

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--semantic-label-alternative)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 2 }}>케이스 목록</div>
        <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.018em' }}>리스크 케이스 · {cases.length}건</div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
        {grouped.map(({ sev, items }) => {
          const p = SEVERITY_PALETTE[sev];
          return (
            <div key={sev}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10,
                paddingBottom: 10, borderBottom: `2px solid ${p.bd}` }}>
                <span style={{ width: 8, height: 8, borderRadius: 999, background: p.dot }}/>
                <span style={{ fontSize: 13, fontWeight: 700, color: p.fg }}>{p.label}</span>
                <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', fontWeight: 500,
                  padding: '1px 8px', borderRadius: 4, background: p.bg }}>{items.length}건</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {items.map(c => {
                  const worker = getWorker(c.workerId);
                  const cits = c.citationIds.map(id => citations[id]).filter(Boolean);
                  const acts = c.actions.map(id => actions[id]).filter(Boolean);
                  return (
                    <div key={c.id} style={{
                      padding: '16px 20px', borderRadius: 14,
                      background: 'var(--semantic-background-elevated-normal)',
                      border: `1px solid ${p.bd}`,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                          <RiskPill level={c.severity} compact/>
                          <span style={{ fontSize: 15, fontWeight: 700 }}>{c.label}</span>
                          {worker && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <Avatar name={worker.name} initial={worker.avatar} size={22} hue={workers.indexOf(worker)}/>
                              <span style={{ fontSize: 13, color: 'var(--semantic-label-neutral)' }}>{worker.flag} {worker.name}</span>
                            </div>
                          )}
                          {!worker && (
                            <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', padding: '2px 7px',
                              borderRadius: 4, background: 'var(--semantic-fill-alternative)' }}>사업장 전체</span>
                          )}
                        </div>
                        <span style={{ fontSize: 11, color: 'var(--semantic-label-alternative)',
                          fontFamily: 'var(--font-mono)', flexShrink: 0, marginLeft: 12 }}>{c.id}</span>
                      </div>
                      <div style={{ fontSize: 13.5, color: 'var(--semantic-label-neutral)', lineHeight: 1.65, marginBottom: 12 }}>{c.summary}</div>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                        {cits.map(ct => (
                          <span key={ct.id} style={{ fontSize: 11.5, padding: '3px 9px', borderRadius: 5, fontWeight: 500,
                            background: 'var(--semantic-fill-alternative)', color: 'var(--semantic-label-neutral)',
                            border: '1px solid var(--semantic-line-normal-alternative)' }}>
                            <span style={{ fontWeight: 700, color: 'var(--semantic-primary-normal)', marginRight: 5 }}>{ct.grade}</span>
                            {ct.title}
                          </span>
                        ))}
                        {acts.map(a => (
                          <span key={a.id} style={{ fontSize: 11.5, padding: '3px 9px', borderRadius: 5, fontWeight: 500,
                            background: 'rgba(0,102,255,0.07)', color: 'var(--semantic-primary-normal)',
                            border: '1px solid rgba(0,102,255,0.18)' }}>
                            {a.label}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

Object.assign(window, { WorkersView, CasesView });
