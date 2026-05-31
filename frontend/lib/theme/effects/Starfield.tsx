"use client";

import { useCanvasScene } from "../useCanvasScene";
import { fxLayerStyle, rand } from "./shared";

interface Star {
  x: number;
  y: number;
  z: number;
  pz: number;
}

interface State {
  stars: Star[];
  cx: number;
  cy: number;
}

/** Star Wars — a gentle hyperspace starfield warping out from center. */
export function Starfield() {
  const ref = useCanvasScene<State>({
    setup: (w, h) => {
      const stars: Star[] = Array.from({ length: 520 }, () => {
        const z = rand(0, w);
        return { x: rand(-w, w), y: rand(-h, h), z, pz: z };
      });
      return { stars, cx: w / 2, cy: h / 2 };
    },
    draw: ({ ctx, width, height, dt }, s) => {
      s.cx = width / 2;
      s.cy = height / 2;
      ctx.fillStyle = "rgba(2, 3, 8, 0.35)";
      ctx.fillRect(0, 0, width, height);

      const speed = width * 0.35;
      for (const st of s.stars) {
        st.pz = st.z;
        st.z -= speed * dt;
        if (st.z < 1) {
          st.x = rand(-width, width);
          st.y = rand(-height, height);
          st.z = width;
          st.pz = st.z;
        }
        const sx = s.cx + (st.x / st.z) * width;
        const sy = s.cy + (st.y / st.z) * width;
        const px = s.cx + (st.x / st.pz) * width;
        const py = s.cy + (st.y / st.pz) * width;
        const size = Math.max(0.4, (1 - st.z / width) * 2.2);
        const a = Math.min(1, (1 - st.z / width) * 1.4);
        ctx.strokeStyle = `rgba(220, 232, 255, ${a})`;
        ctx.lineWidth = size;
        ctx.beginPath();
        ctx.moveTo(px, py);
        ctx.lineTo(sx, sy);
        ctx.stroke();
      }

      // Faint blue core glow
      const g = ctx.createRadialGradient(s.cx, s.cy, 0, s.cx, s.cy, Math.max(width, height) * 0.4);
      g.addColorStop(0, "rgba(90, 150, 255, 0.05)");
      g.addColorStop(1, "rgba(90, 150, 255, 0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, width, height);
    },
  });

  return <canvas ref={ref} style={fxLayerStyle} aria-hidden />;
}
