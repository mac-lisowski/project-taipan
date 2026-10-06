"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { cn } from "cn";
import { Panel, PanelHeader } from "./panel";

// Live step-line chart on a 2d canvas. values is a sliding window; the
// newest point blinks. Zero deps, matches the dither backdrop's register.
export function Sparkline({
  label,
  values,
  unit,
  className,
}: {
  label: string;
  values: readonly number[];
  unit?: string | undefined;
  className?: string;
}): ReactNode {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const max = Math.max(...values, 1);
    const min = Math.min(...values, 0);
    const range = Math.max(max - min, 1e-6);
    const stepX = w / Math.max(values.length - 1, 1);
    const y = (v: number) => h - 4 - ((v - min) / range) * (h - 8);

    // Baseline grid: 3 dim rows.
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.lineWidth = 1;
    for (const gy of [0.25, 0.5, 0.75]) {
      ctx.beginPath();
      ctx.moveTo(0, h * gy);
      ctx.lineTo(w, h * gy);
      ctx.stroke();
    }

    ctx.strokeStyle = "rgba(255,255,255,0.9)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    values.forEach((v, i) => {
      const x = i * stepX;
      if (i === 0) ctx.moveTo(x, y(v));
      else {
        ctx.lineTo(x, y(values[i - 1] ?? v));
        ctx.lineTo(x, y(v));
      }
    });
    ctx.stroke();

    // Newest point carries the signal color (resolved from the token).
    const last = values[values.length - 1] ?? 0;
    ctx.fillStyle =
      getComputedStyle(document.documentElement).getPropertyValue("--signal").trim() ||
      "#5fd695";
    ctx.fillRect(w - 2, y(last) - 2, 4, 4);
  }, [values]);

  const latest = values[values.length - 1] ?? 0;

  return (
    <Panel className={cn("px-5 py-4", className)}>
      <div className="flex items-baseline justify-between">
        <PanelHeader label={label} />
        <p className="font-mono text-[11px] text-foreground">
          {latest.toFixed(1)}
          {unit !== undefined && <span className="text-muted-foreground"> {unit}</span>}
        </p>
      </div>
      <canvas ref={canvasRef} className="mt-3 h-16 w-full" aria-hidden="true" />
    </Panel>
  );
}
