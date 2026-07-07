import { CheckCircle, MoreHorizontal, Search, X } from 'lucide-react';
import { judgmentRows } from '../data';
import { Badge, Button, Card } from '../components/ui';

function tone(tone: string) { return tone === 'green' ? 'green' : tone === 'blue' ? 'blue' : 'orange'; }

export function JudgmentLogView() {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_540px] gap-0 -mx-7 -my-7 min-h-[calc(100vh-102px)]">
      <section className="border-r border-slate-200 p-7">
        <h1 className="mb-6 text-3xl font-black tracking-[-0.04em]">판단 기록</h1>
        <div className="mb-4 flex gap-2"><Button>전체</Button><Button variant="secondary">승인 필요</Button><Button variant="secondary">외부 발송</Button><Button variant="secondary">행정사 검토</Button></div>
        <div className="mb-4 flex gap-3"><div className="flex w-[320px] items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-slate-400"><Search className="h-4 w-4" />키워드 검색 (사유, 이벤트, 대상 등)</div><Button variant="secondary">필터</Button></div>
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500"><tr><th className="w-14 px-5 py-3 text-left"><input type="checkbox" /></th><th className="px-4 py-3 text-left">판단 기록</th><th className="px-4 py-3 text-left">대상 근로자</th><th className="px-4 py-3 text-left">최종 상태</th><th className="px-4 py-3 text-left">판단일</th></tr></thead>
            <tbody>{judgmentRows.map((r, i) => <tr key={r.id} className={`border-t border-slate-100 ${i === 0 ? 'bg-slate-50 border-l-4 border-l-blue-700' : ''}`}><td className="px-5 py-4"><input type="checkbox" /></td><td className="px-4 py-4 font-black text-blue-700">{r.id}</td><td className="px-4 py-4">{r.worker}</td><td className="px-4 py-4"><Badge tone={tone(r.tone) as any}>{r.status}</Badge></td><td className="px-4 py-4 text-slate-500">{r.date}</td></tr>)}</tbody>
          </table>
        </Card>
      </section>
      <aside className="p-8">
        <div className="flex items-start justify-between"><div><h2 className="text-xl font-black">판단 기록 #4789 <Badge tone="green">승인 완료</Badge></h2></div><div className="flex gap-2"><Button variant="secondary" className="px-3"><MoreHorizontal className="h-4 w-4" /></Button><Button variant="ghost" className="px-3"><X className="h-4 w-4" /></Button></div></div>
        <div className="mt-8 grid grid-cols-3 gap-4 text-sm"><Info label="담당자" value="김대리 (인사팀)" /><Info label="대상 근로자" value="Nguyen V." /><Info label="관련 케이스" value="체류기간 연장 서류 요청" /></div>
        <div className="my-8 h-px bg-slate-200" />
        <Block title="판단 요약"><div className="rounded-xl bg-slate-50 p-5 leading-7 text-slate-700">체류만료일이 45일 이내로 확인되어, 누락된 서류를 요청하고 외부 발송 전 베트남어 메시지 초안을 생성하여 대표 승인이 완료됐습니다.</div></Block>
        <Block title="사용한 정보"><div className="flex flex-wrap gap-2"><Badge tone="gray">근로자 프로필</Badge><Badge tone="gray">체류 정보</Badge><Badge tone="gray">케이스 정보</Badge><Badge tone="gray">이전 대화 기록</Badge><Badge tone="gray">서류 체크리스트</Badge></div></Block>
        <Block title="승인 이력"><Card className="p-4"><div className="flex items-center justify-between"><div><div className="font-black">대표 (대표근로계약서)</div><div className="text-sm text-slate-500">김대표 · 2024-05-16 10:42</div></div><Badge tone="green">승인 완료</Badge></div></Card></Block>
        <Block title="이벤트 타임라인"><Timeline /></Block>
      </aside>
    </div>
  );
}
function Info({ label, value }: { label: string; value: string }) { return <div><div className="text-slate-500">{label}</div><div className="mt-1 font-black">{value}</div></div>; }
function Block({ title, children }: { title: string; children: React.ReactNode }) { return <section className="mb-7"><h3 className="mb-3 flex items-center gap-2 font-black"><CheckCircle className="h-4 w-4 text-blue-600" />{title}</h3>{children}</section>; }
function Timeline() { const items = ['체류만료일 확인', '누락 서류 감지', '이전 대화 기록 확인', '베트남어 메시지 초안 생성', '대표 승인 요청', '외부 발송 전 제한 적용']; return <div className="space-y-3">{items.map((i, idx) => <div key={i} className="flex gap-3"><div className="mt-1 h-2 w-2 rounded-full bg-emerald-500" /><div><div className="font-semibold">{i}</div><div className="text-xs text-slate-500">2024-05-16 10:{10 + idx * 3}</div></div></div>)}</div>; }
