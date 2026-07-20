"use client";

import { useCanvasScene } from "../useCanvasScene";
import { fxLayerStyle, rand, density } from "./shared";

interface Drop {
  x: number;
  y: number;
  len: number;
  speed: number;
  hue: string;
  w: number;
}

interface Bokeh {
  x: number;
  y: number;
  r: number;
  hue: string;
  phase: number;
}

interface State {
  drops: Drop[];
  lights: Bokeh[];
}

const HUES = ["255, 70, 200", "70, 220, 255", "180, 90, 255"];

/** Blade Runner — diagonal neon rain over a hazy bokeh cityscape. */
export function NeonRain() {
  const ref = useCanvasScene<State>({
    setup: (w, h) => {
      const d = density();
      const drops: Drop[] = Array.from({ length: Math.max(1, Math.round((w / 7) * d)) }, () => ({
        x: rand(0, w),
        y: rand(0, h),
        len: rand(12, 46),
        speed: rand(380, 760),
        hue: HUES[(Math.random() * HUES.length) | 0],
        w: rand(0.6, 1.6),
      }));
      const lights: Bokeh[] = Array.from({ length: Math.max(1, Math.round(28 * d)) }, () => ({
        x: rand(0, w),
        y: rand(h * 0.3, h),
        r: rand(20, 90),
        hue: HUES[(Math.random() * HUES.length) | 0],
        phase: rand(0, Math.PI * 2),
      }));
      return { drops, lights };
    },
    draw: ({ ctx, width, height, dt, time }, s) => {
      ctx.clearRect(0, 0, width, height);

      // Hazy bokeh city lights
      ctx.globalCompositeOperation = "lighter";
      for (const b of s.lights) {
        const pulse = 0.5 + 0.5 * Math.sin(time * 0.8 + b.phase);
        const g = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.r);
        g.addColorStop(0, `rgba(${b.hue}, ${0.10 * pulse})`);
        g.addColorStop(1, `rgba(${b.hue}, 0)`);
        ctx.fillStyle = g;
        ctx.fillRect(b.x - b.r, b.y - b.r, b.r * 2, b.r * 2);
      }

      // Diagonal neon rain (slight slant for wind)
      const slant = 0.18;
      for (const d of s.drops) {
        d.y += d.speed * dt;
        d.x += d.speed * slant * dt;
        if (d.y > height + d.len) {
          d.y = -d.len;
          d.x = rand(-40, width);
        }
        const grad = ctx.createLinearGradient(d.x, d.y, d.x - d.len * slant, d.y - d.len);
        grad.addColorStop(0, `rgba(${d.hue}, 0.9)`);
        grad.addColorStop(1, `rgba(${d.hue}, 0)`);
        ctx.strokeStyle = grad;
        ctx.lineWidth = d.w;
        ctx.beginPath();
        ctx.moveTo(d.x, d.y);
        ctx.lineTo(d.x - d.len * slant, d.y - d.len);
        ctx.stroke();
      }
      ctx.globalCompositeOperation = "source-over";
    },
  });

  return <canvas ref={ref} style={fxLayerStyle} aria-hidden />;
}
