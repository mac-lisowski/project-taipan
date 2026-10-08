import { apiInternalUrl } from "../env";

export type SharedMessage = {
  // The API never snapshots system rows, so only these two can arrive.
  role: "user" | "assistant";
  // The API stores the OpenAI shape verbatim, so content can be a parts
  // array, not just a string. The page renders a fallback for that.
  content: unknown;
};

export type SharedThread = {
  title: string;
  messages: SharedMessage[];
};

// A dead token and a failed read are different answers: the page 404s
// on the first and shows an error view on the second.
export type SharedThreadResult =
  | { ok: true; data: SharedThread }
  | { ok: false; kind: "not-found" | "upstream-down" };

const ROLES = new Set<string>(["user", "assistant"]);

function isSharedThread(data: unknown): data is SharedThread {
  if (typeof data !== "object" || data === null) return false;
  const t = data as { title?: unknown; messages?: unknown };
  if (typeof t.title !== "string" || !Array.isArray(t.messages)) return false;
  return t.messages.every((m: unknown) => {
    if (typeof m !== "object" || m === null) return false;
    const role = (m as { role?: unknown }).role;
    // Any content type is valid; only the key must be present.
    return typeof role === "string" && ROLES.has(role) && "content" in m;
  });
}

// Server-side read for the share page, no-store so a revoke or expiry
// closes the link on the very next render. The token rides in the path;
// encodeURIComponent keeps any stray escape from reshaping it.
export async function readSharedThread(
  token: string,
): Promise<SharedThreadResult> {
  let res: Response;
  try {
    res = await fetch(
      `${apiInternalUrl()}/api/public/threads/${encodeURIComponent(token)}`,
      { cache: "no-store" },
    );
  } catch {
    return { ok: false, kind: "upstream-down" };
  }
  if (res.status === 404) return { ok: false, kind: "not-found" };
  if (!res.ok) return { ok: false, kind: "upstream-down" };
  const data: unknown = await res.json().catch(() => null);
  if (!isSharedThread(data)) return { ok: false, kind: "upstream-down" };
  return { ok: true, data };
}
