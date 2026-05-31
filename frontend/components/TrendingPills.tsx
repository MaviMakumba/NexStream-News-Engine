"use client";

import type { TrendingEntity } from "@/lib/types";

interface Props {
  entities: TrendingEntity[];
  onSelect?: (entity: string) => void;
}

export function TrendingPills({ entities, onSelect }: Props) {
  if (!entities.length) return null;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {entities.map((e, i) => (
        <button
          key={e.entity}
          onClick={() => onSelect?.(e.entity)}
          className="pill"
          style={{
            animationDelay: `${i * 40}ms`,
            animation: "fade-in 0.4s ease-out both",
          }}
        >
          <span style={{ color: "var(--accent)", fontSize: "0.65rem" }}>↑</span>
          <span style={{ color: "var(--text)" }}>{e.entity}</span>
          <span style={{
            fontSize: "0.65rem",
            color: "var(--text3)",
            background: "rgba(0,0,0,.2)",
            padding: "1px 5px",
            borderRadius: 4,
          }}>
            {e.count}
          </span>
        </button>
      ))}
    </div>
  );
}
