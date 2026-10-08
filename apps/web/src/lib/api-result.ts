export type ApiResult<T = unknown> =
  | { ok: true; data: T }
  | { ok: false; error: string };

// Prefer the API detail line from an upstream error body; else the status.
export async function detailOf(res: Response): Promise<string> {
  const body = (await res.json().catch(() => null)) as {
    detail?: string;
  } | null;
  return body?.detail ?? `request failed (${res.status})`;
}

// One error channel for every failure, so no caller leaks a rejection.
export async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiResult<T>> {
  try {
    // Single-arg GET keeps the one-argument call shape consumer pins assert.
    const res = init === undefined ? await fetch(path) : await fetch(path, init);
    if (res.ok) {
      const data = (await res.json().catch(() => null)) as T;
      return { ok: true, data };
    }
    return { ok: false, error: await detailOf(res) };
  } catch {
    return { ok: false, error: "network error" };
  }
}

export function getJson<T>(path: string): Promise<ApiResult<T>> {
  return requestJson<T>(path);
}

function jsonBody(method: string, payload: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  };
}

export function postJson<T>(path: string, payload: unknown): Promise<ApiResult<T>> {
  return requestJson<T>(path, jsonBody("POST", payload));
}

export function putJson<T>(path: string, payload: unknown): Promise<ApiResult<T>> {
  return requestJson<T>(path, jsonBody("PUT", payload));
}
