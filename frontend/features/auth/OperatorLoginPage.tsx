"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BriefcaseBusiness, ShieldCheck, UserRound } from "lucide-react";

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
    label: "근로자",
    email: "potenup3@gmail.com",
    password: "worker1234",
    description: "본인 요청 서류와 회사 메시지 확인",
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
      const role = data.user.role === "WORKER" ? "worker" : ("admin" as OperatorRole);
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

        <div className="operator-login-hero">
          <ShieldCheck size={24} aria-hidden="true" />
          <div>
            <h1>DB 사용자 정보로 역할을 분리합니다.</h1>
            <p>관리자는 기존 운영 화면으로, 근로자는 본인 포털로 이동합니다.</p>
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
