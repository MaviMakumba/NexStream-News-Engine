"use client";

import { useCanvasScene } from "../useCanvasScene";
import { fxLayerStyle, rand } from "./shared";

interface Grain {
  x: number;
  y: number;
  r: number;
  vx: number;
  drift: number;
  phase: number;
  a: number;
}

interface State {
  grains: Grain[];
}

/** Dune — wind-driven sand grains drifting across a heat-haze desert. */
export function SandStorm() {
  const ref = useCanvasScene<State>({
    setup: (w, h) => {
      const grains: Grain[] = Array.from({ length: Math.round(w / 3) }, () => ({
        x: rand(0, w),
        y: rand(0, h),
        r: rand(0.4, 2.0),
        vx: rand(120, 320),
        drift: rand(6, 22),
        phase: rand(0, Math.PI * 2),
        a: rand(0.06, 0.4),
      }));
      return { grains };
    },
    draw: ({ ctx, width, height, dt, time }, s) => {
      ctx.clearRect(0, 0, width, height);

      // Rolling haze bands sweeping right
      ctx.globalCompositeOperation = "lighter";
      for (let i = 0; i < 3; i++) {
        const y = height * (0.25 + i * 0.25);
        const x = ((time * (40 + i * 25)) % (width + 600)) - 300;
        const g = ctx.createRadialGradient(x, y, 0, x, y, 360);
        g.addColorStop(0, `rgba(214, 158, 78, ${0.05 - i * 0.01})`);
        g.addColorStop(1, "rgba(214, 158, 78, 0)");
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, width, height);
      }

      // Sand grains
      for (const gr of s.grains) {
        gr.x += gr.vx * dt;
        gr.y += Math.sin(time * 1.5 + gr.phase) * gr.drift * dt;
        if (gr.x > width + 6) { gr.x = -6; gr.y = rand(0, height); }
        ctx.beginPath();
        ctx.fillStyle = `rgba(232, 196, 128, ${gr.a})`;
        ctx.arc(gr.x, gr.y, gr.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalCompositeOperation = "source-over";

      // Warm low vignette (dune horizon glow)
      const vg = ctx.createLinearGradient(0, height, 0, height * 0.4);
      vg.addColorStop(0, "rgba(120, 70, 20, 0.30)");
      vg.addColorStop(1, "rgba(120, 70, 20, 0)");
      ctx.fillStyle = vg;
      ctx.fillRect(0, 0, width, height);
    },
  });

  return <canvas ref={ref} style={fxLayerStyle} aria-hidden />;
}
