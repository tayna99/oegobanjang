"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck } from "lucide-react";

import { getOperatorContext, setOperatorContext } from "../../lib/operatorContext";

export function ChangePasswordPage() {
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [userId, setUserId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const context = getOperatorContext();
    if (!context.userId) {
      router.replace("/login");
      return;
    }
    setUserId(context.userId);
  }, [router]);

  async function submit() {
    setError("");
    if (newPassword.length < 8) {
      setError("새 비밀번호는 8자 이상이어야 합니다.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("새 비밀번호 확인이 일치하지 않습니다.");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch("/api/v1/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, current_password: currentPassword, new_password: newPassword }),
      });
      if (!response.ok) {
        setError("현재 비밀번호를 확인해주세요.");
        return;
      }
      const data = await response.json();
      const context = getOperatorContext();
      setOperatorContext({ ...context, mustChangePassword: false });
      router.push(data.user?.role === "WORKER" ? "/worker" : "/dashboard");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="operator-login-page">
      <section className="operator-login-panel">
        <div className="operator-login-hero">
          <ShieldCheck size={24} aria-hidden="true" />
          <div>
            <h1>임시 비밀번호를 변경해주세요.</h1>
            <p>처음 로그인한 근로자 계정은 비밀번호 변경 후 사용할 수 있습니다.</p>
          </div>
        </div>
        <label className="operator-login-field">
          현재 임시 비밀번호
          <input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
        </label>
        <label className="operator-login-field">
          새 비밀번호
          <input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
        </label>
        <label className="operator-login-field">
          새 비밀번호 확인
          <input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
        </label>
        {error ? <p style={{ color: "#DC2626", fontSize: 13, fontWeight: 700 }}>{error}</p> : null}
        <button className="operator-login-submit" disabled={loading || !userId} onClick={submit} type="button">
          비밀번호 변경 후 시작
        </button>
      </section>
    </main>
  );
}
