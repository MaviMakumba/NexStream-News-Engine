"use client";

import type { TrendingEntity } from "@/lib/types";

interface Props {
  entities: TrendingEntity[];
  onSelect?: (entity: string) => void;
}

// Small glyph per entity type so trending reads at a glance.
const TYPE_ICON: Record<string, string> = {
  person: "◉",
  organization: "▣",
  location: "⌖",
};

export function TrendingPills({ entities, onSelect }: Props) {
  if (!entities.length) return null;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {entities.map((e, i) => (
        <button
          key={e.name}
          onClick={() => onSelect?.(e.name)}
          className="pill"
          title={e.example_titles?.[0] ?? e.name}
          style={{ animationDelay: `${i * 40}ms`, animation: "fade-in 0.4s ease-out both" }}
        >
          <span style={{ color: "var(--accent)", fontSize: "0.7rem" }}>
            {TYPE_ICON[e.type ?? ""] ?? "↑"}
          </span>
          <span style={{ color: "var(--text)", fontWeight: 600 }}>{e.name}</span>
          <span style={{
            fontSize: "0.62rem", fontWeight: 700, color: "var(--accent)",
            background: "var(--accent-soft)", border: "1px solid var(--accent-line)",
            padding: "0 6px", borderRadius: 9999, minWidth: 18, textAlign: "center",
          }}>
            {e.count}
          </span>
        </button>
      ))}
    </div>
  );
}
