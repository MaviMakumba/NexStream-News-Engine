// Kimlik doğrulama (/auth/me) çözülene kadar gösterilen ortak yükleme ekranı —
// DashboardShell ve giriş gerektiren diğer sayfalarda tutarlı bir "boş beyaz
// flaş" yerine markalı bir bekleme durumu sağlar.
export function AuthLoadingScreen() {
  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
        <div className="gradient-text" style={{ fontSize: "1.4rem", fontWeight: 800 }}>NexStream</div>
        <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent)",
                      animation: "glow-pulse 1.5s ease-in-out infinite" }} />
      </div>
    </div>
  );
}
