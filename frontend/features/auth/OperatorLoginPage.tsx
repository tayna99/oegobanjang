"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BriefcaseBusiness, UserRound } from "lucide-react";

import { defaultOperatorContext, setOperatorContext, type OperatorRole } from "../../lib/operatorContext";

type LoginUser = {
  id: string;
  email?: string;
  display_name?: string;
  role: "ADMIN" | "WORKER" | string;
  company_id?: string;
  worker_id?: string | null;
  must_change_password?: boolean;
};

type LoginResponse = {
  user: LoginUser;
  access_token: string;
  redirect_to: string;
};

const quickAccounts = [
  {
    label: "관리자",
    email: "admin@oegobanjang.local",
    password: "admin1234",
    description: "오늘 할 일, 채용 준비, 근로자, 메시지 관리",
  },
  {
    label: "행정사",
    email: "expert@oegobanjang.local",
    password: "expert1234",
    description: "행정사 검토 자료와 승인 대기 업무 확인",
  },
  {
    label: "Nguyen V.",
    email: "potenup3@gmail.com",
    password: "worker1234",
    description: "체류만료 경과 · 서류 제출 완료 케이스",
  },
  {
    label: "Dang T.",
    email: "dang.thi.g@worker.oegobanjang.test",
    password: "worker1234",
    description: "체류만료 경과 · 서류 보완 필요 케이스",
  },
  {
    label: "Tran H.",
    email: "tran.hoa.f@worker.oegobanjang.test",
    password: "worker1234",
    description: "체류만료 임박 · 행정사 검토 케이스",
  },
  {
    label: "Pham T.",
    email: "pham.t.demo@gmail.com",
    password: "worker1234",
    description: "체류만료 임박 · 서류 보완 필요 케이스",
  },
  {
    label: "Vu V.",
    email: "vu.van.h@worker.oegobanjang.test",
    password: "worker1234",
    description: "체류만료 D-30 · 승인 대기 케이스",
  },
  {
    label: "Le T.",
    email: "le.thi.d@worker.oegobanjang.test",
    password: "worker1234",
    description: "확인 필요 · 낮은 우선순위 케이스",
  },
];

export function OperatorLoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState(quickAccounts[0].email);
  const [password, setPassword] = useState(quickAccounts[0].password);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const returnTo = useMemo(() => {
    const from = searchParams.get("from");
    return from && from.startsWith("/") ? from : "";
  }, [searchParams]);

  async function submit() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        setError("이메일 또는 비밀번호를 확인해주세요.");
        return;
      }
      const data = (await response.json()) as LoginResponse;
      const role = data.user.role === "WORKER" ? "worker" : data.user.role === "EXPERT" ? "expert" : ("admin" as OperatorRole);
      setOperatorContext({
        companyId: data.user.company_id || defaultOperatorContext.companyId,
        userId: data.user.id,
        role,
        email: data.user.email,
        displayName: data.user.display_name,
        workerId: data.user.worker_id,
        accessToken: data.access_token,
        mustChangePassword: Boolean(data.user.must_change_password),
      });
      router.push(returnTo || data.redirect_to || "/dashboard");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="operator-login-page">
      <section className="operator-login-panel">
        <div className="operator-login-brand">
          <span>반</span>
          <div>
            <strong>외고반장</strong>
            <p>관리자/근로자 로그인</p>
          </div>
        </div>

        <label className="operator-login-field">
          이메일
          <input autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>

        <label className="operator-login-field">
          비밀번호
          <input
            autoComplete="current-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        <div className="operator-role-grid" aria-label="데모 계정 선택">
          {quickAccounts.map((account) => (
            <button
              className={email === account.email ? "active" : ""}
              key={account.email}
              onClick={() => {
                setEmail(account.email);
                setPassword(account.password);
              }}
              type="button"
            >
              <strong>{account.label}</strong>
              <span>{account.email}</span>
              <span>{account.description}</span>
            </button>
          ))}
        </div>

        {error ? <p style={{ color: "#DC2626", fontSize: 13, fontWeight: 700 }}>{error}</p> : null}

        <button className="operator-login-submit" disabled={loading} onClick={submit} type="button">
          {email === quickAccounts[1].email ? <UserRound size={16} aria-hidden="true" /> : <BriefcaseBusiness size={16} aria-hidden="true" />}
          로그인
        </button>
      </section>
    </main>
  );
}
