// Shared seam helpers for the upstream-proxy tests. Not a test file
// itself; the vitest default include only matches *.test.ts.

export const UPSTREAM = "http://upstream.test";

export type RecordedCall = { url: string; init: RequestInit & { duplex?: unknown } };

export function request(path: string, init?: RequestInit): Request {
  return new Request(`http://web.test${path}`, init);
}

// Records what the module sends upstream and answers with a crafted
// upstream response; never touches the network.
export function recordingFetch(
  upstream: () => Response = () => Response.json({ ok: true }),
): { fetchImpl: typeof fetch; calls: RecordedCall[] } {
  const calls: RecordedCall[] = [];
  const fetchImpl = ((url: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: String(url), init: init ?? {} });
    return Promise.resolve(upstream());
  }) as typeof fetch;
  return { fetchImpl, calls };
}

export function requireCall(calls: RecordedCall[]): RecordedCall {
  const call = calls[0];
  if (!call) throw new Error("upstream fetch was not called");
  return call;
}
