import { contactItems } from '../data';
import { Badge, Button, Card } from '../components/ui';

export function ContactView() {
  return (
    <div>
      <div className="mb-6"><h1 className="text-3xl font-black tracking-[-0.04em]">메시지 관리</h1><p className="mt-2 text-sm text-slate-500">근로자별 다국어 컨택 초안을 확인하고 승인합니다.</p></div>
      <Card className="grid min-h-[650px] grid-cols-[320px_1fr] overflow-hidden">
        <aside className="border-r border-slate-200 bg-slate-50/60">
          <div className="border-b border-slate-200 p-4 text-sm font-semibold text-slate-500">컨택 목록 · 3건</div>
          {contactItems.map((item, index) => <div key={item.worker} className={`flex gap-3 border-b border-slate-200 p-5 ${index === 0 ? 'border-l-4 border-blue-700 bg-blue-50/60' : ''}`}>
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-indigo-600 font-black text-white">{item.initials}</div>
            <div className="min-w-0 flex-1"><div className="flex items-center gap-2"><span className="font-black">{item.worker}</span><span className="text-xs font-bold text-slate-500">{item.country}</span><span className="rounded-md bg-blue-600 px-1.5 py-0.5 text-xs font-black text-white">{item.badge}</span></div><div className="truncate text-xs text-slate-500">{item.desc}</div><div className="mt-2 flex items-center gap-2"><Badge tone={item.status === '응답 도착' ? 'green' : item.status === '승인 대기' ? 'orange' : 'gray'}>{item.status}</Badge><span className="text-xs text-slate-500">{item.date}</span></div></div>
          </div>)}
        </aside>
        <section>
          <div className="border-b border-slate-200 p-7">
            <div className="flex items-start justify-between"><div><div className="flex items-center gap-3"><span className="font-bold">VN</span><h2 className="text-xl font-black">Nguyen V.</h2></div><p className="text-sm text-slate-500">베트남 · Zalo · 응우엔 V.</p></div><Badge tone="gray">초안</Badge></div>
            <div className="mt-4 rounded-lg border border-orange-200 bg-orange-50 px-4 py-3 text-sm font-medium text-orange-800">승인 전에는 외부로 발송되지 않습니다. 담당자 검토용 초안입니다.</div>
          </div>
          <div className="p-7">
            <div className="mb-4 flex gap-8 border-b border-slate-100"><button className="border-b-2 border-blue-700 px-2 pb-3 font-bold text-blue-700">Tiếng Việt</button><button className="px-2 pb-3 font-bold text-slate-500">한국어</button></div>
            <div className="rounded-xl border border-teal-200 bg-teal-50/50 p-6 leading-8 text-slate-950">
              Xin chào anh Nguyen V.,<br /><br />Đây là Oegobanjang.<br />Chúng tôi đang chuẩn bị gia hạn thời gian cư trú.<br />Vui lòng gửi các giấy tờ sau trước ngày 20 tháng 5.<br /><br />1. Bản sao hộ chiếu (trang ảnh)<br />2. Bản sao thẻ đăng ký người nước ngoài (mặt trước & mặt sau)<br /><br />Mục đích thu thập: Chuẩn bị hồ sơ gia hạn cư trú.<br />Thời gian lưu giữ: 30 ngày sau khi nộp hồ sơ.
            </div>
            <h3 className="mt-5 font-black">예상 응답 시나리오</h3>
            <div className="mt-3 grid grid-cols-3 gap-3"><Scenario title="긍정 응답" desc="서류 수신 후 행정사 검토 자료에 자동 반영" tone="green" /><Scenario title="추가 정보 요청" desc="필요 서류와 형식 기준을 다시 안내" tone="blue" /><Scenario title="응답 지연" desc="2일 뒤 리마인드 메시지 제안" tone="orange" /></div>
          </div>
          <div className="mt-8 flex justify-end gap-3 border-t border-slate-200 p-6"><Button variant="ghost">나중에 보기</Button><Button variant="secondary">수정 요청</Button><Button>승인</Button></div>
        </section>
      </Card>
    </div>
  );
}
function Scenario({ title, desc, tone }: { title: string; desc: string; tone: 'green' | 'blue' | 'orange' }) {
  const cls = tone === 'green' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : tone === 'blue' ? 'border-blue-200 bg-blue-50 text-blue-800' : 'border-orange-200 bg-orange-50 text-orange-800';
  return <div className={`rounded-xl border p-4 ${cls}`}><div className="font-black">{title}</div><p className="mt-1 text-sm">{desc}</p></div>;
}
