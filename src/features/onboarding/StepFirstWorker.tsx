import { IconDoc, IconLock } from '@/components/icons';
import { SafetyNotice } from '@/components/SafetyNotice';
import { cn } from '@/lib/cn';

// O4 — 첫 근로자 등록. 3경로 세그먼트(서류 사진/직접 입력/CSV 업로드) 중 "직접 입력"만
// 실제 입력 필드를 받는다 — 서류 사진(OCR)·CSV는 각각 별도 파이프라인(OCR 미구현, CSV는
// 4.4에서 PC 전용 구현)이라 여기서는 안내 카드만 보여준다. 외국인등록번호는 편집 가능한
// 입력을 아예 두지 않는다 — 화면 어디에도 원문을 타이핑할 경로 자체를 만들지 않는 것이
// "마스킹 저장" 가드레일을 지키는 가장 확실한 방법이다(GOTCHAS §1).
export type WorkerPath = 'doc' | 'direct' | 'csv';

const PATH_LABEL: Record<WorkerPath, string> = { doc: '서류 사진', direct: '직접 입력', csv: 'CSV 업로드' };
const PATH_CAPTION: Record<WorkerPath, string> = {
  doc: '외국인등록증·여권 사진에서 항목을 인식한 뒤 확인합니다',
  direct: '이름·국적·팀·체류만료일 4개만 입력하면 됩니다',
  csv: 'PC에서 여러 명을 한 번에 등록합니다',
};

export interface WorkerFields {
  name: string;
  nationality: string;
  team: string;
  stayExpiryDate: string;
}

export interface StepFirstWorkerProps {
  path: WorkerPath;
  onPathChange: (path: WorkerPath) => void;
  fields: WorkerFields;
  onFieldsChange: (fields: WorkerFields) => void;
}

export function StepFirstWorker({ path, onPathChange, fields, onFieldsChange }: StepFirstWorkerProps) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-heading1 font-bold text-ink">첫 근로자를 등록하세요</h1>
        <p className="text-body2 text-muted">1명 · 필드 4개면 시작할 수 있습니다</p>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex gap-1 rounded-badge bg-surface p-1" role="group" aria-label="등록 경로 선택">
          {(Object.keys(PATH_LABEL) as WorkerPath[]).map((p) => {
            const active = p === path;
            return (
              <button
                key={p}
                type="button"
                aria-pressed={active}
                onClick={() => onPathChange(p)}
                className={cn(
                  'flex-1 rounded-btn-sm py-2 text-caption1 font-semibold transition-colors duration-btn ease-v2',
                  active ? 'bg-canvas text-ink shadow-card' : 'text-subtle',
                )}
              >
                {PATH_LABEL[p]}
              </button>
            );
          })}
        </div>
        <p className="px-0.5 text-caption1 leading-relaxed text-muted">{PATH_CAPTION[path]}</p>
      </div>

      {path === 'direct' && (
        <div className="flex flex-col gap-3.5">
          <div className="flex flex-col gap-1.5">
            <span className="text-label1 font-semibold text-ink">이름</span>
            <input
              type="text"
              value={fields.name}
              onChange={(event) => onFieldsChange({ ...fields, name: event.target.value })}
              aria-label="이름"
              className="h-12 rounded-in px-3.5 text-label1 text-ink shadow-outline outline-none focus:shadow-rail-focus"
            />
          </div>
          <div className="flex gap-3">
            <div className="flex flex-1 flex-col gap-1.5">
              <span className="text-label1 font-semibold text-ink">국적</span>
              <input
                type="text"
                value={fields.nationality}
                onChange={(event) => onFieldsChange({ ...fields, nationality: event.target.value })}
                aria-label="국적"
                className="h-12 rounded-in px-3.5 text-label1 text-ink shadow-outline outline-none focus:shadow-rail-focus"
              />
            </div>
            <div className="flex flex-1 flex-col gap-1.5">
              <span className="text-label1 font-semibold text-ink">팀</span>
              <input
                type="text"
                value={fields.team}
                onChange={(event) => onFieldsChange({ ...fields, team: event.target.value })}
                aria-label="팀"
                className="h-12 rounded-in px-3.5 text-label1 text-ink shadow-outline outline-none focus:shadow-rail-focus"
              />
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-label1 font-semibold text-ink">체류만료일</span>
            <input
              type="date"
              value={fields.stayExpiryDate}
              onChange={(event) => onFieldsChange({ ...fields, stayExpiryDate: event.target.value })}
              aria-label="체류만료일"
              className="h-12 rounded-in px-3.5 text-label1 text-ink shadow-outline outline-none focus:shadow-rail-focus"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-label1 font-semibold text-ink">외국인등록번호</span>
            <div className="flex h-12 items-center gap-2 rounded-in bg-surface px-3.5">
              <span className="flex-1 text-label1 tracking-wide text-ink">******-*******</span>
              <IconLock width={15} height={15} className="shrink-0 text-subtle" />
            </div>
            <p className="text-caption1 leading-relaxed text-muted">마스킹 저장 · 원문 번호는 저장하지 않습니다</p>
          </div>
        </div>
      )}

      {path === 'doc' && (
        <div className="flex flex-col gap-3">
          <div className="flex flex-col items-center gap-2.5 rounded-card border border-dashed border-line bg-surface p-6 text-center">
            <IconDoc width={34} height={34} className="text-subtle" />
            <span className="text-label1 font-semibold text-ink">서류 사진을 촬영하거나 선택</span>
            <span className="text-caption1 leading-relaxed text-muted">
              외국인등록증 · 여권 사진에서 항목을 인식한 뒤
              <br />
              등록 전에 직접 확인합니다
            </span>
          </div>
          <div className="flex gap-2 rounded-in bg-surface p-3">
            <IconLock width={15} height={15} className="mt-0.5 shrink-0 text-subtle" />
            <span className="text-caption1 leading-relaxed text-muted">
              외국인등록번호는 인식 후에도 마스킹으로 저장합니다
            </span>
          </div>
        </div>
      )}

      {path === 'csv' && (
        <div className="flex flex-col gap-2.5 rounded-card bg-surface p-4">
          <div className="flex items-center gap-2.5">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-in bg-approvalbg">
              <IconDoc width={18} height={18} className="text-primary" />
            </span>
            <div className="flex flex-col gap-0.5">
              <span className="text-label1 font-semibold text-ink">CSV로 여러 명 한 번에 등록</span>
              <span className="text-caption1 text-muted">PC 권장 · 검증 미리보기 후 확정</span>
            </div>
          </div>
          <p className="text-caption1 leading-relaxed text-muted">
            지금은 1명만 먼저 등록하고, 나머지는 PC에서 CSV로 일괄 등록하는 것을 권장합니다.
          </p>
        </div>
      )}

      <SafetyNotice />
    </div>
  );
}
