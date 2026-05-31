"use client";

import { useCanvasScene } from "../useCanvasScene";
import { fxLayerStyle, rand } from "./shared";

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface State {
  nodes: Node[];
  anchor: { x: number; y: number };
}

/** Spider-Man — a living web: a constellation of threads from a top-corner anchor. */
export function WebStrands() {
  const ref = useCanvasScene<State>({
    setup: (w, h) => {
      const nodes: Node[] = Array.from({ length: 60 }, () => ({
        x: rand(0, w),
        y: rand(0, h),
        vx: rand(-12, 12),
        vy: rand(-12, 12),
      }));
      return { nodes, anchor: { x: w * 0.85, y: h * 0.12 } };
    },
    draw: ({ ctx, width, height, dt }, s) => {
      ctx.clearRect(0, 0, width, height);
      s.anchor.x = width * 0.85;
      s.anchor.y = height * 0.12;

      // Move nodes, bounce on edges
      for (const n of s.nodes) {
        n.x += n.vx * dt;
        n.y += n.vy * dt;
        if (n.x < 0 || n.x > width) n.vx *= -1;
        if (n.y < 0 || n.y > height) n.vy *= -1;
      }

      // Radial threads from the anchor
      ctx.strokeStyle = "rgba(220, 30, 40, 0.16)";
      ctx.lineWidth = 1;
      for (const n of s.nodes) {
        ctx.beginPath();
        ctx.moveTo(s.anchor.x, s.anchor.y);
        ctx.lineTo(n.x, n.y);
        ctx.stroke();
      }

      // Cross-links between nearby nodes (the web mesh)
      const maxD = 150;
      for (let i = 0; i < s.nodes.length; i++) {
        for (let j = i + 1; j < s.nodes.length; j++) {
          const a = s.nodes[i];
          const b = s.nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < maxD * maxD) {
            const alpha = (1 - Math.sqrt(d2) / maxD) * 0.28;
            ctx.strokeStyle = `rgba(60, 130, 255, ${alpha})`;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      // Glowing dew nodes
      for (const n of s.nodes) {
        ctx.beginPath();
        ctx.fillStyle = "rgba(230, 60, 70, 0.5)";
        ctx.arc(n.x, n.y, 1.6, 0, Math.PI * 2);
        ctx.fill();
      }

      // Anchor highlight
      const g = ctx.createRadialGradient(s.anchor.x, s.anchor.y, 0, s.anchor.x, s.anchor.y, 90);
      g.addColorStop(0, "rgba(230, 40, 50, 0.18)");
      g.addColorStop(1, "rgba(230, 40, 50, 0)");
      ctx.fillStyle = g;
      ctx.fillRect(s.anchor.x - 90, s.anchor.y - 90, 180, 180);
    },
  });

  return <canvas ref={ref} style={fxLayerStyle} aria-hidden />;
}
