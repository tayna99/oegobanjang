import { Download, FileText } from 'lucide-react';
import { adminPackage } from '../data';
import { Badge, Button, Card } from '../components/ui';

function InfoTable({ rows }: { rows: string[][] }) {
  return <div className="divide-y divide-slate-100 border-t-2 border-slate-900">{rows.map(([k, v]) => <div key={k} className="grid grid-cols-[220px_1fr] py-4 text-sm"><div className="text-slate-500">{k}</div><div className="font-semibold text-slate-950">{v}</div></div>)}</div>;
}

export function AdminReviewView() {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_360px] gap-6">
      <Card className="p-8">
        <div className="flex items-start justify-between border-b border-slate-200 pb-8">
          <div><div className="text-sm text-slate-500">행정사 검토용 자료 · 초안</div><h1 className="mt-1 text-3xl font-black tracking-[-0.04em]">{adminPackage.title}</h1><p className="mt-2 text-sm text-slate-500">생성 {adminPackage.createdAt} · 수신자 {adminPackage.receiver} (검토 대기)</p></div>
          <Badge tone="orange">승인 대기</Badge>
        </div>
        <section className="mt-8"><h2 className="mb-4 text-lg font-black">근로자 기본 정보</h2><InfoTable rows={adminPackage.profile} /></section>
        <section className="mt-8"><h2 className="mb-4 text-lg font-black">체류 / 계약 상태</h2><InfoTable rows={adminPackage.stay} /></section>
        <section className="mt-8"><h2 className="mb-4 text-lg font-black">제출 서류</h2><InfoTable rows={adminPackage.docs} /></section>
      </Card>
      <aside className="space-y-5">
        <Card className="p-6"><h2 className="mb-4 font-black">다음 단계</h2><Button className="w-full">승인 후 검토 자료 확정</Button><Button variant="secondary" className="mt-3 w-full">수정 요청</Button><Button variant="ghost" className="mt-3 w-full"><Download className="h-4 w-4" />PDF 내보내기</Button><p className="mt-4 text-xs text-slate-500">승인 후에도 정부 포털 자동 제출은 수행하지 않습니다.</p></Card>
        <Card className="p-6"><h2 className="mb-4 font-black">포함된 근거 (3)</h2><Evidence source="국가법령정보센터" text="출입국관리법 제25조 (체류기간 연장허가)" grade="A" /><Evidence source="출입국관리법" text="제94조 벌칙 (체류기간 초과)" grade="A" /><Evidence source="HiKorea" text="체류기간 연장허가 신청 안내" grade="B" /></Card>
        <Card className="p-6"><h2 className="mb-4 font-black">승인 흐름</h2>{['시스템 초안 생성', '담당자 검토', '사장님 승인', '행정사 전달'].map((x, i) => <div key={x} className="mb-3 flex items-center gap-3"><span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-black ${i < 2 ? 'bg-emerald-500 text-white' : 'bg-slate-100 text-slate-500'}`}>{i + 1}</span><span className="text-sm font-semibold">{x}</span></div>)}</Card>
      </aside>
    </div>
  );
}
function Evidence({ source, text, grade }: { source: string; text: string; grade: string }) {
  return <div className="mb-3 rounded-xl bg-slate-50 p-3"><div className="mb-1 flex items-center gap-2 text-xs text-slate-500"><span className="rounded bg-blue-600 px-1.5 py-0.5 font-black text-white">{grade}</span>{source}</div><div className="text-sm font-bold text-slate-800">{text}</div></div>;
}
