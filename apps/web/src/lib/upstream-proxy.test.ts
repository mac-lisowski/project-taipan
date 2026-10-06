import { expect, test, vi } from "vitest";
import { proxyUpstream } from "./upstream-proxy";
import {
  UPSTREAM,
  type RecordedCall,
  request,
  recordingFetch,
  requireCall,
} from "./upstream-proxy.testsupport";

function requireHeaders(calls: RecordedCall[]): Headers {
  const headers = requireCall(calls).init.headers;
  if (!(headers instanceof Headers)) {
    throw new Error("upstream fetch was not called with Headers");
  }
  return headers;
}

test("strips client-supplied forwarding headers upstream", async () => {
  const { fetchImpl, calls } = recordingFetch();
  const res = await proxyUpstream(
    request("/api/things", {
      headers: {
        host: "web.test",
        forwarded: "for=1.2.3.4",
        via: "1.1 evil",
        "x-real-ip": "1.2.3.4",
        "x-forwarded-for": "1.2.3.4",
        "x-forwarded-host": "evil.test",
        "x-forwarded-port": "1337",
        "x-forwarded-proto": "https",
        "x-forwarded-scheme": "https",
        "x-forwarded-server": "evil",
        "x-forwarded-ssl": "on",
      },
    }),
    { upstreamUrl: UPSTREAM, fetchImpl },
  );
  expect(res.status).toBe(200);
  const headers = requireHeaders(calls);
  expect(headers.get("forwarded")).toBeNull();
  expect(headers.get("via")).toBeNull();
  expect(headers.get("x-real-ip")).toBeNull();
  expect(headers.get("x-forwarded-for")).toBeNull();
  expect(headers.get("x-forwarded-port")).toBeNull();
  expect(headers.get("x-forwarded-scheme")).toBeNull();
  expect(headers.get("x-forwarded-server")).toBeNull();
  expect(headers.get("x-forwarded-ssl")).toBeNull();
  // Rebuilt from trusted values below, so the spoofed ones never pass.
  expect(headers.get("x-forwarded-host")).toBe("web.test");
  expect(headers.get("x-forwarded-proto")).toBe("http");
});

test("drops hop-by-hop and connection-listed headers upstream", async () => {
  const { fetchImpl, calls } = recordingFetch();
  await proxyUpstream(
    request("/api/things", {
      headers: {
        connection: "keep-alive, x-custom-tag",
        "keep-alive": "timeout=5",
        "x-custom-tag": "v",
        accept: "application/json",
      },
    }),
    { upstreamUrl: UPSTREAM, fetchImpl },
  );
  const headers = requireHeaders(calls);
  expect(headers.get("connection")).toBeNull();
  expect(headers.get("keep-alive")).toBeNull();
  expect(headers.get("x-custom-tag")).toBeNull();
  // Ordinary end-to-end headers still pass through.
  expect(headers.get("accept")).toBe("application/json");
});

test("rebuilds forwarding headers from trusted values", async () => {
  const { fetchImpl, calls } = recordingFetch();
  await proxyUpstream(request("/api/things", { headers: { host: "web.test" } }), {
    upstreamUrl: UPSTREAM,
    publicOrigin: "https://pub.example",
    fetchImpl,
  });
  const headers = requireHeaders(calls);
  expect(headers.get("x-forwarded-host")).toBe("web.test");
  expect(headers.get("x-forwarded-proto")).toBe("https");
});

test("drops content-length and accept-encoding upstream", async () => {
  const { fetchImpl, calls } = recordingFetch();
  await proxyUpstream(
    request("/api/things", {
      method: "POST",
      body: "x",
      headers: {
        "content-length": "1",
        "accept-encoding": "gzip",
        accept: "application/json",
      },
    }),
    { upstreamUrl: UPSTREAM, fetchImpl },
  );
  const headers = requireHeaders(calls);
  expect(headers.get("content-length")).toBeNull();
  expect(headers.get("accept-encoding")).toBeNull();
  // Ordinary end-to-end headers still pass through.
  expect(headers.get("accept")).toBe("application/json");
});

test("re-encodes segments so encoded separators cannot reshape the path", async () => {
  const { fetchImpl, calls } = recordingFetch();
  await proxyUpstream(request("/api/items/a%2Fb?x=1"), {
    upstreamUrl: UPSTREAM,
    fetchImpl,
  });
  expect(requireCall(calls).url).toBe(`${UPSTREAM}/api/items/a%2Fb?x=1`);
});

// A no-op passthrough also emits a%2Fb; only the decode-then-encode round-trip turns a+b into a%2Bb.
test("re-encodes a plus segment to its percent form upstream", async () => {
  const { fetchImpl, calls } = recordingFetch();
  await proxyUpstream(request("/api/items/a+b?x=1"), {
    upstreamUrl: UPSTREAM,
    fetchImpl,
  });
  expect(requireCall(calls).url).toBe(`${UPSTREAM}/api/items/a%2Bb?x=1`);
});

test("returns 400 and never fetches for a backslash segment", async () => {
  const { fetchImpl, calls } = recordingFetch();
  for (const path of ["/api/%5C", "/api/a%5Cb"]) {
    const res = await proxyUpstream(request(path), {
      upstreamUrl: UPSTREAM,
      fetchImpl,
    });
    expect(res.status).toBe(400);
    await expect(res.json()).resolves.toEqual({ detail: "invalid path" });
  }
  expect(calls).toHaveLength(0);
});

test("maps an upstream fetch failure to a 502", async () => {
  const fetchImpl = (async () => {
    throw new TypeError("connection refused");
  }) as typeof fetch;
  const res = await proxyUpstream(request("/api/things"), {
    upstreamUrl: UPSTREAM,
    fetchImpl,
  });
  expect(res.status).toBe(502);
  await expect(res.json()).resolves.toEqual({ detail: "upstream unavailable" });
});

// A bad config is a proxy bug, not an upstream failure: it must throw,
// not hide behind a 502 body.
test("a construction error propagates instead of surfacing as 502", async () => {
  const { fetchImpl, calls } = recordingFetch();
  await expect(
    proxyUpstream(request("/api/things"), {
      upstreamUrl: UPSTREAM,
      publicOrigin: "http://[bad",
      fetchImpl,
    }),
  ).rejects.toThrow(TypeError);
  expect(calls).toHaveLength(0);
});

test("forwards method and streaming body with manual redirects", async () => {
  const { fetchImpl, calls } = recordingFetch();
  const source = request("/api/things", { method: "POST", body: "payload" });
  await proxyUpstream(source, { upstreamUrl: UPSTREAM, fetchImpl });
  const { init } = requireCall(calls);
  expect(init.method).toBe("POST");
  expect(init.body).toBe(source.body);
  expect(init.redirect).toBe("manual");
  expect(init.duplex).toBe("half");
});

test("sends no body for GET", async () => {
  const { fetchImpl, calls } = recordingFetch();
  await proxyUpstream(request("/api/things"), {
    upstreamUrl: UPSTREAM,
    fetchImpl,
  });
  const { init } = requireCall(calls);
  expect(init.method).toBe("GET");
  expect(init.body).toBeUndefined();
});

// AbortSignal.timeout bypasses fake timers on this Node, so real timers with a short budget stay fast and stable.
test("aborts the upstream fetch after timeoutMs", async () => {
  let signal: AbortSignal | undefined;
  const fetchImpl = ((_url: string | URL | Request, init?: RequestInit) => {
    signal = init?.signal ?? undefined;
    return new Promise<Response>((_resolve, reject) => {
      signal?.addEventListener("abort", () => reject(new Error("aborted")));
    });
  }) as typeof fetch;
  const pending = proxyUpstream(request("/api/things"), {
    upstreamUrl: UPSTREAM,
    timeoutMs: 50,
    fetchImpl,
  });
  expect(signal?.aborted).toBe(false);
  await vi.waitFor(() => expect(signal?.aborted).toBe(true), {
    timeout: 2_000,
    interval: 10,
  });
  // The abort surfaces as a fetch rejection, which maps to a 502.
  const res = await pending;
  expect(res.status).toBe(502);
});
