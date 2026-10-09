"use client";

// The split pane: a non-slot child of <AgentInterface>, so the SDK
// renders it inside slots.rest as a permanent flex sibling of the
// thread region (verified in @openuidev/react-ui 0.17.0
// dist/index.mjs extractSlots). It never remounts on navigation or
// thread switch; close hides it without unmounting so ticket 05's
// pane chat keeps a running reply alive.

import { ArrowLeft, X } from "lucide-react";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type PointerEvent,
  type ReactNode,
} from "react";

import { clampPaneRatio, paneAllows } from "@/lib/pane-state";
import { usePaneStore } from "@/lib/pane-state-context";
import {
  isPaneOverlayViewport,
  PANE_KEYBOARD_STEP,
  PANE_KEYBOARD_STEP_LARGE,
  paneAriaValues,
  paneRatioAfterStep,
  paneRatioFromPointer,
  type PaneAriaValues,
} from "@/lib/pane-layout";
import { cn } from "@/ui";

const PANE_ID = "taipan-pane";

function subscribeViewport(onChange: () => void): () => void {
  window.addEventListener("resize", onChange);
  return () => window.removeEventListener("resize", onChange);
}

// 0 until the client measures: SSR renders the split, never the overlay.
function useViewportWidth(): number {
  return useSyncExternalStore(
    subscribeViewport,
    () => window.innerWidth,
    () => 0,
  );
}

// The pane's parent element is the SDK root container (width:100dvw);
// measuring it keeps the floors right if the SDK ever adds gutters.
function useContainerWidth(paneEl: HTMLElement | null): number {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const parent = paneEl?.parentElement ?? null;
    if (parent === null) return;
    const measure = (): void =>
      setWidth(parent.getBoundingClientRect().width);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(parent);
    return () => observer.disconnect();
  }, [paneEl]);
  return width;
}

// WAI-ARIA window-splitter, modeled on the SDK's internal
// ResizableSeparator which is not exported (dist/index.mjs:4744).
function PaneSeparator({
  ratio,
  containerWidth,
  getContainerRect,
  onRatio,
  controlsId,
}: {
  ratio: number;
  containerWidth: number;
  getContainerRect: () => DOMRect | null;
  onRatio: (ratio: number) => void;
  controlsId: string;
}): ReactNode {
  const [aria, setAria] = useState<PaneAriaValues | null>(null);
  const syncAria = useCallback(
    () => setAria(paneAriaValues(ratio, containerWidth)),
    [ratio, containerWidth],
  );

  const endDrag = (e: PointerEvent<HTMLDivElement>): void => {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    e.currentTarget.releasePointerCapture(e.pointerId);
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    syncAria();
  };

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize pane"
      aria-controls={controlsId}
      aria-valuenow={aria?.now}
      aria-valuemin={aria?.min}
      aria-valuemax={aria?.max}
      aria-valuetext={aria === null ? undefined : `${aria.now}%`}
      tabIndex={0}
      className="taipan-pane-separator"
      onPointerDown={(e) => {
        if (e.button !== 0) return;
        e.currentTarget.setPointerCapture(e.pointerId);
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
      }}
      onPointerMove={(e) => {
        if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
        const rect = getContainerRect();
        if (rect === null) return;
        const next = paneRatioFromPointer(e.clientX, rect.left, rect.width);
        // The drag writes the raw pick; floors apply at layout time.
        if (Number.isFinite(next)) onRatio(next);
      }}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onKeyDown={(e) => {
        const step = e.shiftKey ? PANE_KEYBOARD_STEP_LARGE : PANE_KEYBOARD_STEP;
        let delta: number;
        switch (e.key) {
          case "ArrowLeft":
            delta = step; // right-docked pane: a leftward separator widens it
            break;
          case "ArrowRight":
            delta = -step;
            break;
          case "Home":
            delta = Number.NEGATIVE_INFINITY;
            break;
          case "End":
            delta = Number.POSITIVE_INFINITY;
            break;
          default:
            return;
        }
        e.preventDefault();
        onRatio(paneRatioAfterStep(ratio, delta, containerWidth));
        syncAria();
      }}
      onFocus={syncAria}
    >
      <div className="taipan-pane-separator__handle" />
    </div>
  );
}

export function SplitPane(): ReactNode {
  const { state, actions } = usePaneStore();
  const overlay = isPaneOverlayViewport(useViewportWidth());
  const [paneEl, setPaneEl] = useState<HTMLElement | null>(null);
  const containerWidth = useContainerWidth(paneEl);
  const getContainerRect = useCallback(
    () => paneEl?.parentElement?.getBoundingClientRect() ?? null,
    [paneEl],
  );

  // Overlay Escape dismisses; split mode keeps Escape for the views.
  useEffect(() => {
    if (!state.open || !overlay) return;
    const onKeyDown = (e: KeyboardEvent): void => {
      if (e.key === "Escape") actions.close();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [state.open, overlay, actions]);

  // Focus moves into the overlay on open and back to the invoker on
  // close; split mode leaves focus where the user put it.
  const invokerRef = useRef<HTMLElement | null>(null);
  const wasOpenRef = useRef(state.open);
  useEffect(() => {
    const wasOpen = wasOpenRef.current;
    wasOpenRef.current = state.open;
    if (state.open && overlay && paneEl !== null && !paneEl.contains(document.activeElement)) {
      invokerRef.current =
        document.activeElement instanceof HTMLElement
          ? document.activeElement
          : null;
      paneEl.focus();
      return;
    }
    if (!state.open && wasOpen) {
      invokerRef.current?.focus();
      invokerRef.current = null;
    }
  }, [state.open, overlay, paneEl]);

  // Lazy mount: nothing renders before the first open, and after it the
  // subtree only toggles hidden so mounted contents survive close.
  const [openedOnce, setOpenedOnce] = useState(state.open);
  if (state.open && !openedOnce) setOpenedOnce(true); // sticky flag; render-phase set is the documented pattern
  if (!openedOnce) return null;

  const basis = `${clampPaneRatio(state.ratio, containerWidth) * 100}%`;
  const title = state.kind === "chat" ? "chat" : (state.viewPath ?? "pane");

  return (
    <>
      {state.open && !overlay && (
        <PaneSeparator
          ratio={state.ratio}
          containerWidth={containerWidth}
          getContainerRect={getContainerRect}
          onRatio={actions.setRatio}
          controlsId={PANE_ID}
        />
      )}
      <aside
        id={PANE_ID}
        ref={setPaneEl}
        aria-label="Pane"
        tabIndex={-1}
        hidden={!state.open}
        className={cn("taipan-pane", overlay && "taipan-pane--overlay")}
        style={overlay ? undefined : { flexBasis: basis }}
      >
        <div className="taipan-pane__header">
          <button
            type="button"
            className="taipan-pane__header-button"
            aria-label="Pane back"
            disabled={!paneAllows(state, "back")}
            onClick={actions.back}
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="taipan-pane__title">{title}</div>
          <button
            type="button"
            className="taipan-pane__header-button"
            aria-label="Close pane"
            onClick={actions.close}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="taipan-pane__body">Pane contents land in ticket 05.</div>
      </aside>
    </>
  );
}
