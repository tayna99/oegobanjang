import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { StepRole } from './StepRole';

describe('StepRole — O2 역할 선택(mock) / 확인(real, readOnly)', () => {
  it('기본(mock) 모드에서는 대표/담당자를 선택할 수 있고 선택값이 눌린 상태로 표시된다', () => {
    const onRoleChange = vi.fn();
    render(<StepRole role="manager" onRoleChange={onRoleChange} />);

    const ownerBtn = screen.getByRole('button', { name: /대표 owner/ });
    const managerBtn = screen.getByRole('button', { name: /담당자 manager/ });
    expect(managerBtn).toHaveAttribute('aria-pressed', 'true');
    expect(ownerBtn).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(ownerBtn);
    expect(onRoleChange).toHaveBeenCalledWith('owner');
  });

  it('viewer는 mock 모드 선택지에 없다(초대 전용 역할)', () => {
    render(<StepRole role={null} onRoleChange={vi.fn()} />);
    expect(screen.queryByRole('button', { name: /viewer/ })).not.toBeInTheDocument();
  });

  // 코드리뷰 회귀(PR #15 P1): real 모드에서 이 화면이 선택 가능했을 때, 서버 멤버십으로
  // 이미 확정된 role을 사용자가 여기서 골라 roleStore에 그대로 덮어쓸 수 있었다 — readOnly면
  // 버튼이 아예 없어야 하고(클릭해서 바꿀 방법 자체가 없어야 하고), 실제 role을 그대로 보여줘야
  // 한다(viewer도 포함 — mock 선택지에는 없지만 real 확인 화면에는 있어야 한다).
  it('readOnly(real 모드)에서는 선택 버튼이 없고 현재 role을 확인 문구로만 보여준다', () => {
    render(<StepRole role="viewer" onRoleChange={vi.fn()} readOnly />);

    expect(screen.queryByRole('button', { name: /대표 owner/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /담당자 manager/ })).not.toBeInTheDocument();
    expect(screen.getByText(/열람자/)).toBeInTheDocument();
    expect(screen.getByText('viewer')).toBeInTheDocument();
    expect(screen.getByText(/여기서 바꿀 수 없습니다/)).toBeInTheDocument();
  });

  it('readOnly에서 role이 manager/owner여도 그 값 그대로 보여준다', () => {
    render(<StepRole role="owner" onRoleChange={vi.fn()} readOnly />);
    expect(screen.getByText('owner')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
