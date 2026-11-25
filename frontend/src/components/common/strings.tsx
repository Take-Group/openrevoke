"use client";

import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

/**
 * Where the bundle runs. Every value is a share of the box: `from` and `to` are the y of the
 * first and last string at the left and right edge, `waist` is where the strings come together
 * (x, y) and `spread` how far apart they stay there.
 */
export interface StringsShape {
  from: [number, number];
  to: [number, number];
  waist: [number, number];
  spread: number;
}

/** Strings come down from the left, gather low in the middle (under a centred card) and rise to the right. */
export const STRINGS_SWEEP: StringsShape = { from: [0.06, 0.5], to: [0.46, 0.7], waist: [0.44, 0.94], spread: 0.035 };
/** A flatter band across a wide, low box (a card or a banner). */
export const STRINGS_BAND: StringsShape = { from: [0.0, 0.7], to: [0.35, 1.0], waist: [0.62, 0.62], spread: 0.12 };

interface StringsProps {
  shape?: StringsShape;
  /** Number of strings. */
  count?: number;
  /** Opacity of the strongest string, 0-1. The colour is the text colour (`text-*` on `className`). */
  intensity?: number;
  className?: string;
}

/**
 * The Open Revoke pattern: a bundle of thin strings that sway slowly, in the text colour, fading
 * out at both ends. Decoration only: absolutely positioned, behind content, no pointer events.
 * The animation runs only while the box is on screen and the tab is visible; with
 * `prefers-reduced-motion` it draws one still frame.
 */
export function Strings({ shape = STRINGS_SWEEP, count = 16, intensity = 0.22, className }: StringsProps) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let width = 0;
    let height = 0;
    let frame = 0;
    let visible = true;

    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };

    const draw = (time: number) => {
      context.clearRect(0, 0, width, height);
      const rgb = getComputedStyle(canvas).color.match(/\d+(\.\d+)?/g)?.slice(0, 3).join(", ") ?? "0, 0, 0";
      const seconds = time / 1000;
      for (let index = 0; index < count; index += 1) {
        const t = count === 1 ? 0.5 : index / (count - 1);
        const sway = Math.sin(seconds * 0.35 + index * 0.45);
        const drift = Math.sin(seconds * 0.22 + index * 0.3 + 1.3);
        const startY = (shape.from[0] + (shape.from[1] - shape.from[0]) * t) * height;
        const endY = (shape.to[0] + (shape.to[1] - shape.to[0]) * t) * height;
        const waistX = shape.waist[0] * width;
        const waistY = (shape.waist[1] + (t - 0.5) * shape.spread) * height;
        const lift = height * 0.06;

        const gradient = context.createLinearGradient(0, 0, width, 0);
        // The middle strings are the strongest; every string fades out at both ends.
        const alpha = intensity * (0.45 + 0.55 * (1 - Math.abs(t - 0.5) * 2));
        gradient.addColorStop(0, `rgba(${rgb}, 0)`);
        gradient.addColorStop(0.2, `rgba(${rgb}, ${alpha * 0.8})`);
        gradient.addColorStop(0.65, `rgba(${rgb}, ${alpha})`);
        gradient.addColorStop(1, `rgba(${rgb}, 0)`);

        // Two S-curves with level tangents at the ends and at the waist: strings flow, not fan out.
        const left = -width * 0.05;
        const right = width * 1.05;
        context.beginPath();
        context.moveTo(left, startY);
        context.bezierCurveTo(
          left + (waistX - left) * 0.5,
          startY + sway * lift,
          left + (waistX - left) * 0.55,
          waistY + drift * lift * 0.5,
          waistX,
          waistY,
        );
        context.bezierCurveTo(
          waistX + (right - waistX) * 0.45,
          waistY - drift * lift * 0.5,
          waistX + (right - waistX) * 0.5,
          endY - sway * lift,
          right,
          endY,
        );
        context.strokeStyle = gradient;
        context.lineWidth = 1;
        context.stroke();
      }
    };

    const loop = (time: number) => {
      draw(time);
      frame = visible && !document.hidden ? requestAnimationFrame(loop) : 0;
    };
    const start = () => {
      if (still) draw(0);
      else if (!frame) frame = requestAnimationFrame(loop);
    };

    resize();
    start();
    const sizes = new ResizeObserver(() => {
      resize();
      if (still) draw(0);
    });
    sizes.observe(canvas);
    const onScreen = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) start();
    });
    onScreen.observe(canvas);
    const onTab = () => !document.hidden && start();
    document.addEventListener("visibilitychange", onTab);
    // A theme switch changes the text colour: redraw the still frame.
    const theme = new MutationObserver(() => still && draw(0));
    theme.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

    return () => {
      cancelAnimationFrame(frame);
      sizes.disconnect();
      onScreen.disconnect();
      theme.disconnect();
      document.removeEventListener("visibilitychange", onTab);
    };
  }, [shape, count, intensity]);

  return (
    <canvas
      ref={ref}
      aria-hidden
      className={cn("pointer-events-none absolute inset-0 size-full text-foreground", className)}
    />
  );
}
