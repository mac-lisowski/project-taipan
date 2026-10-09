"use client";

// The pane's single React state owner. pane-state.ts stays pure; this
// module holds the useState plus the mount-time URL restore and binds
// the pure transitions to the account's roles. One provider wraps the
// chat surface so the pane shell and later entry points share it.

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from "react";

import {
  closePane,
  initialPaneState,
  navigatePaneView,
  openPane,
  paneBack,
  selectPaneDetail,
  setPaneRatio,
  type PaneContent,
  type PaneState,
} from "@/lib/pane-state";
import { PANE_PARAM, restorePaneState, serializePaneParam } from "@/lib/pane-url";

// Named writes for header controls and entry points; each maps to one
// pure pane-state transition with the roles bound in.
export type PaneActions = {
  open: (target?: PaneContent | null) => void;
  close: () => void;
  navigateView: (viewPath: string, detailId?: number | null) => void;
  selectDetail: (detailId: number | null) => void;
  back: () => void;
  setRatio: (ratio: number) => void;
};

export type PaneStore = {
  state: PaneState;
  // Raw setter so pane-hosted surfaces (PaneNavProvider in ticket 05)
  // can bind their own writes.
  dispatch: Dispatch<SetStateAction<PaneState>>;
  actions: PaneActions;
};

const PaneContext = createContext<PaneStore | null>(null);

export function PaneStateProvider({
  systemRoles,
  children,
}: {
  systemRoles: string[];
  children: ReactNode;
}): ReactNode {
  // SSR and hydration must render the same closed pane; the URL read
  // waits for a mount effect because window is absent on the server.
  const [state, setState] = useState<PaneState>(initialPaneState);
  const restored = useRef(false);
  useEffect(() => {
    if (restored.current) return;
    restored.current = true;
    setState(
      restorePaneState(
        window.location.search,
        window.location.pathname,
        systemRoles,
      ),
    );
  }, [systemRoles]);

  // URL owns pane state; write it back on every change after mount.
  useEffect(() => {
    if (!restored.current) return;
    const params = new URLSearchParams(window.location.search);
    const value = serializePaneParam(state);
    if (value === null) params.delete(PANE_PARAM);
    else params.set(PANE_PARAM, value);
    const query = params.toString();
    const target =
      window.location.pathname + (query === "" ? "" : `?${query}`);
    if (target !== window.location.pathname + window.location.search) {
      window.history.replaceState(null, "", target);
    }
  }, [state]);

  const actions = useMemo<PaneActions>(
    () => ({
      open: (target) =>
        setState((s) => openPane(s, target ?? null, systemRoles)),
      close: () => setState(closePane),
      navigateView: (viewPath, detailId) =>
        setState((s) =>
          navigatePaneView(s, viewPath, systemRoles, detailId ?? null),
        ),
      selectDetail: (detailId) =>
        setState((s) => selectPaneDetail(s, detailId)),
      back: () => setState(paneBack),
      setRatio: (ratio) => setState((s) => setPaneRatio(s, ratio)),
    }),
    [systemRoles],
  );

  const value = useMemo<PaneStore>(
    () => ({ state, dispatch: setState, actions }),
    [state, actions],
  );
  return <PaneContext.Provider value={value}>{children}</PaneContext.Provider>;
}

export function usePaneStore(): PaneStore {
  const store = useContext(PaneContext);
  if (store === null) {
    throw new Error("usePaneStore used outside PaneStateProvider");
  }
  return store;
}

export function usePaneState(): PaneState {
  return usePaneStore().state;
}

export function usePaneActions(): PaneActions {
  return usePaneStore().actions;
}
