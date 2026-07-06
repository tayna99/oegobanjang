import { FileText, MessageSquare, RefreshCcw, Shield, UserRoundPlus } from 'lucide-react';
import { todaysTasks } from '../data';
import { Badge, Button, Card, IconTile, PillButton } from '../components/ui';

const summary = [
  { title: '체류기간 임박', value: '4명', tone: 'red' as const, icon: FileText },
  { title: '서류 보완 필요', value: '7건', tone: 'orange' as const, icon: FileText },
  { title: '신규 채용 준비', value: '1건', tone: 'green' as const, icon: UserRoundPlus },
  { title: '컨택 대기', value: '4건', tone: 'purple' as const, icon: MessageSquare },
  { title: '응답 도착', value: '2건', tone: 'blue' as const, icon: MessageSquare },
  { title: '승인 대기', value: '5건', tone: 'orange' as const, icon: Shield },
  { title: '행정사 검토 준비', value: '2건', tone: 'blue' as const, icon: FileText },
];

function statusTone(tone: string) {
  if (tone === 'orange') return 'orange';
  if (tone === 'blue') return 'blue';
  if (tone === 'green') return 'green';
  return 'gray';
}

export function TodayTasksView() {
  return (
    <div className="space-y-6">
      <Card className="flex items-center justify-between bg-gradient-to-r from-blue-50 to-teal-50 p-5">
        <div className="flex items-center gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-blue-700 to-teal-500 text-sm font-black text-white">반</div>
          <div>
            <div className="font-extrabold">오늘 브리핑이 준비되었습니다</div>
            <p className="text-sm text-slate-600">외고반장이 7개 케이스를 정리했습니다. 즉시 확인 1건, 우선 확인 3건, 승인 대기 5건.</p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm text-slate-500">
          <span>오늘 08:00</span>
          <Button variant="secondary"><RefreshCcw className="h-4 w-4" />다시 생성</Button>
        </div>
      </Card>

      <div className="grid grid-cols-7 gap-3">
        {summary.map((item) => (
          <Card key={item.title} className="p-4">
            <IconTile icon={item.icon} tone={item.tone} />
            <div className="mt-4 text-sm text-slate-500">{item.title}</div>
            <div className={`mt-1 text-3xl font-black ${item.tone === 'red' ? 'text-red-500' : item.tone === 'orange' ? 'text-orange-500' : item.tone === 'green' ? 'text-emerald-600' : item.tone === 'purple' ? 'text-violet-600' : 'text-blue-600'}`}>{item.value}</div>
          </Card>
        ))}
      </div>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-black tracking-[-0.03em]">오늘의 업무 큐 <span className="ml-2 rounded-full bg-blue-50 px-2 py-1 text-sm text-blue-700">4건</span></h2>
          <div className="flex gap-2"><Button variant="secondary">필터</Button><Button variant="secondary">기한 임박 순</Button></div>
        </div>

        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="w-16 px-4 py-3 text-left"><input type="checkbox" /></th>
                <th className="px-4 py-3 text-left">업무</th>
                <th className="px-4 py-3 text-left">대상</th>
                <th className="px-4 py-3 text-left">상태</th>
                <th className="px-4 py-3 text-left">기한</th>
                <th className="px-4 py-3 text-left">다음 처리</th>
                <th className="px-4 py-3 text-right"></th>
              </tr>
            </thead>
            <tbody>
              {todaysTasks.map((task) => (
                <tr key={task.title} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-4"><input type="checkbox" /></td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-3">
                      <IconTile icon={task.kind === 'hiring' ? UserRoundPlus : task.kind === 'message' ? MessageSquare : FileText} tone={task.tone as any} />
                      <span className="font-extrabold text-slate-900">{task.title}</span>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-slate-700">{task.target}</td>
                  <td className="px-4 py-4"><Badge tone={statusTone(task.tone) as any}>{task.status}</Badge></td>
                  <td className="px-4 py-4 font-bold text-slate-700">{task.deadline}</td>
                  <td className="px-4 py-4"><PillButton>{task.next}</PillButton></td>
                  <td className="px-4 py-4 text-right text-slate-400">⋮</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </section>
    </div>
  );
}
