import { describe, expect, it } from "vitest";

import { safeNextPath } from "@/lib/return-path";

describe("safeNextPath", () => {
  it("accepts absolute internal paths with query", () => {
    expect(safeNextPath("/chat")).toBe("/chat");
    expect(safeNextPath("/users?pane=view%3A%2Fusers")).toBe(
      "/users?pane=view%3A%2Fusers",
    );
  });

  it("rejects non-paths and open-redirect shapes", () => {
    for (const raw of [
      undefined,
      "",
      "https://evil.example",
      "//evil.example",
      "/\\evil",
      "relative",
      "/\tpane=chat",
    ]) {
      expect(safeNextPath(raw), String(raw)).toBeNull();
    }
  });

  it("takes the first value of a repeated param", () => {
    expect(safeNextPath(["/chat", "/users"])).toBe("/chat");
  });
});
