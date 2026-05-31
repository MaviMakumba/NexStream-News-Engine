"use client";

import { useCanvasScene } from "../useCanvasScene";
import { fxLayerStyle, rand } from "./shared";

interface Mote {
  x: number;
  y: number;
  r: number;
  vx: number;
  vy: number;
  a: number;
}

interface State {
  noise: HTMLCanvasElement;
  motes: Mote[];
}

/** The Godfather — warm film grain, drifting smoke, golden dust motes, vignette. */
export function FilmGrain() {
  const ref = useCanvasScene<State>({
    setup: (w, h) => {
      // Low-res noise tile, regenerated each frame and scaled up cheaply.
      const noise = document.createElement("canvas");
      noise.width = 160;
      noise.height = 90;
      const motes: Mote[] = Array.from({ length: 26 }, () => ({
        x: rand(0, w),
        y: rand(0, h),
        r: rand(0.5, 2.2),
        vx: rand(-6, 6),
        vy: rand(-10, -2),
        a: rand(0.05, 0.3),
      }));
      return { noise, motes };
    },
    draw: ({ ctx, width, height, dt, time }, s) => {
      ctx.clearRect(0, 0, width, height);

      // Warm vignette base
      const vg = ctx.createRadialGradient(
        width * 0.5, height * 0.42, Math.min(width, height) * 0.1,
        width * 0.5, height * 0.5, Math.max(width, height) * 0.75,
      );
      vg.addColorStop(0, "rgba(40, 26, 10, 0)");
      vg.addColorStop(1, "rgba(8, 4, 2, 0.55)");
      ctx.fillStyle = vg;
      ctx.fillRect(0, 0, width, height);

      // Slow drifting smoke — two soft golden plumes
      ctx.globalCompositeOperation = "lighter";
      for (let i = 0; i < 2; i++) {
        const cx = width * (0.3 + 0.4 * i) + Math.sin(time * 0.15 + i) * width * 0.12;
        const cy = height * 0.7 + Math.cos(time * 0.1 + i) * height * 0.1;
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.min(width, height) * 0.5);
        g.addColorStop(0, "rgba(196, 142, 58, 0.06)");
        g.addColorStop(1, "rgba(196, 142, 58, 0)");
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, width, height);
      }

      // Golden dust motes
      for (const m of s.motes) {
        m.x += m.vx * dt;
        m.y += m.vy * dt;
        if (m.y < -10) { m.y = height + 10; m.x = rand(0, width); }
        if (m.x < -10) m.x = width + 10;
        if (m.x > width + 10) m.x = -10;
        ctx.beginPath();
        ctx.fillStyle = `rgba(228, 188, 110, ${m.a})`;
        ctx.arc(m.x, m.y, m.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalCompositeOperation = "source-over";

      // Animated film grain
      const nctx = s.noise.getContext("2d")!;
      const img = nctx.createImageData(s.noise.width, s.noise.height);
      const d = img.data;
      for (let i = 0; i < d.length; i += 4) {
        const v = (Math.random() * 255) | 0;
        d[i] = d[i + 1] = d[i + 2] = v;
        d[i + 3] = 18; // grain opacity
      }
      nctx.putImageData(img, 0, 0);
      ctx.globalAlpha = 0.5;
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(s.noise, 0, 0, width, height);
      ctx.imageSmoothingEnabled = true;
      ctx.globalAlpha = 1;
    },
  });

  return <canvas ref={ref} style={fxLayerStyle} aria-hidden />;
}
