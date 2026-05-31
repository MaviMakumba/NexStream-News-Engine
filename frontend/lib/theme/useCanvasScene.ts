"use client";

import { useEffect, useRef } from "react";

export interface SceneContext {
  ctx: CanvasRenderingContext2D;
  /** CSS pixel width (already DPR-normalized via ctx transform). */
  width: number;
  /** CSS pixel height. */
  height: number;
  /** Seconds since the scene started. */
  time: number;
  /** Seconds since the previous frame (clamped, good for motion). */
  dt: number;
}

export interface SceneHooks<S> {
  /** Build mutable scene state once we know the canvas size. */
  setup: (width: number, height: number) => S;
  /** Paint one frame. Mutate `state` freely. */
  draw: (scene: SceneContext, state: S) => void;
  /** Rebuild state on resize? Defaults to true. */
  resetOnResize?: boolean;
}

/**
 * Drives a full-bleed <canvas> animation with a single rAF loop.
 *
 * Centralizes the boring-but-critical parts every effect needs:
 *  - device-pixel-ratio scaling so lines stay crisp on retina
 *  - pause when the tab is hidden (saves battery/CPU)
 *  - honors `prefers-reduced-motion` by painting a single static frame
 *  - resize handling + teardown
 *
 * Individual effects only provide `setup` (state) and `draw` (one frame).
 */
export function useCanvasScene<S>({ setup, draw, resetOnResize = true }: SceneHooks<S>) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  // Keep the latest callbacks without restarting the loop on every render.
  const setupRef = useRef(setup);
  const drawRef = useRef(draw);
  setupRef.current = setup;
  drawRef.current = draw;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

    let width = 0;
    let height = 0;
    let state: S | undefined;
    let raf = 0;
    let last = performance.now();
    let start = last;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = Math.max(1, Math.floor(width * dpr));
      canvas.height = Math.max(1, Math.floor(height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (resetOnResize || state === undefined) state = setupRef.current(width, height);
    };

    const frame = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      drawRef.current({ ctx, width, height, time: (now - start) / 1000, dt }, state as S);
      raf = requestAnimationFrame(frame);
    };

    const onVisibility = () => {
      if (document.hidden) {
        cancelAnimationFrame(raf);
        raf = 0;
      } else if (!raf && !reduced) {
        last = performance.now();
        raf = requestAnimationFrame(frame);
      }
    };

    resize();
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", onVisibility);

    if (reduced) {
      // One static frame — respect users who opt out of motion.
      drawRef.current({ ctx, width, height, time: 0, dt: 0 }, state as S);
    } else {
      raf = requestAnimationFrame(frame);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [resetOnResize]);

  return canvasRef;
}

/** Reads a CSS custom property off :root-scoped theme element. */
export function cssVar(name: string, fallback = ""): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}
