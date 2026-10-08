"use client";

import { useEffect, useReducer } from "react";
import type { ReactNode } from "react";
import { Switch } from "@/ui";
import {
  loadRegistrationSwitch,
  reduceSwitchView,
  setRegistrationSwitch,
  switchValue,
} from "@/lib/system-settings";

// Flip saves at once; the endpoint result is the only source of switch state.
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

  function onToggle(next: boolean) {
    if (enabled === null || busy) return;
    dispatch({ type: "save_started", enabled: next });
    void setRegistrationSwitch(next).then((result) => {
      dispatch({ type: "save_finished", result });
    });
  }

  const stateWord = enabled ? "open" : "closed";
  const stateLabel =
    view.state === "loading"
      ? "loading…"
      : view.state === "saving"
        ? "saving…"
        : stateWord;

  return (
    <div className="flex w-full flex-col gap-3">
      <div className="flex items-center justify-between gap-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground">
          registration
        </p>
        <Switch
          checked={enabled === true}
          onCheckedChange={onToggle}
          disabled={busy || enabled === null}
          aria-label="registration enabled"
        />
      </div>
      <p className="font-mono text-xs">sign up is {stateLabel}</p>
      {view.state === "saved" && (
        <p role="status" className="font-mono text-[10px] tracking-[0.15em] text-emerald-400">
          saved. sign up is {stateWord}.
        </p>
      )}
      {view.state === "error" && (
        <p role="alert" className="font-mono text-[10px] tracking-[0.15em] text-red-400">
          err: {view.message}
        </p>
      )}
    </div>
  );
}
