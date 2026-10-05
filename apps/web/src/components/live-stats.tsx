"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Sparkline } from "@/ui";

// A recorded-looking trace beats an honest random walk: fixed base pattern
// with occasional spikes and jitter, advanced every 2.5s. Swap for the
// real telemetry stream when it exists.
const BASE = [
  38, 41, 39, 44, 42, 47, 45, 43, 46, 44, 48, 51, 49, 52, 47, 45, 42, 40,
  43, 46, 44, 41, 39, 42, 45, 49, 74, 71, 52, 48, 45, 47, 44, 42, 46, 50,
  53, 49, 46, 44, 41, 39, 42, 45, 43, 40, 38, 41,
];

export function LiveStats(): ReactNode {
  const cursor = useRef(0);
  const [values, setValues] = useState<number[]>(() => BASE.slice());

  useEffect(() => {
    const timer = setInterval(() => {
      // Updaters must be pure: StrictMode runs them twice. Step the cursor
      // outside setValues.
      cursor.current = (cursor.current + 1) % BASE.length;
      const jitter = (Math.random() - 0.5) * 4;
      const next = Math.round(((BASE[cursor.current] ?? 40) + jitter) * 10) / 10;
      setValues((prev) => [...prev.slice(1), next]);
    }, 2500);
    return () => {
      clearInterval(timer);
    };
  }, []);

  return <Sparkline label="extractions / sec" unit="x/s" values={values} />;
}
