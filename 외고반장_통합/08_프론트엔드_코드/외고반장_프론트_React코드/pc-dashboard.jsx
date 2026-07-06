// PC Dashboard — 인력 담당자 작업대.
// Tone: 90% 실무 SaaS, AI는 보조 역할. 화면의 주인공은 업무 큐.
// References Montage tokens via colors_and_type.css.

const TopBar = ({ company, onChangeCompany, search, onSearch, pendingCount }) => (
  <header style={{
    height: 60, padding: '0 28px',
    display: 'flex', alignItems: 'center', gap: 24,
    background: 'rgba(255,255,255,0.92)',
    backdropFilter: 'blur(32px)',
    borderBottom: '1px solid var(--semantic-line-normal-neutral)',
    position: 'sticky', top: 0, zIndex: 5,
  }}>
    <BrandMark size={20}/>
    <div style={{ width: 1, height: 20, background: 'var(--semantic-line-normal-neutral)' }}/>

    {/* Company selector */}
    <button onClick={onChangeCompany} style={{
      display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px 6px 8px',
      background: 'var(--semantic-fill-alternative)', border: 0, borderRadius: 8,
      cursor: 'pointer', fontFamily: 'inherit',
    }}>
      <div style={{
        width: 24, height: 24, borderRadius: 6,
        background: 'var(--semantic-primary-normal)', color: '#fff',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 12, fontWeight: 700,
      }}>{company.name[0]}</div>
      <div style={{ textAlign: 'left' }}>
        <div style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.2 }}>{company.name}</div>
        <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', lineHeight: 1.2 }}>{company.sub}</div>
      </div>
      <Icon name="chevronDown" size={14} color="var(--semantic-label-alternative)"/>
    </button>

    <nav style={{ display: 'flex', gap: 2, marginLeft: 8 }}>
      {[
        { id: 'today', label: '오늘 할 일', active: true },
        { id: 'workers', label: '근로자' },
        { id: 'cases', label: '케이스' },
        { id: 'handoff', label: '행정사 검토' },
        { id: 'evidence', label: 'Evidence Log' },
      ].map(t => (
        <button key={t.id} style={{
          padding: '7px 14px', borderRadius: 8, border: 0, cursor: 'pointer',
          fontSize: 13.5, fontWeight: 500, fontFamily: 'inherit',
          color: t.active ? 'var(--semantic-label-normal)' : 'var(--semantic-label-alternative)',
          background: t.active ? 'var(--semantic-fill-normal)' : 'transparent',
        }}>{t.label}</button>
      ))}
    </nav>

    <div style={{ flex: 1 }}/>

    {/* Search + AI ask (small, secondary per UI plan §6.2) */}
    <div style={{ display: 'flex', alignItems: 'center', gap: 8,
      padding: '7px 12px', background: 'var(--semantic-fill-alternative)',
      borderRadius: 10, width: 320 }}>
      <Icon name="search" size={16} color="var(--semantic-label-alternative)"/>
      <input value={search} onChange={(e) => onSearch(e.target.value)} placeholder="근로자, 케이스, 사업장 검색"
        style={{ flex: 1, border: 0, background: 'transparent', outline: 'none', fontFamily: 'inherit', fontSize: 13, color: 'var(--semantic-label-normal)' }}/>
      <span style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', padding: '2px 6px',
        background: 'var(--semantic-background-elevated-normal)', borderRadius: 4 }}>⌘K</span>
    </div>
    <button title="AI 반장에게 물어보기" style={{
      display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px',
      background: 'transparent', border: '1px solid var(--semantic-line-normal-normal)',
      borderRadius: 10, cursor: 'pointer', fontFamily: 'inherit',
      fontSize: 13, color: 'var(--semantic-label-neutral)',
    }}>
      <Icon name="sparkle" size={14} color="var(--semantic-primary-normal)"/>
      AI 반장에게 물어보기
    </button>

    <div style={{ position: 'relative' }}>
      <Icon name="bell" size={20} color="var(--semantic-label-neutral)"/>
      {pendingCount > 0 && (
        <span style={{ position: 'absolute', top: -2, right: -4, minWidth: 16, height: 16, padding: '0 4px',
          borderRadius: 999, background: 'var(--semantic-status-negative)', color: '#fff',
          fontSize: 10, fontWeight: 700, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>{pendingCount}</span>
      )}
    </div>
    <div style={{
      width: 32, height: 32, borderRadius: 999, marginLeft: 4,
      background: 'linear-gradient(135deg,#0066FF,#6541F2)',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      color: '#fff', fontSize: 12, fontWeight: 700,
    }}>김</div>
  </header>
);

// "오늘 처리할 외국인 고용 업무" — top summary cards
const TodaySummary = ({ counts, onFilter, activeFilter }) => {
  const cards = [
    { id: 'visa',     label: '체류기간 임박',  count: counts.visa,     icon: 'calendar', sev: 'CRITICAL', sub: '즉시 1, 우선 1' },
    { id: 'docs',     label: '서류 보완 필요', count: counts.docs,     icon: 'fileMissing', sev: 'HIGH',  sub: '필수 2, 선택 0' },
    { id: 'contract', label: '계약 종료 임박', count: counts.contract, icon: 'clock',    sev: 'MEDIUM', sub: 'D-30 이내 0건' },
    { id: 'approval', label: '승인 대기',      count: counts.approval, icon: 'shield',   sev: 'HIGH',   sub: '담당자 검토 5건' },
    { id: 'handoff',  label: '행정사 검토 준비', count: counts.handoff,  icon: 'handshake', sev: 'MEDIUM', sub: '초안 완료 1건' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
      {cards.map(c => {
        const p = SEVERITY_PALETTE[c.sev];
        const active = activeFilter === c.id;
        return (
          <button key={c.id} onClick={() => onFilter(c.id)} style={{
            textAlign: 'left', padding: 18, borderRadius: 14,
            background: 'var(--semantic-background-elevated-normal)',
            border: `1px solid ${active ? p.bd : 'var(--semantic-line-normal-neutral)'}`,
            cursor: 'pointer', fontFamily: 'inherit',
            transition: 'border-color .2s, box-shadow .2s',
            boxShadow: active ? `0 0 0 3px ${p.bg}` : 'none',
            position: 'relative', overflow: 'hidden',
          }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: p.dot }}/>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14, marginTop: 2 }}>
              <div style={{
                width: 32, height: 32, borderRadius: 8,
                background: p.bg, color: p.fg,
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              }}><Icon name={c.icon} size={16}/></div>
              <Icon name="arrowUpRight" size={14} color="var(--semantic-label-alternative)"/>
            </div>
            <div style={{ fontSize: 12.5, fontWeight: 500, color: 'var(--semantic-label-neutral)', marginBottom: 4 }}>{c.label}</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 6 }}>
              <span style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.025em', color: 'var(--semantic-label-strong)', lineHeight: 1 }}>{c.count}</span>
              <span style={{ fontSize: 13, color: 'var(--semantic-label-alternative)', fontWeight: 500 }}>건</span>
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)' }}>{c.sub}</div>
          </button>
        );
      })}
    </div>
  );
};

// AI briefing ribbon — small, restrained per UI plan §5
const BriefingBanner = ({ generatedAt, onRegenerate }) => (
  <div style={{
    display: 'flex', alignItems: 'center', gap: 14,
    padding: '14px 18px', borderRadius: 12,
    background: 'linear-gradient(90deg, rgba(0,102,255,0.06), rgba(0,102,255,0.02))',
    border: '1px solid rgba(0,102,255,0.18)',
  }}>
    <div style={{
      width: 32, height: 32, borderRadius: 8,
      background: 'var(--semantic-primary-normal)', color: '#fff',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 13, fontWeight: 700,
    }}>반</div>
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--semantic-label-normal)', marginBottom: 2 }}>
        오늘 브리핑이 준비되었습니다
      </div>
      <div style={{ fontSize: 12, color: 'var(--semantic-label-neutral)' }}>
        외고반장이 7개 케이스를 정리했습니다. 즉시 확인 1건, 우선 확인 3건, 승인 대기 5건. 모든 판단의 근거는 항목 클릭으로 확인할 수 있습니다.
      </div>
    </div>
    <span style={{ fontSize: 12, color: 'var(--semantic-label-alternative)' }}>
      {generatedAt}
    </span>
    <Button variant="outlined" size="small" leadingIcon={<Icon name="refresh" size={14}/>} onClick={onRegenerate}>
      다시 생성
    </Button>
  </div>
);

// Risk-row table — the workbench centerpiece
const WorkerRiskTable = ({ workers, cases, selectedId, onSelect, severityFilter, density }) => {
  const rowH = density === 'compact' ? 52 : 64;
  const rowsByWorker = workers.map(w => ({
    worker: w,
    cases: cases.filter(c => c.workerId === w.id),
  })).filter(r => r.cases.length > 0)
    .sort((a, b) => {
      const order = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
      const aMin = Math.min(...a.cases.map(c => order[c.severity]));
      const bMin = Math.min(...b.cases.map(c => order[c.severity]));
      return aMin - bMin;
    });

  // filter by severity if set
  const filtered = !severityFilter ? rowsByWorker : rowsByWorker.filter(r =>
    r.cases.some(c => {
      if (severityFilter === 'visa')     return c.riskType === 'visa_expiry';
      if (severityFilter === 'docs')     return c.riskType === 'missing_document';
      if (severityFilter === 'contract') return c.riskType === 'contract_expiry' || c.riskType === 'contract_visa_conflict';
      if (severityFilter === 'approval') return true;
      if (severityFilter === 'handoff')  return c.severity === 'CRITICAL';
      return true;
    }));

  return (
    <Card padded={false} style={{ overflow: 'hidden' }}>
      <div style={{
        display: 'grid', gridTemplateColumns: '1.6fr 0.8fr 1fr 1.1fr 1fr 1.4fr 0.9fr',
        padding: '10px 18px', gap: 12,
        fontSize: 12, fontWeight: 500, color: 'var(--semantic-label-alternative)',
        borderBottom: '1px solid var(--semantic-line-normal-neutral)',
        background: 'var(--semantic-background-normal-alternative)',
      }}>
        <div>근로자</div>
        <div>국적·체류</div>
        <div>체류만료 / D-day</div>
        <div>계약 종료</div>
        <div>서류</div>
        <div>위험도 / 케이스</div>
        <div style={{ textAlign: 'right' }}>다음 처리</div>
      </div>
      {filtered.map(({ worker, cases }, i) => {
        const topCase = cases.sort((a, b) => {
          const o = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
          return o[a.severity] - o[b.severity];
        })[0];
        const dDayLabel = dDay(worker.visaExpiry);
        const dNum = dDayNum(worker.visaExpiry);
        const isCritical = topCase.severity === 'CRITICAL';
        const isSelected = selectedId === worker.id;
        const docMissing = Object.values(worker.docs).filter(s => s === 'missing' || s === 'expired').length;
        const sev = SEVERITY_PALETTE[topCase.severity];

        return (
          <div key={worker.id} onClick={() => onSelect(worker.id)} style={{
            display: 'grid', gridTemplateColumns: '1.6fr 0.8fr 1fr 1.1fr 1fr 1.4fr 0.9fr',
            padding: density === 'compact' ? '10px 18px' : '14px 18px', gap: 12,
            alignItems: 'center', minHeight: rowH,
            borderBottom: i < filtered.length - 1 ? '1px solid var(--semantic-line-normal-alternative)' : 0,
            cursor: 'pointer', position: 'relative',
            background: isSelected ? 'rgba(0,102,255,0.04)' : 'transparent',
            transition: 'background .15s',
          }}
          onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = 'var(--semantic-fill-alternative)'; }}
          onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
          >
            {/* severity left bar */}
            <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: isCritical ? sev.dot : 'transparent' }}/>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Avatar name={worker.name} initial={worker.avatar} size={36} hue={i}/>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--semantic-label-normal)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  {worker.name}
                  <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--semantic-label-alternative)' }}>· {worker.nameKo}</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', marginTop: 1 }}>
                  {worker.line}
                </div>
              </div>
            </div>
            <div style={{ fontSize: 13, color: 'var(--semantic-label-neutral)' }}>
              <div>{worker.flag} {worker.nationality}</div>
              <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)', marginTop: 2 }}>{worker.visaType}</div>
            </div>
            <div>
              <div style={{ fontSize: 13, color: 'var(--semantic-label-normal)', fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>{fmtDate(worker.visaExpiry)}</div>
              <div style={{ marginTop: 4 }}>
                <DDayBar dNum={dNum} severity={topCase.severity}/>
              </div>
            </div>
            <div style={{ fontSize: 13, color: 'var(--semantic-label-normal)', fontVariantNumeric: 'tabular-nums' }}>
              {fmtDate(worker.contractEnd)}
              <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', marginTop: 2 }}>{dDay(worker.contractEnd)}</div>
            </div>
            <div style={{ display: 'flex', gap: 4 }}>
              {Object.entries(worker.docs).map(([k, v]) => (
                <span key={k} title={`${k}: ${v}`} style={{
                  width: 22, height: 22, borderRadius: 6,
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  background: v === 'ok' ? 'rgba(0,191,64,0.12)' : v === 'expired' ? 'rgba(255,66,66,0.12)' : 'rgba(255,146,0,0.12)',
                  color:      v === 'ok' ? '#006E25'              : v === 'expired' ? '#B00C0C'              : '#9C5800',
                  fontSize: 10, fontWeight: 600,
                }}>{k[0]}</span>
              ))}
              {docMissing > 0 && (
                <span style={{ fontSize: 11, color: 'var(--semantic-status-cautionary)', alignSelf: 'center', marginLeft: 4, fontWeight: 600 }}>+{docMissing} 보완</span>
              )}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
              <RiskPill level={topCase.severity} dDay={dDay(worker.visaExpiry)} compact/>
              <span style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)' }}>
                {cases.length === 1 ? topCase.label : `${topCase.label} 외 ${cases.length - 1}건`}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 6 }}>
              {topCase.actions.length > 0 && (
                <Button variant="outlined" size="small" trailingIcon={<Icon name="chevronRight" size={12}/>}>
                  처리
                </Button>
              )}
            </div>
          </div>
        );
      })}
      {filtered.length === 0 && (
        <div style={{ padding: 60, textAlign: 'center', color: 'var(--semantic-label-alternative)' }}>
          <div style={{ fontSize: 14, marginBottom: 4 }}>해당 조건에 위험 항목이 없습니다.</div>
          <div style={{ fontSize: 12 }}>다른 필터를 선택하거나 모든 항목 보기를 눌러주세요.</div>
        </div>
      )}
    </Card>
  );
};

// D-day visualizer — strong tell signal in the table
const DDayBar = ({ dNum, severity }) => {
  const sev = SEVERITY_PALETTE[severity];
  // Map dNum (-90 to +90) to 0..100% with pivot at today=50%
  const window = 60;
  const pct = Math.max(0, Math.min(100, 50 + (-dNum / window) * 50));
  const isPast = dNum < 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{ position: 'relative', flex: 1, height: 4, borderRadius: 999, background: 'var(--semantic-fill-alternative)', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0,
          width: `${pct}%`, background: sev.dot, opacity: isPast ? 1 : 0.7,
        }}/>
        <div style={{ position: 'absolute', left: '50%', top: -2, bottom: -2, width: 1, background: 'var(--semantic-label-alternative)', opacity: 0.4 }}/>
      </div>
      <span style={{ fontSize: 11, fontWeight: 600, color: sev.fg, fontVariantNumeric: 'tabular-nums', minWidth: 30, textAlign: 'right' }}>{dNum < 0 ? `D+${Math.abs(dNum)}` : `D-${dNum}`}</span>
    </div>
  );
};

// Filter bar — live above the table
const FilterBar = ({ severityFilter, onClear, onSetDensity, density }) => {
  const counts = { all: 6, critical: 1, high: 3, medium: 2, low: 1 };
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
      <div style={{ display: 'flex', gap: 6 }}>
        <Chip active={!severityFilter} onClick={onClear}>전체</Chip>
        <Chip count={counts.critical}>즉시 확인</Chip>
        <Chip count={counts.high}>우선 확인</Chip>
        <Chip count={counts.medium}>확인 필요</Chip>
        <Chip count={counts.low}>참고</Chip>
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
        <Chip active={density === 'compact'}  onClick={() => onSetDensity('compact')}>compact</Chip>
        <Chip active={density === 'comfortable'} onClick={() => onSetDensity('comfortable')}>comfy</Chip>
      </div>
    </div>
  );
};

Object.assign(window, { TopBar, TodaySummary, BriefingBanner, WorkerRiskTable, FilterBar, DDayBar });
