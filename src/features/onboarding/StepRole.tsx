import { cn } from '@/lib/cn';
import { ROLE_LABEL } from '@/lib/role';
import type { Role } from '@/types';

// O2 — 역할 선택(대표/담당자). 열람자(viewer)는 초대로만 생기는 역할이라 온보딩에선
// 선택지에 없다(7단계 §1 — 계정을 스스로 만드는 사람은 대표 또는 담당자뿐).
const SELECTABLE_ROLES: Role[] = ['owner', 'manager'];

const ROLE_SUMMARY: Record<Role, string> = {
  owner: '승인 권한 · 자율성 승급 결정',
  manager: '케이스 검토 · 승인 요청 처리',
  viewer: '케이스 조회만 가능 · 승인/처리 불가',
};

const ROLE_DIFF: Record<Role, string> = {
  owner: '대표는 승인 권한을 가지고, 담당자에게 자율성 승급을 결정합니다.',
  manager: '담당자는 케이스를 검토하고 대표에게 승인을 요청합니다.',
  viewer: '열람자는 케이스를 조회만 할 수 있고, 승인·처리 권한은 없습니다.',
};

export interface StepRoleProps {
  role: Role | null;
  onRoleChange: (role: Role) => void;
  /** real 모드(R2.2) 전용 — role이 서버 멤버십으로 이미 확정된 경우 선택 UI 대신 확인
   * 문구만 보여준다(코드리뷰 지적: 그렇지 않으면 사용자가 여기서 골라 서버가 정한 role을
   * roleStore에 그대로 덮어써버릴 수 있었다 — viewer는 선택지에도 없어 manager/owner로
   * 자기 승급하는 경로가 됐다). */
  readOnly?: boolean;
}

export function StepRole({ role, onRoleChange, readOnly = false }: StepRoleProps) {
  if (readOnly && role) {
    return (
      <div className="flex flex-col gap-5">
        <h1 className="text-heading1 font-bold text-ink">확인된 역할</h1>
        <div className="flex items-start gap-3 rounded-card bg-approvalbg p-4 shadow-rail-focus">
          <span className="flex flex-col gap-0.5">
            <span className="text-body2 font-semibold text-ink">
              {ROLE_LABEL[role]} <span className="text-caption1 font-medium text-subtle">{role}</span>
            </span>
            <span className="text-caption1 leading-relaxed text-subtle">{ROLE_SUMMARY[role]}</span>
          </span>
        </div>
        <div className="rounded-in bg-surface px-3.5 py-3">
          <p className="text-label1 leading-relaxed text-subtle">
            로그인한 계정에 연결된 역할이며, 여기서 바꿀 수 없습니다. 역할 변경은 대표에게 요청하세요.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-heading1 font-bold text-ink">어떤 역할로 시작하시나요?</h1>

      <div className="flex flex-col gap-3" role="group" aria-label="역할 선택">
        {SELECTABLE_ROLES.map((r) => {
          const selected = role === r;
          return (
            <button
              key={r}
              type="button"
              aria-pressed={selected}
              onClick={() => onRoleChange(r)}
              className={cn(
                'flex items-start gap-3 rounded-card p-4 text-left transition-colors duration-btn ease-v2',
                selected ? 'bg-approvalbg shadow-rail-focus' : 'shadow-outline hover:bg-surface',
              )}
            >
              <span
                className={cn(
                  'mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full',
                  selected ? 'shadow-rail-focus' : 'shadow-outline-strong',
                )}
              >
                {selected && <span className="size-2.5 rounded-full bg-primary" />}
              </span>
              <span className="flex flex-col gap-0.5">
                <span className="text-body2 font-semibold text-ink">
                  {ROLE_LABEL[r]} <span className="text-caption1 font-medium text-subtle">{r}</span>
                </span>
                <span className="text-caption1 leading-relaxed text-subtle">{ROLE_SUMMARY[r]}</span>
              </span>
            </button>
          );
        })}
      </div>

      <div className="rounded-in bg-surface px-3.5 py-3">
        <p className="text-label1 leading-relaxed text-subtle">
          {role ? ROLE_DIFF[role] : '역할에 따라 승인 권한과 처리 범위가 달라집니다.'}
        </p>
      </div>
    </div>
  );
}
