import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { BottomSheet } from './BottomSheet';

describe('BottomSheet', () => {
  it('open이 false면 아무것도 렌더하지 않는다', () => {
    render(
      <BottomSheet open={false} onClose={vi.fn()}>
        <p>내용</p>
      </BottomSheet>,
    );
    expect(screen.queryByText('내용')).not.toBeInTheDocument();
  });

  it('open이 true면 children과 footer를 렌더한다', () => {
    render(
      <BottomSheet open onClose={vi.fn()} footer={<button type="button">확인</button>}>
        <p>내용</p>
      </BottomSheet>,
    );
    expect(screen.getByText('내용')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '확인' })).toBeInTheDocument();
  });

  it('dismissible(기본값 true)이면 배경(scrim)을 탭하면 onClose가 실행된다', () => {
    const onClose = vi.fn();
    render(
      <BottomSheet open onClose={onClose}>
        <p>내용</p>
      </BottomSheet>,
    );
    fireEvent.click(screen.getByTestId('bottom-sheet-scrim'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('dismissible=false면 배경을 탭해도 onClose가 실행되지 않는다', () => {
    const onClose = vi.fn();
    render(
      <BottomSheet open onClose={onClose} dismissible={false}>
        <p>내용</p>
      </BottomSheet>,
    );
    fireEvent.click(screen.getByTestId('bottom-sheet-scrim'));
    expect(onClose).not.toHaveBeenCalled();
  });

  it('핸들을 탭하면 dismissible 여부와 무관하게 항상 onClose가 실행된다', () => {
    const onClose = vi.fn();
    render(
      <BottomSheet open onClose={onClose} dismissible={false}>
        <p>내용</p>
      </BottomSheet>,
    );
    fireEvent.click(screen.getByLabelText('시트 닫기'));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
