import {
  Check,
  CheckCircle,
  Download,
  FileText,
  MessageSquare,
  MoreHorizontal,
  RefreshCcw,
  Search,
  UserRoundPlus,
  X,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import React, { useEffect, useState } from "react";
import { adminPackage, contactItems, judgmentRows, riskCases, todaysTasks, workers, type Tone } from "../data";
import { Badge, Button, Card, cn, PillButton, textToneClass, toneClass } from "../ui";
import styles from "../PcShell.module.css";

const summary = [
  {
    id: "visa", label: "체류기간 임박", count: 4, unit: "명",
    color: "#EF4444", bg: "#FEF2F2", workerId: "w_bayar",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="#EF4444" strokeWidth="1.8"/><path d="M12 7v5l3 3" stroke="#EF4444" strokeWidth="1.8" strokeLinecap="round"/></svg>),
  },
  {
    id: "docs", label: "서류 보완 필요", count: 7, unit: "건",
    color: "#F97316", bg: "#FFF7ED", workerId: "w_nguyen",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z" stroke="#F97316" strokeWidth="1.8" strokeLinejoin="round"/><path d="M14 2v6h6M12 12v4M12 10h.01" stroke="#F97316" strokeWidth="1.8" strokeLinecap="round"/></svg>),
  },
  {
    id: "recruit", label: "신규 채용 준비", count: 1, unit: "건",
    color: "#10B981", bg: "#ECFDF5", workerId: "w_nguyen",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><circle cx="9" cy="8" r="3.5" stroke="#10B981" strokeWidth="1.8"/><path d="M3 20c0-3.866 2.686-6 6-6s6 2.134 6 6" stroke="#10B981" strokeWidth="1.8" strokeLinecap="round"/><path d="M17 6l1.5 1.5L21 5" stroke="#10B981" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>),
  },
  {
    id: "contact", label: "컨택 대기", count: 4, unit: "건",
    color: "#8B5CF6", bg: "#F5F3FF", workerId: "w_nguyen",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M4 4h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H6l-4 4V5a1 1 0 0 1 1-1z" stroke="#8B5CF6" strokeWidth="1.8" strokeLinejoin="round"/></svg>),
  },
  {
    id: "reply", label: "응답 도착", count: 2, unit: "건",
    color: "#0EA5E9", bg: "#F0F9FF", workerId: "w_tran",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="#0EA5E9" strokeWidth="1.8" strokeLinejoin="round"/><path d="M8 10h8M8 14h4" stroke="#0EA5E9" strokeWidth="1.8" strokeLinecap="round"/></svg>),
  },
  {
    id: "approval", label: "승인 대기", count: 5, unit: "건",
    color: "#F59E0B", bg: "#FFFBEB", workerId: "w_nguyen",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="#F59E0B" strokeWidth="1.8" strokeLinejoin="round"/></svg>),
  },
  {
    id: "handoff", label: "행정사 검토 준비", count: 2, unit: "건",
    color: "#6366F1", bg: "#EEF2FF", workerId: "w_bayar",
    icon: (<svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M9 11l3 3L22 4" stroke="#6366F1" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke="#6366F1" strokeWidth="1.8" strokeLinecap="round"/></svg>),
  },
];
const totalRiskCaseCount = riskCases.length;

export type PcActionKind =
  | "refresh"
  | "document-draft"
  | "handoff-preview"
  | "approval-preview"
  | "revision-request"
  | "response-summary"
  | "worker-register"
  | "pdf-draft"
  | "open-ai";

export type PcViewAction = {
  kind: PcActionKind;
  label: string;
};

export type PcViewProps = {
  onAction?: (action: PcViewAction) => void;
};

const TASK_STATUS_MAP: Record<string, { label: string; bg: string; fg: string }> = {
  "승인 필요": { label: "승인 필요", bg: "#FFF7ED", fg: "#C2410C" },
  "진행 중":   { label: "진행 중",   bg: "#EFF6FF", fg: "#1D4ED8" },
  "승인 대기": { label: "승인 대기", bg: "#FFF7ED", fg: "#C2410C" },
  "응답 도착": { label: "응답 도착", bg: "#ECFDF5", fg: "#065F46" },
  "검토 필요": { label: "검토 필요", bg: "#FFFBEB", fg: "#B45309" },
};

const TASK_TYPE_ICON: Record<string, React.ReactElement> = {
  doc: (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M12 2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V6l-4-4z" stroke="#1B3FA0" strokeWidth="1.5" strokeLinejoin="round"/>
      <path d="M12 2v4h4M8 10h4M8 13h2" stroke="#1B3FA0" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),
  hiring: (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <circle cx="8" cy="6" r="3" stroke="#10B981" strokeWidth="1.5"/>
      <path d="M3 17c0-3 2-4.5 5-4.5s5 1.5 5 4.5" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M14 3l1.5 1.5L18 2" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  message: (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
      <path d="M3 3h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H5l-3 3V4a1 1 0 0 1 1-1z" stroke="#8B5CF6" strokeWidth="1.5" strokeLinejoin="round"/>
    </svg>
  ),
};

const CASE_SEV: Record<string, { bg: string; bd: string; fg: string; dot: string }> = {
  red:    { bg: "rgba(255,66,66,0.10)",   bd: "rgba(255,66,66,0.32)",   fg: "#B00C0C", dot: "#FF4242" },
  orange: { bg: "rgba(255,146,0,0.10)",   bd: "rgba(255,146,0,0.30)",   fg: "#9C5800", dot: "#FF9200" },
  blue:   { bg: "rgba(0,102,255,0.07)",   bd: "rgba(0,102,255,0.20)",   fg: "#003699", dot: "#0066FF" },
  gray:   { bg: "rgba(112,115,124,0.06)", bd: "rgba(112,115,124,0.20)", fg: "#70737C", dot: "#B0B3BA" },
};

const candidateArrivalChecklist = [
  "여권 사본 확보",
  "증명사진 제출 확인",
  "건강진단서 원본 확인",
  "입국 전 취업교육 수료증 확인",
  "표준근로계약서 사본 확인",
  "사증발급인정서 또는 비자 진행 정보 확인",
  "입국 예정일과 사업장 배치일 확인",
  "입국 후 외국인등록 준비 서류 확인",
];
const CANDIDATE_ARRIVAL_STORAGE_KEY = "oegobanjang:candidate-arrival-checklist:v1";
const CANDIDATE_ID = "candidate-001";
const CANDIDATE_PACKAGE_STORAGE_KEY = "oegobanjang:candidate-arrival-package:candidate-001:v1";
const CANDIDATE_PACKAGE_API_PATH = `/api/v1/hiring/candidates/${CANDIDATE_ID}/pre-entry-package`;

type HiringTab = "new-hiring" | "candidate";
type HiringDraftMode = "edit" | "draft";
type CandidateMode = "list" | "package";
type PackageStatus = "미작성" | "작성 중" | "검토 필요" | "준비 완료";

type PackageSection = {
  id: string;
  index: number;
  title: string;
  status: PackageStatus;
  rows: Array<{ label: string; value: string; tone?: "muted" | "warning" | "ok" }>;
  attachments?: string[];
  note?: string;
};

const statusTone: Record<PackageStatus, { bg: string; fg: string; bd: string }> = {
  "미작성": { bg: "#F3F4F6", fg: "#6B7280", bd: "#E5E7EB" },
  "작성 중": { bg: "#EFF6FF", fg: "#1D4ED8", bd: "#BFDBFE" },
  "검토 필요": { bg: "#FFF7ED", fg: "#C2410C", bd: "#FED7AA" },
  "준비 완료": { bg: "#ECFDF5", fg: "#047857", bd: "#A7F3D0" },
};

const initialNewHiringSections: PackageSection[] = [
  {
    id: "company",
    index: 1,
    title: "사업장 요건",
    status: "작성 중",
    rows: [
      { label: "업종", value: "전자부품 제조업" },
      { label: "사업장 소재지", value: "부산광역시 강서구" },
      { label: "기존 외국인근로자 수", value: "4명" },
      { label: "요청 인원", value: "2명" },
    ],
    note: "workforce_templates의 new_hiring industry, region, needed_headcount 항목 기준",
  },
  {
    id: "native-recruitment",
    index: 2,
    title: "내국인 구인노력",
    status: "검토 필요",
    rows: [
      { label: "구인 등록일", value: "2026-04-15" },
      { label: "구인 기간", value: "2026-04-15 ~ 2026-05-14 (30일)" },
      { label: "모집 직무", value: "전자부품 조립원" },
      { label: "모집 인원", value: "2명" },
      { label: "지원자 수", value: "0명" },
      { label: "미충원 사유", value: "지원자 없음", tone: "warning" },
    ],
    attachments: ["구인공고 캡처.pdf", "고용24 구인신청 확인자료.png"],
    note: "EPS 신규 고용 절차의 내국인 구인노력 단계 기준",
  },
  {
    id: "working-condition",
    index: 3,
    title: "근로조건",
    status: "미작성",
    rows: [
      { label: "임금", value: "-", tone: "warning" },
      { label: "근무시간", value: "-", tone: "warning" },
      { label: "교대 여부", value: "-", tone: "warning" },
      { label: "요청 직무", value: "전자부품 조립원" },
      { label: "희망 입사일", value: "-", tone: "warning" },
    ],
    note: "표준근로계약서 초안 작성을 위해 필요한 사업장 입력값",
  },
  {
    id: "housing-safety",
    index: 4,
    title: "숙소/안전 안내",
    status: "준비 완료",
    rows: [
      { label: "숙소 제공 여부", value: "제공", tone: "ok" },
      { label: "숙소 주소", value: "부산광역시 강서구 OO로 123" },
      { label: "비용 부담", value: "사업주 부담" },
      { label: "안전교육 자료", value: "첨부 완료", tone: "ok" },
    ],
    attachments: ["안전교육 안내문.pdf"],
    note: "workforce_company_requirements의 숙소/근무조건/안전교육 준비 항목 기준",
  },
  {
    id: "permit-docs",
    index: 5,
    title: "고용허가 신청자료",
    status: "작성 중",
    rows: [
      { label: "고용허가 신청서", value: "작성 중" },
      { label: "사업자등록증", value: "첨부 완료", tone: "ok" },
      { label: "업종별 구비서류", value: "검토 중", tone: "warning" },
      { label: "표준근로계약서", value: "작성 중" },
    ],
    attachments: ["사업자등록증.pdf"],
    note: "고용24 고용허가 신청 안내와 EPS 고용허가 신청 단계 기준",
  },
];

const candidatePackageSections = [
  {
    title: "후보자 기본 정보",
    rows: [
      ["성명", "Nguyen Thi Lan"],
      ["국적", "베트남"],
      ["예정 체류자격", "E-9"],
      ["후보 상태", "입국 전 서류 준비"],
      ["배치 예정 사업장", "삼성전자 부산공장 / 부산공장 도장라인"],
    ],
  },
  {
    title: "입국 전 준비 상태",
    rows: [
      ["입국 예정일", "2026.05.20"],
      ["근무 가능일", "2026.05.27"],
      ["표준근로계약서", "확인 필요"],
      ["사증발급인정서/비자 진행 정보", "확인 필요"],
    ],
  },
  {
    title: "제출 서류",
    rows: [
      ["여권 사본", "확보됨"],
      ["증명사진", "확보됨"],
      ["건강진단서 원본", "확인 필요"],
      ["입국 전 취업교육 수료증", "확인 필요"],
      ["표준근로계약서 사본", "확인 필요"],
      ["입국 후 외국인등록 준비 서류", "확인 필요"],
    ],
  },
];

function actionForNext(next: string): PcActionKind {
  if (next.includes("초안")) return "document-draft";
  if (next.includes("요청서")) return "handoff-preview";
  if (next.includes("승인")) return "approval-preview";
  if (next.includes("응답")) return "response-summary";
  return "handoff-preview";
}

function workerTestId(workerId: string) {
  return `worker-row-${workerId.replace("w_", "")}`;
}

export function HiringPreparationView({ onAction }: PcViewProps = {}) {
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState<HiringTab>("new-hiring");
  const [draftMode, setDraftMode] = useState<HiringDraftMode>("edit");
  const [candidateMode, setCandidateMode] = useState<CandidateMode>("list");
  const [packageSections, setPackageSections] = useState<PackageSection[]>(initialNewHiringSections);
  const [candidatePackageDraft, setCandidatePackageDraft] = useState(candidatePackageSections);
  const [candidatePackageEditing, setCandidatePackageEditing] = useState(false);
  const [candidatePackageSaveState, setCandidatePackageSaveState] = useState<"idle" | "saving" | "saved" | "local">("idle");
  const [selectedSectionId, setSelectedSectionId] = useState("native-recruitment");
  const [candidateCheckedItems, setCandidateCheckedItems] = useState<Record<string, boolean>>({});
  const [candidateChecklistLoaded, setCandidateChecklistLoaded] = useState(false);
  const candidateCheckedCount = candidateArrivalChecklist.filter((item) => candidateCheckedItems[item]).length;
  const candidateChecklistComplete = candidateCheckedCount === candidateArrivalChecklist.length;
  const selectedSection = packageSections.find((section) => section.id === selectedSectionId) ?? packageSections[0];
  const readySectionCount = packageSections.filter((section) => section.status === "준비 완료").length;
  const missingSectionCount = packageSections.filter((section) => section.status === "미작성").length;
  const reviewSectionCount = packageSections.filter((section) => section.status === "검토 필요").length;
  const draftMissingRows = packageSections.flatMap((section) =>
    section.rows
      .filter((row) => row.value === "-" || row.tone === "warning")
      .map((row) => `${section.title}: ${row.label}`),
  );
  const requestedWorkerId = searchParams.get("worker_id");
  const requestedWorker = workers.find((worker) => worker.id === requestedWorkerId) ?? null;
  const requestedActionLabel = searchParams.get("label");

  useEffect(() => {
    if (searchParams.get("from") !== "today") return;
    if (!requestedWorker) return;
    setActiveTab("new-hiring");
    setDraftMode("draft");
    setCandidateMode("list");
  }, [requestedWorker, searchParams]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(CANDIDATE_ARRIVAL_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as Record<string, boolean>;
      const next = Object.fromEntries(
        candidateArrivalChecklist.map((item) => [item, Boolean(parsed[item])]),
      );
      setCandidateCheckedItems(next);
    } catch {
      window.localStorage.removeItem(CANDIDATE_ARRIVAL_STORAGE_KEY);
    } finally {
      setCandidateChecklistLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (!candidateChecklistLoaded) return;
    window.localStorage.setItem(CANDIDATE_ARRIVAL_STORAGE_KEY, JSON.stringify(candidateCheckedItems));
  }, [candidateCheckedItems, candidateChecklistLoaded]);

  useEffect(() => {
    let cancelled = false;
    async function loadCandidatePackage() {
      try {
        const response = await fetch(CANDIDATE_PACKAGE_API_PATH, { cache: "no-store" });
        if (response.ok) {
          const data = await response.json() as { sections?: typeof candidatePackageSections; saved?: boolean };
          if (!cancelled && data.saved && Array.isArray(data.sections) && data.sections.length > 0) {
            setCandidatePackageDraft(data.sections);
            setCandidatePackageSaveState("saved");
            return;
          }
        }
      } catch {
        // 서버 저장이 아직 준비되지 않은 경우 브라우저 임시 저장값을 사용한다.
      }

      try {
        const raw = window.localStorage.getItem(CANDIDATE_PACKAGE_STORAGE_KEY);
        if (!raw) return;
        const parsed = JSON.parse(raw) as typeof candidatePackageSections;
        if (!cancelled && Array.isArray(parsed)) {
          setCandidatePackageDraft(parsed);
          setCandidatePackageSaveState("local");
        }
      } catch {
        window.localStorage.removeItem(CANDIDATE_PACKAGE_STORAGE_KEY);
      }
    }
    loadCandidatePackage();
    return () => { cancelled = true; };
  }, []);

  function updatePackageRow(sectionId: string, label: string, value: string) {
    setPackageSections((sections) =>
      sections.map((section) => {
        if (section.id !== sectionId) return section;
        const rows = section.rows.map((row) =>
          row.label === label
            ? { ...row, value, tone: value.trim() && value !== "-" ? undefined : row.tone }
            : row,
        );
        const hasMissing = rows.some((row) => !row.value.trim() || row.value === "-");
        return { ...section, rows, status: hasMissing ? "작성 중" : section.status };
      }),
    );
  }

  function updateCandidatePackageRow(sectionTitle: string, label: string, value: string) {
    setCandidatePackageDraft((sections) =>
      sections.map((section) => {
        if (section.title !== sectionTitle) return section;
        return {
          ...section,
          rows: section.rows.map(([currentLabel, currentValue]) =>
            currentLabel === label ? [currentLabel, value] : [currentLabel, currentValue],
          ),
        };
      }),
    );
  }

  async function saveCandidatePackageDraft() {
    setCandidatePackageSaveState("saving");
    try {
      const response = await fetch(CANDIDATE_PACKAGE_API_PATH, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sections: candidatePackageDraft, status: "DRAFT" }),
      });
      if (!response.ok) throw new Error("failed to save package");
      window.localStorage.removeItem(CANDIDATE_PACKAGE_STORAGE_KEY);
      setCandidatePackageSaveState("saved");
    } catch {
      window.localStorage.setItem(
        CANDIDATE_PACKAGE_STORAGE_KEY,
        JSON.stringify(candidatePackageDraft),
      );
      setCandidatePackageSaveState("local");
    } finally {
      setCandidatePackageEditing(false);
      onAction?.({ kind: "document-draft", label: "입국 전 패키지 저장" });
    }
  }

  return (
    <div className={styles.stack}>
      <div>
        <div className={styles.subtle}>채용 준비</div>
        <h1 className={styles.headline}>신규 고용 준비</h1>
        <p className={styles.subtle}>신규 고용 준비 상태를 점검합니다. 후보자 점수화나 추천은 하지 않습니다.</p>
      </div>

      {requestedWorker ? (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: "12px 14px", borderRadius: 12, background: "#EFF6FF", border: "1px solid #BFDBFE", color: "#1E3A8A" }}>
          <div>
            <strong style={{ display: "block", fontSize: 13.5 }}>오늘 할 일에서 이동: {requestedWorker.name}</strong>
            <span style={{ fontSize: 12 }}>{requestedWorker.nationality} · {requestedWorker.visaType} · {requestedWorker.line} · {requestedActionLabel ?? "요청서 보기"}</span>
          </div>
          <span style={{ fontSize: 12, fontWeight: 800 }}>{requestedWorker.dday}</span>
        </div>
      ) : null}

      <div style={{ display: "inline-flex", gap: 6, padding: 4, borderRadius: 10, background: "#F3F6FB", border: "1px solid #E5EAF3", width: "fit-content" }}>
        {[
          { id: "new-hiring" as HiringTab, label: "신규 채용 준비", count: 1 },
          { id: "candidate" as HiringTab, label: "후보자 관리", count: 1 },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => {
              setActiveTab(tab.id);
              setDraftMode("edit");
              setCandidateMode("list");
            }}
            style={{
              border: 0,
              borderRadius: 8,
              padding: "8px 14px",
              background: activeTab === tab.id ? "#FFFFFF" : "transparent",
              color: activeTab === tab.id ? "#0F3B8F" : "#64748B",
              fontWeight: 800,
              boxShadow: activeTab === tab.id ? "0 1px 4px rgba(15,23,42,0.08)" : "none",
              cursor: "pointer",
            }}
          >
            {tab.label} <span style={{ fontSize: 12, color: activeTab === tab.id ? "#2563EB" : "#94A3B8" }}>{tab.count}건</span>
          </button>
        ))}
      </div>

      {activeTab === "new-hiring" && draftMode === "edit" ? (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.2fr) minmax(340px, 0.8fr)", gap: 18, alignItems: "start" }}>
          <div className={styles.stack}>
            <section style={{ border: "1px solid #D9E2F2", borderRadius: 12, background: "#fff", padding: 18 }}>
              <div className={styles.pageHead} style={{ marginBottom: 16 }}>
                <div>
                  <div className={styles.subtle}>신규 E-9 채용 준비</div>
                  <h2 style={{ margin: "2px 0 4px", fontSize: 18 }}>고용허가 준비 패키지</h2>
                  <p className={styles.subtle} style={{ fontSize: 12.5 }}>EPS/고용24 근거와 사업장 데이터를 기준으로 준비자료를 정리합니다.</p>
                </div>
                <Button variant="primary" onClick={() => setDraftMode("draft")}>
                  <FileText size={15} /> 준비 자료 만들기
                </Button>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", border: "1px solid #E5EAF3", borderRadius: 10, overflow: "hidden", marginBottom: 16 }}>
                {[
                  ["준비율", `${readySectionCount}/${packageSections.length}`, "#2563EB"],
                  ["누락 자료", `${missingSectionCount}개`, "#F97316"],
                  ["검토 필요", `${reviewSectionCount}개`, "#D97706"],
                ].map(([label, value, color]) => (
                  <div key={label} style={{ padding: "14px 16px", borderRight: label === "검토 필요" ? "none" : "1px solid #E5EAF3" }}>
                    <div className={styles.subtle} style={{ fontSize: 12 }}>{label}</div>
                    <strong style={{ fontSize: 20, color }}>{value}</strong>
                  </div>
                ))}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
                {packageSections.map((section) => {
                  const tone = statusTone[section.status];
                  const selected = section.id === selectedSection.id;
                  return (
                    <button
                      key={section.id}
                      type="button"
                      onClick={() => setSelectedSectionId(section.id)}
                      style={{
                        textAlign: "left",
                        background: "#fff",
                        borderRadius: 10,
                        border: selected ? "1.5px solid #2563EB" : "1px solid #E5EAF3",
                        boxShadow: selected ? "0 0 0 3px rgba(37,99,235,0.08)" : "none",
                        padding: 14,
                        cursor: "pointer",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, marginBottom: 10 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{ width: 22, height: 22, borderRadius: 999, background: "#EAF2FF", color: "#2563EB", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 900 }}>{section.index}</span>
                          <strong>{section.title}</strong>
                        </div>
                        <span style={{ padding: "3px 8px", borderRadius: 999, background: tone.bg, color: tone.fg, border: `1px solid ${tone.bd}`, fontSize: 11, fontWeight: 800 }}>{section.status}</span>
                      </div>
                      <div className={styles.stack} style={{ gap: 6 }}>
                        {section.rows.slice(0, 4).map((row) => (
                          <div key={row.label} style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 12.5 }}>
                            <span className={styles.subtle}>{row.label}</span>
                            <strong style={{ color: row.tone === "warning" ? "#C2410C" : row.tone === "ok" ? "#047857" : "#111827" }}>{row.value}</strong>
                          </div>
                        ))}
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          </div>

          <section style={{ border: "1px solid #D9E2F2", borderRadius: 12, background: "#fff", padding: 18, position: "sticky", top: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 14 }}>
              <div>
                <div className={styles.subtle}>상세 입력/증빙</div>
                <h2 style={{ margin: "2px 0 0", fontSize: 18 }}>{selectedSection.title}</h2>
              </div>
              <span style={{ padding: "4px 9px", borderRadius: 999, background: statusTone[selectedSection.status].bg, color: statusTone[selectedSection.status].fg, border: `1px solid ${statusTone[selectedSection.status].bd}`, fontSize: 12, fontWeight: 800 }}>{selectedSection.status}</span>
            </div>
            <div className={styles.stack} style={{ gap: 10 }}>
              {selectedSection.rows.map((row) => (
                <label key={row.label} style={{ display: "grid", gap: 5 }}>
                  <span className={styles.subtle} style={{ fontSize: 12 }}>{row.label}</span>
                  <input
                    value={row.value === "-" ? "" : row.value}
                    placeholder="입력 필요"
                    onChange={(event) => updatePackageRow(selectedSection.id, row.label, event.target.value)}
                    style={{
                    border: "1px solid #E5EAF3",
                    borderRadius: 8,
                    background: row.value === "-" ? "#FFF7ED" : "#F8FAFC",
                    padding: "10px 12px",
                    fontSize: 13,
                    fontWeight: 700,
                    color: row.value === "-" ? "#C2410C" : "#1F2937",
                  }}
                  />
                </label>
              ))}
              <div style={{ display: "grid", gap: 8 }}>
                <div className={styles.subtle} style={{ fontSize: 12 }}>첨부자료</div>
                {(selectedSection.attachments ?? []).map((file) => (
                  <div key={file} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid #E5EAF3", borderRadius: 8, padding: "9px 11px", fontSize: 13 }}>
                    <span>{file}</span>
                    <span className={styles.subtle}>첨부됨</span>
                  </div>
                ))}
                <Button variant="secondary" onClick={() => onAction?.({ kind: "document-draft", label: "파일 추가" })}>
                  <FileText size={14} /> 파일 추가
                </Button>
              </div>
              <div style={{ border: "1px solid #DBEAFE", background: "#EFF6FF", borderRadius: 10, padding: 12, color: "#1E3A8A", fontSize: 12.5 }}>
                {selectedSection.note}
              </div>
            </div>
          </section>
        </div>
      ) : null}

      {activeTab === "new-hiring" && draftMode === "draft" ? (
        <section style={{ border: "1px solid #D9E2F2", borderRadius: 12, background: "#fff", overflow: "hidden" }}>
          <div style={{ padding: 22, borderBottom: "1px solid #E5EAF3" }}>
            <div className={styles.badgeLine}>
              <span style={{ padding: "4px 10px", borderRadius: 999, background: "#EFF6FF", color: "#1D4ED8", fontSize: 12, fontWeight: 800 }}>초안</span>
              <span className={styles.subtle}>생성 2026.05.14 10:32 · 내부 준비용</span>
            </div>
            <h2 style={{ margin: "8px 0 4px", fontSize: 22 }}>고용허가 준비자료 초안</h2>
            <p className={styles.subtle}>신규 E-9 고용허가 신청 전 내부 확인용 자료입니다. 정부 제출은 자동으로 수행하지 않습니다.</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 320px", gap: 20, padding: 22 }}>
            <div className={styles.stack}>
              {[
                { title: "요청 개요", rows: [["비자유형", "E-9"], ["요청 인원", "2명"], ["배치 예정", "부산공장 조립라인"], ["희망 입사 시점", "2026.06"]] },
                ...packageSections.map((section) => ({ title: section.title, rows: section.rows.map((row) => [row.label, row.value]) })),
              ].map((block) => (
                <div key={block.title} style={{ borderBottom: "1px solid #EEF2F7", paddingBottom: 14 }}>
                  <h3 style={{ fontSize: 15, margin: "0 0 10px" }}>{block.title}</h3>
                  <div style={{ display: "grid", gap: 8 }}>
                    {block.rows.map(([label, value]) => (
                      <div key={label} style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: 12, fontSize: 13 }}>
                        <span className={styles.subtle}>{label}</span>
                        <strong style={{ color: value === "-" ? "#C2410C" : "#111827" }}>{value === "-" ? "미입력" : value}</strong>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <aside className={styles.stack}>
              <div style={{ border: "1px solid #E5EAF3", borderRadius: 10, padding: 14 }}>
                <h3 style={{ margin: "0 0 12px", fontSize: 15 }}>AI 확인 결과</h3>
                <div className={styles.stack} style={{ gap: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span>누락/확인 필요</span><strong style={{ color: "#F97316" }}>{draftMissingRows.length}개</strong></div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span>검토 필요 섹션</span><strong style={{ color: "#D97706" }}>{reviewSectionCount}개</strong></div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}><span>첨부 완료</span><strong style={{ color: "#047857" }}>4개</strong></div>
                </div>
              </div>
              <div style={{ border: "1px solid #E5EAF3", borderRadius: 10, padding: 14 }}>
                <h3 style={{ margin: "0 0 10px", fontSize: 15 }}>근거</h3>
                <div className={styles.badgeLine}>
                  <Badge>EPS</Badge>
                  <Badge>고용24</Badge>
                  <Badge>workforce_templates</Badge>
                </div>
                <p className={styles.subtle} style={{ fontSize: 12.5, lineHeight: 1.6, marginTop: 8 }}>내국인 구인노력, 고용허가 신청 단계, 사업장 요건 체크 항목을 기준으로 초안을 구성했습니다.</p>
              </div>
              <div style={{ border: "1px solid #DBEAFE", background: "#EFF6FF", borderRadius: 10, padding: 12, color: "#1E3A8A", fontSize: 12.5 }}>이 자료는 내부 준비용이며 제출·발송은 수행하지 않습니다.</div>
            </aside>
          </div>
          <div style={{ display: "flex", gap: 8, padding: 18, borderTop: "1px solid #E5EAF3" }}>
            <Button variant="primary" onClick={() => onAction?.({ kind: "document-draft", label: "초안 저장" })}><Check size={15} /> 초안 저장</Button>
            <Button variant="secondary" onClick={() => setDraftMode("edit")}>수정하기</Button>
            <Button variant="secondary" onClick={() => onAction?.({ kind: "pdf-draft", label: "PDF 미리보기" })}><FileText size={15} /> PDF 미리보기</Button>
          </div>
        </section>
      ) : null}

      {activeTab === "candidate" && candidateMode === "list" ? (
        <section
          style={{
            borderRadius: 12,
            border: "1px solid rgba(255,146,0,0.30)",
            background: "#fff",
            borderLeft: "3px solid #FF9200",
            padding: "20px 22px 20px 20px",
          }}
        >
          <div className={styles.pageHead} style={{ marginBottom: 16 }}>
            <div style={{ flex: 1 }}>
              <div className={styles.badgeLine} style={{ marginBottom: 6 }}>
                <span style={{ display: "inline-flex", padding: "2px 8px", borderRadius: 6, fontSize: 11, fontWeight: 600, background: "rgba(112,115,124,0.08)", color: "#374151" }}>E-9</span>
                <span style={{ display: "inline-flex", padding: "2px 8px", borderRadius: 6, fontSize: 11, fontWeight: 700, background: "rgba(255,146,0,0.10)", border: "1px solid rgba(255,146,0,0.30)", color: "#9C5800" }}>검토 필요</span>
              </div>
              <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 4px" }}>Nguyen Thi Lan 입국 전 서류 패키지</h2>
              <p className={styles.subtle} style={{ fontSize: 12.5 }}>화성 1공장 · 도장라인 · 후보자가 이미 정해진 경우의 입국 전 준비자료</p>
            </div>
            <div style={{ textAlign: "right", flexShrink: 0 }}>
              <div className={styles.subtle} style={{ fontSize: 11 }}>마감</div>
              <strong style={{ fontSize: 14 }}>2026.05.20</strong>
            </div>
          </div>
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: 12.5, color: "#374151" }}>준비 완료도</span>
              <strong style={{ fontSize: 14, fontWeight: 800, color: "#FF9200" }}>{Math.round((candidateCheckedCount / candidateArrivalChecklist.length) * 100)}%</strong>
            </div>
            <div className={styles.progressTrack}>
              <div className={styles.progressBar} style={{ width: `${Math.round((candidateCheckedCount / candidateArrivalChecklist.length) * 100)}%`, background: "#FF9200" }} />
            </div>
            <p className={styles.subtle} style={{ fontSize: 12, marginTop: 4 }}>{candidateCheckedCount}/{candidateArrivalChecklist.length} 완료</p>
          </div>
          <div className={styles.stack} style={{ marginBottom: 16 }}>
            {candidateArrivalChecklist.map((task) => (
              <button key={task} onClick={() => {
                setCandidateCheckedItems((current) => ({ ...current, [task]: !current[task] }));
              }} style={{
                display: "flex", alignItems: "center", gap: 10,
                width: "100%",
                padding: "10px 14px", borderRadius: 8,
                background: candidateCheckedItems[task] ? "rgba(0,191,64,0.08)" : "rgba(112,115,124,0.05)",
                border: candidateCheckedItems[task] ? "1px solid rgba(0,191,64,0.24)" : "1px solid rgba(112,115,124,0.10)",
                cursor: "pointer",
                textAlign: "left",
              }}>
                <span style={{
                  width: 18, height: 18, borderRadius: 5, flexShrink: 0,
                  border: `1.5px solid ${candidateCheckedItems[task] ? "rgba(0,191,64,0.45)" : "rgba(255,146,0,0.30)"}`,
                  background: candidateCheckedItems[task] ? "rgba(0,191,64,0.12)" : "rgba(255,146,0,0.10)",
                  display: "inline-flex", alignItems: "center", justifyContent: "center",
                }}>
                  {candidateCheckedItems[task] ? (
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                      <path d="M2 5l2.5 2.5L8 3" stroke="#00A550" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  ) : null}
                </span>
                <span style={{ fontSize: 13, color: "#374151" }}>{task}</span>
              </button>
            ))}
          </div>
          <div className={styles.buttonRow}>
            <Button
              disabled={!candidateChecklistComplete}
              style={!candidateChecklistComplete ? { opacity: 0.45, cursor: "not-allowed", filter: "grayscale(1)" } : undefined}
              variant="secondary"
              onClick={() => {
                if (!candidateChecklistComplete) return;
                setCandidateMode("package");
                setCandidatePackageEditing(false);
              }}
            >
              <FileText size={15} /> 입국 전 패키지 보기
            </Button>
            <span className={styles.subtle} style={{ fontSize: 12, marginLeft: "auto" }}>
              남은 작업 {candidateArrivalChecklist.length - candidateCheckedCount}개
            </span>
          </div>
        </section>
      ) : null}

      {activeTab === "candidate" && candidateMode === "package" ? (
        <section style={{ border: "1px solid rgba(255,146,0,0.30)", borderRadius: 12, background: "#fff", overflow: "hidden" }}>
          <div style={{ padding: 22, borderBottom: "1px solid #EEF2F7" }}>
            <div className={styles.badgeLine}>
              <span style={{ padding: "4px 10px", borderRadius: 999, background: "#FFF7ED", color: "#C2410C", fontSize: 12, fontWeight: 800 }}>입국 전 패키지</span>
              <span className={styles.subtle}>생성 2026.05.14 10:32 · 후보자 서류 준비용</span>
              {candidatePackageSaveState === "saved" ? <span className={styles.subtle}>SQLite 저장됨</span> : null}
              {candidatePackageSaveState === "local" ? <span className={styles.subtle}>브라우저 임시 저장</span> : null}
            </div>
            <div className={styles.pageHead} style={{ marginTop: 8 }}>
              <div>
                <h2 style={{ margin: "0 0 4px", fontSize: 22 }}>Nguyen Thi Lan 입국 전 서류 패키지</h2>
              </div>
              <Button variant="secondary" onClick={() => setCandidateMode("list")}>목록으로 돌아가기</Button>
            </div>
          </div>

          <div style={{ padding: "20px 22px 22px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, border: "1px solid #DBEAFE", background: "#EFF6FF", borderRadius: 10, padding: "10px 12px", color: "#1E3A8A", fontSize: 12.5, marginBottom: 20 }}>
              <span style={{ width: 18, height: 18, borderRadius: 999, background: "#DBEAFE", display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: 900, flexShrink: 0 }}>i</span>
              <span>입국 후 관리 항목은 근로자 등록 단계에서 별도로 관리합니다.</span>
            </div>

            <div className={styles.stack} style={{ gap: 20 }}>
              {candidatePackageDraft.map((section) => (
                <section key={section.title}>
                  <h3 style={{ margin: "0 0 10px", fontSize: 15, color: "#334155" }}>{section.title}</h3>
                  <div style={{ borderTop: "1px solid #EEF2F7", background: "#fff" }}>
                    {section.rows.map(([label, value]) => {
                      const ok = value === "확보됨" || value === "완료";
                      const warning = value === "확인 필요";
                      return (
                        <div key={label} style={{ display: "grid", gridTemplateColumns: "190px minmax(0, 1fr)", gap: 16, alignItems: "center", borderBottom: "1px solid #EEF2F7", padding: "10px 0" }}>
                          <span className={styles.subtle} style={{ fontSize: 13.5 }}>{label}</span>
                          {candidatePackageEditing ? (
                            <input
                              value={value}
                              onChange={(event) => updateCandidatePackageRow(section.title, label, event.target.value)}
                              style={{
                                border: "1px solid #E5EAF3",
                                borderRadius: 8,
                                background: "#F8FAFC",
                                padding: "8px 10px",
                                fontSize: 13,
                                fontWeight: 700,
                                color: "#111827",
                                maxWidth: 420,
                              }}
                            />
                          ) : ok || warning ? (
                            <span style={{
                              width: "fit-content",
                              padding: "3px 9px",
                              borderRadius: 8,
                              background: ok ? "#ECFDF5" : "#FFF7ED",
                              color: ok ? "#047857" : "#B45309",
                              fontWeight: 800,
                              fontSize: 13,
                            }}>
                              {value}
                            </span>
                          ) : (
                            <strong style={{ fontSize: 14 }}>{value}</strong>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              ))}
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, padding: 18, borderTop: "1px solid #EEF2F7" }}>
            <Button variant="primary" disabled={candidatePackageSaveState === "saving"} onClick={saveCandidatePackageDraft}>
              <Check size={15} /> {candidatePackageSaveState === "saving" ? "저장 중" : "패키지 저장"}
            </Button>
            <Button variant="secondary" onClick={() => setCandidatePackageEditing(true)}>수정하기</Button>
            <Button variant="secondary" onClick={() => onAction?.({ kind: "pdf-draft", label: "PDF 미리보기" })}>
              <FileText size={15} /> PDF 미리보기
            </Button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
function Scenario({ title, desc, tone }: { title: string; desc: string; tone: Tone }) {
  return <div className={cn(styles.panel, toneClass(tone))}><strong>{title}</strong><p>{desc}</p></div>;
}

function InfoTable({ title, rows }: { title: string; rows: string[][] }) {
  return (
    <section>
      <h2>{title}</h2>
      <div className={styles.infoTable}>{rows.map(([key, value]) => <div className={styles.infoRow} key={key}><span className={styles.subtle}>{key}</span><strong>{value}</strong></div>)}</div>
    </section>
  );
}

function Evidence({ source, text, grade }: { source: string; text: string; grade: string }) {
  return <div className={cn(styles.panel, styles.toneGray)}><div className={styles.badgeLine}><Badge>{grade}</Badge><span className={styles.subtle}>{source}</span></div><strong>{text}</strong></div>;
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><div className={styles.subtle}>{label}</div><strong>{value}</strong></div>;
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return <section><h3 className={styles.titleLine}><CheckCircle size={16} /> {title}</h3>{children}</section>;
}

function Timeline() {
  const items = ["체류만료일 확인", "누락 서류 감지", "이전 대화 기록 확인", "베트남어 메시지 초안 생성", "대표 승인 요청", "발송 예정 상태로 제한 적용"];
  return <div className={styles.timeline}>{items.map((item, index) => <div className={styles.row} key={item}><span className={cn(styles.dot, styles.toneGreen)} /><div><strong>{item}</strong><div className={styles.subtle}>2026-05-21 10:{10 + index * 3}</div></div></div>)}</div>;
}

