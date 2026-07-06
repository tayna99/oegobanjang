import { workers } from '../data';
import { Badge, Card } from '../components/ui';

const statCards = [
  ['전체 등록', '6명', 'text-blue-600'],
  ['즉시·우선 확인', '2명', 'text-orange-500'],
  ['서류 보완 필요', '3명', 'text-red-500'],
  ['정상', '1명', 'text-emerald-600'],
];

function tone(tone: string) {
  if (tone === 'red') return 'red';
  if (tone === 'orange') return 'orange';
  if (tone === 'blue') return 'blue';
  if (tone === 'green') return 'green';
  return 'gray';
}

export function WorkersView() {
  return (
    <div>
      <div className="mb-6 flex items-start justify-between">
        <div><div className="text-sm text-slate-500">근로자 목록</div><h1 className="text-3xl font-black tracking-[-0.04em]">한별제조 · 6명</h1></div>
        <button className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold">+ 근로자 등록</button>
      </div>
      <div className="mb-5 grid grid-cols-4 gap-4">
        {statCards.map(([title, value, cls]) => <Card key={title} className="p-5"><div className="text-sm text-slate-500">{title}</div><div className={`mt-2 text-3xl font-black ${cls}`}>{value}</div></Card>)}
      </div>
      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500"><tr><th className="px-5 py-3 text-left">근로자</th><th className="px-5 py-3 text-left">국적·체류</th><th className="px-5 py-3 text-left">체류만료 / D-day</th><th className="px-5 py-3 text-left">계약 종료</th><th className="px-5 py-3 text-left">서류 현황</th><th className="px-5 py-3 text-left">위험도</th><th className="px-5 py-3 text-right">근속</th></tr></thead>
          <tbody>
            {workers.map((w, idx) => <tr key={w.id} className="border-t border-slate-100 hover:bg-slate-50">
              <td className="px-5 py-4"><div className="flex items-center gap-3"><div className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-black text-white ${idx % 6 === 0 ? 'bg-blue-600' : idx % 6 === 1 ? 'bg-violet-600' : idx % 6 === 2 ? 'bg-orange-500' : idx % 6 === 3 ? 'bg-emerald-600' : idx % 6 === 4 ? 'bg-cyan-600' : 'bg-pink-500'}`}>{w.initials}</div><div><div className="font-black">{w.name} <span className="text-slate-400">{w.localName}</span></div><div className="text-xs text-slate-500">{w.line}</div></div></div></td>
              <td className="px-5 py-4"><div className="font-bold">{w.nationalityCode} {w.nationality}</div><div className="text-xs text-slate-500">{w.visaType}</div></td>
              <td className="px-5 py-4"><div className="font-bold">{w.visaExpiry}</div><div className={`mt-1 text-xs font-black ${w.dday.includes('+') ? 'text-red-600' : 'text-blue-600'}`}>{w.dday}</div></td>
              <td className="px-5 py-4"><div className="font-bold">{w.contractEnd}</div><div className="text-xs text-slate-500">{w.dday}</div></td>
              <td className="px-5 py-4"><div className="flex gap-1">{w.docs.map(d => <span key={d} className="rounded-md bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-700">{d}</span>)}{w.docExtra && <span className="text-xs font-bold text-orange-500">{w.docExtra}</span>}</div></td>
              <td className="px-5 py-4"><Badge tone={tone(w.statusTone) as any}>{w.status}</Badge></td>
              <td className="px-5 py-4 text-right text-slate-700">{w.tenure}</td>
            </tr>)}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
