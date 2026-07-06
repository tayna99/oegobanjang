import { Check, FileText } from 'lucide-react';
import { Badge, Button, Card } from '../components/ui';

const hiringCards = [
  { title: '신규 베트남 E-9 3명 채용 요청', meta: '화성 1공장 · 조립라인 · 행정사 검토 전 확인 필요', deadline: '2026.05.20', percent: 72, done: '5/8 완료', tone: 'teal', tasks: ['구인노력 기간 확인', '고용허가 신청서 준비', '송출회사 요청서 확인'] },
  { title: 'Candidate A 입국 전 서류 패키지', meta: '화성 1공장 · 도장라인 · 행정사 검토 전 확인 필요', deadline: '2026.05.20', percent: 45, done: '2/5 완료', tone: 'orange', tasks: ['건강진단서 원본 확인', '입국 전 교육 수료증 확인', '근로계약서 사본 확인'] },
];

export function HiringPreparationView() {
  return (
    <div className="space-y-6">
      <div><h1 className="text-3xl font-black tracking-[-0.04em]">채용 준비</h1><p className="mt-2 text-sm text-slate-500">신규 고용 준비 상태를 점검합니다. 후보자 점수화나 추천은 하지 않습니다.</p></div>
      <Card className="flex items-center gap-5 bg-gradient-to-r from-blue-50 to-teal-50 p-5"><div className="h-11 w-11 rounded-xl bg-gradient-to-br from-blue-700 to-teal-500" /><div><div className="font-black">신규 채용 준비 2건 진행 중</div><p className="text-sm text-slate-600">검토 필요 1건 · 준비 중 1건</p></div></Card>
      <div className="space-y-6">
        {hiringCards.map((card) => <Card key={card.title} className={`border-t-4 p-7 ${card.tone === 'teal' ? 'border-t-teal-500' : 'border-t-orange-500'}`}>
          <div className="flex items-start justify-between"><div><div className="mb-2 flex gap-2"><Badge tone="blue">E-9 · 3명</Badge><Badge tone={card.tone === 'teal' ? 'blue' : 'orange'}>{card.tone === 'teal' ? '준비 중' : '검토 필요'}</Badge></div><h2 className="text-2xl font-black">{card.title}</h2><p className="mt-1 text-sm text-slate-600">{card.meta}</p></div><div className="text-right"><div className="text-xs text-slate-500">마감</div><div className="font-black">{card.deadline}</div></div></div>
          <div className="mt-6"><div className="mb-2 flex justify-between text-sm"><span>준비 완료도</span><span className={card.tone === 'teal' ? 'text-blue-700 font-black' : 'text-orange-600 font-black'}>{card.percent}%</span></div><div className="h-2 rounded-full bg-slate-100"><div className={`h-full rounded-full ${card.tone === 'teal' ? 'bg-gradient-to-r from-blue-700 to-teal-500' : 'bg-gradient-to-r from-blue-700 to-teal-500'}`} style={{ width: `${card.percent}%` }} /></div><div className="mt-3 text-right text-sm text-slate-500">{card.done}</div></div>
          <div className="mt-4 space-y-3">{card.tasks.map((t) => <div key={t} className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3"><span className="flex h-5 w-5 items-center justify-center rounded border border-slate-300 bg-white" /> <span className="text-sm font-medium text-slate-700">{t}</span></div>)}</div>
          <div className="mt-5 flex gap-2"><Button variant="secondary"><FileText className="h-4 w-4" />요청서 보기</Button><Button variant="secondary"><Check className="h-4 w-4" />행정사 검토 요청</Button><span className="ml-auto text-sm text-slate-500">남은 작업 {card.tasks.length}개</span></div>
        </Card>)}
      </div>
    </div>
  );
}
