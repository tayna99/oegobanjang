// 위임 관리 — owner 전용(system-derived, 설정 허브와 동일 근거, 7단계 §3.1). 위임 대상
// 선택은 구성원 행 관용구(탭 선택), 기간은 이 앱 최초의 <input type="date">(원시 폼
// 컨트롤 — 새 시각 결정이 아니라 그냥 날짜 입력, 목업 필요 없음).
import { useState } from 'react';
import { Button } from '@/components/Button';
import { BackHeader } from '@/components/BackHeader';
import { cn } from '@/lib/cn';
import { useCompanyActions } from '@/lib/company';
import { useNav } from '@/lib/nav';
import { useCompanyStore } from '@/stores/companyStore';
import { useRoleStore } from '@/stores/roleStore';

export function DelegationPage() {
  const nav = useNav();
  const role = useRoleStore((s) => s.role);
  const members = useCompanyStore((s) => s.members);
  const delegation = useCompanyStore((s) => s.delegation);
  const { grantDelegation, revokeDelegation } = useCompanyActions();
  const managers = members.filter((m) => m.role === 'manager');

  const [delegateId, setDelegateId] = useState(delegation.delegateId);
  const [from, setFrom] = useState(delegation.from);
  const [until, setUntil] = useState(delegation.until ?? '');

  if (role !== 'owner') {
    return (
      <div className="p-5">
        <p className="text-body2 text-muted">위임 관리는 대표 권한으로만 열 수 있습니다.</p>
        <Button variant="outline" className="mt-4" onClick={() => nav.toSettings()}>
          설정으로 돌아가기
        </Button>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <BackHeader title="위임 관리" onBack={() => nav.toSettings()} />

      <main className="flex flex-1 flex-col gap-5 px-5 pt-4">
        <section className="flex flex-col gap-1.5 rounded-in bg-approvalbg px-3.5 py-3">
          <p className="text-label1 font-semibold text-approval">
            {delegation.active ? '위임이 활성 상태입니다' : '위임이 설정되지 않았습니다'}
          </p>
          <p className="text-caption1 leading-relaxed text-approval">
            "내가 승인하지 못할 때 대신 승인" — 위임 중에도 대표에게는 항상 알림이 함께 갑니다.
          </p>
        </section>

        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">위임 대상</h3>
          <ul className="overflow-hidden rounded-in border border-hairline">
            {managers.map((manager) => {
              const selected = manager.id === delegateId;
              return (
                <li key={manager.id}>
                  <button
                    type="button"
                    aria-pressed={selected}
                    onClick={() => setDelegateId(manager.id)}
                    className={cn(
                      'flex w-full items-center gap-2.5 border-b border-hairline px-3.5 py-3 text-left last:border-none',
                      selected ? 'bg-approvalbg shadow-rail-active' : 'hover:bg-surface',
                    )}
                  >
                    <span className="min-w-0 flex-1 truncate text-label1 text-ink">{manager.name}</span>
                    {selected && <span className="text-caption1 font-semibold text-approval">선택됨</span>}
                  </button>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="flex flex-col gap-2">
          <h3 className="text-caption1 font-bold text-subtle">위임 기간</h3>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={from}
              onChange={(event) => setFrom(event.target.value)}
              aria-label="위임 시작일"
              className="flex-1 rounded-in bg-canvas px-3 py-2 text-label1 text-ink shadow-outline outline-none focus:shadow-rail-focus"
            />
            <span className="text-caption1 text-dim">~</span>
            <input
              type="date"
              value={until}
              onChange={(event) => setUntil(event.target.value)}
              aria-label="위임 종료일(선택)"
              className="flex-1 rounded-in bg-canvas px-3 py-2 text-label1 text-ink shadow-outline outline-none focus:shadow-rail-focus"
            />
          </div>
          <p className="text-caption1 text-dim">종료일을 비우면 무기한 위임입니다.</p>
        </section>

        <div className="flex gap-2.5">
          <Button
            variant="primary"
            className="flex-1"
            disabled={!delegateId || !from}
            onClick={() => grantDelegation(delegateId, from, until || undefined)}
          >
            위임 설정
          </Button>
          <Button variant="outline" className="flex-1" disabled={!delegation.active} onClick={revokeDelegation}>
            위임 해제
          </Button>
        </div>
      </main>
    </div>
  );
}
