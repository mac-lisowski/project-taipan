import { describe, expect, it } from "vitest";
import { resolveTrustedOrigin } from "./origin";

describe("resolveTrustedOrigin", () => {
  it("prefers explicitOrigin when provided", () => {
    const req = new Request("http://internal:3000/logout", {
      headers: { host: "internal:3000" },
    });
    expect(resolveTrustedOrigin(req, "https://example.com")).toBe(
      "https://example.com",
    );
  });

  it("falls back to request protocol and trusted Host header", () => {
    const req = new Request("https://myhost:3000/logout", {
      headers: { host: "myhost:3000" },
    });
    expect(resolveTrustedOrigin(req)).toBe("https://myhost:3000");
  });

  it("ignores untrusted x-forwarded headers", () => {
    const req = new Request("http://myhost:3000/logout", {
      headers: {
        host: "myhost:3000",
        "x-forwarded-host": "evil.com",
        "x-forwarded-proto": "https",
      },
    });
    expect(resolveTrustedOrigin(req)).toBe("http://myhost:3000");
  });

  it("falls back to localhost when Host header is missing", () => {
    const req = new Request("http://internal.example/logout");
    req.headers.delete("host");
    expect(resolveTrustedOrigin(req)).toBe("http://localhost");
  });
});
