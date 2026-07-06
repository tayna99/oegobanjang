"use client";

import { useState } from "react";
import { Upload } from "lucide-react";

import {
  importDailyBriefingSourceCsv,
  uploadDailyBriefingSourceCsv,
  validateDailyBriefingSourceCsv,
} from "../../lib/api";
import type {
  DailyBriefingCsvImportPayload,
  DailyBriefingCsvValidationReport,
  DailyBriefingImportResult,
} from "../../types/dailyBriefing";

const samplePayload: Required<DailyBriefingCsvImportPayload> = {
  companies_csv:
    "company_id,company_name,timezone,quota_limit,current_foreign_worker_count\ncompany_admin_csv,Admin CSV Company,Asia/Seoul,2,1\n",
  workers_csv:
    "worker_id,company_id,display_name_masked,raw_name,visa_expiry_date,contract_end_date\nworker_admin_csv_001,company_admin_csv,[WORKER_ADMIN_CSV_001],Admin Private Name,2026-05-18,2026-06-30\n",
  documents_csv:
    "worker_id,document_type,status,required,due_date\nworker_admin_csv_001,passport_copy,missing,true,2026-05-09\n",
  candidates_csv:
    "candidate_id,company_id,display_name_masked,raw_name,status\ncandidate_admin_001,company_admin_csv,[CANDIDATE_ADMIN_001],Candidate Private Name,registered\n",
  candidate_documents_csv:
    "candidate_id,document_type,status,required,due_date\ncandidate_admin_001,passport_copy,missing,true,2026-05-20\n",
  reporting_events_csv:
    "event_id,company_id,worker_id,event_type,occurred_at,discovered_at,reporting_due_date,reported_at,status\nreport_admin_001,company_admin_csv,worker_admin_csv_001,employment_change,2026-05-01,2026-05-02,2026-05-10,,open\n",
  citations_csv:
    "citation_id,title,source_type,source,ingest_at,document_id,chunk_id,chunk_version,retrieved_at,source_url\ncit_visa_expiry,Admin visa citation,official,Admin source,2026-05-01T00:00:00+09:00,doc_visa_expiry,chunk_visa_expiry,2026-05-01,2026-05-08T00:00:00+09:00,mock://admin\n",
  user_company_access_csv:
    "user_id,company_id,role\nmanager_admin_csv,company_admin_csv,manager\n",
};

const csvFields: Array<{ key: keyof DailyBriefingCsvImportPayload; label: string; sourceType: string }> = [
  { key: "companies_csv", label: "Companies CSV", sourceType: "companies" },
  { key: "workers_csv", label: "Workers CSV", sourceType: "workers" },
  { key: "documents_csv", label: "Documents CSV", sourceType: "documents" },
  { key: "citations_csv", label: "Citations CSV", sourceType: "citations" },
  { key: "candidates_csv", label: "Candidates CSV", sourceType: "candidates" },
  { key: "candidate_documents_csv", label: "Candidate Documents CSV", sourceType: "candidate_documents" },
  { key: "reporting_events_csv", label: "Reporting Events CSV", sourceType: "reporting_events" },
  { key: "user_company_access_csv", label: "User Company Access CSV", sourceType: "user_company_access" },
];

export function CsvSourceImportPanel() {
  const [payload, setPayload] = useState<DailyBriefingCsvImportPayload>(samplePayload);
  const [uploadSourceType, setUploadSourceType] = useState(csvFields[0].sourceType);
  const [validationReport, setValidationReport] = useState<DailyBriefingCsvValidationReport | null>(null);
  const [importResult, setImportResult] = useState<DailyBriefingImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateField(key: keyof DailyBriefingCsvImportPayload, value: string) {
    setPayload((current) => ({ ...current, [key]: value }));
  }

  async function validate() {
    setError(null);
    try {
      setValidationReport(await validateDailyBriefingSourceCsv(payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV validation failed");
    }
  }

  async function importRows() {
    setError(null);
    try {
      setImportResult(await importDailyBriefingSourceCsv(payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV import failed");
    }
  }

  async function upload(file: File | null) {
    if (!file) return;
    setError(null);
    try {
      setImportResult(await uploadDailyBriefingSourceCsv(uploadSourceType, file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV upload failed");
    }
  }

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-10">
      <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">
          Daily Briefing Source Import
        </p>
        <h1 className="mt-3 text-4xl font-black tracking-tight text-slate-950">
          CSV 원천 데이터 검증과 임포트
        </h1>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-600">
          운영자 전용 화면입니다. 검증 리포트는 원문 민감정보를 되돌려주지 않고, 실제 외부 발송이나 제출도 수행하지 않습니다.
        </p>
        {error ? <p className="mt-4 text-sm font-bold text-red-700">{error}</p> : null}
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-2 text-sm font-bold text-slate-700">
            Upload source type
            <select
              className="rounded-2xl border border-slate-200 px-4 py-3 text-slate-950"
              onChange={(event) => setUploadSourceType(event.target.value)}
              value={uploadSourceType}
            >
              {csvFields.map((field) => (
                <option key={field.sourceType} value={field.sourceType}>{field.sourceType}</option>
              ))}
            </select>
          </label>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-slate-300 px-5 py-3 text-sm font-bold text-slate-700">
            <Upload size={16} aria-hidden="true" />
            CSV 파일 업로드
            <input
              accept=".csv,text/csv"
              className="hidden"
              onChange={(event) => upload(event.target.files?.[0] ?? null)}
              type="file"
            />
          </label>
          <button className="rounded-full bg-slate-950 px-5 py-3 text-sm font-bold text-white" onClick={validate} type="button">
            Validate CSV rows
          </button>
          <button className="rounded-full bg-slate-950 px-5 py-3 text-sm font-bold text-white" onClick={importRows} type="button">
            Import CSV rows
          </button>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        {csvFields.map((field) => (
          <label className="block rounded-3xl border border-slate-200 bg-white p-5 shadow-sm" key={field.key}>
            <span className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500">{field.label}</span>
            <textarea
              className="mt-3 min-h-36 w-full rounded-2xl border border-slate-200 p-3 font-mono text-xs text-slate-950"
              onChange={(event) => updateField(field.key, event.target.value)}
              value={payload[field.key] ?? ""}
            />
          </label>
        ))}
      </div>

      {validationReport ? (
        <pre className="overflow-auto rounded-3xl bg-amber-50 p-5 text-xs">
          {JSON.stringify(validationReport, null, 2)}
        </pre>
      ) : null}

      {importResult ? (
        <pre className="overflow-auto rounded-3xl bg-slate-50 p-5 text-xs">
          {JSON.stringify(importResult.upserted_counts, null, 2)}
        </pre>
      ) : null}
    </main>
  );
}
