"use client";

import { useCanvasScene } from "../useCanvasScene";
import { fxLayerStyle, rand, density } from "./shared";

interface Ember {
  x: number;
  y: number;
  vy: number;
  drift: number;
  phase: number;
  r: number;
  a: number;
}

interface State {
  embers: Ember[];
}

/** Wolfenstein — dieselpunk: rising embers, heavy iron-red haze, scanlines. */
export function EmberHaze() {
  const ref = useCanvasScene<State>({
    setup: (w, h) => {
      const embers: Ember[] = Array.from({ length: Math.max(1, Math.round(90 * density())) }, () => ({
        x: rand(0, w),
        y: rand(0, h),
        vy: rand(-60, -22),
        drift: rand(8, 26),
        phase: rand(0, Math.PI * 2),
        r: rand(0.6, 2.4),
        a: rand(0.2, 0.8),
      }));
      return { embers };
    },
    draw: ({ ctx, width, height, dt, time }, s) => {
      ctx.clearRect(0, 0, width, height);

      // Iron-red bottom furnace glow
      const glow = ctx.createLinearGradient(0, height, 0, height * 0.35);
      glow.addColorStop(0, "rgba(150, 30, 20, 0.32)");
      glow.addColorStop(1, "rgba(150, 30, 20, 0)");
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, width, height);

      // Rising embers
      ctx.globalCompositeOperation = "lighter";
      for (const e of s.embers) {
        e.y += e.vy * dt;
        e.x += Math.sin(time * 1.2 + e.phase) * e.drift * dt;
        if (e.y < -6) { e.y = height + 6; e.x = rand(0, width); }
        const flick = 0.6 + 0.4 * Math.sin(time * 8 + e.phase);
        ctx.beginPath();
        ctx.fillStyle = `rgba(255, ${120 + Math.floor(60 * flick)}, 40, ${e.a * flick})`;
        ctx.arc(e.x, e.y, e.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalCompositeOperation = "source-over";

      // CRT scanlines
      ctx.fillStyle = "rgba(0, 0, 0, 0.10)";
      for (let y = 0; y < height; y += 3) ctx.fillRect(0, y, width, 1);

      // Dark vignette
      const vg = ctx.createRadialGradient(
        width / 2, height / 2, Math.min(width, height) * 0.2,
        width / 2, height / 2, Math.max(width, height) * 0.75,
      );
      vg.addColorStop(0, "rgba(0,0,0,0)");
      vg.addColorStop(1, "rgba(0,0,0,0.5)");
      ctx.fillStyle = vg;
      ctx.fillRect(0, 0, width, height);
    },
  });

  return <canvas ref={ref} style={fxLayerStyle} aria-hidden />;
}
