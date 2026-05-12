// Worker / case detail panel — slides in on the right of the PC dashboard.
// Ref: UI plan §6.5 "상세 패널" — must show 기본정보, 체류/계약, 누락서류, 근거, 추천액션, 승인상태, 행정사 초안, 업무이력.

const DetailPanel = ({ worker, cases, citations, actions, onClose, onApprove, onOpenDocReq }) => {
  if (!worker) return null;
  const [piiVisible, setPiiVisible] = React.useState(false);
  const workerCases = cases.filter(c => c.workerId === worker.id);
  const workerActions = workerCases.flatMap(c => c.actions.map(id => ({ ...actions[id], caseId: c.id, severity: c.severity })));
  const cited = [...new Set(workerCases.flatMap(c => c.citationIds))].map(id => citations[id]);
  const maskPii = (v) => piiVisible ? v : v.replace(/\d/g, '*');

  return (
    <aside style={{
      width: 460, flexShrink: 0,
      background: 'var(--semantic-background-elevated-normal)',
      borderLeft: '1px solid var(--semantic-line-normal-neutral)',
      overflowY: 'auto', height: 'calc(100vh - 60px)',
      position: 'sticky', top: 60,
    }}>
      {/* Header */}
      <div style={{ padding: '20px 24px 16px', borderBottom: '1px solid var(--semantic-line-normal-alternative)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--semantic-label-alternative)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            근로자 상세
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {/* PII 마스킹 토글 */}
            <button
              onClick={() => setPiiVisible(v => !v)}
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '3px 9px', borderRadius: 6, fontSize: 11.5, fontWeight: 600,
                border: `1px solid ${piiVisible ? '#EF4444' : 'var(--semantic-line-normal-normal)'}`,
                background: piiVisible ? '#FEE2E2' : 'var(--semantic-fill-alternative)',
                color: piiVisible ? '#7F1D1D' : 'var(--semantic-label-alternative)',
                cursor: 'pointer', fontFamily: 'inherit',
              }}
            >
              <Icon name="eye" size={12} color={piiVisible ? '#7F1D1D' : 'var(--semantic-label-alternative)'}/>
              {piiVisible ? 'PII 표시 중' : 'PII 마스킹'}
            </button>
            <button onClick={onClose} style={{ background: 'transparent', border: 0, cursor: 'pointer', color: 'var(--semantic-label-alternative)', padding: 4 }}>
              <Icon name="close" size={16}/>
            </button>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <Avatar name={worker.name} initial={worker.avatar} size={56} hue={3}/>
          <div>
            <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.018em' }}>{worker.name}</div>
            <div style={{ fontSize: 13, color: 'var(--semantic-label-neutral)', marginTop: 2 }}>
              {worker.flag} {worker.nationality} · {worker.visaType} · 근속 {worker.tenure}
            </div>
            <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', marginTop: 1,
              display: 'flex', alignItems: 'center', gap: 4 }}>
              {worker.line} · 외등{' '}
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11.5,
                background: piiVisible ? 'transparent' : '#F3F4F6',
                padding: piiVisible ? 0 : '1px 5px', borderRadius: 4 }}>
                {piiVisible ? worker.arn : worker.arn.replace(/\d/g, '●')}
              </span>
              {!piiVisible && (
                <span style={{ fontSize: 10, color: 'var(--semantic-label-alternative)',
                  background: '#FEF9C3', padding: '1px 5px', borderRadius: 4, fontWeight: 600 }}>
                  마스킹
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Risk overview */}
      <Section title="현재 리스크" count={workerCases.length}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {workerCases.map(c => {
            const sev = SEVERITY_PALETTE[c.severity];
            return (
              <div key={c.id} style={{
                padding: '12px 14px', borderRadius: 10,
                background: sev.bg, border: `1px solid ${sev.bd}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--semantic-label-strong)' }}>{c.label}</span>
                  <RiskPill level={c.severity} compact/>
                </div>
                <div style={{ fontSize: 12.5, color: 'var(--semantic-label-neutral)', lineHeight: 1.5 }}>
                  {c.summary}
                </div>
                {c.citationIds.length > 0 && (
                  <div style={{ display: 'flex', gap: 4, marginTop: 8, flexWrap: 'wrap' }}>
                    {c.citationIds.map(id => {
                      const ct = citations[id];
                      return (
                        <span key={id} style={{
                          fontSize: 11, padding: '2px 7px', borderRadius: 4,
                          background: 'rgba(255,255,255,0.7)', color: 'var(--semantic-label-neutral)',
                          fontWeight: 500, border: '1px solid var(--semantic-line-normal-alternative)',
                        }}>
                          <span style={{ fontWeight: 700, color: 'var(--semantic-primary-normal)', marginRight: 4 }}>{ct.grade}</span>
                          {ct.title}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Section>

      {/* Schedule */}
      <Section title="체류 / 계약">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <KV k="체류만료일" v={fmtDate(worker.visaExpiry)} sub={dDay(worker.visaExpiry)} accent={dDayNum(worker.visaExpiry) <= 30}/>
          <KV k="계약종료일" v={fmtDate(worker.contractEnd)} sub={dDay(worker.contractEnd)} accent={dDayNum(worker.contractEnd) <= 30}/>
        </div>
      </Section>

      {/* Documents */}
      <Section title="제출 서류" count={Object.keys(worker.docs).length}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {Object.entries(worker.docs).map(([k, v]) => (
            <div key={k} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '10px 12px', borderRadius: 8,
              background: v === 'ok' ? 'transparent' : 'var(--semantic-fill-alternative)',
              border: '1px solid var(--semantic-line-normal-alternative)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Icon name={v === 'ok' ? 'fileCheck' : 'fileMissing'} size={16}
                  color={v === 'ok' ? 'var(--semantic-status-positive)' : v === 'expired' ? 'var(--semantic-status-negative)' : 'var(--semantic-status-cautionary)'}/>
                <span style={{ fontSize: 13, fontWeight: 500 }}>{k}</span>
              </div>
              {v === 'ok'      && <StatusBadge tone="approved">확보됨</StatusBadge>}
              {v === 'missing' && <StatusBadge tone="pending">보완 필요</StatusBadge>}
              {v === 'expired' && <StatusBadge tone="expired">만료</StatusBadge>}
            </div>
          ))}
        </div>
      </Section>

      {/* Recommended actions */}
      {workerActions.length > 0 && (
        <Section title="추천 액션" count={workerActions.length}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {workerActions.map(a => (
              <div key={a.id} style={{
                padding: 12, borderRadius: 10,
                border: '1px solid var(--semantic-line-normal-neutral)',
                background: 'var(--semantic-background-elevated-normal)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <div>
                    <div style={{ fontSize: 13.5, fontWeight: 600, marginBottom: 2 }}>{a.label}</div>
                    <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)' }}>대상: {a.for}</div>
                  </div>
                  {a.status === 'pending_approval' && <StatusBadge tone="pending">승인 대기</StatusBadge>}
                  {a.status === 'pending_review'   && <StatusBadge tone="info">검토 필요</StatusBadge>}
                  {a.status === 'draft'            && <StatusBadge tone="draft">초안</StatusBadge>}
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  {a.type === 'request_document' && (
                    <Button variant="tonal" size="small" onClick={() => onOpenDocReq(a.id)}>초안 보기</Button>
                  )}
                  {a.type === 'create_handoff' && (
                    <Button variant="tonal" size="small">검토 자료 보기</Button>
                  )}
                  {a.status === 'pending_approval' && (
                    <Button variant="solid" size="small" leadingIcon={<Icon name="check" size={12}/>} onClick={() => onApprove(a.id)}>
                      승인
                    </Button>
                  )}
                  {a.status === 'pending_review' && (
                    <Button variant="outlined" size="small">담당자 확인 요청</Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Citations */}
      <Section title="근거 자료" count={cited.length}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {cited.map(c => (
            <div key={c.id} style={{
              padding: 10, borderRadius: 8,
              background: 'var(--semantic-background-normal-alternative)',
              border: '1px solid var(--semantic-line-normal-alternative)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <span style={{
                  fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
                  background: 'var(--semantic-primary-normal)', color: '#fff',
                }}>{c.grade}</span>
                <span style={{ fontSize: 11, color: 'var(--semantic-label-alternative)' }}>{c.source}</span>
                <span style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', marginLeft: 'auto' }}>{c.updated}</span>
              </div>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>{c.title}</div>
              <div style={{ fontSize: 12, color: 'var(--semantic-label-neutral)', lineHeight: 1.5 }}>{c.snippet}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* Activity timeline */}
      <Section title="업무 기록">
        <Timeline workerName={worker.name}/>
      </Section>

      <div style={{ height: 24 }}/>
    </aside>
  );
};

const Section = ({ title, count, children }) => (
  <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--semantic-line-normal-alternative)' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--semantic-label-strong)' }}>{title}</span>
      {count !== undefined && (
        <span style={{ fontSize: 11, fontWeight: 600, padding: '1px 7px', borderRadius: 4,
          background: 'var(--semantic-fill-normal)', color: 'var(--semantic-label-neutral)' }}>{count}</span>
      )}
    </div>
    {children}
  </div>
);

const KV = ({ k, v, sub, accent }) => (
  <div style={{
    padding: '10px 12px', borderRadius: 8,
    background: 'var(--semantic-background-normal-alternative)',
    border: `1px solid ${accent ? 'rgba(255,146,0,0.32)' : 'var(--semantic-line-normal-alternative)'}`,
  }}>
    <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', marginBottom: 2 }}>{k}</div>
    <div style={{ fontSize: 14, fontWeight: 600, fontVariantNumeric: 'tabular-nums', color: 'var(--semantic-label-strong)' }}>{v}</div>
    {sub && <div style={{ fontSize: 11.5, fontWeight: 600, color: accent ? 'var(--semantic-status-cautionary)' : 'var(--semantic-label-neutral)', marginTop: 2 }}>{sub}</div>}
  </div>
);

const Timeline = ({ workerName }) => {
  const events = [
    { ts: '08:14', actor: '김인사 차장', text: 'Bayar M. 케이스 승인 요청' },
    { ts: '08:01', actor: '시스템',     text: '오늘 브리핑 7건 생성' },
    { ts: '08:00', actor: '시스템',     text: `${workerName} 리스크 플래그 (visa_expiry / missing_document)` },
    { ts: '어제 17:42', actor: '김인사 차장', text: 'CSV 업로드 — 24명 동기화' },
  ];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, position: 'relative' }}>
      {events.map((e, i) => (
        <div key={i} style={{ display: 'flex', gap: 10 }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 4 }}>
            <div style={{ width: 7, height: 7, borderRadius: 999, background: i === 0 ? 'var(--semantic-primary-normal)' : 'var(--semantic-line-normal-normal)' }}/>
            {i < events.length - 1 && <div style={{ width: 1, flex: 1, background: 'var(--semantic-line-normal-alternative)', marginTop: 2 }}/>}
          </div>
          <div style={{ paddingBottom: 4 }}>
            <div style={{ fontSize: 12.5, color: 'var(--semantic-label-normal)' }}>{e.text}</div>
            <div style={{ fontSize: 11, color: 'var(--semantic-label-alternative)', marginTop: 2 }}>{e.ts} · {e.actor}</div>
          </div>
        </div>
      ))}
    </div>
  );
};

Object.assign(window, { DetailPanel });
