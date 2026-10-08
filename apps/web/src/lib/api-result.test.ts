import { readFileSync } from "node:fs";
import { dirname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getJson, postJson, putJson, requestJson, type ApiResult } from "./api-result";

const libDir = dirname(fileURLToPath(import.meta.url));
const srcDir = resolve(libDir, "..");

// A stubbed fetch must not leak into other test files in the same worker.
afterEach(() => {
  vi.unstubAllGlobals();
});

function stubFetchWith(body: BodyInit | null, status: number) {
  const fetchMock = vi.fn().mockResolvedValue(new Response(body, { status }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("postJson", () => {
  it("sends the payload as JSON to the relative path", async () => {
    const fetchMock = stubFetchWith(null, 200);

    await postJson("/api/auth/register", { email: "a@b.c" });

    expect(fetchMock).toHaveBeenCalledWith("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: '{"email":"a@b.c"}',
    });
  });
});

describe("putJson", () => {
  it("sends the payload as JSON with the PUT method", async () => {
    const fetchMock = stubFetchWith(null, 200);

    await putJson("/api/settings/registration", { enabled: false });

    expect(fetchMock).toHaveBeenCalledWith("/api/settings/registration", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: '{"enabled":false}',
    });
  });
});

describe("getJson", () => {
  it("calls fetch with the path as the only argument", async () => {
    const fetchMock = stubFetchWith(null, 200);

    await getJson("/api/session");

    expect(fetchMock).toHaveBeenCalledWith("/api/session");
  });
});

describe("requestJson paths", () => {
  it("passes the relative path to fetch verbatim, with no origin prefix", async () => {
    const fetchMock = stubFetchWith(null, 200);

    await requestJson("/api/x");

    expect(fetchMock).toHaveBeenCalledWith("/api/x");
  });
});

describe("requestJson error mapping", () => {
  it("surfaces the upstream detail verbatim", async () => {
    stubFetchWith(JSON.stringify({ detail: "weak password" }), 400);
    expect(await requestJson("/api/x")).toEqual({ ok: false, error: "weak password" });
  });

  it("falls back to the status when a JSON body has no detail", async () => {
    stubFetchWith(JSON.stringify({ message: "x" }), 500);
    expect(await requestJson("/api/x")).toEqual({ ok: false, error: "request failed (500)" });
  });

  it("falls back to the status when the error body is not JSON", async () => {
    stubFetchWith("nope", 502);
    expect(await requestJson("/api/x")).toEqual({ ok: false, error: "request failed (502)" });
  });

  it("surfaces an empty detail verbatim instead of the fallback", async () => {
    stubFetchWith(JSON.stringify({ detail: "" }), 400);
    expect(await requestJson("/api/x")).toEqual({ ok: false, error: "" });
  });

  it("folds a thrown fetch into a network error instead of rejecting", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(await requestJson("/api/x")).toEqual({ ok: false, error: "network error" });
  });
});

describe("requestJson success mapping", () => {
  it("carries the parsed JSON body as data", async () => {
    stubFetchWith(JSON.stringify({ token: "t" }), 200);

    const result: ApiResult<{ token: string }> = await requestJson("/api/x");

    expect(result).toEqual({ ok: true, data: { token: "t" } });
  });

  it("returns a null body when the response has none", async () => {
    stubFetchWith(null, 204);
    expect(await requestJson("/api/x")).toEqual({ ok: true, data: null });
  });

  it("returns a null body when the body is invalid JSON, without rejecting", async () => {
    stubFetchWith("garbage", 200);
    expect(await requestJson("/api/x")).toEqual({ ok: true, data: null });
  });
});

describe("layering", () => {
  it("imports nothing from the app directory", () => {
    const source = readFileSync(join(libDir, "api-result.ts"), "utf8");
    const specifiers = [
      ...source.matchAll(/(?:\bfrom\b|\bimport\b)\s*\(?\s*["']([^"']+)["']/g),
    ].flatMap((match) => (match[1] !== undefined ? [match[1]] : []));
    const appRoot = join(srcDir, "app");
    const offenders = specifiers.filter((spec) => {
      const resolved = spec.startsWith("@/")
        ? resolve(srcDir, spec.slice(2))
        : spec.startsWith(".")
          ? resolve(libDir, spec)
          : null;
      return resolved !== null && resolved.startsWith(appRoot + sep);
    });
    expect(offenders).toEqual([]);
  });
});
