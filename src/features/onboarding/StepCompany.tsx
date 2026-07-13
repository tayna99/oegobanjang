// O3 — 사업장 정보 4필드. 시각적 목업(companyStore에 아직 회사 프로필 슬롯이 없고,
// BriefingHomePage/CaseListPage가 이미 "그린푸드 제조"를 하드코딩된 헤더 문자열로 쓰고 있어
// 여기 입력값을 영속화해도 그 표시에 반영되지 않는다 — 새 스토어 슬롯을 만드는 대신 이미
// 확립된 데모 세계관 값을 기본값으로 채워 그대로 보여준다).
export interface CompanyFields {
  name: string;
  region: string;
  industry: string;
  workerCount: string;
}

export interface StepCompanyProps {
  fields: CompanyFields;
  onFieldsChange: (fields: CompanyFields) => void;
}

const FIELD_LABELS: { key: keyof CompanyFields; label: string }[] = [
  { key: 'name', label: '사업장명' },
  { key: 'region', label: '지역' },
  { key: 'industry', label: '업종' },
  { key: 'workerCount', label: 'E-9 근로자 수' },
];

export function StepCompany({ fields, onFieldsChange }: StepCompanyProps) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <h1 className="text-heading1 font-bold text-ink">사업장 정보</h1>
        <p className="text-body2 text-muted">브리핑 기준이 되는 사업장을 등록합니다</p>
      </div>

      <div className="flex flex-col gap-4">
        {FIELD_LABELS.map(({ key, label }) => (
          <div key={key} className="flex flex-col gap-1.5">
            <span className="text-label1 font-semibold text-ink">{label}</span>
            <input
              type="text"
              value={fields[key]}
              onChange={(event) => onFieldsChange({ ...fields, [key]: event.target.value })}
              aria-label={label}
              className="h-12 rounded-in px-3.5 text-label1 text-ink shadow-outline outline-none focus:shadow-rail-focus"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
