export default function HomePage() {
  return (
    <main style={{
      minHeight: "100vh",
      display: "grid",
      placeItems: "center",
      background: "#F4F7FB",
      color: "#0F172A",
      padding: 24,
    }}>
      <section style={{
        width: "min(420px, 100%)",
        border: "1px solid #D8E0EC",
        borderRadius: 18,
        background: "#fff",
        padding: 28,
        textAlign: "center",
        boxShadow: "0 20px 60px rgba(15, 23, 42, 0.08)",
      }}>
        <div style={{
          width: 46,
          height: 46,
          borderRadius: 13,
          background: "#2563EB",
          color: "#fff",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          fontWeight: 900,
          marginBottom: 16,
        }}>반</div>
        <h1 style={{ margin: 0, fontSize: 28 }}>외고반장</h1>
        <p style={{ margin: "12px 0 22px", color: "#64748B" }}>로그인 후 사용 가능합니다.</p>
        <a href="/login" style={{
          display: "inline-flex",
          justifyContent: "center",
          alignItems: "center",
          width: "100%",
          height: 44,
          borderRadius: 10,
          background: "#2563EB",
          color: "#fff",
          fontWeight: 900,
          textDecoration: "none",
        }}>로그인</a>
      </section>
    </main>
  );
}
