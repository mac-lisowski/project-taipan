import { expect, test } from "vitest";
import { proxyUpstream } from "./upstream-proxy";
import {
  UPSTREAM,
  request,
  recordingFetch,
} from "./upstream-proxy.testsupport";

// Response-side policy: the module must return the final
// browser-facing Response built from the upstream one.

test("host-binds set-cookie and preserves order and count", async () => {
  const { fetchImpl } = recordingFetch(() => {
    const res = new Response(null, { status: 200, headers: { "x-keep": "y" } });
    res.headers.append("set-cookie", "a=1; Path=/; Domain=api.internal");
    res.headers.append("set-cookie", "b=2; Path=/; Secure");
    return res;
  });
  const res = await proxyUpstream(request("/api/things"), {
    upstreamUrl: UPSTREAM,
    fetchImpl,
  });
  // Domain would be wrong on the public origin; the rest survives.
  expect(res.headers.getSetCookie()).toEqual([
    "a=1; Path=/",
    "b=2; Path=/; Secure",
  ]);
  expect(res.headers.get("x-keep")).toBe("y");
});

test("rewrites a same-origin location to the public origin", async () => {
  const { fetchImpl } = recordingFetch(
    () =>
      new Response(null, {
        status: 302,
        headers: { location: `${UPSTREAM}/login?next=/x#frag` },
      }),
  );
  const res = await proxyUpstream(request("/api/things"), {
    upstreamUrl: UPSTREAM,
    publicOrigin: "https://pub.example",
    fetchImpl,
  });
  expect(res.headers.get("location")).toBe(
    "https://pub.example/login?next=/x#frag",
  );
});

test("leaves a foreign-origin location untouched", async () => {
  const foreign = "https://other.test/away?x=1";
  const { fetchImpl } = recordingFetch(
    () => new Response(null, { status: 302, headers: { location: foreign } }),
  );
  const res = await proxyUpstream(request("/api/things"), {
    upstreamUrl: UPSTREAM,
    publicOrigin: "https://pub.example",
    fetchImpl,
  });
  expect(res.headers.get("location")).toBe(foreign);
});

test("rewrites a same-origin content-location like location", async () => {
  const { fetchImpl } = recordingFetch(
    () =>
      new Response(null, {
        status: 200,
        headers: { "content-location": `${UPSTREAM}/res/1` },
      }),
  );
  const res = await proxyUpstream(request("/api/things"), {
    upstreamUrl: UPSTREAM,
    publicOrigin: "https://pub.example",
    fetchImpl,
  });
  expect(res.headers.get("content-location")).toBe(
    "https://pub.example/res/1",
  );
});

test("drops the response drop-list headers downstream", async () => {
  const { fetchImpl } = recordingFetch(() => {
    const res = new Response("body", {
      status: 200,
      headers: { "x-keep": "y" },
    });
    res.headers.set("server", "uvicorn");
    res.headers.set("x-powered-by", "FastAPI");
    res.headers.set("content-length", "4");
    res.headers.set("content-encoding", "gzip");
    return res;
  });
  const res = await proxyUpstream(request("/api/things"), {
    upstreamUrl: UPSTREAM,
    fetchImpl,
  });
  expect(res.headers.get("server")).toBeNull();
  expect(res.headers.get("x-powered-by")).toBeNull();
  expect(res.headers.get("content-length")).toBeNull();
  expect(res.headers.get("content-encoding")).toBeNull();
  // Ordinary end-to-end headers still pass through.
  expect(res.headers.get("x-keep")).toBe("y");
});

test("drops the body for no-body statuses", async () => {
  for (const status of [204, 205, 304]) {
    const { fetchImpl } = recordingFetch(() => {
      // Response forbids a body on these statuses, but the wire can deliver one; force the status so the seam sees a body.
      const res = new Response("x", { status: 200 });
      return Object.defineProperty(res, "status", { value: status });
    });
    const res = await proxyUpstream(request("/api/things"), {
      upstreamUrl: UPSTREAM,
      fetchImpl,
    });
    expect(res.status).toBe(status);
    await expect(res.text()).resolves.toBe("");
    expect(res.body).toBeNull();
  }
});

test("passes the upstream status through verbatim", async () => {
  for (const status of [201, 404]) {
    const { fetchImpl } = recordingFetch(() =>
      Response.json({ ok: false }, { status }),
    );
    const res = await proxyUpstream(request("/api/things"), {
      upstreamUrl: UPSTREAM,
      fetchImpl,
    });
    expect(res.status).toBe(status);
    await expect(res.json()).resolves.toEqual({ ok: false });
  }
});
