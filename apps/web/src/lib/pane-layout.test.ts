import { describe, expect, it } from "vitest";

import {
  isPaneOverlayViewport,
  PANE_KEYBOARD_STEP,
  PANE_KEYBOARD_STEP_LARGE,
  PANE_OVERLAY_BREAKPOINT,
  paneAriaValues,
  paneRatioAfterStep,
  paneRatioFromPointer,
} from "@/lib/pane-layout";

describe("overlay breakpoint", () => {
  it("splits at and above 1024px, overlays below", () => {
    expect(isPaneOverlayViewport(1600)).toBe(false);
    expect(isPaneOverlayViewport(PANE_OVERLAY_BREAKPOINT)).toBe(false);
    expect(isPaneOverlayViewport(PANE_OVERLAY_BREAKPOINT - 1)).toBe(true);
    expect(isPaneOverlayViewport(320)).toBe(true);
  });

  it("treats an unmeasured viewport as split, never overlay", () => {
    // SSR and the first client read see 0; flipping to overlay there
    // would swap the markup between server and hydration.
    expect(isPaneOverlayViewport(0)).toBe(false);
    expect(isPaneOverlayViewport(Number.NaN)).toBe(false);
  });
});

describe("pointer drag", () => {
  // Pane docks on the right edge: pane width is container right minus x.
  it("maps pointer x to the raw ratio", () => {
    expect(paneRatioFromPointer(800, 0, 1600)).toBeCloseTo(0.5);
    expect(paneRatioFromPointer(1600, 0, 1600)).toBeCloseTo(0);
    expect(paneRatioFromPointer(0, 0, 1600)).toBeCloseTo(1);
  });

  it("honors a container offset", () => {
    // A 1000px container starting at x=100: its right edge is 1100.
    expect(paneRatioFromPointer(600, 100, 1000)).toBeCloseTo(0.5);
  });

  it("returns out-of-range picks unclamped", () => {
    // Dragging past the right edge asks for a sub-zero pane; the state
    // layer clamps the stored pick and layout clamps the floors.
    expect(paneRatioFromPointer(1700, 0, 1600)).toBeLessThan(0);
    expect(paneRatioFromPointer(-100, 0, 1600)).toBeGreaterThan(1);
  });

  it("refuses an unmeasurable container", () => {
    expect(paneRatioFromPointer(800, 0, 0)).toBeNaN();
    expect(paneRatioFromPointer(800, 0, -5)).toBeNaN();
    expect(paneRatioFromPointer(Number.NaN, 0, 1600)).toBeNaN();
  });
});

describe("keyboard step", () => {
  it("steps the pane width in px", () => {
    // ArrowLeft on a right-docked pane passes +step (pane widens).
    expect(paneRatioAfterStep(0.5, PANE_KEYBOARD_STEP, 1600)).toBeCloseTo(0.51);
    expect(paneRatioAfterStep(0.5, -PANE_KEYBOARD_STEP, 1600)).toBeCloseTo(0.49);
    expect(paneRatioAfterStep(0.5, PANE_KEYBOARD_STEP_LARGE, 1600)).toBeCloseTo(0.54);
  });

  it("snaps to the raw bounds on +-Infinity", () => {
    // Home/End dispatch infinities; 0 and 1 let clampPaneRatio land on
    // the pixel floors whatever the container width is.
    expect(paneRatioAfterStep(0.5, Number.NEGATIVE_INFINITY, 1600)).toBe(0);
    expect(paneRatioAfterStep(0.5, Number.POSITIVE_INFINITY, 1600)).toBe(1);
  });

  it("keeps the ratio when the container is unmeasurable", () => {
    expect(paneRatioAfterStep(0.5, PANE_KEYBOARD_STEP, 0)).toBe(0.5);
    expect(paneRatioAfterStep(0.5, PANE_KEYBOARD_STEP, Number.NaN)).toBe(0.5);
  });
});

describe("aria readout", () => {
  it("reports clamped percents of the container", () => {
    // 1600px: pane floor 360px (~23%), max 1600-272-360=968px (~61%).
    expect(paneAriaValues(0.5, 1600)).toEqual({ now: 50, min: 23, max: 61 });
    // An out-of-floor pick reads as the clamped size, not the raw pick.
    expect(paneAriaValues(0.05, 1600)?.now).toBe(23);
    expect(paneAriaValues(0.95, 1600)?.now).toBe(61);
  });

  it("is null when the container is unmeasurable", () => {
    expect(paneAriaValues(0.5, 0)).toBeNull();
    expect(paneAriaValues(0.5, Number.NaN)).toBeNull();
  });
});
