// Screen 9: Runtime Metrics + Screen 10: Sub-Agent Trace
// SVG 아키텍처 기준: PII 집계값만 표시, grade 색상, 트레이스 트리

/* ── 공통 미니 차트 (CSS bar) ── */
function BarChart({ items, max, color = '#1B3FA0' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {items.map((item, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 130, fontSize: 12, color: 'var(--semantic-label-neutral)',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flexShrink: 0 }}>
            {item.name}
          </span>
          <div style={{ flex: 1, height: 8, borderRadius: 99,
            background: 'var(--semantic-fill-alternative)', overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: 99,
              width: `${Math.round((item.value / max) * 100)}%`,
              background: color,
              transition: 'width .4s ease',
            }}/>
          </div>
          <span style={{ width: 40, fontSize: 12, color: 'var(--semantic-label-alternative)',
            textAlign: 'right', fontVariantNumeric: 'tabular-nums', flexShrink: 0 }}>
            {item.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function MetricCard({ label, value, unit, sub, color }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 12, padding: '16px 20px',
      border: '1px solid var(--semantic-line-normal-alternative)',
      boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
    }}>
      <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', marginBottom: 6,
        fontWeight: 500 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.03em',
        color: color || 'var(--semantic-label-normal)', lineHeight: 1 }}>
        {value}
        <span style={{ fontSize: 14, fontWeight: 500, marginLeft: 4,
          color: 'var(--semantic-label-alternative)' }}>{unit}</span>
      </div>
      {sub && <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

/* ── Screen 9: Runtime Metrics ── */
function RuntimeMetricsView() {
  const m = RUNTIME_METRICS;
  const toolMax = Math.max(...m.tools.map(t => t.calls));
  const retMax = Math.max(...m.retrieval.collections.map(c => c.hits));

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 4 }}>
          Runtime Metrics
        </h2>
        <div style={{ fontSize: 12.5, color: 'var(--semantic-label-alternative)', display: 'flex',
          alignItems: 'center', gap: 6 }}>
          <span style={{ width: 7, height: 7, borderRadius: 99, background: '#10B981', flexShrink: 0 }}/>
          집계값만 표시 · PII 원문 없음
        </div>
      </div>

      {/* 모델 메트릭 */}
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--semantic-label-neutral)',
        marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>모델</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: 10, marginBottom: 24 }}>
        <MetricCard label="평균 응답 지연" value={m.model.avgLatencyMs.toLocaleString()} unit="ms"
          sub={`P95: ${m.model.p95LatencyMs.toLocaleString()}ms`}/>
        <MetricCard label="오늘 총 토큰" value={(m.model.totalTokensToday / 1000).toFixed(1)} unit="K"
          sub={`호출 ${m.model.callsToday}회`}/>
        <MetricCard label="예상 비용" value={m.model.estimatedCostKrw.toLocaleString()} unit="원"
          sub="오늘 기준"/>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        {/* 도구 실행 */}
        <div style={{ background: '#fff', borderRadius: 12, padding: '16px 20px',
          border: '1px solid var(--semantic-line-normal-alternative)' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--semantic-label-neutral)',
            marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.06em' }}>도구 실행</div>
          <BarChart
            items={m.tools.map(t => ({ name: t.name, value: t.calls }))}
            max={toolMax}
            color="#1B3FA0"
          />
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 4 }}>
            {m.tools.map(t => (
              <div key={t.name} style={{ display: 'flex', justifyContent: 'space-between',
                fontSize: 11.5, color: 'var(--semantic-label-alternative)' }}>
                <span>{t.name}</span>
                <span>{t.avgLatencyMs}ms avg</span>
              </div>
            ))}
          </div>
        </div>

        {/* RAG 검색 */}
        <div style={{ background: '#fff', borderRadius: 12, padding: '16px 20px',
          border: '1px solid var(--semantic-line-normal-alternative)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--semantic-label-neutral)',
              textTransform: 'uppercase', letterSpacing: '0.06em' }}>RAG 검색</div>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#065F46',
              background: '#D1FAE5', padding: '2px 10px', borderRadius: 99 }}>
              Hit Rate {Math.round(m.retrieval.hitRate * 100)}%
            </span>
          </div>
          <BarChart
            items={m.retrieval.collections.map(c => ({ name: c.name, value: c.hits }))}
            max={retMax}
            color="#00BFA5"
          />
        </div>
      </div>

      {/* 승인 현황 */}
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--semantic-label-neutral)',
        marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.06em' }}>승인 현황</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 24 }}>
        <MetricCard label="대기" value={m.approval.pending} unit="건" color="#1B3FA0"/>
        <MetricCard label="승인" value={m.approval.approved} unit="건" color="#10B981"/>
        <MetricCard label="반려" value={m.approval.rejected} unit="건" color="#EF4444"/>
        <MetricCard label="수정 요청" value={m.approval.revised} unit="건" color="#F59E0B"/>
      </div>

      {/* 안전 & 파일럿 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div style={{ background: '#fff', borderRadius: 12, padding: '16px 20px',
          border: '1px solid var(--semantic-line-normal-alternative)' }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12,
            textTransform: 'uppercase', letterSpacing: '0.06em',
            color: 'var(--semantic-label-neutral)' }}>안전 지표</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span style={{ color: 'var(--semantic-label-neutral)' }}>Forbidden 차단 횟수</span>
              <strong style={{ color: '#EF4444' }}>{m.safety.forbiddenBlocks}회</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span style={{ color: 'var(--semantic-label-neutral)' }}>수정 요청률</span>
              <strong>{Math.round(m.safety.revisionRate * 100)}%</strong>
            </div>
          </div>
        </div>
        <div style={{ background: '#fff', borderRadius: 12, padding: '16px 20px',
          border: '1px solid var(--semantic-line-normal-alternative)' }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12,
            textTransform: 'uppercase', letterSpacing: '0.06em',
            color: 'var(--semantic-label-neutral)' }}>파일럿 지표</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span style={{ color: 'var(--semantic-label-neutral)' }}>내보내기 건수</span>
              <strong>{m.pilot.exportCount}건</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span style={{ color: 'var(--semantic-label-neutral)' }}>평균 승인 소요</span>
              <strong>{m.pilot.avgApprovalTimeSec}초</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Screen 10: Sub-Agent Trace ── */
const STEP_TYPE_COLOR = {
  intent_router:  '#7C3AED',
  mission_agent:  '#1B3FA0',
  sub_agent:      '#0891B2',
  approval_gate:  '#D97706',
  final_response: '#059669',
};

const EVENT_TYPE_STYLE = {
  rag_retrieved:      { bg: '#DBEAFE', fg: '#1E40AF', icon: '🔍' },
  tool_executed:      { bg: '#D1FAE5', fg: '#065F46', icon: '⚙️' },
  approval_requested: { bg: '#FFEDD5', fg: '#9A3412', icon: '✋' },
  forbidden_block:    { bg: '#FEE2E2', fg: '#7F1D1D', icon: '🚫' },
};

function TraceStepItem({ step, onCitationClick }) {
  const [open, setOpen] = React.useState(false);
  const dot = STEP_TYPE_COLOR[step.type] || '#888';
  const gradeP = step.evidenceGrade ? EVIDENCE_GRADE_PALETTE[step.evidenceGrade] : null;

  return (
    <div style={{ display: 'flex', gap: 12, marginBottom: 4 }}>
      {/* 타임라인 선 */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
        <div style={{ width: 14, height: 14, borderRadius: 99, background: dot,
          border: '2px solid #fff', boxShadow: `0 0 0 2px ${dot}40`, flexShrink: 0, marginTop: 14 }}/>
        <div style={{ width: 2, flex: 1, background: 'var(--semantic-line-normal-alternative)',
          minHeight: 16 }}/>
      </div>

      {/* 카드 */}
      <div style={{ flex: 1, marginBottom: 8 }}>
        <div
          onClick={() => setOpen(v => !v)}
          style={{
            background: '#fff', borderRadius: 10, padding: '12px 14px',
            border: '1px solid var(--semantic-line-normal-alternative)',
            cursor: 'pointer', display: 'flex', gap: 10, alignItems: 'center',
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 3, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, fontWeight: 700, padding: '1px 7px', borderRadius: 99,
                background: dot + '18', color: dot }}>
                {step.type.replace(/_/g, ' ')}
              </span>
              <span style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--semantic-label-normal)' }}>
                {step.label}
              </span>
              {gradeP && (
                <span style={{ padding: '1px 7px', borderRadius: 99, fontSize: 11, fontWeight: 700,
                  background: gradeP.bg, color: gradeP.fg, border: `1px solid ${gradeP.border}` }}>
                  Grade {step.evidenceGrade}
                </span>
              )}
            </div>
            <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)' }}>
              {step.latencyMs}ms
            </div>
          </div>
          <Icon name={open ? 'chevronUp' : 'chevronDown'} size={14} color="var(--semantic-label-alternative)"/>
        </div>

        {/* 펼침: rationale */}
        {open && (
          <div style={{ marginTop: 4, padding: '12px 14px',
            background: 'var(--semantic-background-normal-alternative)',
            borderRadius: 10, border: '1px solid var(--semantic-line-normal-alternative)',
            fontSize: 13, lineHeight: 1.65, color: 'var(--semantic-label-neutral)' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--semantic-label-alternative)',
              textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 5 }}>
              Rationale / 판단 근거
            </div>
            <div>{step.rationale}</div>
            {step.citationId && (
              <button onClick={() => onCitationClick(step.citationId)}
                style={{ marginTop: 8, padding: '4px 10px', borderRadius: 6,
                  border: '1px solid #BFDBFE', background: '#EFF6FF', cursor: 'pointer',
                  fontFamily: 'inherit', fontSize: 12, color: '#1D4ED8', fontWeight: 600 }}>
                citation 보기 → {step.citationId}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function AgentTraceView({ onGoToEvidence }) {
  const t = AGENT_TRACE;

  return (
    <div style={{ maxWidth: 820, margin: '0 auto' }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 4 }}>
          Sub-Agent Activity Trace
        </h2>
        <div style={{ fontSize: 12.5, color: 'var(--semantic-label-alternative)' }}>
          request_id: <code style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{t.requestId}</code>
          {' · '}총 {t.totalMs.toLocaleString()}ms
        </div>
      </div>

      {/* 요청 요약 */}
      <div style={{ marginBottom: 20, padding: '14px 18px', borderRadius: 12,
        background: 'linear-gradient(90deg, rgba(27,63,160,0.07), rgba(0,191,165,0.06))',
        border: '1px solid rgba(27,63,160,0.16)' }}>
        <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--semantic-label-alternative)',
          textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 5 }}>입력 요청</div>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#1B3FA0' }}>"{t.input}"</div>
        <div style={{ fontSize: 12, color: 'var(--semantic-label-alternative)', marginTop: 4 }}>
          {new Date(t.startedAt).toLocaleString('ko-KR')} → {new Date(t.completedAt).toLocaleString('ko-KR')}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 20 }}>
        {/* 왼쪽: 단계 트리 */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--semantic-label-alternative)',
            textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
            실행 단계 ({t.steps.length}단계)
          </div>
          {t.steps.map(step => (
            <TraceStepItem
              key={step.id}
              step={step}
              onCitationClick={(citId) => onGoToEvidence && onGoToEvidence(citId)}
            />
          ))}
        </div>

        {/* 오른쪽: Evidence Events */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--semantic-label-alternative)',
            textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
            Evidence Events
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {t.evidenceEvents.map((ev, i) => {
              const s = EVENT_TYPE_STYLE[ev.type] || { bg: '#F3F4F6', fg: '#374151', icon: '·' };
              return (
                <div key={i} style={{ padding: '10px 12px', borderRadius: 10,
                  background: s.bg, border: `1px solid ${s.bg}` }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: s.fg,
                    textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 3 }}>
                    {s.icon} {ev.type.replace(/_/g, ' ')}
                  </div>
                  <div style={{ fontSize: 12.5, color: s.fg, lineHeight: 1.5 }}>{ev.summary}</div>
                  <div style={{ fontSize: 11, color: s.fg, opacity: 0.7, marginTop: 2 }}>
                    step: {ev.stepId}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { RuntimeMetricsView, AgentTraceView });
