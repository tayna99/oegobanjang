import { riskCases } from '../data';
import { Badge, Card, PillButton } from '../components/ui';

function border(tone: string) {
  if (tone === 'red') return 'border-red-200 bg-red-50/20';
  if (tone === 'orange') return 'border-orange-200 bg-orange-50/20';
  return 'border-blue-200 bg-blue-50/20';
}
function dot(tone: string) {
  if (tone === 'red') return 'bg-red-500';
  if (tone === 'orange') return 'bg-orange-500';
  return 'bg-blue-500';
}
function badgeTone(tone: string) {
  if (tone === 'red') return 'red';
  if (tone === 'orange') return 'orange';
  return 'blue';
}

export function CasesView() {
  const groups = ['즉시 확인', '우선 확인', '확인 필요'];
  return (
    <div className="space-y-7">
      <div><div className="text-sm text-slate-500">케이스 목록</div><h1 className="text-3xl font-black tracking-[-0.04em]">리스크 케이스 · 7건</h1></div>
      {groups.map((group) => {
        const items = riskCases.filter((item) => item.group === group);
        if (!items.length) return null;
        const groupTone = items[0].tone;
        return <section key={group}>
          <div className="mb-3 flex items-center gap-2"><span className={`h-2.5 w-2.5 rounded-full ${dot(groupTone)}`} /><h2 className="font-black text-slate-900">{group}</h2><span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-600">{items.length}건</span></div>
          <div className="space-y-3">
            {items.map((item) => <Card key={item.id} className={`p-5 ${border(item.tone)}`}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2"><Badge tone={badgeTone(item.tone) as any}>{group}</Badge><h3 className="text-lg font-black">{item.title}</h3><span className="rounded-full bg-violet-500 px-2 py-1 text-xs font-black text-white">{item.nationalityCode}</span><span className="font-semibold text-slate-600">{item.worker}</span></div>
                  <p className="mt-3 text-slate-700">{item.desc}</p>
                  <div className="mt-4 flex flex-wrap gap-2">{item.actions.map((a) => <PillButton key={a}>{a}</PillButton>)}</div>
                </div>
                <span className="font-mono text-xs text-slate-400">{item.id}</span>
              </div>
            </Card>)}
          </div>
        </section>;
      })}
    </div>
  );
}
