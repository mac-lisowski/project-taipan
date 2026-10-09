// Client calls to the share endpoints. The threads catch-all forwards
// /api/threads/shares/* upstream, so relative paths keep the session
// cookie on the Next origin.

import { detailOf, getJson } from "./api-result";

type CreateShareResponse = { token?: string };

export async function generateShareLink(
  threadId: string,
  origin: string = window.location.origin,
): Promise<string> {
  const res = await fetch(
    `/api/threads/shares/create/${encodeURIComponent(threadId)}`,
    { method: "POST" },
  );
  // A non-OK response must reject: the SDK modal shows nothing on
  // rejection, which beats showing a link that 404s. Keep the upstream
  // detail line so the console error says why.
  if (!res.ok) throw new Error(`share create failed: ${await detailOf(res)}`);
  const { token } = (await res.json()) as CreateShareResponse;
  if (typeof token !== "string" || token.length === 0) {
    throw new Error("share create returned no token");
  }
  return `${origin}/share/${token}`;
}

export async function revokeShareLink(threadId: string): Promise<boolean> {
  const res = await fetch(
    `/api/threads/shares/delete/${encodeURIComponent(threadId)}`,
    { method: "DELETE" },
  );
  return res.ok;
}

// Owner-scoped share status for one thread. Any failure reads as "not
// shared": the revoke button just stays hidden until a create runs.
export async function getShareStatus(threadId: string): Promise<boolean> {
  const res = await getJson<{ shared?: boolean }>(
    `/api/threads/shares/get/${encodeURIComponent(threadId)}`,
  );
  return res.ok && res.data?.shared === true;
}
