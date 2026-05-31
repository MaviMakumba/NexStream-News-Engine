"use client";

import { useCanvasScene } from "../useCanvasScene";
import { fxLayerStyle } from "./shared";

const GLYPHS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈ0123456789:.=*+-<>".split("");

interface Column {
  y: number;
  speed: number;
  glyphs: string[];
}

interface State {
  fontSize: number;
  cols: Column[];
}

/** The Matrix — falling green code rain with a fading trail. */
export function MatrixRain() {
  const ref = useCanvasScene<State>({
    setup: (w) => {
      const fontSize = 16;
      const count = Math.ceil(w / fontSize);
      const cols: Column[] = Array.from({ length: count }, () => ({
        y: Math.random() * -60,
        speed: 6 + Math.random() * 10,
        glyphs: Array.from({ length: 30 }, () => GLYPHS[(Math.random() * GLYPHS.length) | 0]),
      }));
      return { fontSize, cols };
    },
    draw: ({ ctx, width, height, dt }, s) => {
      // Trail fade — translucent black over the previous frame.
      ctx.fillStyle = "rgba(2, 8, 4, 0.10)";
      ctx.fillRect(0, 0, width, height);
      ctx.font = `${s.fontSize}px "Share Tech Mono", monospace`;
      ctx.textBaseline = "top";

      for (let i = 0; i < s.cols.length; i++) {
        const col = s.cols[i];
        col.y += col.speed * dt;
        const headRow = Math.floor(col.y);
        const x = i * s.fontSize;
        // randomly mutate a glyph so the stream shimmers
        if (Math.random() < 0.04) col.glyphs[headRow % col.glyphs.length] = GLYPHS[(Math.random() * GLYPHS.length) | 0];

        for (let t = 0; t < 14; t++) {
          const row = headRow - t;
          if (row < 0) continue;
          const y = row * s.fontSize;
          if (y > height) continue;
          const g = col.glyphs[row % col.glyphs.length];
          if (t === 0) {
            ctx.fillStyle = "#d7ffe6";
            ctx.shadowColor = "#22ff88";
            ctx.shadowBlur = 10;
          } else {
            ctx.shadowBlur = 0;
            ctx.fillStyle = `rgba(34, 255, 120, ${Math.max(0, 0.55 - t * 0.045)})`;
          }
          ctx.fillText(g, x, y);
        }
        ctx.shadowBlur = 0;

        if (headRow * s.fontSize - 14 * s.fontSize > height) {
          col.y = Math.random() * -40;
          col.speed = 6 + Math.random() * 10;
        }
      }
    },
  });

  return <canvas ref={ref} style={fxLayerStyle} aria-hidden />;
}
