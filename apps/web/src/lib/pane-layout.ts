// Layout math for the split pane. Pure module: no DOM or React
// imports, so the window-splitter behavior stays unit-testable.

import { clampPaneRatio } from "@/lib/pane-state";

// Below this viewport width the pane overlays instead of splitting.
export const PANE_OVERLAY_BREAKPOINT = 1024;

// Arrow-key travel per press in px; Shift multiplies. Same magnitudes
// as the SDK's internal ResizableSeparator.
export const PANE_KEYBOARD_STEP = 16;
export const PANE_KEYBOARD_STEP_LARGE = 64;

export function isPaneOverlayViewport(viewportWidth: number): boolean {
  // 0 means unmeasured (SSR): treat it as a desktop split.
  return viewportWidth > 0 && viewportWidth < PANE_OVERLAY_BREAKPOINT;
}

// Pointer -> raw pick; layout-time clamp keeps narrow screens harmless.
export function paneRatioFromPointer(
  clientX: number,
  containerLeft: number,
  containerWidth: number,
): number {
  if (
    !Number.isFinite(clientX) ||
    !Number.isFinite(containerLeft) ||
    !Number.isFinite(containerWidth) ||
    containerWidth <= 0
  ) {
    return Number.NaN;
  }
  return (containerLeft + containerWidth - clientX) / containerWidth;
}

// Delta is pane width, not separator travel: ArrowLeft widens a
// right-docked pane. +-Infinity are the raw bounds; floors apply later.
export function paneRatioAfterStep(
  ratio: number,
  paneDeltaPx: number,
  containerWidth: number,
): number {
  if (paneDeltaPx === Number.POSITIVE_INFINITY) return 1;
  if (paneDeltaPx === Number.NEGATIVE_INFINITY) return 0;
  if (
    !Number.isFinite(ratio) ||
    !Number.isFinite(containerWidth) ||
    containerWidth <= 0
  ) {
    return ratio;
  }
  return ratio + paneDeltaPx / containerWidth;
}

export type PaneAriaValues = { now: number; min: number; max: number };

// Percent of container width, mirroring the SDK's ResizeAriaValues.
export function paneAriaValues(
  ratio: number,
  containerWidth: number,
): PaneAriaValues | null {
  if (!Number.isFinite(containerWidth) || containerWidth <= 0) return null;
  return {
    now: Math.round(clampPaneRatio(ratio, containerWidth) * 100),
    min: Math.round(clampPaneRatio(0, containerWidth) * 100),
    max: Math.round(clampPaneRatio(1, containerWidth) * 100),
  };
}
