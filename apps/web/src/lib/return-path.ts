// Login return path (`next` param) shared by the request proxy, the
// session guard, and the public landing page.

// proxy.ts stamps the attempted private URL here; session.ts reads it
// when the account check redirects an unauthenticated visitor.
export const NEXT_HEADER = "x-taipan-next";

// Only same-origin absolute paths survive; protocol-relative (//) and
// backslash/control tricks are rejected so `next` cannot become an
// open redirect.
export function safeNextPath(
  raw: string | string[] | undefined,
): string | null {
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (typeof value !== "string") return null;
  if (!value.startsWith("/") || value.startsWith("//")) return null;
  if (value.includes("\\")) return null;
  for (const ch of value) {
    const code = ch.charCodeAt(0);
    if (code < 0x20 || code > 0x7e) return null;
  }
  return value;
}
