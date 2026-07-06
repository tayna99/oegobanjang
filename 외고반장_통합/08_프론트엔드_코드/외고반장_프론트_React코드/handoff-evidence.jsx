// Handoff Preview + Evidence Log views.
// Both are tabs inside the PC dashboard surface.

const HandoffPreview = () => {
  const d = window.HANDOFF_DRAFT;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20, alignItems: 'start' }}>
      <Card padded={false} style={{ overflow: 'hidden' }}>
        <div style={{ padding: '20px 28px', borderBottom: '1px solid var(--semantic-line-normal-alternative)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--semantic-label-alternative)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 4 }}>
              행정사 검토용 자료 · 초안
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.018em' }}>{d.workerName} 케이스 검토 패키지</div>
            <div style={{ fontSize: 13, color: 'var(--semantic-label-neutral)', marginTop: 4 }}>
              생성 {d.generatedAt} · 수신자 {d.recipient}
            </div>
          </div>
          <StatusBadge tone="pending">승인 대기</StatusBadge>
        </div>

        <div style={{ padding: 28 }}>
          {d.sections.map(s => (
            <div key={s.title} style={{ marginBottom: 28 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--semantic-label-strong)', marginBottom: 10, paddingBottom: 6, borderBottom: '2px solid var(--semantic-label-strong)' }}>
                {s.title}
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <tbody>
                  {s.rows.map(([k, v]) => (
                    <tr key={k} style={{ borderBottom: '1px solid var(--semantic-line-normal-alternative)' }}>
                      <td style={{ padding: '10px 0', fontSize: 13, color: 'var(--semantic-label-alternative)', width: 220, fontWeight: 500 }}>{k}</td>
                      <td style={{ padding: '10px 0', fontSize: 13.5, color: 'var(--semantic-label-normal)', fontVariantNumeric: 'tabular-nums' }}>{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
          <div style={{ marginTop: 32, padding: 16, borderRadius: 10, background: 'var(--semantic-background-normal-alternative)', border: '1px solid var(--semantic-line-normal-alternative)' }}>
            <div style={{ fontSize: 11.5, color: 'var(--semantic-label-alternative)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Icon name="shield" size={12}/>
              <span>안내</span>
            </div>
            <div style={{ fontSize: 12.5, color: 'var(--semantic-label-neutral)', lineHeight: 1.7 }}>
              본 자료는 외고반장이 자동 생성한 검토용 초안입니다. 외국인등록번호와 같은 식별 정보는 마스킹되어 있습니다.<br/>
              실제 행정사 전달은 담당자 승인 이후에 진행되며, 승인 전에는 외부로 발송되지 않습니다.
            </div>
          </div>
        </div>
      </Card>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, position: 'sticky', top: 80 }}>
        <Card>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>다음 단계</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Button variant="solid" size="medium" fullWidth leadingIcon={<Icon name="check" size={14}/>}>승인 후 검토 자료 확정</Button>
            <Button variant="outlined" size="medium" fullWidth>수정 요청</Button>
            <Button variant="ghost" size="medium" fullWidth leadingIcon={<Icon name="download" size={14}/>}>PDF 내보내기</Button>
          </div>
          <div style={{ marginTop: 12, fontSize: 11.5, color: 'var(--semantic-label-alternative)', lineHeight: 1.6 }}>
            <Icon name="alertCircle" size={11}/> 승인 후에도 정부 포털 자동 제출은 수행하지 않습니다.
          </div>
        </Card>

        <Card>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>포함된 근거 (3)</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {Object.values(window.CITATIONS).slice(0, 3).map(c => (
              <div key={c.id} style={{ padding: 10, borderRadius: 8, background: 'var(--semantic-background-normal-alternative)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, padding: '1px 5px', borderRadius: 3, background: 'var(--semantic-primary-normal)', color: '#fff' }}>{c.grade}</span>
                  <span style={{ fontSize: 11, color: 'var(--semantic-label-alternative)' }}>{c.source}</span>
                </div>
                <div style={{ fontSize: 12.5, fontWeight: 500 }}>{c.title}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>승인 흐름</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {[
              { t: '시스템 초안 생성', state: 'done' },
              { t: '담당자 검토',      state: 'active' },
              { t: '사장님 승인',      state: 'pending' },
              { t: '행정사 전달',      state: 'pending' },
            ].map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}>
                <div style={{
                  width: 18, height: 18, borderRadius: 999,
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  background: s.state === 'done' ? 'var(--semantic-status-positive)' : s.state === 'active' ? 'var(--semantic-primary-normal)' : 'var(--semantic-fill-normal)',
                  color: '#fff',
                  border: s.state === 'pending' ? '1px solid var(--semantic-line-normal-normal)' : 0,
                }}>{s.state === 'done' ? <Icon name="check" size={11} color="#fff"/> : <span style={{ fontSize: 10, color: s.state === 'pending' ? 'var(--semantic-label-alternative)' : '#fff' }}>{i + 1}</span>}</div>
                <span style={{ color: s.state === 'pending' ? 'var(--semantic-label-alternative)' : 'var(--semantic-label-normal)', fontWeight: s.state === 'active' ? 600 : 500 }}>{s.t}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

const EvidenceLogView = () => {
  const events = window.EVIDENCE_EVENTS;
  return (
    <div>
      <Card padded={false}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--semantic-line-normal-alternative)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700 }}>Evidence Log</div>
            <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)' }}>판단 근거, 승인 이력, 실행 이력이 append-only 로 기록됩니다.</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <Chip>전체</Chip>
            <Chip count={3}>risk_flagged</Chip>
            <Chip count={1}>citation_resolved</Chip>
            <Chip count={1}>handoff_drafted</Chip>
          </div>
        </div>
        <div>
          {events.map((e, i) => {
            const typeColors = {
              risk_flagged:       { bg: 'rgba(255,66,66,0.10)', fg: '#B00C0C' },
              citation_resolved:  { bg: 'rgba(0,102,255,0.08)', fg: '#0054D1' },
              action_drafted:     { bg: 'rgba(101,65,242,0.10)', fg: '#3A16C9' },
              briefing_emitted:   { bg: 'var(--semantic-fill-normal)', fg: 'var(--semantic-label-neutral)' },
              approval_requested: { bg: 'rgba(255,146,0,0.10)', fg: '#9C5800' },
              handoff_drafted:    { bg: 'rgba(0,191,64,0.10)', fg: '#006E25' },
            };
            const tc = typeColors[e.type];
            return (
              <div key={e.id} style={{
                display: 'grid', gridTemplateColumns: '160px 180px 120px 1fr 80px',
                padding: '12px 20px', gap: 14, alignItems: 'center',
                borderBottom: i < events.length - 1 ? '1px solid var(--semantic-line-normal-alternative)' : 0,
                fontSize: 13,
              }}>
                <span style={{ fontVariantNumeric: 'tabular-nums', fontSize: 12, color: 'var(--semantic-label-alternative)' }}>{e.ts.slice(11, 16)} · {e.ts.slice(0, 10)}</span>
                <span style={{
                  display: 'inline-flex', padding: '2px 8px', borderRadius: 4,
                  background: tc.bg, color: tc.fg,
                  fontSize: 11.5, fontWeight: 600, fontFamily: 'var(--font-mono)',
                  width: 'fit-content',
                }}>{e.type}</span>
                <span style={{ fontSize: 12, color: 'var(--semantic-label-neutral)' }}>{e.actor}</span>
                <span style={{ color: 'var(--semantic-label-normal)' }}>{e.summary}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--semantic-label-alternative)', textAlign: 'right' }}>{e.id}</span>
              </div>
            );
          })}
        </div>
      </Card>

      <div style={{ marginTop: 16, padding: 14, borderRadius: 10, background: 'var(--semantic-background-normal-alternative)', border: '1px solid var(--semantic-line-normal-alternative)', fontSize: 12.5, color: 'var(--semantic-label-neutral)', lineHeight: 1.6 }}>
        <Icon name="shield" size={12} color="var(--semantic-primary-normal)"/>
        <span style={{ marginLeft: 6 }}>모든 이벤트는 source_snapshot_hash와 redacted_input/output_hash를 함께 기록합니다. 원문 PII는 저장되지 않습니다.</span>
      </div>
    </div>
  );
};

Object.assign(window, { HandoffPreview, EvidenceLogView });
