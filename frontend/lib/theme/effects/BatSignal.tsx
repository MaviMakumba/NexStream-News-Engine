"use client";

import { useCanvasScene } from "../useCanvasScene";
import { fxLayerStyle, rand } from "./shared";

interface Drop {
  x: number;
  y: number;
  len: number;
  speed: number;
}

interface State {
  drops: Drop[];
}

/** Batman — a slow sweeping searchlight over Gotham fog with cold rain. */
export function BatSignal() {
  const ref = useCanvasScene<State>({
    setup: (w, h) => {
      const drops: Drop[] = Array.from({ length: Math.round(w / 10) }, () => ({
        x: rand(0, w),
        y: rand(0, h),
        len: rand(10, 26),
        speed: rand(420, 720),
      }));
      return { drops };
    },
    draw: ({ ctx, width, height, dt, time }, s) => {
      ctx.clearRect(0, 0, width, height);

      // Drifting fog
      ctx.globalCompositeOperation = "lighter";
      for (let i = 0; i < 3; i++) {
        const x = width * 0.5 + Math.sin(time * 0.12 + i * 2) * width * 0.3;
        const y = height * (0.4 + i * 0.2);
        const g = ctx.createRadialGradient(x, y, 0, x, y, Math.min(width, height) * 0.45);
        g.addColorStop(0, "rgba(120, 140, 170, 0.04)");
        g.addColorStop(1, "rgba(120, 140, 170, 0)");
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, width, height);
      }

      // Sweeping searchlight cone from bottom-center
      const baseX = width * 0.5;
      const baseY = height + 40;
      const sweep = Math.sin(time * 0.25) * 0.5; // radians
      const aim = -Math.PI / 2 + sweep;
      const reach = Math.max(width, height) * 1.1;
      const spread = 0.16;
      const tipX = baseX + Math.cos(aim) * reach;
      const tipY = baseY + Math.sin(aim) * reach;
      const lx = baseX + Math.cos(aim - spread) * reach;
      const ly = baseY + Math.sin(aim - spread) * reach;
      const rx = baseX + Math.cos(aim + spread) * reach;
      const ry = baseY + Math.sin(aim + spread) * reach;
      const cone = ctx.createLinearGradient(baseX, baseY, tipX, tipY);
      cone.addColorStop(0, "rgba(220, 200, 120, 0.12)");
      cone.addColorStop(1, "rgba(220, 200, 120, 0)");
      ctx.fillStyle = cone;
      ctx.beginPath();
      ctx.moveTo(baseX, baseY);
      ctx.lineTo(lx, ly);
      ctx.lineTo(rx, ry);
      ctx.closePath();
      ctx.fill();

      // Pale moon disc at the cone tip
      const moon = ctx.createRadialGradient(tipX, tipY, 0, tipX, tipY, 120);
      moon.addColorStop(0, "rgba(230, 220, 150, 0.10)");
      moon.addColorStop(1, "rgba(230, 220, 150, 0)");
      ctx.fillStyle = moon;
      ctx.fillRect(tipX - 120, tipY - 120, 240, 240);
      ctx.globalCompositeOperation = "source-over";

      // Cold rain
      ctx.strokeStyle = "rgba(150, 170, 200, 0.28)";
      ctx.lineWidth = 1;
      for (const d of s.drops) {
        d.y += d.speed * dt;
        d.x -= d.speed * 0.08 * dt;
        if (d.y > height + d.len) { d.y = -d.len; d.x = rand(0, width + 60); }
        ctx.beginPath();
        ctx.moveTo(d.x, d.y);
        ctx.lineTo(d.x - d.len * 0.08, d.y - d.len);
        ctx.stroke();
      }
    },
  });

  return <canvas ref={ref} style={fxLayerStyle} aria-hidden />;
}
