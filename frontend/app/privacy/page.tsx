"use client";

import { Navbar } from "@/components/Navbar";
import { useSettings } from "@/lib/settings-context";
import { PRIVACY_POLICY } from "@/lib/legal-content";

export default function PrivacyPage() {
  const { lang } = useSettings();
  const page = PRIVACY_POLICY[lang];

  return (
    <div style={{ minHeight: "100vh" }}>
      <Navbar />
      <div style={{ maxWidth: 720, margin: "0 auto", padding: "40px 20px 80px", display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: "1.6rem", fontWeight: 800, color: "var(--text)", marginBottom: 6 }}>
            {page.title}
          </h1>
          <p className="section-label">{page.updated}</p>
        </div>

        <div style={{
          background: "var(--neu-bg)", border: "1px solid var(--neu)", borderRadius: 12,
          padding: "12px 16px", fontSize: "0.84rem", color: "var(--text2)", lineHeight: 1.6,
        }}>
          {page.disclaimer}
        </div>

        {page.sections.map((s) => (
          <div key={s.heading} className="card">
            <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text)", marginBottom: 8 }}>
              {s.heading}
            </h2>
            <p style={{ fontSize: "0.88rem", color: "var(--text2)", lineHeight: 1.7 }}>
              {s.body}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
