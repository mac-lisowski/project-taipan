"use client";

import { useEffect, useReducer } from "react";
import type { FormEvent, ReactNode } from "react";
import { Button } from "@/ui";
import {
  loadRegistrationSwitch,
  reduceSwitchView,
  setRegistrationSwitch,
  switchValue,
} from "@/lib/system-settings";

// Owner control for the sign up switch. Load paints the stored value,
// save paints the outcome; the endpoint result is the only source, so
// the checkbox itself never carries state.
export function RegistrationSwitch(): ReactNode {
  const [view, dispatch] = useReducer(reduceSwitchView, { state: "loading" });

  useEffect(() => {
    let alive = true;
    void loadRegistrationSwitch().then((result) => {
      if (alive) dispatch({ type: "loaded", result });
    });
    return () => {
      alive = false;
    };
  }, []);

  const enabled = switchValue(view);
  const busy = view.state === "loading" || view.state === "saving";

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (enabled === null || busy) return;
    const next = !enabled;
    dispatch({ type: "save_started", enabled: next });
    const result = await setRegistrationSwitch(next);
    dispatch({ type: "save_finished", result });
  }

  const actionLabel =
    enabled === null ? "loading…" : enabled ? "close sign up" : "open sign up";

  return (
    <form onSubmit={onSubmit} className="flex w-full flex-col gap-3">
      <label className="flex items-center gap-3 font-mono text-xs">
        <input
          type="checkbox"
          checked={enabled === true}
          readOnly
          disabled={busy}
          aria-label="registration enabled"
          className="size-4 accent-emerald-400"
        />
        registration {enabled === null ? "…" : enabled ? "open" : "closed"}
      </label>
      <Button
        type="submit"
        disabled={busy || enabled === null}
        className="font-mono text-[11px] uppercase tracking-[0.25em]"
      >
        {view.state === "saving" ? "saving…" : actionLabel}
      </Button>
      {view.state === "saved" && (
        <p role="status" className="font-mono text-[10px] tracking-[0.15em] text-emerald-400">
          saved. sign up is {view.enabled ? "open" : "closed"}.
        </p>
      )}
      {view.state === "error" && (
        <p role="alert" className="font-mono text-[10px] tracking-[0.15em] text-red-400">
          err: {view.message}
        </p>
      )}
    </form>
  );
}
