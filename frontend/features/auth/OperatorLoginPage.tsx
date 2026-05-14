"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BriefcaseBusiness, ShieldCheck } from "lucide-react";

import {
  defaultOperatorContext,
  setOperatorContext,
  type OperatorContext,
  type OperatorRole,
} from "../../lib/operatorContext";

const roleOptions: Array<{ label: string; value: OperatorRole; description: string }> = [
  { label: "담당자", value: "manager", description: "브리핑 확인, 승인 요청, 초안 검토" },
  { label: "관리자", value: "admin", description: "CSV 원천 데이터와 운영 지표 관리" },
  { label: "조회자", value: "viewer", description: "대시보드와 기록 조회 중심" },
];

export function OperatorLoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [companyId, setCompanyId] = useState(defaultOperatorContext.companyId);
  const [userId, setUserId] = useState(defaultOperatorContext.userId);
  const [role, setRole] = useState<OperatorRole>(defaultOperatorContext.role);

  const returnTo = useMemo(() => {
    const from = searchParams.get("from");
    return from && from.startsWith("/") ? from : "/dashboard";
  }, [searchParams]);

  function submit() {
    const context: OperatorContext = {
      companyId: companyId.trim() || defaultOperatorContext.companyId,
      userId: userId.trim() || defaultOperatorContext.userId,
      role,
    };
    setOperatorContext(context);
    router.push(returnTo);
  }

  return (
    <main className="operator-login-page">
      <section className="operator-login-panel">
        <div className="operator-login-brand">
          <span>반</span>
          <div>
            <strong>외고반장</strong>
            <p>운영자 컨텍스트 선택</p>
          </div>
        </div>

        <div className="operator-login-hero">
          <ShieldCheck size={24} aria-hidden="true" />
          <div>
            <h1>실제 인증이 아닌 MVP 작업 컨텍스트입니다.</h1>
            <p>선택한 회사와 역할은 프론트 API 헤더에만 반영됩니다.</p>
          </div>
        </div>

        <label className="operator-login-field">
          Company ID
          <input value={companyId} onChange={(event) => setCompanyId(event.target.value)} />
        </label>

        <label className="operator-login-field">
          User ID
          <input value={userId} onChange={(event) => setUserId(event.target.value)} />
        </label>

        <div className="operator-role-grid" aria-label="역할 선택">
          {roleOptions.map((option) => (
            <button
              className={role === option.value ? "active" : ""}
              key={option.value}
              onClick={() => setRole(option.value)}
              type="button"
            >
              <strong>{option.label}</strong>
              <span>{option.description}</span>
            </button>
          ))}
        </div>

        <button className="operator-login-submit" onClick={submit} type="button">
          <BriefcaseBusiness size={16} aria-hidden="true" />
          컨텍스트 저장 후 이동
        </button>
      </section>
    </main>
  );
}
