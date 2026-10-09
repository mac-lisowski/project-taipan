"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";

import { paneNavigate, type ShellNavigate } from "@/lib/shell-nav";
import type { PaneState } from "@/lib/pane-state";

// An unwrapped tree degrades to a real page load: the same move the
// views made before this context existed.
const fallbackNav: ShellNavigate = (target) => {
  if (typeof window === "undefined") return;
  if (target.replace === true) window.location.replace(target.path);
  else window.location.assign(target.path);
};

const ShellNavContext = createContext<ShellNavigate>(fallbackNav);

// Each surface hands in its navigate: the main surface delegates to the
// real router, a pane writes pane state.
export function ShellNavProvider({
  navigate,
  children,
}: {
  navigate: ShellNavigate;
  children: ReactNode;
}): ReactNode {
  return (
    <ShellNavContext.Provider value={navigate}>
      {children}
    </ShellNavContext.Provider>
  );
}

// Views call this for internal moves; per-surface providers decide
// whether a call becomes a real navigation or a pane-state write.
export function useShellNavigate(): ShellNavigate {
  return useContext(ShellNavContext);
}

// The pane half: nav calls from views inside the pane become pane-state
// writes through the host's setter. Usable before the pane mounts so
// the provider idiom is ready for ticket 05.
export function PaneNavProvider({
  state,
  systemRoles,
  dispatch,
  children,
}: {
  state: PaneState;
  systemRoles: string[];
  dispatch: (next: PaneState) => void;
  children: ReactNode;
}): ReactNode {
  const navigate = useMemo(
    () => paneNavigate(state, systemRoles, dispatch),
    [state, systemRoles, dispatch],
  );
  return <ShellNavProvider navigate={navigate}>{children}</ShellNavProvider>;
}
