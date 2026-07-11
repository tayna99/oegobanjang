import type { ReactNode } from 'react';

export interface BottomSheetProps {
  open: boolean;
  onClose: () => void;
  dismissible?: boolean;
  footer?: ReactNode;
  children: ReactNode;
}

// 1단계 스펙 §0.3 BottomSheet(M2·승인 모달 공용) — 프로토타입 v3 .ovl/.sheet/.handle/.sbody/.sfoot 이식.
// half↔full 드래그 리사이즈는 범위 밖 — 고정 max-h-sheet(86%)로만 렌더한다.
export function BottomSheet({ open, onClose, dismissible = true, footer, children }: BottomSheetProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-20">
      <div
        data-testid="bottom-sheet-scrim"
        onClick={() => dismissible && onClose()}
        className="absolute inset-0 bg-ink/40"
      />
      <div className="absolute inset-x-0 bottom-0 flex max-h-sheet flex-col rounded-t-sheet bg-canvas shadow-sheet">
        <button
          type="button"
          onClick={onClose}
          aria-label="시트 닫기"
          className="flex justify-center py-3"
        >
          <span className="h-1 w-9 rounded-full bg-line" />
        </button>
        <div className="flex-1 overflow-y-auto px-6 pb-2">{children}</div>
        {footer && <div className="border-t border-hairline px-6 py-3">{footer}</div>}
      </div>
    </div>
  );
}
