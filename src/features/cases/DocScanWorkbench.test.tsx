import { fireEvent, render, screen } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { routeConfig } from '@/router';
import { useCaseStore } from '@/stores/caseStore';
import { useEvidenceStore } from '@/stores/evidenceStore';
import { useRoleStore } from '@/stores/roleStore';

function scanFiles(names: string[]): FileList {
  const files = names.map((name) => new File(['x'], name, { type: 'image/jpeg' }));
  const list: Partial<FileList> & { [i: number]: File } = {
    length: files.length,
    item: (i: number) => files[i] ?? null,
    [Symbol.iterator]: () => files[Symbol.iterator](),
  };
  files.forEach((f, i) => {
    list[i] = f;
  });
  return list as FileList;
}

// 서류 스캔 분류(감사 §2)는 classifyScanFiles가 파일명만 동기적으로 훑으므로
// FileReader 대기가 필요 없다 — classifying 단계(1200ms) 전환만 실시간으로 기다린다.
async function uploadFiles(names: string[]) {
  const input = screen.getByLabelText('스캔 파일 선택');
  fireEvent.change(input, { target: { files: scanFiles(names) } });
  await screen.findByRole('button', { name: /^전체/ }, { timeout: 3000 });
}

function mockViewport(desktop: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: desktop,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

function renderAt(path: string) {
  useCaseStore.getState().reset();
  useEvidenceStore.getState().reset();
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

afterEach(() => {
  delete (window as { matchMedia?: unknown }).matchMedia;
  useRoleStore.getState().reset();
});

// UI-2 DoD(plans/ROADMAP.md) — 미매칭 전건 해결 전 확인 대기 버튼 비활성, docUpdates 재사용,
// 일괄 확정 UI 부재, tool_executed evidence(파일명 미포함).
describe('DocScanWorkbench (PC, UI-2 DoD)', () => {
  beforeEach(() => {
    mockViewport(true);
  });

  it('파일을 분류하면 상태별로 필터·개수가 나뉜다', async () => {
    renderAt('/cases/scan');
    expect(screen.getByRole('heading', { name: '서류 스캔 자동분류 확인' })).toBeInTheDocument();

    await uploadFiles(['nguyen_passport.jpg', 'scan_0009.jpg']);

    expect(screen.getByText('전체 2')).toBeInTheDocument();
    expect(screen.getByText('정상 매칭 1')).toBeInTheDocument();
    expect(screen.getByText('미매칭 1')).toBeInTheDocument();
    expect(screen.getByText('Nguyen Van A')).toBeInTheDocument();
  });

  it('미매칭 행이 남아있으면 확인 대기로 올리기 버튼이 비활성이다', async () => {
    renderAt('/cases/scan');
    await uploadFiles(['nguyen_passport.jpg', 'scan_0009.jpg']);

    const confirmButton = screen.getByRole('button', { name: '확인 대기로 올리기' });
    expect(confirmButton).toBeDisabled();
    expect(screen.getByText('미매칭 건에 근로자를 지정해야 진행할 수 있습니다')).toBeInTheDocument();
  });

  // 확정 게이트는 모든 행이 근로자·서류 유형을 둘 다 갖출 것을 요구한다(hasUnresolvedRows,
  // 3a3b2b7). 서류 유형만 지정하고 근로자를 지정하지 않으면 여전히 막혀야 한다.
  it('미매칭 행에 서류 유형만 지정하고 근로자는 지정하지 않으면 게이트가 계속 막힌다', async () => {
    renderAt('/cases/scan');
    await uploadFiles(['nguyen_passport.jpg', 'scan_0009.jpg']);

    fireEvent.click(screen.getByRole('button', { name: /지정 필요/ }));
    fireEvent.click(screen.getByRole('button', { name: '외국인등록증' }));
    fireEvent.click(screen.getByRole('button', { name: '적용' }));

    expect(screen.getByText('미매칭 1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '확인 대기로 올리기' })).toBeDisabled();
    expect(screen.getByText('미매칭 건에 근로자를 지정해야 진행할 수 있습니다')).toBeInTheDocument();
  });

  it('일괄 확정을 위한 체크박스·전체선택 UI는 없다', async () => {
    renderAt('/cases/scan');
    await uploadFiles(['nguyen_passport.jpg', 'scan_0009.jpg']);
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });

  it('미매칭 행에 근로자·서류 유형을 모두 지정하면 버튼이 활성화되고, 확정 시 docUpdates·evidence에 반영된다(파일명 미노출)', async () => {
    renderAt('/cases/scan');
    await uploadFiles(['nguyen_passport.jpg', 'scan_0009.jpg']);

    // 게이트(3a3b2b7)는 근로자와 서류 유형을 둘 다 요구하므로 미매칭 행에 둘 다 지정한다.
    fireEvent.click(screen.getByRole('button', { name: /지정 필요/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Siti R.' }));
    fireEvent.click(screen.getByRole('button', { name: '외국인등록증' }));
    fireEvent.click(screen.getByRole('button', { name: '적용' }));

    // 게이트가 풀리는 것을 비동기로 기다린 뒤 버튼 활성화를 확인한다 — 게이트 힌트 문구는
    // blocked=false일 때만 렌더되므로 이 문구를 기다리는 것이 곧 재렌더 커밋을 기다리는 것.
    // (동기 assert는 느린 CI에서 상태 커밋 한 틱 뒤 실행될 수 있어 플래키하다.)
    expect(
      await screen.findByText('정상 매칭·확인 필요 건도 함께 확인 대기로 올라갑니다', undefined, { timeout: 3000 }),
    ).toBeInTheDocument();
    const confirmButton = screen.getByRole('button', { name: '확인 대기로 올리기' });
    expect(confirmButton).not.toBeDisabled();

    fireEvent.click(confirmButton);

    const docUpdates = useCaseStore.getState().docUpdates;
    expect(docUpdates.nguyen?.['여권 사본']?.to).toBe('스캔 확인 대기');
    expect(docUpdates.siti?.['외국인등록증']?.to).toBe('스캔 확인 대기');

    const events = useEvidenceStore.getState().events;
    const scanEvent = events.find((e) => e.type === 'tool_executed' && e.summary?.includes('서류 스캔 분류'));
    expect(scanEvent?.summary).toBe('서류 스캔 분류 — 2건 확인 대기 반영');
    expect(scanEvent?.summary).not.toMatch(/\.jpg/);

    expect(screen.getByText('2건이 확인 대기로 올라갔습니다')).toBeInTheDocument();
  });

  it('열람자·대표 권한으로는 안내 문구만 보인다', () => {
    useRoleStore.getState().setRole('viewer');
    renderAt('/cases/scan');
    expect(screen.getByText('서류 스캔 분류는 담당자 권한으로만 이용할 수 있습니다.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '파일 선택' })).not.toBeInTheDocument();
  });

  it('비데스크톱에서는 PC 유도 안내만 보인다', () => {
    mockViewport(false);
    renderAt('/cases/scan');
    expect(screen.getByText('서류 스캔 분류는 PC에서 이용해 주세요')).toBeInTheDocument();
  });
});
